# mneme Python wrapper

First Python wrapper for the `mneme` embedded vector database core.

## Install (source, local dev)

1. Install package in editable mode from this repo:

```bash
pip install -e ./python
```

2. Import and use `mneme`; the wrapper will auto-download a matching native release asset if local libs are not found.

## Usage

```python
from mneme import Collection

db = Collection("docs", dimension=3)
db.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
db.insert("b", [0.0, 1.0, 0.0], metadata="beta")

results = db.search([1.0, 0.0, 0.0], k=2)
for row in results:
    print(row.id, row.score)
```

## Behavior reference

- `Collection.load(path)` sets `collection.dimension` and `collection.metric` to `None` because
  current C ABI does not expose readback accessors for loaded collection config.
- `Collection.delete(id)` raises `ValueError` when `id` is not found.
- `Collection.search_hnsw(...)` raises:
  - `IndexNotBuiltError` if HNSW index is not built
  - `IndexStaleError` if collection mutated after index build
- Handles are not thread-safe. Sharing one `Collection` across concurrent threads is undefined.
- Search scores are cosine similarity scores in `[-1.0, 1.0]`.

Count semantics:

- `count()` returns the number of currently stored rows for a valid, open collection handle.
- Calling `count()` after `close()` is invalid and raises a native-mapped exception (`ValueError`).
- `count()` reflects inserts/deletes immediately for that in-memory handle.

Save/load behavior:

- `save(path)` writes canonical collection state (`.mneme`) to disk.
- `load(path)` creates a new collection handle from canonical persisted state.
- HNSW graph is not persisted; rebuild via `build_hnsw()` after load when ANN search is needed.

Metadata contract:

- Metadata is optional (`str | None`) on insert.
- Metadata is passed as UTF-8 encoded text over the C ABI.
- Retrieval/filtering APIs for metadata are not exposed in this Python wrapper yet.
- Practical metadata size limits are determined by available memory and core ABI validation.

Error mapping:

| C status code | Python exception |
| --- | --- |
| `MNEME_ERROR_INVALID_ARGUMENT` | `ValueError` |
| `MNEME_ERROR_DIMENSION_MISMATCH` | `DimensionMismatchError` |
| `MNEME_ERROR_IO` | `OSError` |
| `MNEME_ERROR_INDEX_NOT_BUILT` | `IndexNotBuiltError` |
| `MNEME_ERROR_INDEX_STALE` | `IndexStaleError` |
| `MNEME_ERROR_OUT_OF_MEMORY` | `MemoryError` |
| `MNEME_ERROR_INTERNAL` | `MnemeError` |

## Native library requirements

- macOS: `libmneme.dylib`
- Linux: `libmneme.so`

Lookup order:

1. `MNEME_LIBRARY_PATH`
2. `MNEME_REPO_PATH` (`<repo>/zig-out/lib` then `<repo>`)
3. `../mneme/zig-out/lib` (sibling dependency default)
4. current working directory fallbacks
5. system dynamic loader paths
6. GitHub release auto-download (cached)

Release auto-download defaults:

- repo: `mneme-db/mneme`
- tag: `latest` (override with `MNEME_RELEASE_TAG`, e.g. `v0.5.0`)
- cache dir: `~/.cache/mneme-python` (override with `MNEME_CACHE_DIR`)
- disable with `MNEME_AUTO_DOWNLOAD=0`
- debug loader selection with `MNEME_DEBUG_LOAD=1`

Debug logging example:

```python
import logging
import os

os.environ["MNEME_DEBUG_LOAD"] = "1"

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("mneme").setLevel(logging.DEBUG)

import mneme  # loader debug messages emitted via the "mneme" logger
```

API notes:

- `Collection` accepts `metric` as either `int` or `mneme.Metric` (for now: `Metric.COSINE`).
- `Collection.delete(id)` raises `ValueError` if the id does not exist.
- `Collection` is not thread-safe; sharing a single handle across concurrent threads is undefined.

## Testing

```bash
pytest python/tests
```

Quality checks:

```bash
ruff check python/src python/tests
ruff format --check python/src python/tests
bandit -c python/pyproject.toml -r python/src
mypy --config-file python/pyproject.toml python/src/mneme
```

CI runs the same checks in `.github/workflows/ci.yml`.

## Troubleshooting

- If import fails with native load error, set `MNEME_RELEASE_TAG` to a known release like `v0.5.0` and retry.
- Set `MNEME_LIBRARY_PATH` explicitly to a compiled shared library if you use a custom build location.
