# mneme-python

[![CI](https://github.com/mneme-db/mneme-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/mneme-db/mneme-python/actions/workflows/ci.yml)
[![Release Check](https://github.com/mneme-db/mneme-python/actions/workflows/release-check.yml/badge.svg)](https://github.com/mneme-db/mneme-python/actions/workflows/release-check.yml)
[![Release](https://github.com/mneme-db/mneme-python/actions/workflows/release.yml/badge.svg)](https://github.com/mneme-db/mneme-python/actions/workflows/release.yml)
[![TestPyPI](https://github.com/mneme-db/mneme-python/actions/workflows/testpypi.yml/badge.svg)](https://github.com/mneme-db/mneme-python/actions/workflows/testpypi.yml)

Python wrapper package for [`mneme`](https://github.com/mneme-db/mneme), the embedded-first vector/memory database core written in Zig.

## Status

Phase 6 initial wrapper is implemented with a `ctypes` binding over the stable C ABI.

## Install from source

```bash
pip install -e ./python
```

## Canonical documentation

Use `python/README.md` as the canonical Python package guide:

- installation and environment setup
- full API usage examples
- native library loader behavior and environment variables
- testing and quality checks
- troubleshooting

Quick link: [`python/README.md`](python/README.md)

## Minimal example

```python
from mneme import Collection, Metric

db = Collection("docs", dimension=3, metric=Metric.COSINE)
db.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
db.insert("b", [0.0, 1.0, 0.0], metadata="beta")
print(db.search([1.0, 0.0, 0.0], k=2))
db.close()
```

## Known limitations

- No wheels published yet.
- Native library may be auto-fetched from releases; offline usage still requires local library availability.
- Windows support is not included in this phase.
- Metadata remains string-only.
- HNSW index is not persisted.
- PyOZ remains experimental and not the production binding path in Phase 6.

## CI/CD

GitHub Actions is configured with:

- `CI` workflow on pushes/PRs:
  - matrix testing on macOS/Linux and Python `3.10`, `3.12`, `3.14`
  - `ruff`, `bandit`, `mypy`, and `pytest` with coverage gate
  - package build validation (`python -m build` + `twine check`)
- `Release` workflow on published GitHub releases:
  - builds package and publishes to PyPI via trusted publishing (OIDC)
- `Release Check` workflow on `v*` tag pushes:
  - verifies tag/version parity before release steps
  - builds package + runs `twine check` for artifact integrity
- `Publish TestPyPI` workflow:
  - publishes prerelease or manually dispatched builds to TestPyPI
  - validates release tag/version parity before publish
- Dependabot for GitHub Actions and Python dependency updates.
