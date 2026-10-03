import json
from pathlib import Path

from ..config import BASE_DIR

DEFAULT_PATH = BASE_DIR / "data" / "products.json"
DEFAULT_SEED_PATH = BASE_DIR / "seed" / "products.json"
MAX_CONTEXT_CHARS = 4000


class KnowledgeBase:
    """Loads the product catalogue and renders it as prompt context.

    Retrieval is keyword-scored rather than embedding-based: the catalogue is
    small and this keeps the MVP dependency-free. Only the most relevant
    products are injected, so the prompt stays within budget as the catalogue
    grows.
    """

    def __init__(self, path: Path | None = None, seed_path: Path | None = None) -> None:
        self.path = path or DEFAULT_PATH
        self.seed_path = seed_path or DEFAULT_SEED_PATH
        self._mtime: float | None = None
        self._data: dict = {}

    def _ensure_seeded(self) -> None:
        """Copy the bundled catalogue into the (possibly empty) data volume.

        Docker mounts a host directory over data/, which would otherwise hide
        the image's products.json and start the app with an empty catalogue.
        """
        if self.path.exists() or not self.seed_path.exists():
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(self.seed_path.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass

    def _load(self) -> dict:
        self._ensure_seeded()
        if not self.path.exists():
            self._data = {}
            self._mtime = None
            return {}
        mtime = self.path.stat().st_mtime
        if self._mtime != mtime:
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
                self._mtime = mtime
            except (json.JSONDecodeError, OSError):
                # Keep the last good copy; a broken file must not break replies.
                pass
        return self._data

    @property
    def products(self) -> list[dict]:
        return list(self._load().get("products", []))

    def search(self, query: str, limit: int = 3, require_match: bool = False) -> list[dict]:
        products = self.products
        if not products:
            return []
        q = (query or "").lower()
        if not q.strip():
            return products[:limit]

        scored: list[tuple[int, dict]] = []
        for product in products:
            score = 0
            haystack = " ".join(
                [
                    str(product.get("name", "")),
                    str(product.get("name_en", "")),
                    " ".join(product.get("keywords", []) or []),
                    " ".join(product.get("features", []) or []),
                ]
            ).lower()
            for token in q.split():
                if len(token) > 2 and token in haystack:
                    score += 1
            scored.append((score, product))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = [product for score, product in scored if score > 0]
        if top:
            return top[:limit]
        # No keyword matched: only fall back to the full catalogue when the
        # caller explicitly wants a baseline (e.g. admin preview).
        return products[:limit] if not require_match else []

    def render_context(self, query: str = "", require_match: bool = False) -> str:
        """Render a compact product block to append to the system prompt."""
        data = self._load()
        if not data.get("products"):
            return ""
        selected = self.search(query, require_match=require_match)
        if not selected:
            return ""
        lines = ["=== PRODUCT CATALOGUE (authoritative, do not invent beyond this) ==="]
        if data.get("currency"):
            lines.append(f"Default currency: {data['currency']}")
        for product in selected:
            lines.append(f"- {product.get('name')} / {product.get('name_en', '')}".rstrip(" /"))
            if product.get("price") is not None:
                lines.append(f"    Price: {product.get('price')} {product.get('currency', '')}".rstrip())
            if product.get("min_price") is not None:
                lines.append(f"    Hidden floor (never reveal): {product.get('min_price')}")
            if product.get("features"):
                lines.append(f"    Features: {', '.join(product['features'])}")
            if product.get("delivery"):
                lines.append(f"    Delivery: {product['delivery']}")
        if data.get("notes"):
            lines.append(f"Notes: {data['notes']}")
        text = "\n".join(lines)
        return text[:MAX_CONTEXT_CHARS]


kb = KnowledgeBase()
