from __future__ import annotations

import ctypes
import json
import logging
import os
import platform
import tarfile
from enum import IntEnum
from pathlib import Path
from typing import Any, cast
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .errors import DimensionMismatchError, IndexNotBuiltError, IndexStaleError, MnemeError

MNEME_OK = 0
MNEME_ERROR_INVALID_ARGUMENT = 1
MNEME_ERROR_OUT_OF_MEMORY = 2
MNEME_ERROR_DIMENSION_MISMATCH = 3
MNEME_ERROR_IO = 4
MNEME_ERROR_INDEX_NOT_BUILT = 5
MNEME_ERROR_INDEX_STALE = 6
MNEME_ERROR_INTERNAL = 255

MNEME_METRIC_COSINE = 1
MNEME_EF_SEARCH_DEFAULT = 0


class Metric(IntEnum):
    COSINE = MNEME_METRIC_COSINE


class MnemeHnswConfig(ctypes.Structure):
    _fields_ = [
        ("m", ctypes.c_uint32),
        ("ef_construction", ctypes.c_uint32),
        ("ef_search", ctypes.c_uint32),
        ("seed", ctypes.c_uint64),
    ]


_ALLOWED_DOWNLOAD_HOSTS = {
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}

_LIB_INSTANCE: ctypes.CDLL | None = None
_LOGGER = logging.getLogger("mneme")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _validated_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise OSError(f"Only https URLs are allowed for release download, got: {url}")
    if parsed.hostname not in _ALLOWED_DOWNLOAD_HOSTS:
        raise OSError(f"Unsupported download host for release download: {parsed.hostname}")
    return url


def _safe_extract_tar(tf: tarfile.TarFile, out_dir: Path) -> None:
    output_root = out_dir.resolve()
    for member in tf.getmembers():
        if member.issym() or member.islnk():
            raise OSError(f"Refusing to extract link entry from archive: {member.name}")
        if not (member.isdir() or member.isreg()):
            raise OSError(f"Refusing to extract unsupported archive entry type: {member.name}")
        member_target = (out_dir / member.name).resolve()
        if output_root not in member_target.parents and member_target != output_root:
            raise OSError(f"Unsafe tar member path detected: {member.name}")
    for member in tf.getmembers():
        tf.extract(member, out_dir)


def _library_filenames() -> list[str]:
    if os.name == "nt":
        return ["mneme.dll"]
    system = platform.system().lower()
    if system == "darwin":
        return ["libmneme.dylib"]
    return ["libmneme.so"]


def _candidate_library_paths() -> list[Path]:
    paths: list[Path] = []
    explicit = os.environ.get("MNEME_LIBRARY_PATH")
    if explicit:
        paths.append(Path(explicit))

    package_dir = Path(__file__).resolve().parent
    for name in _library_filenames():
        paths.append(package_dir / "_native" / name)

    explicit_repo = os.environ.get("MNEME_REPO_PATH")
    if explicit_repo:
        repo = Path(explicit_repo).expanduser()
        for name in _library_filenames():
            paths.extend([repo / "zig-out" / "lib" / name, repo / name])

    package_file = Path(__file__).resolve()
    repo_root = package_file.parents[3]
    sibling_mneme = repo_root.parent / "mneme"
    names = _library_filenames()

    for name in names:
        paths.extend(
            [
                sibling_mneme / "zig-out" / "lib" / name,
                sibling_mneme / name,
                Path.cwd() / "zig-out" / "lib" / name,
                Path.cwd() / name,
            ]
        )
    return paths


def _release_platform_id() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        if machine in ("arm64", "aarch64"):
            return "macos-arm64"
        if machine in ("x86_64", "amd64"):
            return "macos-x86_64"
    if system == "linux" and machine in ("x86_64", "amd64"):
        return "linux-x86_64"
    raise OSError(
        f"Unsupported platform for release auto-download: system={system} machine={machine}"
    )


def _cache_dir() -> Path:
    explicit = os.environ.get("MNEME_CACHE_DIR")
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".cache" / "mneme-python"


