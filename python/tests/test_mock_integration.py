from __future__ import annotations

import ctypes
import importlib
from pathlib import Path
from typing import Any


class _FakeLib:
    def __init__(self) -> None:
        self.saved_path: bytes | None = None
        self.search_calls = 0
        self.insert_calls = 0

    def mneme_collection_insert(self, *args: Any) -> int:
        self.insert_calls += 1
        return 0

    def mneme_collection_delete(self, *args: Any) -> int:
        return 0

    def mneme_collection_count(self, *args: Any) -> int:
        return 7

    def mneme_collection_search_flat(self, *args: Any) -> int:
        self.search_calls += 1
        return 0

    def mneme_collection_search_hnsw(self, *args: Any) -> int:
        self.search_calls += 1
        return 0

    def mneme_collection_build_hnsw(self, *args: Any) -> int:
        return 0

    def mneme_collection_save(self, _handle: Any, path: bytes) -> int:
        self.saved_path = path
        return 0

    def mneme_collection_free(self, *args: Any) -> None:
        return None

    def mneme_results_len(self, *args: Any) -> int:
        return 2

    def mneme_results_id(self, _results: Any, index: int) -> bytes:
        return b"a" if index == 0 else b"b"

    def mneme_results_score(self, _results: Any, index: int) -> float:
        return 0.99 if index == 0 else 0.42

    def mneme_results_free(self, *args: Any) -> None:
        return None


def _mock_collection(collection_cls):
    col = collection_cls.__new__(collection_cls)
    col._handle = ctypes.c_void_p(1)
    col._name = "mock"
    col._dimension = 3
    col._metric = 1
    return col


def test_collection_methods_with_mocked_native(monkeypatch, native_module):
    _ = native_module
    collection_module = importlib.import_module("mneme.collection")
    collection_cls = collection_module.Collection
    search_result_cls = importlib.import_module("mneme.results").SearchResult

    fake_lib = _FakeLib()
    monkeypatch.setattr("mneme.collection.native.LIB", fake_lib)
    monkeypatch.setattr("mneme.collection.native.raise_for_status", lambda _status: None)

    collection = _mock_collection(collection_cls)
    collection.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
    collection.delete("a")
    assert collection.count() == 7

    flat_results = collection.search([1.0, 0.0, 0.0], k=2)
    ann_results = collection.search_hnsw([1.0, 0.0, 0.0], k=2, ef_search=64)
    collection.build_hnsw()
    collection.save(Path("tmp.mneme"))
    collection.close()

    assert fake_lib.insert_calls == 1
    assert fake_lib.search_calls == 2
    assert fake_lib.saved_path == b"tmp.mneme"
    assert flat_results == [
        search_result_cls(id="a", score=0.99),
        search_result_cls(id="b", score=0.42),
    ]
    assert ann_results == [
        search_result_cls(id="a", score=0.99),
        search_result_cls(id="b", score=0.42),
    ]
