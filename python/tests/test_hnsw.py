import pytest


def test_hnsw_search(mneme_module):
    collection = mneme_module.Collection("docs", dimension=3)
    try:
        collection.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
        collection.insert("b", [0.0, 1.0, 0.0], metadata="beta")
        collection.build_hnsw(m=16, ef_construction=64, ef_search=32, seed=42)
        results = collection.search_hnsw([1.0, 0.0, 0.0], k=2, ef_search=32)
        assert len(results) == 2
        assert [row.id for row in results] == ["a", "b"]
        assert results[0].score >= results[1].score
    finally:
        collection.close()


def test_hnsw_before_build_raises(mneme_module):
    collection = mneme_module.Collection("docs", dimension=3)
    try:
        collection.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
        try:
            collection.search_hnsw([1.0, 0.0, 0.0], k=1)
            raise AssertionError("expected IndexNotBuiltError")
        except mneme_module.IndexNotBuiltError:
            pass
    finally:
        collection.close()


def test_hnsw_stale_after_mutation(mneme_module):
    collection = mneme_module.Collection("docs", dimension=3)
    try:
        collection.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
        collection.insert("b", [0.0, 1.0, 0.0], metadata="beta")
        collection.build_hnsw()
        collection.insert("c", [0.0, 0.0, 1.0], metadata="gamma")
        with pytest.raises(mneme_module.IndexStaleError):
            collection.search_hnsw([1.0, 0.0, 0.0], k=2)
    finally:
        collection.close()
