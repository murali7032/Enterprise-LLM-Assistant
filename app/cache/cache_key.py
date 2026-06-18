import hashlib
import json
from typing import Any


def build_cache_key(namespace: str, payload: dict[str, Any]) -> str:
    """Generate a deterministic cache key from a payload."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"
