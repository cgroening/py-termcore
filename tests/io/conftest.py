from collections.abc import Iterator

import pytest

from termz.io.database import Database

SCHEMA = (
    "CREATE TABLE tasks ("
    "  id INTEGER PRIMARY KEY,"
    "  title TEXT,"
    "  done INTEGER,"
    "  note TEXT"
    ")"
)


@pytest.fixture
def db() -> Iterator[Database]:
    """An empty in-memory database holding one `tasks` table."""
    database = Database(":memory:")
    database.query(SCHEMA)
    yield database
    database.close()


@pytest.fixture
def filled_db(db: Database) -> Database:
    """The `tasks` table with three rows, ids 1 to 3."""
    db.insert("tasks", [
        {"title": "write", "done": 0, "note": "first"},
        {"title": "review", "done": 1, "note": None},
        {"title": "ship", "done": 0, "note": "last"},
    ])
    return db
