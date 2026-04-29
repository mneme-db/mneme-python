from __future__ import annotations

import ctypes
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING

from . import native
from .results import SearchResult

try:
    import numpy as _np
except Exception:  # pragma: no cover - optional dependency
    _np = None

if TYPE_CHECKING:
    from .native import Metric


def _as_float_vector(values: Sequence[float]) -> tuple[ctypes.Array[ctypes.c_float], int]:
    if _np is not None and isinstance(values, _np.ndarray):
        arr = _np.asarray(values, dtype=_np.float32)
        if arr.ndim != 1:
            raise ValueError("vector must be a 1D array")
        contiguous = _np.ascontiguousarray(arr, dtype=_np.float32)
        vector_len = int(contiguous.size)
        vector = (ctypes.c_float * vector_len).from_buffer_copy(contiguous.tobytes())
        return vector, vector_len

    data = [float(v) for v in values]
    vector_len = len(data)
    return (ctypes.c_float * vector_len)(*data), vector_len


def _decode_results(handle: native.ResultsHandle) -> list[SearchResult]:
    # mneme_results_id returns borrowed pointers that remain valid only until
    # mneme_results_free is called for this handle; decode eagerly into Python strs.
    count = int(native.LIB.mneme_results_len(handle))
    out: list[SearchResult] = []
    for idx in range(count):
        row_id = native.LIB.mneme_results_id(handle, idx)
        row_id_text = "" if row_id is None else row_id.decode("utf-8")
        score = float(native.LIB.mneme_results_score(handle, idx))
        out.append(SearchResult(id=row_id_text, score=score))
    return out


class Collection:
    dimension: int | None
    metric: int | None

    def __init__(
        self, name: str, dimension: int, metric: int | Metric = native.MNEME_METRIC_COSINE
    ) -> None:
        if not name:
            raise ValueError("name must be non-empty")
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self._handle = native.CollectionHandle()
        status = native.LIB.mneme_collection_create(
            name.encode("utf-8"),
            int(dimension),
            int(metric),
            ctypes.byref(self._handle),
        )
        native.raise_for_status(int(status))
        try:
            self.name = name
            self.dimension = int(dimension)
            self.metric = int(metric)
        except Exception:
            native.LIB.mneme_collection_free(self._handle)
            self._handle = native.CollectionHandle()
            raise

    @classmethod
    def load(cls, path: str | Path) -> Collection:
        handle = native.CollectionHandle()
        status = native.LIB.mneme_collection_load(str(path).encode("utf-8"), ctypes.byref(handle))
        native.raise_for_status(int(status))
        obj = cls.__new__(cls)
        obj._handle = handle
        obj.name = Path(path).stem
        # ABI currently does not expose dimension/metric accessors after load.
        # Keep these unknown instead of fabricating potentially wrong values.
        obj.dimension = None
        obj.metric = None
        return obj

    def close(self) -> None:
        if getattr(self, "_handle", None):
            native.LIB.mneme_collection_free(self._handle)
            self._handle = native.CollectionHandle()

    def __enter__(self) -> Collection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - best effort cleanup
        with suppress(Exception):
            self.close()

    def insert(self, row_id: str, vector: Sequence[float], metadata: str | None = None) -> None:
        vec, vec_len = _as_float_vector(vector)
        metadata_ptr = metadata.encode("utf-8") if metadata is not None else None
        status = native.LIB.mneme_collection_insert(
            self._handle,
            row_id.encode("utf-8"),
            vec,
            vec_len,
            metadata_ptr,
        )
        native.raise_for_status(int(status))

    def delete(self, row_id: str) -> None:
        status = native.LIB.mneme_collection_delete(self._handle, row_id.encode("utf-8"))
        native.raise_for_status(int(status))

    def count(self) -> int:
        return int(native.LIB.mneme_collection_count(self._handle))

    def search(self, query: Sequence[float], k: int) -> list[SearchResult]:
        q, q_len = _as_float_vector(query)
        result_handle = native.ResultsHandle()
        status = native.LIB.mneme_collection_search_flat(
            self._handle,
            q,
            q_len,
            int(k),
            ctypes.byref(result_handle),
        )
        native.raise_for_status(int(status))
        try:
            return _decode_results(result_handle)
        finally:
            native.LIB.mneme_results_free(result_handle)

    def build_hnsw(
        self,
        m: int = 16,
        ef_construction: int = 64,
        ef_search: int = 32,
        seed: int = 42,
    ) -> None:
        cfg = native.MnemeHnswConfig(
            m=int(m),
            ef_construction=int(ef_construction),
            ef_search=int(ef_search),
            seed=int(seed),
        )
        status = native.LIB.mneme_collection_build_hnsw(self._handle, ctypes.byref(cfg))
        native.raise_for_status(int(status))

    def search_hnsw(
        self, query: Sequence[float], k: int, ef_search: int | None = None
    ) -> list[SearchResult]:
        q, q_len = _as_float_vector(query)
        result_handle = native.ResultsHandle()
        ef = native.MNEME_EF_SEARCH_DEFAULT if ef_search is None else int(ef_search)
        status = native.LIB.mneme_collection_search_hnsw(
            self._handle,
            q,
            q_len,
            int(k),
            ef,
            ctypes.byref(result_handle),
        )
        native.raise_for_status(int(status))
        try:
            return _decode_results(result_handle)
        finally:
            native.LIB.mneme_results_free(result_handle)

    def save(self, path: str | Path) -> None:
        status = native.LIB.mneme_collection_save(self._handle, str(path).encode("utf-8"))
        native.raise_for_status(int(status))
