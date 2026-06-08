# Contributing to esport-api

Thanks for wanting to contribute! 🎉 This document explains how to take part.

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.

## Setting up the dev environment

```bash
git clone https://github.com/Kwickos/esport-api.git
cd esport-api
make dev          # creates the venv, installs ".[dev]" and the pre-commit hooks
cp .env.example .env
```

Check that everything passes:

```bash
make lint         # ruff check
make test         # pytest
```

## Branching model

- `main` — stable and always green; every commit is releasable. Tagged releases are cut from here.
- `develop` — integration branch where features land first.
- `feat/*`, `fix/*`, `docs/*`, … — short-lived topic branches, one per change.

Open topic branches from `develop` and target your PRs at `develop`. Releases are merged `develop → main` and tagged.

## Workflow

1. **Open an issue** first to discuss any non-trivial change.
2. **Fork** + create a branch from `develop`:
   `git switch -c feat/my-feature`
3. Code, add **tests**, and keep `make lint` and `make test` green.
4. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: ...` new feature
   - `fix: ...` bug fix
   - `docs: ...` documentation
   - `refactor: ...` · `test: ...` · `chore: ...` · `ci: ...`
5. Open a **Pull Request** against `develop` and fill in the template.

## Code style

- **Python 3.11+**, formatted and linted by [ruff](https://github.com/astral-sh/ruff)
  (`make format` before committing; `pre-commit` does it automatically).
- Comments and docstrings in English, identifiers in English.
- Keep the architecture **source-agnostic**: every new data source
  goes through a `SourceAdapter` and produces `NormalizedFrame`s — never couple
  the core (diff engine, API) to a specific source.

## Adding a data source

This is the main extension point. To add a game or a source:

1. Create `app/sources/<my_source>.py` implementing the `Protocol` from
   [`app/sources/base.py`](app/sources/base.py) (`list_live_games`, `fetch_slice`).
2. Map the raw data to the types in [`app/schemas/domain.py`](app/schemas/domain.py).
3. Add tests. The diff engine and the API do **not** need to change.

## Reporting a bug

Use the "Bug report" issue template. Include the version, the reproduction steps,
and the expected vs observed behavior.

## License of contributions

By contributing, you agree that your code will be distributed under the project's [MIT license](LICENSE).
