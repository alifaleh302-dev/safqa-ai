import asyncio
import random
import re

from ..config import get_settings

# Average human typing speed in characters per second (conservative).
_CHARS_PER_SECOND = 6.0


def reading_delay(text: str) -> float:
    """Time a human would plausibly spend reading the incoming message."""
    base = 1.2 + len(text) / 40.0
    return min(base, 6.0) * random.uniform(0.8, 1.3)


def typing_delay(reply: str) -> float:
    """Time a human would spend typing the reply, with jitter."""
    settings = get_settings()
    natural = len(reply) / _CHARS_PER_SECOND
    natural *= random.uniform(0.85, 1.25)
    return max(settings.reply_min_delay, min(natural, settings.reply_max_delay))


def split_message(text: str) -> list[str]:
    """Split a reply into short consecutive bubbles, the way people actually chat.

    Only splits on sentence boundaries and only when the text is long enough;
    short replies are left as a single message.
    """
    text = text.strip()
    if len(text) < 140:
        return [text]

    parts = re.split(r"(?<=[.!?؟\n])\s+", text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        return [text]

    # Greedily group sentences so no bubble is too small.
    bubbles: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current} {part}".strip()
        if len(candidate) > 180 and current:
            bubbles.append(current)
            current = part
        else:
            current = candidate
    if current:
        bubbles.append(current)
    return bubbles


async def human_pause(seconds: float) -> None:
    await asyncio.sleep(seconds)
