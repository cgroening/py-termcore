"""Tests for the SQLite wrapper: statement building, safety and lifecycle.

The point of the builder is that a caller never writes SQL, which means the
caller also never gets to check it. Two properties therefore carry the whole
module and are pinned hardest below: a value can never be read as SQL, and an
identifier that is not in the schema never reaches the statement at all.
"""

import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from termz.io.database import (
    ColumnOrder,
    Condition,
    Database,
    SQLCombinationOperator,
    SQLComparisonOperator,
    SQLOrderByDirection,
)
from termz.io.errors import EmptyConditionsError, UnknownIdentifierError

ASC = SQLOrderByDirection.ASC
DESC = SQLOrderByDirection.DESC
EQ = SQLComparisonOperator.EQ


def titles(rows: Sequence[Mapping[str, object]]) -> list[object]:
    """Returns the title of every row, in order."""
    return [row["title"] for row in rows]


class TestConnectionLifecycle:
    def test_a_clean_block_commits(self, tmp_path: Path) -> None:
        # Only insert/update/remove commit on their own, so a write made
        # through query() used to be lost when the block ended.
        path = str(tmp_path / "tasks.db")
        with Database(path) as db:
            db.query("CREATE TABLE t (a TEXT)")
            db.query("INSERT INTO t (a) VALUES (?)", ["kept"])

        with Database(path) as reopened:
            assert reopened.fetch("t") == [{"a": "kept"}]

    def test_a_failed_block_rolls_back(self, tmp_path: Path) -> None:
        path = str(tmp_path / "tasks.db")
        with Database(path) as db:
            db.query("CREATE TABLE t (a TEXT)")

        def write_then_fail() -> None:
            with Database(path) as db:
                db.query("INSERT INTO t (a) VALUES (?)", ["discarded"])
                raise RuntimeError("something went wrong")

        with pytest.raises(RuntimeError):
            write_then_fail()

        with Database(path) as reopened:
            assert reopened.fetch("t") == []

    def test_closing_twice_is_harmless(self, db: Database) -> None:
        db.close()
        db.close()

    def test_saving_after_close_is_refused(self, db: Database) -> None:
        db.close()
        with pytest.raises(sqlite3.ProgrammingError):
            db.save()

    def test_data_survives_reopening_the_file(self, tmp_path: Path) -> None:
        path = str(tmp_path / "tasks.db")
        first = Database(path)
        first.query("CREATE TABLE t (a TEXT)")
        first.insert("t", [{"a": "persisted"}])
        first.close()

        second = Database(path)
        assert second.fetch("t") == [{"a": "persisted"}]
        second.close()


class TestFetch:
    def test_returns_every_row_by_default(self, filled_db: Database) -> None:
        assert len(filled_db.fetch("tasks")) == 3

    def test_returns_dictionaries_keyed_by_column(
        self, filled_db: Database
    ) -> None:
        row = filled_db.fetch("tasks", conditions=[Condition("id", EQ, 1)])[0]

        assert row == {"id": 1, "title": "write", "done": 0, "note": "first"}

    def test_selects_the_requested_columns(
        self, filled_db: Database
    ) -> None:
        rows = filled_db.fetch("tasks", columns=["title"])

        assert rows[0] == {"title": "write"}

    def test_an_empty_column_list_is_refused(
        self, filled_db: Database
    ) -> None:
        # Used to build "SELECT  FROM tasks" and fail as a syntax error.
        with pytest.raises(ValueError):
            filled_db.fetch("tasks", columns=[])

    def test_orders_ascending(self, filled_db: Database) -> None:
        rows = filled_db.fetch("tasks", orderby=[ColumnOrder("title", ASC)])

        assert titles(rows) == ["review", "ship", "write"]

    def test_orders_descending(self, filled_db: Database) -> None:
        rows = filled_db.fetch("tasks", orderby=[ColumnOrder("title", DESC)])

        assert titles(rows) == ["write", "ship", "review"]

    def test_orders_by_several_columns(self, filled_db: Database) -> None:
        rows = filled_db.fetch("tasks", orderby=[
            ColumnOrder("done", ASC), ColumnOrder("title", ASC)
        ])

        assert titles(rows) == ["ship", "write", "review"]

    def test_the_same_order_object_twice_still_joins(
        self, filled_db: Database
    ) -> None:
        # The separator used to be chosen with `is not orderby[-1]`, so the
        # same object at two positions produced "title ASCtitle ASC".
        order = ColumnOrder("title", ASC)

        rows = filled_db.fetch("tasks", orderby=[order, order])

        assert titles(rows) == ["review", "ship", "write"]

    def test_applies_a_limit(self, filled_db: Database) -> None:
        assert len(filled_db.fetch("tasks", limit=2)) == 2

    def test_a_limit_of_zero_returns_nothing(
        self, filled_db: Database
    ) -> None:
        # Used to be dropped by a `> 0` guard, so LIMIT 0 was unreachable.
        assert filled_db.fetch("tasks", limit=0) == []

    def test_applies_an_offset_together_with_a_limit(
        self, filled_db: Database
    ) -> None:
        rows = filled_db.fetch(
            "tasks", orderby=[ColumnOrder("id", ASC)], limit=1, offset=1
        )

        assert titles(rows) == ["review"]

    def test_an_offset_without_a_limit_works(
        self, filled_db: Database
    ) -> None:
        # SQLite requires LIMIT before OFFSET, so this used to be a syntax
        # error rather than a query.
        rows = filled_db.fetch(
            "tasks", orderby=[ColumnOrder("id", ASC)], offset=1
        )

        assert titles(rows) == ["review", "ship"]

    def test_a_negative_limit_is_refused(self, filled_db: Database) -> None:
        with pytest.raises(ValueError):
            filled_db.fetch("tasks", limit=-1)

    def test_a_negative_offset_is_refused(self, filled_db: Database) -> None:
        with pytest.raises(ValueError):
            filled_db.fetch("tasks", offset=-1)

    def test_empty_condition_and_order_lists_are_ignored(
        self, filled_db: Database
    ) -> None:
        assert len(filled_db.fetch("tasks", conditions=[], orderby=[])) == 3


