import json
from dataclasses import dataclass

from .gemini import GeminiClient, GeminiError

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
) -> Decision:
    """Ask Gemini for the next action given the operator's prompt and context."""
    client = GeminiClient()
    if not client.configured:
        raise GeminiError("Gemini is not configured. Add an API key in Settings.")

    conversation = list(history) + [
        {"role": "user", "text": f"{sender_name}: {latest_text}"}
    ]
    system = f"{DECISION_INSTRUCTION}\n\n=== OPERATOR RULES ===\n{system_prompt}"

    data = await client.generate_json(system, conversation)

    action = str(data.get("action", "ignore")).lower()
    if action not in {"reply", "ignore", "escalate"}:
        action = "escalate"
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
