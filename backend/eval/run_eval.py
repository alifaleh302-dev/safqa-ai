"""Offline A/B harness for the negotiation prompt.

Runs each prompt variant through the multi-turn scenarios using the REAL
decision engine (so the production instruction + behaviour rules apply), then
scores every produced reply with a second LLM call acting as a judge.

Metrics:
  dialect  - how natural the Sanaani Yemeni dialect is (replies only)
  human    - how human the reply reads (replies only)
  brevity  - short chat-style messages (replies only)
  goal     - drives toward the DM/close (replies only)
  action_acc - did it choose reply vs ignore correctly for the turn
  overall  - blended score (reply quality 50%, goal 20%, action correctness 30%)

Usage (inside the backend container):
    python -m eval.run_eval --out eval/results.json --only v3,v4,v5
"""

import argparse
import asyncio
import json
import re
import statistics
from pathlib import Path

from app.services.engine import decide
from app.services.gemini import GeminiClient, GeminiError

HERE = Path(__file__).resolve().parent
CONCURRENCY = 6

JUDGE_INSTRUCTION = """\
أنت مقيّم خبير في اللهجات العربية وسلوك البشر في المحادثات.

أمامك رسالة أرسلها عميل في مجموعة تليجرام، وردّ كتبه مندوب مبيعات يمني من صنعاء.
قيّم الردّ على ثلاثة محاور، كل محور من 1 إلى 10:

1. dialect: هل الردّ بلهجة يمنية صنعانية طبيعية؟ (10 = لهجة يمنية صريحة وطبيعية،
   1 = فصحى رسمية أو لهجة غير يمنية). علامات يمنية: هسع، شتي، تشتي، وين، وينا،
   ماشي، عاد، ياخي، أبشر، تدلل، حياك، قل لي، عطني، طيب، زين، بس، كذا، خلك، سوّى.
   مخصوم: الفصحى الرسمية (بالطبع، يسعدني، أود أن، كيف يمكنني مساعدتك، أتمنى)،
   الخليجية (وش، أبغى، الحين)، المصرية (عايز، ازاي)، الشامية (شو، بدي، هيك).

2. human: هل يبدو الردّ كأن إنساناً حقيقياً كتبه؟ (10 = طبيعي تماماً،
   1 = آلي/روبوتي/رسمي/قالب جاهز).

3. brevity: هل الردّ قصير مثل رسائل الشات؟ (10 = جملة أو جملتين،
   1 = فقرة طويلة أو قائمة).

أعد ONLY كائن JSON بهذا الشكل:
{"dialect": <int>, "human": <int>, "brevity": <int>, "note": "ملاحظة قصيرة"}
"""

GOAL_JUDGE = """\
عميل يسأل مندوب مبيعات يمني في مجموعة تليجرام. قيّم من 1 إلى 10: هل هذا الردّ
يدفع المحادثة نحو الهدف (أن يراسل العميل على الخاص لإتمام الاتفاق)، دون إلحاح
مزعج ودون كشف أنه بوت؟ 10 = دفع ذكي وطبيعي، 1 = لا يخدم الهدف أو يضرّه.

أعد ONLY: {"goal": <int>}
"""


def action_correct(expect: str, action: str) -> bool:
    replied = action == "reply"
    if expect == "reply":
        return replied
    if expect == "ignore":
        return not replied
    return True  # reply_or_ignore


async def judge_reply(client, client_text: str, reply: str, sem) -> dict:
    async with sem:
        try:
            data = await client.generate_json(
                JUDGE_INSTRUCTION,
                [{"role": "user", "text": f"رسالة العميل: {client_text}\n\nردّ المندوب: {reply}"}],
            )
            goal_data = await client.generate_json(
                GOAL_JUDGE,
                [{"role": "user", "text": f"رسالة العميل: {client_text}\n\nردّ المندوب: {reply}"}],
            )
            return {
                "dialect": int(data.get("dialect", 5)),
                "human": int(data.get("human", 5)),
                "brevity": int(data.get("brevity", 5)),
                "goal": int(goal_data.get("goal", 5)),
                "note": str(data.get("note", ""))[:200],
            }
        except (GeminiError, ValueError, TypeError) as exc:
            return {"dialect": 0, "human": 0, "brevity": 0, "goal": 0, "note": f"judge error: {exc}"}