def _fetch_json(url: str) -> dict[str, Any]:
    checked_url = _validated_url(url)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "mneme-python"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        checked_url,
        headers=headers,
    )
    with urlopen(request, timeout=15) as response:  # nosec B310
        data = response.read()
    return cast(dict[str, Any], json.loads(data.decode("utf-8")))


def _resolve_release_asset(tag: str, platform_id: str) -> tuple[str, str]:
    if tag == "latest":
        api_url = "https://api.github.com/repos/mneme-db/mneme/releases/latest"
    else:
        api_url = f"https://api.github.com/repos/mneme-db/mneme/releases/tags/{tag}"
    payload = _fetch_json(api_url)
    resolved_tag = str(payload["tag_name"])
    suffix = f"-{platform_id}.tar.gz"
    for asset in payload.get("assets", []):
        name = str(asset.get("name", ""))
        if name.endswith(suffix):
            return str(asset["browser_download_url"]), resolved_tag
    raise OSError(f"No release asset found for platform '{platform_id}' in tag '{resolved_tag}'")


def _download_release_library() -> Path | None:
    if not _env_bool("MNEME_AUTO_DOWNLOAD", True):
        return None

    names = _library_filenames()
    if not names:
        return None
    libname = names[0]

    platform_id = _release_platform_id()
    tag = os.environ.get("MNEME_RELEASE_TAG", "latest")
    cache_root = _cache_dir()
    requested_dir = cache_root / tag / platform_id
    if requested_dir.exists():
        cached = requested_dir / "lib" / libname
        if cached.exists():
            return cached

    download_url, resolved_tag = _resolve_release_asset(tag, platform_id)
    out_dir = cache_root / resolved_tag / platform_id
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / "release.tar.gz"
    if not archive_path.exists():
        checked_url = _validated_url(download_url)
        headers = {"User-Agent": "mneme-python"}
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(checked_url, headers=headers)
        with urlopen(request, timeout=30) as response:  # nosec B310
            archive_path.write_bytes(response.read())

    with tarfile.open(archive_path, "r:gz") as tf:
        _safe_extract_tar(tf, out_dir)

    extracted = out_dir / "lib" / libname
    if extracted.exists():
        return extracted

    for candidate in out_dir.rglob(libname):
        if candidate.is_file():
            return candidate
    return None


def _load_library() -> ctypes.CDLL:
    errors: list[str] = []
    debug = _env_bool("MNEME_DEBUG_LOAD", False)
    attempts: list[str] = []
    if debug:
        if not _LOGGER.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("[mneme] %(message)s"))
            _LOGGER.addHandler(handler)
        _LOGGER.setLevel(logging.DEBUG)

    def _debug(msg: str) -> None:
        if debug:
            _LOGGER.debug(msg)

    for candidate in _candidate_library_paths():
        attempts.append(f"candidate:{candidate}")
        if not candidate.exists():
            continue
        try:
            lib = ctypes.CDLL(str(candidate))
            _debug(f"loaded native library from candidate path: {candidate}")
            return lib
        except OSError as exc:
            errors.append(f"{candidate}: {exc}")

    names = _library_filenames()
    for name in names:
        attempts.append(f"loader:{name}")
        try:
            lib = ctypes.CDLL(name)
            _debug(f"loaded native library from system loader name: {name}")
            return lib
        except OSError as exc:
            errors.append(f"{name}: {exc}")

    try:
        attempts.append("release-download")
        downloaded = _download_release_library()
        if downloaded and downloaded.exists():
            lib = ctypes.CDLL(str(downloaded))
            _debug(f"loaded native library from downloaded release: {downloaded}")
            return lib
        errors.append("release-download: no compatible library found in downloaded release asset")
    except (OSError, URLError, tarfile.TarError, ValueError) as exc:
        errors.append(f"release-download: {exc}")

    detail = "; ".join(errors) if errors else "no candidate library found"
    if debug:
        _debug(f"load attempts: {', '.join(attempts)}")
        _debug(f"load errors: {detail}")
    raise OSError(
        "Unable to load mneme native library. "
        "Tried local paths, system loader, and release auto-download. "
        "You can set MNEME_LIBRARY_PATH directly, set MNEME_RELEASE_TAG "
        "(default: latest), or disable auto-download via MNEME_AUTO_DOWNLOAD=0. "
        f"Details: {detail}"
    )


