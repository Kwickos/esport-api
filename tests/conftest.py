"""Pytest configuration: isolate the test database from the dev one."""

import os
import pathlib

# Must be set before `app.config` is imported (an env var beats .env and defaults).
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_esport.db"

import pytest  # noqa: E402

_DB = pathlib.Path("test_esport.db")


@pytest.fixture(scope="session", autouse=True)
def _clean_db():
    if _DB.exists():
        _DB.unlink()
    yield
    if _DB.exists():
        _DB.unlink()