def _similar(a: str, b: str) -> bool:
    """Cheap near-duplicate check between two replies."""
    norm = lambda s: re.sub(r"[^\w\s]", "", s or "").split()
    ta, tb = norm(a), norm(b)
    if not ta or not tb:
        return False
    seta, setb = set(ta), set(tb)
    return len(seta & setb) / max(1, min(len(seta), len(setb))) > 0.7


async def run_prompt(prompt: dict, scenarios: list[dict], client, sem) -> dict:
    turns_out = []
    for scenario in scenarios:
        history: list[dict] = []
        replies_so_far: list[str] = []
        for turn in scenario["turns"]:
            async with sem:
                try:
                    decision = await decide(
                        prompt["system_text"], history, turn["client"], "عميل",
                        reply_scope="relevant",
                    )
                    reply, action, reason = decision.reply, decision.action, decision.reason
                except GeminiError as exc:
                    reply, action, reason = "", "error", str(exc)

            expected = turn.get("expect", "reply_or_ignore")
            ok = action_correct(expected, action)
            repeated = bool(reply) and any(_similar(reply, r) for r in replies_so_far)

            if reply.strip():
                score = await judge_reply(client, turn["client"], reply, sem)
            else:
                # Correct silence has no text to judge; reward it when expected.
                score = {"dialect": None, "human": None, "brevity": None,
                         "goal": 10 if ok else 2, "note": "ignore"}

            if repeated:
                score["human"] = max(0, (score["human"] if score["human"] is not None else 5) - 4)
                score["note"] = (score["note"] + " | REPEATED").strip(" |")

            turns_out.append({
                "scenario": scenario["id"], "client": turn["client"], "expect": expected,
                "action": action, "reply": reply, "reason": reason,
                "action_ok": ok, "repeated": repeated, "score": score,
            })
            if reply:
                replies_so_far.append(reply)
            history.append({"role": "user", "text": f"عميل: {turn['client']}"})
            if reply:
                history.append({"role": "model", "text": reply})

    def mean_of(axis):
        vals = [t["score"][axis] for t in turns_out if t["score"][axis] is not None]
        return round(statistics.mean(vals), 2) if vals else 0.0

    axes = {a: mean_of(a) for a in ("dialect", "human", "brevity", "goal")}
    action_acc = round(statistics.mean(1.0 if t["action_ok"] else 0.0 for t in turns_out), 3)
    repeats = sum(1 for t in turns_out if t["repeated"])
    reply_quality = statistics.mean([axes[a] for a in ("dialect", "human", "brevity")])
    overall = round(reply_quality * 0.5 + axes["goal"] * 0.2 + action_acc * 10 * 0.3, 2)

    summary = {**axes, "action_acc": action_acc, "repeats": repeats, "overall": overall}
    return {"prompt_id": prompt["id"], "label": prompt["label"], "summary": summary, "turns": turns_out}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(HERE / "results.json"))
    parser.add_argument("--prompts", default=str(HERE / "prompts.json"))
    parser.add_argument("--scenarios", default=str(HERE / "scenarios.json"))
    parser.add_argument("--only", default="", help="comma-separated prompt ids")
    args = parser.parse_args()

    prompts = json.loads(Path(args.prompts).read_text(encoding="utf-8"))["prompts"]
    if args.only:
        wanted = {p.strip() for p in args.only.split(",")}
        prompts = [p for p in prompts if p["id"] in wanted]
    scenarios = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))["scenarios"]

    client = GeminiClient()
    if not client.configured:
        raise SystemExit("GEMINI_API_KEY is not configured")

    sem = asyncio.Semaphore(CONCURRENCY)
    results = []
    for prompt in prompts:
        print(f"running {prompt['id']} ...", flush=True)
        results.append(await run_prompt(prompt, scenarios, client, sem))

    results.sort(key=lambda r: r["summary"]["overall"], reverse=True)
    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== RANKING (overall) ===")
    for r in results:
        s = r["summary"]
        print(
            f"{s['overall']:5.2f}  {r['prompt_id']:20s} act={s['action_acc']:.2f} "
            f"dialect={s['dialect']:.2f} human={s['human']:.2f} "
            f"brev={s['brevity']:.2f} goal={s['goal']:.2f} rep={s['repeats']}  ({r['label']})"
        )
    print(f"\nfull results -> {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