CollectionHandle = ctypes.c_void_p
ResultsHandle = ctypes.c_void_p


def _bind_function_signatures(lib: ctypes.CDLL) -> None:
    lib.mneme_last_error.argtypes = []
    lib.mneme_last_error.restype = ctypes.c_char_p

    lib.mneme_abi_version.argtypes = []
    lib.mneme_abi_version.restype = ctypes.c_uint32

    lib.mneme_collection_create.argtypes = [
        ctypes.c_char_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(CollectionHandle),
    ]
    lib.mneme_collection_create.restype = ctypes.c_uint32

    lib.mneme_collection_free.argtypes = [CollectionHandle]
    lib.mneme_collection_free.restype = None

    lib.mneme_collection_insert.argtypes = [
        CollectionHandle,
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_uint32,
        ctypes.c_char_p,
    ]
    lib.mneme_collection_insert.restype = ctypes.c_uint32

    lib.mneme_collection_delete.argtypes = [CollectionHandle, ctypes.c_char_p]
    lib.mneme_collection_delete.restype = ctypes.c_uint32

    lib.mneme_collection_count.argtypes = [CollectionHandle]
    lib.mneme_collection_count.restype = ctypes.c_uint64

    lib.mneme_collection_search_flat.argtypes = [
        CollectionHandle,
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(ResultsHandle),
    ]
    lib.mneme_collection_search_flat.restype = ctypes.c_uint32

    lib.mneme_collection_build_hnsw.argtypes = [CollectionHandle, ctypes.POINTER(MnemeHnswConfig)]
    lib.mneme_collection_build_hnsw.restype = ctypes.c_uint32

    lib.mneme_collection_search_hnsw.argtypes = [
        CollectionHandle,
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(ResultsHandle),
    ]
    lib.mneme_collection_search_hnsw.restype = ctypes.c_uint32

    lib.mneme_collection_save.argtypes = [CollectionHandle, ctypes.c_char_p]
    lib.mneme_collection_save.restype = ctypes.c_uint32

    lib.mneme_collection_load.argtypes = [ctypes.c_char_p, ctypes.POINTER(CollectionHandle)]
    lib.mneme_collection_load.restype = ctypes.c_uint32

    lib.mneme_results_len.argtypes = [ResultsHandle]
    lib.mneme_results_len.restype = ctypes.c_uint32

    lib.mneme_results_id.argtypes = [ResultsHandle, ctypes.c_uint32]
    lib.mneme_results_id.restype = ctypes.c_char_p

    lib.mneme_results_score.argtypes = [ResultsHandle, ctypes.c_uint32]
    lib.mneme_results_score.restype = ctypes.c_float

    lib.mneme_results_free.argtypes = [ResultsHandle]
    lib.mneme_results_free.restype = None


def get_lib() -> ctypes.CDLL:
    global _LIB_INSTANCE
    if _LIB_INSTANCE is None:
        lib = _load_library()
        _bind_function_signatures(lib)
        _LIB_INSTANCE = lib
    return _LIB_INSTANCE


def __getattr__(name: str) -> Any:
    if name == "LIB":
        return get_lib()
    raise AttributeError(name)


def last_error_text() -> str:
    value = get_lib().mneme_last_error()
    return value.decode("utf-8") if value else "unknown mneme error"


def raise_for_status(status: int) -> None:
    if status == MNEME_OK:
        return
    message = last_error_text()
    if status == MNEME_ERROR_INVALID_ARGUMENT:
        raise ValueError(message)
    if status == MNEME_ERROR_DIMENSION_MISMATCH:
        raise DimensionMismatchError(message)
    if status == MNEME_ERROR_IO:
        raise OSError(message)
    if status == MNEME_ERROR_INDEX_NOT_BUILT:
        raise IndexNotBuiltError(message)
    if status == MNEME_ERROR_INDEX_STALE:
        raise IndexStaleError(message)
    if status == MNEME_ERROR_OUT_OF_MEMORY:
        raise MemoryError(message)
    raise MnemeError(message)
