# mneme Python wrapper

First Python wrapper for the `mneme` embedded vector database core.

## Install (source, local dev)

1. Install package in editable mode from this repo:

```bash
pip install -e ./python
```

2. Import and use `mneme`; the wrapper will auto-download a matching native release asset if local libs are not found.

## Usage

```python
from mneme import Collection

db = Collection("docs", dimension=3)
db.insert("a", [1.0, 0.0, 0.0], metadata="alpha")
db.insert("b", [0.0, 1.0, 0.0], metadata="beta")

results = db.search([1.0, 0.0, 0.0], k=2)
for row in results:
    print(row.id, row.score)
```

## Native library requirements

- macOS: `libmneme.dylib`
- Linux: `libmneme.so`

Lookup order:

1. `MNEME_LIBRARY_PATH`
2. `MNEME_REPO_PATH` (`<repo>/zig-out/lib` then `<repo>`)
3. `../mneme/zig-out/lib` (sibling dependency default)
4. current working directory fallbacks
5. system dynamic loader paths
6. GitHub release auto-download (cached)

Release auto-download defaults:

- repo: `mneme-db/mneme`
- tag: `latest` (override with `MNEME_RELEASE_TAG`, e.g. `v0.5.0`)
- cache dir: `~/.cache/mneme-python` (override with `MNEME_CACHE_DIR`)
- disable with `MNEME_AUTO_DOWNLOAD=0`
- debug loader selection with `MNEME_DEBUG_LOAD=1`

Debug logging example:

```python
import logging
import os

os.environ["MNEME_DEBUG_LOAD"] = "1"

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("mneme").setLevel(logging.DEBUG)

import mneme  # loader debug messages emitted via the "mneme" logger
```

API notes:

- `Collection` accepts `metric` as either `int` or `mneme.Metric` (for now: `Metric.COSINE`).
- `Collection.delete(id)` raises `ValueError` if the id does not exist.

## Testing

```bash
pytest python/tests
```

Quality checks:

```bash
ruff check python/src python/tests
ruff format --check python/src python/tests
bandit -c python/pyproject.toml -r python/src
mypy --config-file python/pyproject.toml python/src/mneme
```

CI runs the same checks in `.github/workflows/ci.yml`.

## Troubleshooting

- If import fails with native load error, set `MNEME_RELEASE_TAG` to a known release like `v0.5.0` and retry.
- Set `MNEME_LIBRARY_PATH` explicitly to a compiled shared library if you use a custom build location.
