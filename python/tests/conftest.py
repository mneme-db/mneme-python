from __future__ import annotations

import importlib

import pytest


@pytest.fixture(scope="session")
def mneme_module():
    try:
        return importlib.import_module("mneme")
    except OSError as exc:
        pytest.skip(f"native library unavailable: {exc}")


@pytest.fixture(scope="session")
def native_module():
    try:
        return importlib.import_module("mneme.native")
    except OSError as exc:
        pytest.skip(f"native library unavailable: {exc}")
