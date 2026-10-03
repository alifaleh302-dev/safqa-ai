import json
from typing import Optional

import httpx

from ..config import get_settings


class GeminiError(RuntimeError):
    pass


class GeminiClient:
    """Thin wrapper around the Gemini generateContent REST API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.base_url = settings.gemini_base_url

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        system_prompt: str,
        conversation: list[dict],
        response_mime_type: Optional[str] = None,
        temperature: float = 0.9,
    ) -> str:
        if not self.configured:
            raise GeminiError("GEMINI_API_KEY is not configured")

        contents = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["text"]}]}
            for m in conversation
        ]
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if response_mime_type:
            payload["generationConfig"]["responseMimeType"] = response_mime_type

        url = f"{self.base_url}/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, params={"key": self.api_key}, json=payload)
        if resp.status_code >= 400:
            raise GeminiError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise GeminiError(f"Unexpected Gemini response: {json.dumps(data)[:500]}") from exc

    async def generate_json(self, system_prompt: str, conversation: list[dict]) -> dict:
        raw = await self.generate(system_prompt, conversation, response_mime_type="application/json")
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text.split("\n", 1)[-1] if "\n" in text else text
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise GeminiError(f"Model did not return valid JSON: {raw[:300]}") from exc
