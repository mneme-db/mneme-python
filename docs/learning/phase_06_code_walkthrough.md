# Phase 6 Code Walkthrough

## Wrapper layout

- `python/src/mneme/native.py`: loads shared library and declares `ctypes` signatures.
- `python/src/mneme/collection.py`: Pythonic `Collection` API over C ABI.
- `python/src/mneme/errors.py`: typed exception hierarchy.
- `python/src/mneme/results.py`: `SearchResult` data model.

## API shape

`Collection` is the top-level abstraction:

- `insert`, `delete`, `count`
- `search` (flat)
- `build_hnsw`, `search_hnsw`
- `save`, `load`

Search output uses typed objects (`SearchResult`) with `id` and `score`.

## Testing

`pytest` tests cover:

- core collection operations,
- flat and HNSW search behavior,
- save/load persistence round-trip,
- NumPy input path when available.
