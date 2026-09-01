---
name: content-hash-cache
description: Caches expensive file operations by SHA-256 content hash instead of path. Use for pipelines processing files needing caching.
---

# Content Hash Cache Pattern

Cache by **content** (SHA-256), not by path. Rename = cache hit. Content change = auto-invalidation. No index file needed.

## Core Implementation

```python
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

def compute_file_hash(path: Path) -> str:
    """SHA-256 of file contents, chunked for large files."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):  # 64KB chunks
            sha256.update(chunk)
    return sha256.hexdigest()


@dataclass(frozen=True)
class CacheEntry:
    file_hash: str
    source_path: str
    result: Any  # The cached computation result


def extract_with_cache(
    file_path: Path,
    process_fn,
    *,
    cache_enabled: bool = True,
    cache_dir: Path = Path(".cache"),
) -> Any:
    """Wrapper that caches process_fn results by file content hash."""
    if not cache_enabled:
        return process_fn(file_path)

    file_hash = compute_file_hash(file_path)
    cache_file = cache_dir / f"{file_hash}.json"

    # Cache hit
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            return data["result"]
        except (json.JSONDecodeError, KeyError):
            pass  # Corrupted cache, recompute

    # Cache miss — compute and store
    result = process_fn(file_path)

    cache_dir.mkdir(parents=True, exist_ok=True)
    entry = {"file_hash": file_hash, "source_path": str(file_path), "result": result}
    cache_file.write_text(json.dumps(entry, default=str))

    return result
```

## Design Decisions
- **O(1) lookup**: `{hash}.json` — no index file to maintain or corrupt
- **Corruption tolerance**: Returns `None` on bad cache, recomputes silently
- **Lazy directory creation**: Cache dir created only when first entry is written
- **Frozen dataclass**: Immutable cache entries prevent accidental mutation
- **Pure function wrapping**: `process_fn` stays pure; caching is a separate concern

## When to Use
- PDF/document text extraction
- Image analysis or OCR
- Signal computation on price data files
- Any expensive file → result transformation that's deterministic