class TestConditions:
    def test_equal(self, filled_db: Database) -> None:
        rows = filled_db.fetch("tasks", conditions=[
            Condition("title", SQLComparisonOperator.EQ, "ship")
        ])

        assert titles(rows) == ["ship"]

    def test_not_equal(self, filled_db: Database) -> None:
        # There was no way to express this at all before.
        rows = filled_db.fetch("tasks", conditions=[
            Condition("title", SQLComparisonOperator.NE, "ship")
        ], orderby=[ColumnOrder("id", ASC)])

        assert titles(rows) == ["write", "review"]

    def test_greater_and_less(self, filled_db: Database) -> None:
        rows = filled_db.fetch("tasks", conditions=[
            Condition("id", SQLComparisonOperator.GT, 1),
            Condition("id", SQLComparisonOperator.LT, 3),
        ])

        assert titles(rows) == ["review"]

    def test_greater_equal_and_less_equal(self, filled_db: Database) -> None:
        rows = filled_db.fetch("tasks", conditions=[
            Condition("id", SQLComparisonOperator.GE, 2),
            Condition("id", SQLComparisonOperator.LE, 2),
        ])

        assert titles(rows) == ["review"]

    def test_like(self, filled_db: Database) -> None:
        rows = filled_db.fetch("tasks", conditions=[
            Condition("title", SQLComparisonOperator.LIKE, "%i%")
        ], orderby=[ColumnOrder("id", ASC)])

        assert titles(rows) == ["write", "review", "ship"]

    def test_is_null_needs_no_value(self, filled_db: Database) -> None:
        rows = filled_db.fetch("tasks", conditions=[
            Condition("note", SQLComparisonOperator.IS_NULL)
        ])

        assert titles(rows) == ["review"]

    def test_is_not_null_needs_no_value(self, filled_db: Database) -> None:
        rows = filled_db.fetch("tasks", conditions=[
            Condition("note", SQLComparisonOperator.IS_NOT_NULL)
        ], orderby=[ColumnOrder("id", ASC)])

        assert titles(rows) == ["write", "ship"]

    def test_conditions_are_combined_with_and_by_default(
        self, filled_db: Database
    ) -> None:
        rows = filled_db.fetch("tasks", conditions=[
            Condition("done", EQ, 0),
            Condition("title", EQ, "ship"),
        ])

        assert titles(rows) == ["ship"]

    def test_conditions_can_be_combined_with_or(
        self, filled_db: Database
    ) -> None:
        rows = filled_db.fetch("tasks", conditions=[
            Condition("title", EQ, "write"),
            Condition(
                "title", EQ, "ship",
                combination=SQLCombinationOperator.OR
            ),
        ], orderby=[ColumnOrder("id", ASC)])

        assert titles(rows) == ["write", "ship"]

    def test_the_first_combination_is_ignored(
        self, filled_db: Database
    ) -> None:
        # The first condition has nothing to join to, so OR on it is inert.
        rows = filled_db.fetch("tasks", conditions=[
            Condition(
                "title", EQ, "ship",
                combination=SQLCombinationOperator.OR
            )
        ])

        assert titles(rows) == ["ship"]

    def test_the_same_condition_object_twice_still_joins(
        self, filled_db: Database
    ) -> None:
        # The separator used to be chosen with `is not conditions[0]`, so the
        # same object at two positions produced "id=1id=1".
        condition = Condition("id", EQ, 1)

        rows = filled_db.fetch("tasks", conditions=[condition, condition])

        assert titles(rows) == ["write"]


