# Contributing

Focused bug fixes, model clarifications, tests, and report improvements are
welcome.

## Before opening a change

1. Open an issue for a material model or schema change.
2. Keep examples synthetic and reproducible.
3. Do not include production traces, secrets, customer data, or private URLs.
4. Update the model identifier or JSON schema version when compatibility
   requires it.

## Local verification

```bash
python -m pip install -e '.[dev]'
ruff format --check .
ruff check .
mypy src
pytest --cov=retry_jitter_lab --cov-branch --cov-report=term-missing
python -m build
```

## Pull requests

Explain the scenario or defect, the model impact, and the verification. New
strategies need documented equations, deterministic tests, and clear state
semantics. Keep unrelated changes in separate pull requests.

By contributing, you agree that your contribution is licensed under this
repository's MIT licence.

Maintainers follow the reviewed-tag process in [Releasing](./docs/releasing.md).
