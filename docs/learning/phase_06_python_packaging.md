# Phase 6 Python Packaging

Phase 6 introduces a first Python package with `src/` layout and `pyproject.toml`.

## Local workflow

1. Install wrapper in editable mode:
   - `pip install -e ./python`
2. Run tests:
   - `pytest python/tests`

## Native library loading

The wrapper searches for:

- `MNEME_LIBRARY_PATH` (explicit override),
- `MNEME_REPO_PATH` (`<repo>/zig-out/lib` then `<repo>`),
- sibling dependency build output (`../mneme/zig-out/lib`),
- current working directory fallback,
- system loader path names (`libmneme.dylib` or `libmneme.so`),
- GitHub release auto-download and cache (no manual download needed).

Auto-download controls:

- `MNEME_RELEASE_TAG` (default: `latest`, can pin like `v0.5.0`)
- `MNEME_CACHE_DIR` (default: `~/.cache/mneme-python`)
- `MNEME_AUTO_DOWNLOAD=0` to disable network fallback.
- `MNEME_DEBUG_LOAD=1` to enable loader debug logs (`mneme` logger).

## Wheel strategy

Current status: no published wheels yet. Phase 6 focuses on source install with release-based fallback for native binaries.
