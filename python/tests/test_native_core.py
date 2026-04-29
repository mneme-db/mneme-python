from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from mneme.errors import DimensionMismatchError, IndexNotBuiltError, IndexStaleError, MnemeError


def test_validated_url_accepts_known_host(native_module):
    url = "https://api.github.com/repos/mneme-db/mneme/releases/latest"
    assert native_module._validated_url(url) == url


def test_validated_url_rejects_non_https(native_module):
    with pytest.raises(OSError, match="Only https URLs are allowed"):
        native_module._validated_url("http://api.github.com/repos/mneme-db/mneme/releases/latest")


def test_validated_url_rejects_unknown_host(native_module):
    with pytest.raises(OSError, match="Unsupported download host"):
        native_module._validated_url("https://example.com/release.tgz")


def test_release_platform_id_paths(monkeypatch, native_module):
    monkeypatch.setattr(native_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(native_module.platform, "machine", lambda: "arm64")
    assert native_module._release_platform_id() == "macos-arm64"

    monkeypatch.setattr(native_module.platform, "machine", lambda: "x86_64")
    assert native_module._release_platform_id() == "macos-x86_64"

    monkeypatch.setattr(native_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(native_module.platform, "machine", lambda: "amd64")
    assert native_module._release_platform_id() == "linux-x86_64"


def test_release_platform_id_unsupported(monkeypatch, native_module):
    monkeypatch.setattr(native_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(native_module.platform, "machine", lambda: "arm64")
    with pytest.raises(OSError, match="Unsupported platform"):
        native_module._release_platform_id()


def test_safe_extract_tar_rejects_escape(tmp_path, native_module):
    tar_path = tmp_path / "bad.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        info = tarfile.TarInfo("../escape.txt")
        payload = b"bad"
        info.size = len(payload)
        tf.addfile(info, io.BytesIO(payload))

    with (
        tarfile.open(tar_path, "r:gz") as tf,
        pytest.raises(OSError, match="Unsafe tar member path detected"),
    ):
        native_module._safe_extract_tar(tf, tmp_path / "out")


def test_safe_extract_tar_extracts_valid_member(tmp_path, native_module):
    tar_path = tmp_path / "ok.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        info = tarfile.TarInfo("lib/libmneme.dylib")
        payload = b"ok"
        info.size = len(payload)
        tf.addfile(info, io.BytesIO(payload))

    out = tmp_path / "out"
    out.mkdir()
    with tarfile.open(tar_path, "r:gz") as tf:
        native_module._safe_extract_tar(tf, out)
    assert (out / "lib" / "libmneme.dylib").exists()


def test_cache_dir_env_override(monkeypatch, tmp_path, native_module):
    monkeypatch.setenv("MNEME_CACHE_DIR", str(tmp_path))
    assert native_module._cache_dir() == tmp_path


def test_download_release_library_disabled(monkeypatch, native_module):
    monkeypatch.setenv("MNEME_AUTO_DOWNLOAD", "0")
    assert native_module._download_release_library() is None


def test_download_release_library_uses_cached_requested_dir(monkeypatch, tmp_path, native_module):
    lib_name = "libmneme.dylib"
    cached = tmp_path / "latest" / "macos-arm64" / "lib"
    cached.mkdir(parents=True)
    lib_path = cached / lib_name
    lib_path.write_bytes(b"x")

    monkeypatch.setenv("MNEME_AUTO_DOWNLOAD", "1")
    monkeypatch.setenv("MNEME_RELEASE_TAG", "latest")
    monkeypatch.setattr(native_module, "_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(native_module, "_release_platform_id", lambda: "macos-arm64")
    monkeypatch.setattr(native_module, "_library_filenames", lambda: [lib_name])

    assert native_module._download_release_library() == lib_path


def test_download_release_library_finds_nested_extracted_lib(monkeypatch, tmp_path, native_module):
    lib_name = "libmneme.dylib"
    out_dir = tmp_path / "v0.5.0" / "macos-arm64"
    nested_lib = out_dir / "mneme-v0.5.0-macos-arm64" / "lib" / lib_name
    nested_lib.parent.mkdir(parents=True, exist_ok=True)
    nested_lib.write_bytes(b"mock-lib")

    def _fake_open(_archive: Path, _mode: str):
        class _Ctx:
            def __enter__(self):
                class _FakeTar:
                    def getmembers(self):
                        return []

                    def extract(self, *args, **kwargs):
                        return None

                return _FakeTar()

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Ctx()

    monkeypatch.setenv("MNEME_AUTO_DOWNLOAD", "1")
    monkeypatch.setenv("MNEME_RELEASE_TAG", "latest")
    monkeypatch.setattr(native_module, "_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(native_module, "_release_platform_id", lambda: "macos-arm64")
    monkeypatch.setattr(native_module, "_library_filenames", lambda: [lib_name])
    monkeypatch.setattr(
        native_module,
        "_resolve_release_asset",
        lambda _tag, _pid: ("https://github.com/mneme-db/mneme/archive.tar.gz", "v0.5.0"),
    )
    monkeypatch.setattr(native_module, "urlopen", lambda *_a, **_k: io.BytesIO(b"fake"))
    monkeypatch.setattr(native_module.tarfile, "open", _fake_open)

    found = native_module._download_release_library()
    assert found == nested_lib


def test_raise_for_status_mappings(monkeypatch, native_module):
    monkeypatch.setattr(native_module, "last_error_text", lambda: "boom")
    with pytest.raises(ValueError):
        native_module.raise_for_status(native_module.MNEME_ERROR_INVALID_ARGUMENT)
    with pytest.raises(DimensionMismatchError):
        native_module.raise_for_status(native_module.MNEME_ERROR_DIMENSION_MISMATCH)
    with pytest.raises(OSError):
        native_module.raise_for_status(native_module.MNEME_ERROR_IO)
    with pytest.raises(IndexNotBuiltError):
        native_module.raise_for_status(native_module.MNEME_ERROR_INDEX_NOT_BUILT)
    with pytest.raises(IndexStaleError):
        native_module.raise_for_status(native_module.MNEME_ERROR_INDEX_STALE)
    with pytest.raises(MemoryError):
        native_module.raise_for_status(native_module.MNEME_ERROR_OUT_OF_MEMORY)
    with pytest.raises(MnemeError):
        native_module.raise_for_status(native_module.MNEME_ERROR_INTERNAL)


def test_ensure_count_zero_invalid_raises(monkeypatch, native_module):
    class _Lib:
        @staticmethod
        def mneme_collection_count(_collection):
            return 0

    monkeypatch.setattr(native_module, "LIB", _Lib())
    monkeypatch.setattr(native_module, "last_error_text", lambda: "invalid handle")
    with pytest.raises(MnemeError):
        native_module.ensure_count(None)


def test_ensure_count_zero_non_error_returns_zero(monkeypatch, native_module):
    class _Lib:
        @staticmethod
        def mneme_collection_count(_collection):
            return 0

    monkeypatch.setattr(native_module, "LIB", _Lib())
    monkeypatch.setattr(native_module, "last_error_text", lambda: "")
    assert native_module.ensure_count(None) == 0
