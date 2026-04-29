import pytest


def test_save_load_roundtrip(tmp_path, mneme_module):
    path = tmp_path / "docs.mneme"

    vectors = {
        "a": [1.0, 0.0, 0.0],
        "b": [0.0, 1.0, 0.0],
        "c": [0.0, 0.0, 1.0],
    }
    metadata = {"a": "alpha", "b": "beta", "c": "gamma"}

    collection = mneme_module.Collection("docs", dimension=3)
    try:
        for row_id, vector in vectors.items():
            collection.insert(row_id, vector, metadata=metadata[row_id])
        collection.save(path)
    finally:
        collection.close()

    loaded = mneme_module.Collection.load(path)
    try:
        assert loaded.name == "docs"
        assert loaded.dimension is None
        assert loaded.metric is None
        assert loaded.count() == 3
        results = loaded.search([1.0, 0.0, 0.0], k=3)
        assert [row.id for row in results] == ["a", "b", "c"]
        assert results[0].score >= results[1].score >= results[2].score
    finally:
        loaded.close()


def test_load_missing_file_raises_oserror(tmp_path, mneme_module):
    missing = tmp_path / "missing.mneme"
    with pytest.raises(OSError):
        mneme_module.Collection.load(missing)
