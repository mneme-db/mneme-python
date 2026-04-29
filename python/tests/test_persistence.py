def test_save_load_roundtrip(tmp_path, mneme_module):
    path = tmp_path / "docs.mneme"

    collection = mneme_module.Collection("docs", dimension=3)
    try:
        collection.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
        collection.insert("b", [0.0, 1.0, 0.0], metadata="beta")
        collection.save(path)
    finally:
        collection.close()

    loaded = mneme_module.Collection.load(path)
    try:
        assert loaded.count() == 2
        results = loaded.search([1.0, 0.0, 0.0], k=2)
        assert results[0].id == "a"
    finally:
        loaded.close()
