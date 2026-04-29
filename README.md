# mneme-python

[![CI](https://github.com/mneme-db/mneme-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/mneme-db/mneme-python/actions/workflows/ci.yml)
[![Release Check](https://github.com/mneme-db/mneme-python/actions/workflows/release-check.yml/badge.svg)](https://github.com/mneme-db/mneme-python/actions/workflows/release-check.yml)
[![Release](https://github.com/mneme-db/mneme-python/actions/workflows/release.yml/badge.svg)](https://github.com/mneme-db/mneme-python/actions/workflows/release.yml)
[![TestPyPI](https://github.com/mneme-db/mneme-python/actions/workflows/testpypi.yml/badge.svg)](https://github.com/mneme-db/mneme-python/actions/workflows/testpypi.yml)

Python wrapper package for [`mneme`](https://github.com/mneme-db/mneme), the embedded-first vector/memory database core written in Zig.

## Status

Phase 6 initial wrapper is implemented with a `ctypes` binding over the stable C ABI.

## Install from source

```bash
pip install -e ./python
```

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

## Detailed end-to-end example (different use case)

### Customer support incident triage with semantic retrieval

This example shows how to:

1. create embeddings with a real model,
2. store incidents in `mneme`,
3. query by natural language symptoms,
4. evaluate retrieval quality with `hit@k` and `MRR@k`.

```python
from __future__ import annotations

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from mneme import Collection, Metric

# 1) Incident knowledge base
incidents = [
    "Mobile app crashes on launch after updating to iOS 18.",
    "Users cannot reset password because email links expire immediately.",
    "Checkout fails with timeout errors when cart has more than 20 items.",
    "Search results are empty when query contains special characters like '+'.",
    "Webhook retries spike due to TLS handshake failures in eu-west.",
    "CSV export generates corrupted files for accounts with unicode names.",
    "Login latency increased after enabling strict bot detection rules.",
    "Dashboard charts fail to render for users with read-only role.",
]

incident_df = pd.DataFrame(
    {
        "id": [f"inc_{i}" for i in range(len(incidents))],
        "text": incidents,
        "severity": ["high", "medium", "high", "medium", "high", "medium", "medium", "low"],
    }
)

# 2) Build embeddings
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
vectors = model.encode(incident_df["text"].tolist(), normalize_embeddings=True)
vectors = np.asarray(vectors, dtype=np.float32)

# 3) Index in mneme
db = Collection("support_incidents", dimension=vectors.shape[1], metric=Metric.COSINE)
for i, row in incident_df.iterrows():
    # Metadata is optional string; include severity+text payload.
    db.insert(row["id"], vectors[i], metadata=f"severity={row['severity']} | {row['text']}")

print("rows indexed:", db.count())

# 4) Query helper
id_to_text = dict(zip(incident_df["id"], incident_df["text"]))

def retrieve(query: str, k: int = 3) -> pd.DataFrame:
    q_vec = model.encode([query], normalize_embeddings=True)
    q_vec = np.asarray(q_vec, dtype=np.float32)[0]
    results = db.search(q_vec, k=k)
    return pd.DataFrame(
        [{"id": r.id, "score": float(r.score), "text": id_to_text.get(r.id, "")} for r in results]
    )

print(retrieve("password reset email link is invalid", k=3))
print(retrieve("ios app immediately crashes after update", k=3))

# 5) Lightweight retrieval evaluation
eval_cases = [
    {"query": "password reset links are broken", "gold": {"inc_1"}},
    {"query": "app crash after iOS upgrade", "gold": {"inc_0"}},
    {"query": "timeouts during checkout on large carts", "gold": {"inc_2"}},
]

def evaluate(k: int = 3) -> pd.DataFrame:
    rows = []
    for case in eval_cases:
        retrieved = retrieve(case["query"], k=k)["id"].tolist()
        gold = case["gold"]
        hit = any(doc_id in gold for doc_id in retrieved)
        rr = 0.0
        for rank, doc_id in enumerate(retrieved, start=1):
            if doc_id in gold:
                rr = 1.0 / rank
                break
        rows.append({"query": case["query"], "hit@k": float(hit), "rr": rr, "top_ids": retrieved})
    out = pd.DataFrame(rows)
    print(f"Average hit@{k}: {out['hit@k'].mean():.3f}")
    print(f"MRR@{k}: {out['rr'].mean():.3f}")
    return out

print(evaluate(k=3))

db.close()
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
```

## Known limitations

- No wheels published yet.
- Native library may be auto-fetched from releases; offline usage still requires local library availability.
- Windows support is not included in this phase.
- Metadata remains string-only.
- HNSW index is not persisted.
- PyOZ remains experimental and not the production binding path in Phase 6.

## CI/CD

GitHub Actions is configured with:

- `CI` workflow on pushes/PRs:
  - matrix testing on macOS/Linux and Python `3.10`, `3.12`, `3.14`
  - `ruff`, `bandit`, `mypy`, and `pytest` with coverage gate
  - package build validation (`python -m build` + `twine check`)
- `Release` workflow on published GitHub releases:
  - builds package and publishes to PyPI via trusted publishing (OIDC)
- `Release Check` workflow on `v*` tag pushes:
  - verifies tag/version parity before release steps
  - builds package + runs `twine check` for artifact integrity
- `Publish TestPyPI` workflow:
  - publishes prerelease or manually dispatched builds to TestPyPI
  - validates release tag/version parity before publish
- Dependabot for GitHub Actions and Python dependency updates.
