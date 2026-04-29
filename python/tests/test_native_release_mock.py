from __future__ import annotations


def test_resolve_release_asset_from_mocked_payload(monkeypatch, native_module):
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
    monkeypatch.setattr(native_module, "_fetch_json", lambda _url: payload)

    url, tag = native_module._resolve_release_asset("latest", "macos-arm64")
    assert tag == "v0.5.0"
    assert url == "https://example/macos"
