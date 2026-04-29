# Phase 6 Python-Zig Interop

The Python wrapper is a thin layer over the stable C ABI (`include/mneme.h`) from the Zig core project.

## Why ABI-first

- Keeps Python package small and explicit.
- Reuses existing hardened contracts and ownership model.
- Avoids introducing a new native extension framework in the critical path.

## Exception mapping

- `MNEME_ERROR_INVALID_ARGUMENT` -> `ValueError`
- `MNEME_ERROR_DIMENSION_MISMATCH` -> `DimensionMismatchError`
- `MNEME_ERROR_IO` -> `OSError`
- `MNEME_ERROR_INDEX_NOT_BUILT` -> `IndexNotBuiltError`
- `MNEME_ERROR_INDEX_STALE` -> `IndexStaleError`
- `MNEME_ERROR_OUT_OF_MEMORY` -> `MemoryError`
- `MNEME_ERROR_INTERNAL` -> `MnemeError`

`mneme_last_error()` is used for the error message text.

## NumPy handling

The API accepts Python lists and NumPy arrays. NumPy remains optional and is converted to 1D `float32` data before native calls.
