import pytest


def test_create_insert_count_delete(mneme_module):
    collection = mneme_module.Collection("docs", dimension=3)
    collection.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
    collection.insert("b", [0.0, 1.0, 0.0], metadata="beta")
    assert collection.count() == 2

    collection.delete("a")
    assert collection.count() == 1

    collection.close()


def test_constructor_validates_name_and_dimension(mneme_module):
    with pytest.raises(ValueError, match="name must be non-empty"):
        mneme_module.Collection("", dimension=3)
    with pytest.raises(ValueError, match="dimension must be positive"):
        mneme_module.Collection("docs", dimension=0)


def test_metric_enum_constructor(mneme_module):
    collection = mneme_module.Collection("docs", dimension=3, metric=mneme_module.Metric.COSINE)
    try:
        assert collection.metric == int(mneme_module.Metric.COSINE)
    finally:
        collection.close()


def test_context_manager_closes_collection(mneme_module):
    with mneme_module.Collection("docs", dimension=3) as collection:
        collection.insert("a", [1.0, 0.0, 0.0])
        assert collection.count() == 1
    assert collection._handle.value is None


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


def test_delete_missing_id_raises_value_error(mneme_module):
    collection = mneme_module.Collection("docs", dimension=3)
    try:
        with pytest.raises(ValueError):
            collection.delete("missing-id")
    finally:
        collection.close()


def test_constructor_frees_handle_on_post_create_assignment_failure(mneme_module, monkeypatch):
    import mneme.collection as collection_module

    class FlakyMetric:
        def __init__(self):
            self.calls = 0

        def __int__(self):
            self.calls += 1
            if self.calls == 1:
                return 1
            raise RuntimeError("boom")

    class FakeLib:
        def __init__(self):
            self.freed = 0

        def mneme_collection_create(self, *_args):
            return 0

        def mneme_collection_free(self, *_args):
            self.freed += 1

    fake_lib = FakeLib()
    monkeypatch.setattr(collection_module.native, "LIB", fake_lib)
    monkeypatch.setattr(collection_module.native, "raise_for_status", lambda _status: None)

    with pytest.raises(RuntimeError, match="boom"):
        collection_module.Collection("docs", dimension=3, metric=FlakyMetric())
    assert fake_lib.freed == 1


def test_as_float_vector_numpy_fast_path(monkeypatch):
    import mneme.collection as collection_module

    class FakeArray:
        def __init__(self, values):
            self._values = [float(v) for v in values]
            self.ndim = 1
            self.size = len(values)

        def tobytes(self):
            import struct

            return struct.pack(f"{len(self._values)}f", *self._values)

    class FakeNumpy:
        ndarray = FakeArray
        float32 = "float32"

        @staticmethod
        def asarray(values, dtype=None):
            _ = dtype
            return values if isinstance(values, FakeArray) else FakeArray(values)

        @staticmethod
        def ascontiguousarray(values, dtype=None):
            _ = dtype
            return values

    monkeypatch.setattr(collection_module, "_np", FakeNumpy)
    vec, vec_len = collection_module._as_float_vector(FakeArray([1.0, 2.0, 3.0]))
    assert vec_len == 3
    assert [float(vec[i]) for i in range(vec_len)] == [1.0, 2.0, 3.0]
