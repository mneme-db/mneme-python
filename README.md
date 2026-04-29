# mneme-python

[![CI](https://github.com/mneme-db/mneme-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/mneme-db/mneme-python/actions/workflows/ci.yml)
[![Release Check](https://github.com/mneme-db/mneme-python/actions/workflows/release-check.yml/badge.svg)](https://github.com/mneme-db/mneme-python/actions/workflows/release-check.yml)
[![Release](https://github.com/mneme-db/mneme-python/actions/workflows/release.yml/badge.svg)](https://github.com/mneme-db/mneme-python/actions/workflows/release.yml)
[![TestPyPI](https://github.com/mneme-db/mneme-python/actions/workflows/testpypi.yml/badge.svg)](https://github.com/mneme-db/mneme-python/actions/workflows/testpypi.yml)

Python wrapper package for [`mneme`](https://github.com/mneme-db/mneme), the embedded-first vector/memory database core written in Zig.

## Status

Phase 6 initial wrapper is implemented with a `ctypes` binding over the stable C ABI.

## Install from source

1. Install this package:

```bash
pip install -e ./python
```

2. Import and use `mneme`; native library resolution tries local paths first, then automatically fetches a compatible release artifact from `mneme-db/mneme` if needed.

## Full functionality examples

### End-to-end: create, mutate, search, persist, reload

```python
from mneme import Collection, Metric

# Create a fixed-dimension cosine collection.
db = Collection("docs", dimension=3, metric=Metric.COSINE)

# Insert rows (metadata is optional string).
db.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
db.insert("b", [0.0, 1.0, 0.0], metadata="beta")
db.insert("c", [0.0, 0.0, 1.0], metadata=None)

# Count rows.
print("count:", db.count())  # 3

# Exact flat search.
flat_results = db.search([1.0, 0.0, 0.0], k=2)
for row in flat_results:
    print("flat:", row.id, row.score)

# Build HNSW index and run ANN search.
db.build_hnsw(m=16, ef_construction=64, ef_search=32, seed=42)
hnsw_results = db.search_hnsw([1.0, 0.0, 0.0], k=2, ef_search=64)
for row in hnsw_results:
    print("hnsw:", row.id, row.score)

# Delete by id.
db.delete("c")
print("count after delete:", db.count())  # 2

# Save canonical collection state.
db.save("docs.mneme")
db.close()

# Load persisted collection into a new handle.
loaded = Collection.load("docs.mneme")
print("loaded count:", loaded.count())  # 2
print("loaded search:", loaded.search([1.0, 0.0, 0.0], k=2))
loaded.close()
```

### Context manager usage

```python
from mneme import Collection

with Collection("docs", dimension=3) as db:
    db.insert("a", [1.0, 0.0, 0.0])
    print(db.search([1.0, 0.0, 0.0], k=1))
```

### Optional NumPy vectors

NumPy is optional. If installed, `numpy.ndarray(dtype=float32)` is accepted for inserts and queries.

```python
import numpy as np
from mneme import Collection

db = Collection("docs", dimension=3)
db.insert("a", np.array([1.0, 0.0, 0.0], dtype=np.float32))
print(db.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), k=1))
db.close()
```

### Error handling examples

```python
from mneme import Collection, DimensionMismatchError, IndexNotBuiltError, IndexStaleError

db = Collection("docs", dimension=3)

try:
    db.insert("bad", [1.0, 2.0])  # wrong vector length
except DimensionMismatchError as exc:
    print("dimension mismatch:", exc)

try:
    db.search_hnsw([1.0, 0.0, 0.0], k=1)  # index not built yet
except IndexNotBuiltError as exc:
    print("index not built:", exc)

# IndexStaleError may be raised if collection mutates after HNSW build and
# ANN search is attempted before rebuilding index.
try:
    db.build_hnsw()
    db.insert("a", [1.0, 0.0, 0.0])
    db.search_hnsw([1.0, 0.0, 0.0], k=1)
except IndexStaleError as exc:
    print("index stale:", exc)
finally:
    db.close()
```

## API summary

- `Collection(name, dimension, metric=1)`
- `Collection.load(path)`
- `insert(id, vector, metadata=None)`
- `delete(id)`
- `count()`
- `search(query, k)`
- `build_hnsw(m=16, ef_construction=64, ef_search=32, seed=42)`
- `search_hnsw(query, k, ef_search=None)`
- `save(path)`
- `close()`

Search results are `SearchResult` objects with:

- `result.id`
- `result.score`

Note on loaded metadata:

- `Collection.load()` currently sets `dimension` and `metric` to `None` because the
  current C ABI does not expose readback accessors for those values.

Native loader note:

- Use `MNEME_REPO_PATH` to point at a local mneme repo when your directory layout
  is not the default sibling `../mneme`.

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
