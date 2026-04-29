from __future__ import annotations

from mneme import native


def test_resolve_release_asset_from_mocked_payload(monkeypatch):
    payload = {
        "tag_name": "v0.5.0",
        "assets": [
            {
                "name": "mneme-v0.5.0-linux-x86_64.tar.gz",
                "browser_download_url": "https://example/linux",
            },
            {
                "name": "mneme-v0.5.0-macos-arm64.tar.gz",
                "browser_download_url": "https://example/macos",
            },
        ],
    }
    monkeypatch.setattr(native, "_fetch_json", lambda _url: payload)

    url, tag = native._resolve_release_asset("latest", "macos-arm64")
    assert tag == "v0.5.0"
    assert url == "https://example/macos"
