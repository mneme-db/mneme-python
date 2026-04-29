#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tarfile
from pathlib import Path
from urllib.request import Request, urlopen


def _lib_name(platform_id: str) -> str:
    if platform_id.startswith("macos-"):
        return "libmneme.dylib"
    if platform_id.startswith("linux-"):
        return "libmneme.so"
    raise ValueError(f"unsupported platform id: {platform_id}")


def _release_payload(tag: str, token: str | None) -> dict:
    if tag == "latest":
        url = "https://api.github.com/repos/mneme-db/mneme/releases/latest"
    else:
        url = f"https://api.github.com/repos/mneme-db/mneme/releases/tags/{tag}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "mneme-python-build"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _download_asset(url: str, out_file: Path, token: str | None) -> None:
    headers = {"User-Agent": "mneme-python-build"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=60) as resp:
        out_file.write_bytes(resp.read())


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and bundle mneme native library into wheel sources.")
    parser.add_argument("--tag", default="latest", help="mneme release tag (default: latest)")
    parser.add_argument(
        "--platform-id",
        required=True,
        help="release platform id, e.g. linux-x86_64, macos-arm64, macos-x86_64",
    )
    parser.add_argument("--token", default=None, help="optional GitHub token")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    bundle_dir = repo_root / "python" / "src" / "mneme" / "_native"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    payload = _release_payload(args.tag, args.token)
    suffix = f"-{args.platform_id}.tar.gz"
    asset_url = None
    for asset in payload.get("assets", []):
        name = str(asset.get("name", ""))
        if name.endswith(suffix):
            asset_url = str(asset["browser_download_url"])
            break
    if not asset_url:
        raise RuntimeError(f"no asset found for platform {args.platform_id} in tag {payload.get('tag_name')}")

    tmp_archive = bundle_dir / "release.tar.gz"
    _download_asset(asset_url, tmp_archive, args.token)

    with tarfile.open(tmp_archive, "r:gz") as tf:
        tf.extractall(bundle_dir)

    libname = _lib_name(args.platform_id)
    extracted = None
    for candidate in bundle_dir.rglob(libname):
        if candidate.is_file():
            extracted = candidate
            break
    if not extracted:
        raise RuntimeError(f"downloaded asset did not contain {libname}")

    final_lib = bundle_dir / libname
    final_lib.write_bytes(extracted.read_bytes())

    # Cleanup expanded tree and temp archive, keep only final library.
    for child in list(bundle_dir.iterdir()):
        if child == final_lib:
            continue
        if child.is_dir():
            for nested in sorted(child.rglob("*"), reverse=True):
                if nested.is_file():
                    nested.unlink()
                elif nested.is_dir():
                    nested.rmdir()
            child.rmdir()
        else:
            child.unlink()

    print(f"bundled native library: {final_lib}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
