from fastapi import APIRouter, HTTPException

from ..services.knowledge import kb

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("")
def get_knowledge():
    """Return the raw product catalogue and the rendered prompt context."""
    return {
        "path": str(kb.path),
        "exists": kb.path.exists(),
        "products": kb.products,
        "rendered": kb.render_context(),
    }


@router.put("")
def update_knowledge(payload: dict):
    """Overwrite the catalogue with a new JSON document.

    Accepts either a full document ({"products": [...]}) or a bare list of
    products, then validates it loads back cleanly before persisting.
    """
    import json

    if isinstance(payload, list):
        document = {"products": payload}
    elif isinstance(payload, dict) and "products" in payload:
        document = payload
    else:
        raise HTTPException(400, "Expected a JSON object with 'products' or a list of products")

    if not isinstance(document["products"], list):
        raise HTTPException(400, "'products' must be a list")

    kb.path.parent.mkdir(parents=True, exist_ok=True)
    kb.path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    # Force reload on next access.
    kb._mtime = None  # noqa: SLF001 - intentional cache invalidation
    return get_knowledge()


@router.get("/preview")
def preview(query: str = ""):
    """Preview the exact catalogue block injected into a prompt for a query."""
    return {"query": query, "context": kb.render_context(query)}