class TestInsert:
    def test_returns_the_stored_rows(self, db: Database) -> None:
        rows = db.insert("tasks", [{"title": "one", "done": 0}])

        assert rows == [
            {"id": 1, "title": "one", "done": 0, "note": None}
        ]

    def test_writes_every_row(self, db: Database) -> None:
        db.insert("tasks", [{"title": "one"}, {"title": "two"}])

        assert len(db.fetch("tasks")) == 2

    def test_an_empty_list_writes_nothing(self, db: Database) -> None:
        assert db.insert("tasks", []) == []

    def test_a_row_without_columns_is_refused(self, db: Database) -> None:
        with pytest.raises(ValueError):
            db.insert("tasks", [{}])

    def test_a_table_without_an_id_column_works(self, db: Database) -> None:
        # The row used to be read back with "WHERE id = lastrowid", so any
        # table without an id column failed after the write had happened.
        db.query("CREATE TABLE notes (body TEXT)")

        assert db.insert("notes", [{"body": "hello"}]) == [{"body": "hello"}]

    def test_a_failing_row_rolls_the_whole_batch_back(
        self, db: Database
    ) -> None:
        # Each row used to be committed on its own, so a failure half way
        # through left the earlier rows behind.
        with pytest.raises(sqlite3.IntegrityError):
            db.insert("tasks", [
                {"id": 1, "title": "first"},
                {"id": 1, "title": "duplicate id"},
            ])

        assert db.fetch("tasks") == []


class TestUpdate:
    def test_changes_the_matching_rows(self, filled_db: Database) -> None:
        filled_db.update("tasks", {"done": 1}, [Condition("id", EQ, 1)])

        row = filled_db.fetch("tasks", conditions=[Condition("id", EQ, 1)])[0]
        assert row["done"] == 1

    def test_returns_the_number_of_changed_rows(
        self, filled_db: Database
    ) -> None:
        changed = filled_db.update(
            "tasks", {"done": 1}, [Condition("done", EQ, 0)]
        )

        assert changed == 2

    def test_leaves_other_rows_alone(self, filled_db: Database) -> None:
        filled_db.update("tasks", {"title": "x"}, [Condition("id", EQ, 1)])

        assert titles(filled_db.fetch(
            "tasks", orderby=[ColumnOrder("id", ASC)]
        )) == ["x", "review", "ship"]

    def test_the_same_call_can_be_repeated(
        self, filled_db: Database
    ) -> None:
        # The conditions used to be carried inside the data dictionary and
        # deleted out of it while parsing, so a second identical call built
        # a statement with an empty WHERE clause.
        conditions = [Condition("id", EQ, 1)]
        values = {"done": 1}

        filled_db.update("tasks", values, conditions)
        filled_db.update("tasks", values, conditions)

        assert values == {"done": 1}
        assert len(conditions) == 1

    def test_without_conditions_it_refuses(
        self, filled_db: Database
    ) -> None:
        with pytest.raises(EmptyConditionsError):
            filled_db.update("tasks", {"done": 1}, [])

        assert filled_db.fetch("tasks", conditions=[
            Condition("done", EQ, 0)
        ]) != []

    def test_without_values_it_refuses(self, filled_db: Database) -> None:
        with pytest.raises(ValueError):
            filled_db.update("tasks", {}, [Condition("id", EQ, 1)])


class TestRemove:
    def test_deletes_the_matching_rows(self, filled_db: Database) -> None:
        filled_db.remove("tasks", [Condition("done", EQ, 0)])

        assert titles(filled_db.fetch("tasks")) == ["review"]

    def test_returns_the_number_of_deleted_rows(
        self, filled_db: Database
    ) -> None:
        assert filled_db.remove("tasks", [Condition("done", EQ, 0)]) == 2

    def test_without_conditions_it_refuses(
        self, filled_db: Database
    ) -> None:
        with pytest.raises(EmptyConditionsError):
            filled_db.remove("tasks", [])

        assert len(filled_db.fetch("tasks")) == 3


