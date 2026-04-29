class MnemeError(Exception):
    """Base exception for mneme Python wrapper failures."""


class DimensionMismatchError(MnemeError):
    """Raised when input vector dimensions do not match collection dimension."""


class IndexNotBuiltError(MnemeError):
    """Raised when HNSW search is requested before index build."""


class IndexStaleError(MnemeError):
    """Raised when HNSW index is stale after mutation."""
