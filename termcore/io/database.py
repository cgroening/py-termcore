"""
Lightweight database management module for handling SQLite databases with ease.

This module provides an abstraction layer for SQLite databases, simplifying
common database operations such as fetching, inserting, updating and deleting
records. It includes classes for defining query conditions, sorting orders
and combination operators to facilitate SQL query construction.

Features:

- Establish and manage SQLite database connections
- Query execution with debugging support
- Fetching data with filtering, ordering, and pagination
- Insert, update, and delete operations with structured condition handling
- Automatic resource management using context (`with` statement)
- Ensures proper connection closure on object deletion

Ideal for applications requiring a simple, efficient database interaction layer.

How statements are built
------------------------
The `# noqa: S608` markers below say the same thing in machine terms: the
rule sees an f-string in a statement and cannot see that every value is a
parameter and every identifier came through `_quoted_table` or
`_quoted_column`, which reject anything the schema does not know.

Values never reach the statement text. They are bound as parameters, so no
value can be read as SQL, whatever it contains.

Identifiers cannot be parameters - SQL has no placeholder for a table or a
column - so they are checked against the schema of the open database before
they are used, and quoted afterwards. A name that is not a table, or not a
column of the table being addressed, raises `UnknownIdentifierError` instead
of becoming a fragment of the query.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, cast

from termcore.io.errors import EmptyConditionsError, UnknownIdentifierError

__all__ = [
    "VALUELESS_OPERATORS",
    "ColumnOrder",
    "Condition",
    "Database",
    "SQLCombinationOperator",
    "SQLComparisonOperator",
    "SQLOrderByDirection",
]

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from types import TracebackType

_logger = logging.getLogger(__name__)


class SQLComparisonOperator(Enum):
    """
    Enumeration defining comparison operators for SQL queries.

    `IS_NULL` and `IS_NOT_NULL` are complete on their own; the `value` of a
    `Condition` using them is ignored.
    """

    LT = "<"
    LE = "<="
    EQ = "="
    NE = "!="
    GE = ">="
    GT = ">"
    LIKE = "LIKE"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"


# The operators that carry no value and therefore bind no parameter
VALUELESS_OPERATORS = (
    SQLComparisonOperator.IS_NULL,
    SQLComparisonOperator.IS_NOT_NULL,
)


class SQLCombinationOperator(Enum):
    """Combination operators (AND, OR) joining two SQL conditions."""

    AND = "AND"
    OR = "OR"


class SQLOrderByDirection(Enum):
    """Enumeration defining sorting order (ASC or DESC) for SQL queries."""

    ASC = "ASC"
    DESC = "DESC"


@dataclass(slots=True, frozen=True)
class ColumnOrder:
    """
    Class representing column sorting order in SQL queries.

    Attributes
    ----------
    column_name : str
        Name of the column to sort by.
    direction : SQLOrderByDirection
        Direction of sorting (ASC or DESC).
    """

    column_name: str
    direction: SQLOrderByDirection


@dataclass(slots=True, frozen=True)  # Higher memory efficiency with slots=True
class Condition:
    """
    Class representing a condition for the WHERE statement of an SQL query.

    Attributes
    ----------
    column_name : str
        Name of the column for the condition.
    operator : SQLComparisonOperator
        Comparison operator to use.
    value : str or int or float or bytes or None, optional
        Value to compare against. Ignored by `IS_NULL` and `IS_NOT_NULL`.
    combination : SQLCombinationOperator, optional
        Logical operator joining this condition to the previous one (default
        is AND). The first condition of a list has nothing to join to, so its
        combination is ignored.

    Examples
    --------
    >>> model = Condition("model", SQLComparisonOperator.EQ, "standard")
    >>> size = Condition("size", SQLComparisonOperator.GE, 4)

    These conditions are translated by the Database class into this WHERE
    statement, with both values bound as parameters::

        WHERE "model" = ? AND "size" >= ?
    """

    column_name: str
    operator: SQLComparisonOperator
    value: str | int | float | bytes | None = None
    combination: SQLCombinationOperator = SQLCombinationOperator.AND


class Database:
    """
    Class for managing an SQLite database.

    It provides a structured API for retrieving, inserting, updating and
    deleting data.

    Attributes
    ----------
    debug_mode : bool
        If this is True, every statement is written to the module logger at
        debug level before it runs.
    connection : sqlite3.Connection
        Instance of the database connection.
    cursor : sqlite3.Cursor
        Instance of the database cursor.
    """

    connection: sqlite3.Connection
    cursor: sqlite3.Cursor
    debug_mode: bool
    _table_cache: frozenset[str] | None
    _column_cache: dict[str, frozenset[str]]


    def __init__(self, database: str) -> None:
        """
        Opens the connection to the database.

        Parameters
        ----------
        database : str
            Path of the SQLite database file.
        """
        self.debug_mode = False
        self._table_cache = None
        self._column_cache = {}

        # Establish database connection
        self.connection = sqlite3.connect(database=database)

        # Make sure that a dictionary in the form {column_name: value} is
        # returned on queries (instead of a list with just the values)
        self.connection.row_factory = sqlite3.Row

        # Get cursor
        self.cursor = self.connection.cursor()

    def __enter__(self) -> Database:
        """
        Enables the use of the `with` statement for the database connection.

        Returns
        -------
        Database
            The Database instance.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None
    ) -> None:
        """
        Commits and closes the connection when leaving a `with` block.

        On the way out of an exception the transaction is rolled back
        instead, so a block that failed half way through leaves nothing
        behind.

        Parameters
        ----------
        exc_type : type or None
            Exception type if an exception was raised.
        exc_value : Exception or None
            Exception instance if an exception was raised.
        traceback : traceback or None
            Traceback object if an exception was raised.
        """
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()

        self.close()

    def __del__(self) -> None:
        """Closes the connection when the object is garbage collected."""
        # __init__ may have failed before the connection was assigned, and an
        # AttributeError raised in here would surface as an unraisable
        if hasattr(self, "connection"):
            self.close()

    def close(self) -> None:
        """Closes the database connection."""
        if self.connection:
            self.connection.close()

    def query(
        self, sql: str, params: Sequence[object] = ()
    ) -> sqlite3.Cursor:
        """
        Runs an SQL command.

        Use this method for commands that are not wrapped by this class. It
        is the one place where the statement text comes from the caller, so
        pass values through `params` rather than formatting them into `sql`.

        Parameters
        ----------
        sql : str
            The SQL command, with a `?` for every value.
        params : Sequence[object], optional
            Values bound to the placeholders in `sql`.

        Returns
        -------
        sqlite3.Cursor
            The cursor.
        """
        # The statement may have altered the schema, and the schema is what
        # the identifier check is validated against
        self._invalidate_schema_cache()

        return self._execute(sql, params)

    def fetch(  # noqa: PLR0913 - the clauses of a SELECT are the point
            self,
            table: str,
            columns: list[str] | None = None,
            conditions: list[Condition] | None = None,
            orderby: list[ColumnOrder] | None = None,
            limit: int | None = None,
            offset: int | None = None
    ) -> list[dict[str, str | int | float | bytes | None]]:
        """
        Fetches entries from a table.

        Parameters
        ----------
        table : str
            Name of the table.
        columns : list[str] or None, optional
            Optional list of columns to be fetched; if None is given
            all columns will be fetched.
        conditions : list[Condition] or None, optional
            Optional list of conditions.
        orderby : list[ColumnOrder] or None, optional
            Optional list defining column order.
        limit : int or None, optional
            Optional limit for the query.
        offset : int or None, optional
            Optional offset for the query.

        Returns
        -------
        list[dict[str, Any]]
            List of dictionaries in the form [{column_name: value}]

        Raises
        ------
        UnknownIdentifierError
            If the table or one of the columns is not part of the schema.
        ValueError
            If `columns` is an empty list, or a limit or offset is negative.
        """
        quoted_table = self._quoted_table(table)
        sql = f"SELECT {self._select_list(table, columns)} FROM {quoted_table}"  # noqa: S608
        params: list[object] = []

        # WHERE
        if conditions:
            where_sql, where_params = self._build_where(table, conditions)
            sql += f" WHERE {where_sql}"
            params.extend(where_params)

        # ORDER BY
        if orderby:
            sql += f" ORDER BY {self._order_list(table, orderby)}"

        # LIMIT / OFFSET
        limit_sql, limit_params = self._build_limit(limit, offset)
        sql += limit_sql
        params.extend(limit_params)

        rows: list[sqlite3.Row] = self._execute(sql, params).fetchall()

        return [dict(row) for row in rows]

    def insert(self, table: str, data: Sequence[Mapping[str, object]]) \
    -> list[dict[str, str | int | float | bytes | None]]:
        """
        Inserts rows into the table.

        All rows are written in one transaction: if any of them fails, none
        of them is kept.

        Parameters
        ----------
        table : str
            Name of the table.
        data : Sequence[Mapping[str, object]]
            List of dictionaries, e.g.:
            data = [{'col1': 'val1', 'col2': 'val2'}, ...]

        Returns
        -------
        list[dict[str, str | int | float | bytes | None]]
            List of dictionaries containing the inserted rows, e.g.:
            [{'id': 1, 'col1': 'val1', 'col2': 'val2'}, ...]

        Raises
        ------
        UnknownIdentifierError
            If the table or one of the columns is not part of the schema.
        ValueError
            If one of the rows has no columns.
        """
        quoted_table = self._quoted_table(table)
        inserted: list[dict[str, str | int | float | bytes | None]] = []

        try:
            for row in data:
                inserted.append(self._insert_row(table, quoted_table, row))
        except Exception:
            self.connection.rollback()
            raise

        self.connection.commit()

        return inserted

    def update(
        self, table: str,
        values: Mapping[str, object],
        conditions: list[Condition]
    ) -> int:
        """
        Updates every row matching the given conditions.

        Parameters
        ----------
        table : str
            Name of the table.
        values : Mapping[str, object]
            New values, in the form {column_name: value}.
        conditions : list[Condition]
            Conditions selecting the rows to update.

        Returns
        -------
        int
            Number of rows that were changed.

        Raises
        ------
        EmptyConditionsError
            If `conditions` is empty. Rewriting every row is not something
            this method does by accident.
        UnknownIdentifierError
            If the table or one of the columns is not part of the schema.
        ValueError
            If `values` is empty.
        """
        if not conditions:
            raise EmptyConditionsError("update")
        if not values:
            raise ValueError("values must not be empty")

        quoted_table = self._quoted_table(table)
        columns = list(values.keys())
        assignments = ", ".join(
            f"{self._quoted_column(table, column)} = ?" for column in columns
        )
        where_sql, where_params = self._build_where(table, conditions)

        sql = f"UPDATE {quoted_table} SET {assignments} WHERE {where_sql}"  # noqa: S608
        params = [values[column] for column in columns] + where_params

        cursor = self._execute(sql, params)
        self.connection.commit()

        return cursor.rowcount

    def remove(self, table: str, conditions: list[Condition]) -> int:
        """
        Removes the rows from the table which match the list of conditions.

        Parameters
        ----------
        table : str
            Name of the table.
        conditions : list[Condition]
            List of conditions.

        Returns
        -------
        int
            Number of rows that were deleted.

        Raises
        ------
        EmptyConditionsError
            If `conditions` is empty. Emptying the table is not something
            this method does by accident.
        UnknownIdentifierError
            If the table or one of the columns is not part of the schema.
        """
        if not conditions:
            raise EmptyConditionsError("delete")

        quoted_table = self._quoted_table(table)
        where_sql, where_params = self._build_where(table, conditions)

        sql = f"DELETE FROM {quoted_table} WHERE {where_sql}"  # noqa: S608

        cursor = self._execute(sql, where_params)
        self.connection.commit()

        return cursor.rowcount

    def save(self) -> None:
        """Commits the current transaction."""
        self.connection.commit()

    def _insert_row(
        self, table: str, quoted_table: str, row: Mapping[str, object]
    ) -> dict[str, str | int | float | bytes | None]:
        """Inserts one row and returns it as it was stored."""
        if not row:
            raise ValueError("cannot insert a row without any columns")

        columns = list(row.keys())
        column_list = ", ".join(
            self._quoted_column(table, column) for column in columns
        )
        placeholders = ", ".join("?" for _ in columns)

        sql = (f"INSERT INTO {quoted_table} ({column_list}) "  # noqa: S608
               f"VALUES ({placeholders})")
        cursor = self._execute(sql, [row[column] for column in columns])

        # Read the row back by rowid: every ordinary table has one, whatever
        # its own columns happen to be called
        stored: sqlite3.Row | None = self._execute(
            f"SELECT * FROM {quoted_table} WHERE rowid = ?",  # noqa: S608
            [cursor.lastrowid]
        ).fetchone()

        # A table without a rowid cannot be read back this way; handing
        # the caller what was written beats handing them nothing
        if stored is None:
            return cast(
                "dict[str, str | int | float | bytes | None]", dict(row)
            )

        return dict(stored)

    def _select_list(self, table: str, columns: list[str] | None) -> str:
        """Builds the column list of a SELECT, or `*` for all columns."""
        if columns is None:
            return "*"
        if not columns:
            raise ValueError(
                "columns must not be empty; pass None to select all columns"
            )

        return ", ".join(
            self._quoted_column(table, column) for column in columns
        )

    def _order_list(self, table: str, orderby: list[ColumnOrder]) -> str:
        """Builds the column list of an ORDER BY clause."""
        return ", ".join(
            f"{self._quoted_column(table, column.column_name)} "
            f"{column.direction.value}"
            for column in orderby
        )

    def _build_where(
        self, table: str, conditions: list[Condition]
    ) -> tuple[str, list[object]]:
        """
        Builds a WHERE clause plus the values bound to its placeholders.

        The first condition has nothing to join to, so its `combination` is
        ignored.
        """
        fragments: list[str] = []
        params: list[object] = []

        for position, condition in enumerate(conditions):
            # Add "AND"/"OR" if it's not the first condition
            if position > 0:
                fragments.append(condition.combination.value)

            column = self._quoted_column(table, condition.column_name)
            if condition.operator in VALUELESS_OPERATORS:
                fragments.append(f"{column} {condition.operator.value}")
            else:
                fragments.append(f"{column} {condition.operator.value} ?")
                params.append(condition.value)

        return " ".join(fragments), params

    def _build_limit(
        self, limit: int | None, offset: int | None
    ) -> tuple[str, list[object]]:
        """
        Builds the LIMIT and OFFSET clause.

        SQLite accepts OFFSET only together with LIMIT, so an offset given on
        its own is paired with -1, which is SQLite's "no limit".
        """
        if limit is not None and limit < 0:
            raise ValueError(f"limit must not be negative, got {limit}")
        if offset is not None and offset < 0:
            raise ValueError(f"offset must not be negative, got {offset}")

        if limit is None and offset is None:
            return "", []

        clause = " LIMIT ?"
        params: list[object] = [-1 if limit is None else limit]

        if offset is not None:
            clause += " OFFSET ?"
            params.append(offset)

        return clause, params

    def _quoted_table(self, table: str) -> str:
        """Checks a table name against the schema and quotes it."""
        known = self._table_names()
        if table not in known:
            raise UnknownIdentifierError(table, tuple(sorted(known)))

        return _quote_identifier(table)

    def _quoted_column(self, table: str, column: str) -> str:
        """Checks a column name against the table's schema and quotes it."""
        known = self._column_names(table)
        if column not in known:
            raise UnknownIdentifierError(column, tuple(sorted(known)))

        return _quote_identifier(column)

    def _table_names(self) -> frozenset[str]:
        """Returns the names of every table and view in the database."""
        if self._table_cache is None:
            rows: list[sqlite3.Row] = self._execute(
                "SELECT name FROM sqlite_master "
                "WHERE type IN ('table', 'view')"
            ).fetchall()
            self._table_cache = frozenset(
                cast("str", row["name"]) for row in rows
            )

        return self._table_cache

    def _column_names(self, table: str) -> frozenset[str]:
        """Returns the column names of the given table."""
        if table not in self._column_cache:
            quoted_table = self._quoted_table(table)
            rows: list[sqlite3.Row] = self._execute(
                f"PRAGMA table_info({quoted_table})"
            ).fetchall()
            self._column_cache[table] = frozenset(
                cast("str", row["name"]) for row in rows
            )

        return self._column_cache[table]

    def _invalidate_schema_cache(self) -> None:
        """Forgets the cached schema, e.g. after a statement that altered it."""
        self._table_cache = None
        self._column_cache.clear()

    def _execute(
        self, sql: str, params: Sequence[object] = ()
    ) -> sqlite3.Cursor:
        """Runs one statement with its values bound as parameters."""
        if self.debug_mode:
            _logger.debug("SQL: %s -- params: %r", sql, list(params))

        return self.cursor.execute(sql, params)


def _quote_identifier(name: str) -> str:
    """
    Quotes an identifier so that it can be used in a statement.

    Quoting is what makes a reserved word or a name containing a space usable
    as a column. It is not the safety mechanism on its own - the callers check
    the name against the schema first.
    """
    escaped = name.replace("\"", "\"\"")

    return "\"" + escaped + "\""
