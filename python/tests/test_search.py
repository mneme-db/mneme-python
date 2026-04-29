def test_flat_search(mneme_module):
    collection = mneme_module.Collection("docs", dimension=3)
    try:
        collection.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
        collection.insert("b", [0.0, 1.0, 0.0], metadata="beta")
        results = collection.search([1.0, 0.0, 0.0], k=2)

        assert len(results) == 2
        assert results[0].id == "a"
        assert isinstance(results[0].score, float)
    finally:
        collection.close()


def test_numpy_input_if_available(mneme_module):
    collection = mneme_module.Collection("docs", dimension=3)
    try:
        try:
            import numpy as np
        except Exception:
            return
        collection.insert("a", np.array([1.0, 0.0, 0.0], dtype=np.float32))
        results = collection.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), k=1)
        assert results[0].id == "a"
    finally:
        collection.close()
