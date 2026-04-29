#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync python/README.md from root README.md")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if python/README.md is not in sync instead of rewriting it.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    source = repo_root / "README.md"
    target = repo_root / "python" / "README.md"

    source_text = source.read_text(encoding="utf-8")
    target_text = target.read_text(encoding="utf-8") if target.exists() else ""

    if source_text == target_text:
        print("python/README.md is already in sync.")
        return 0

    if args.check:
        print("python/README.md is out of sync with README.md.", file=sys.stderr)
        print("Run: python scripts/sync_python_readme.py", file=sys.stderr)
        return 1

    target.write_text(source_text, encoding="utf-8")
    print("Updated python/README.md from README.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
