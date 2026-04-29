def test_create_insert_count_delete(mneme_module):
    collection = mneme_module.Collection("docs", dimension=3)
    collection.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
    collection.insert("b", [0.0, 1.0, 0.0], metadata="beta")
    assert collection.count() == 2

    collection.delete("a")
    assert collection.count() == 1

    collection.close()


def test_dimension_mismatch_raises(mneme_module):
    collection = mneme_module.Collection("docs", dimension=3)
    try:
        try:
            collection.insert("bad", [1.0, 2.0])
            raise AssertionError("expected DimensionMismatchError")
        except mneme_module.DimensionMismatchError:
            pass
    finally:
        collection.close()