class TestIdentifiersAreCheckedAgainstTheSchema:
    """Identifiers cannot be parameters, so they are checked instead.

    Each payload below is one that reaches the database as SQL when the
    names are interpolated unchecked.
    """

    def test_an_unknown_table_is_refused(self, db: Database) -> None:
        with pytest.raises(UnknownIdentifierError):
            db.fetch("no_such_table")

    def test_an_unknown_column_is_refused(self, db: Database) -> None:
        with pytest.raises(UnknownIdentifierError):
            db.fetch("tasks", columns=["no_such_column"])

    def test_a_condition_carrying_sql_is_refused(
        self, filled_db: Database
    ) -> None:
        with pytest.raises(UnknownIdentifierError):
            filled_db.fetch("tasks", conditions=[
                Condition("1=1 OR title", EQ, "nothing")
            ])

    def test_a_table_name_carrying_sql_is_refused(
        self, filled_db: Database
    ) -> None:
        with pytest.raises(UnknownIdentifierError):
            filled_db.fetch("tasks; DROP TABLE tasks")

    def test_an_order_column_carrying_sql_is_refused(
        self, filled_db: Database
    ) -> None:
        with pytest.raises(UnknownIdentifierError):
            filled_db.fetch("tasks", orderby=[
                ColumnOrder("id, (SELECT 1)", ASC)
            ])

    def test_an_insert_column_carrying_sql_is_refused(
        self, db: Database
    ) -> None:
        with pytest.raises(UnknownIdentifierError):
            db.insert("tasks", [{"title) VALUES ('x'); --": "x"}])

    def test_the_error_names_what_would_have_been_accepted(
        self, db: Database
    ) -> None:
        with pytest.raises(UnknownIdentifierError) as caught:
            db.fetch("tasks", columns=["titel"])

        assert "title" in str(caught.value)

    def test_a_reserved_word_is_still_a_usable_column(
        self, db: Database
    ) -> None:
        # This is what the quoting is for: the name is legitimate, it just
        # collides with SQL syntax.
        db.query("CREATE TABLE t (\"order\" INTEGER)")

        db.insert("t", [{"order": 1}])

        assert db.fetch("t", columns=["order"]) == [{"order": 1}]

    def test_a_column_name_with_a_space_is_still_usable(
        self, db: Database
    ) -> None:
        db.query("CREATE TABLE t (\"my col\" TEXT)")

        db.insert("t", [{"my col": "value"}])

        assert db.fetch("t", columns=["my col"]) == [{"my col": "value"}]

    def test_a_table_created_later_is_found(self, db: Database) -> None:
        # The schema is cached, so the cache has to be dropped when a
        # statement changes it.
        db.query("CREATE TABLE later (a TEXT)")

        assert db.fetch("later") == []


class TestValuesArePassedAsParameters:
    def test_a_value_containing_a_quote_round_trips(
        self, db: Database
    ) -> None:
        db.insert("tasks", [{"title": "O'Brien"}])

        assert titles(db.fetch("tasks")) == ["O'Brien"]

    def test_a_value_that_looks_like_sql_is_stored_as_text(
        self, db: Database
    ) -> None:
        payload = "'; DROP TABLE tasks; --"

        db.insert("tasks", [{"title": payload}])

        assert titles(db.fetch("tasks")) == [payload]

    def test_none_becomes_null(self, db: Database) -> None:
        db.insert("tasks", [{"title": "a", "note": None}])

        assert db.fetch("tasks")[0]["note"] is None

    def test_bytes_round_trip(self, db: Database) -> None:
        # Rendered as the repr b'...' before, which is not valid SQL.
        db.query("CREATE TABLE blobs (data BLOB)")

        db.insert("blobs", [{"data": b"\x00\x01\x02"}])

        assert db.fetch("blobs")[0]["data"] == b"\x00\x01\x02"

    def test_a_float_round_trips(self, db: Database) -> None:
        db.query("CREATE TABLE numbers (value REAL)")

        db.insert("numbers", [{"value": 1.5}])

        assert db.fetch("numbers")[0]["value"] == 1.5

    def test_a_condition_value_is_bound_too(self, db: Database) -> None:
        db.insert("tasks", [{"title": "O'Brien"}, {"title": "other"}])

        rows = db.fetch("tasks", conditions=[
            Condition("title", EQ, "O'Brien")
        ])

        assert titles(rows) == ["O'Brien"]


class TestQuery:
    def test_binds_its_parameters(self, db: Database) -> None:
        db.query("INSERT INTO tasks (title) VALUES (?)", ["direct"])
        db.save()

        assert titles(db.fetch("tasks")) == ["direct"]

    def test_returns_a_cursor(self, db: Database) -> None:
        cursor = db.query("SELECT 1 AS one")

        assert cursor.fetchone()["one"] == 1

    def test_logs_the_statement_in_debug_mode(
        self, db: Database, caplog: pytest.LogCaptureFixture
    ) -> None:
        db.debug_mode = True

        with caplog.at_level("DEBUG", logger="termz.io.database"):
            db.fetch("tasks")

        assert "SELECT" in caplog.text

    def test_stays_quiet_otherwise(
        self, db: Database, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level("DEBUG", logger="termz.io.database"):
            db.fetch("tasks")

        assert caplog.text == ""
