import json
from dataclasses import dataclass

from .gemini import GeminiClient, GeminiError
from .knowledge import kb

# The model must return strict JSON so the userbot can decide deterministically.
# "escalate" is the safe escape hatch: anything sensitive is handed to a human.
DECISION_INSTRUCTION = """\
You are the decision layer of an autonomous Telegram negotiation agent.

Given the CONVERSATION and the OPERATOR RULES below, decide the next action.

Return ONLY a JSON object with this exact shape:
{
  "action": "reply" | "ignore" | "escalate",
  "reply": "the message text to send, in the client's language, or empty string",
  "reason": "short internal explanation (not sent to the client)"
}

Rules for your own output:
- "reply": you should answer now. Write a natural, human, concise message.
- "ignore": the message is not addressed to us or needs no response.
- "escalate": the request is sensitive, out of policy, a complaint, a price below
  the allowed floor, a legal/refund/commitment matter, or you are unsure.
  For "escalate" set "reply" to a short holding message ONLY if a human reply is
  expected soon; otherwise leave it empty.

Never invent facts, prices, discounts or promises that are not in the OPERATOR RULES.
Mirror the client's language (Arabic or English). Sound like a real person, not a bot:
no corporate tone, no emojis unless the client used them, no bullet lists.
"""

RELEVANCE_RULE = """\

Before deciding, judge whether the message is relevant to our offer.

Add this field to the JSON:
  "relevant": true | false

- "relevant": true when the message is, or plausibly could be, about our product,
  pricing, delivery, ordering, or is otherwise addressed to us.
- "relevant": false when it is unrelated chatter between other members, a plain
  greeting or small talk not aimed at us, spam, forwarded ads, or a topic clearly
  unrelated to what we sell. When "relevant" is false you MUST set "action" to
  "ignore" and "reply" to "".
"""


@dataclass
class Decision:
    action: str
    reply: str
    reason: str


async def decide(
    system_prompt: str,
    history: list[dict],
    latest_text: str,
    sender_name: str,
    reply_scope: str = "relevant",
) -> Decision:
    """Ask Gemini for the next action given the operator's prompt and context.

    ``reply_scope`` controls the relevance gate: "relevant" (default) ignores
    messages unrelated to the offer, "all" answers anything addressed to us.
    """
    client = GeminiClient()
    if not client.configured:
        raise GeminiError("Gemini is not configured. Add an API key in Settings.")

    conversation = list(history) + [
        {"role": "user", "text": f"{sender_name}: {latest_text}"}
    ]

    # Inject the authoritative product catalogue for this query so the model
    # never has to rely on prices hand-written in the operator prompt.
    catalogue = kb.render_context(latest_text)
    instruction = DECISION_INSTRUCTION
    if reply_scope != "all":
        instruction += RELEVANCE_RULE
    system = f"{instruction}\n\n=== OPERATOR RULES ===\n{system_prompt}"
    if catalogue:
        system += f"\n\n{catalogue}"

    data = await client.generate_json(system, conversation)

    action = str(data.get("action", "ignore")).lower()
    if action not in {"reply", "ignore", "escalate"}:
        action = "escalate"

    if reply_scope != "all" and not bool(data.get("relevant", True)):
        return Decision(
            action="ignore",
            reply="",
            reason=str(data.get("reason", "")).strip() or "not relevant to our offer",
        )

    return Decision(
        action=action,
        reply=str(data.get("reply", "")).strip(),
        reason=str(data.get("reason", "")).strip(),
    )


def build_history(messages: list[dict], limit: int) -> list[dict]:
    """Convert stored messages into Gemini chat turns (oldest first)."""
    turns = []
    for m in messages[-limit:]:
        role = "user" if m["direction"] == "in" else "model"
        text = m["text"]
        if m["direction"] == "in" and m.get("sender_name"):
            text = f"{m['sender_name']}: {text}"
        turns.append({"role": role, "text": text})
    return turns


def _dump(data: dict) -> str:  # pragma: no cover - debug helper
    return json.dumps(data, ensure_ascii=False)[:400]
