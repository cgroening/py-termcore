"""
termz.io.database
=================

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
"""
from __future__ import annotations
from dataclasses import dataclass
import sqlite3
import copy
from enum import Enum
from types import TracebackType
from typing import cast
from termz.util.string import linewrap


class SQLComparisonOperator(Enum):
    """
    Enumeration defining comparison operators (<, <=, =, >=, >) for SQL queries.
    """
    LT = "<"
    LE = "<="
    EQ = "="
    GE = ">="
    GT = ">"


class SQLCombinationOperator(Enum):
    """
    Enumeration defining combination operators (AND, OR) for SQL conditions.
    """
    AND = "AND"
    OR = "OR"


class SQLOrderByDirection(Enum):
    """
    Enumeration defining sorting order (ASC or DESC) for SQL queries.
    """
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
    value : str or int or float
        Value to compare against.
    combination : SQLCombinationOperator, optional
        Logical operator to combine with the next condition (default is AND).

    Examples
    --------
    >>> c1 = Condition(column='model', operator='=', value='standard')
    >>> c2 = Condition(column='size', operator='>=', value=4, combination='AND')

    These conditions translated by the Database class to this WHERE statement::

        WHERE model='standard' AND size>=4
    """
    column_name: str
    operator: SQLComparisonOperator
    value: str | int | float
    combination: SQLCombinationOperator = SQLCombinationOperator.AND


class Database:
    """
    Class for managing an SQLite database.

    It provides structured API for retrieving, inserting, updating and deleting data.

    Attributes
    ----------
    debug_mode : bool
        If this is True, the SQL statements will be printed.
    connection : sqlite3.Connection
        Instance of the database connection.
    cursor : sqlite3.Cursor
        Instance of the database cursor.
    """
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor
    debug_mode: bool = False


    def __init__(self, database: str) -> None:
        """
        Opens the connection to the database.

        Parameters
        ----------
        database : str
            Path of the SQLite database file.
        """
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

        Ensures that the connection is properly closed when exiting the block.

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
        Ensures that the database connection is closed when exiting
        a `with` block.

        Parameters
        ----------
        exc_type : type or None
            Exception type if an exception was raised.
        exc_value : Exception or None
            Exception instance if an exception was raised.
        traceback : traceback or None
            Traceback object if an exception was raised.
        """
        self.close()

    def __del__(self) -> None:
        """
        Destructor method to ensure the database connection is closed when the object is deleted.
        """
        self.close()

    def close(self) -> None:
        """
        Closes the database connection.
        """
        if self.connection:
            self.connection.close()

    def query(self, sql: str) -> sqlite3.Cursor:
        """
        Runs an SQL command.

        Use this method for commands that are not wrapped by this class.

        Parameters
        ----------
        sql : str
            The SQL command.

        Returns
        -------
        sqlite3.Cursor
            The cursor.
        """
        if self.debug_mode:
            print(linewrap(sql, 60))
        cursor = self.cursor.execute(sql)

        return cursor

    def fetch(
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
            Optional list of columns to be fetched; if Null is given
            all columns will be fetched.
        conditions : list[Condition] or None, optional
            Optional list of conditions.
        orderby : list[ColumnOrder] or None, optional
            Optional dictionary defining column order.
        limit : int or None, optional
            Optional limit for the query.
        offset : int or None, optional
            Optional offset for the query.

        Returns
        -------
        list[dict[str, Any]]
            List of dictionaries in the form [{column_name: value}]
        """
        # Generate columns string for SELECT
        if columns is None:
            cols_str = "*"
        else:
            cols_str = ", ".join(columns)

        # Generate string of conditions for WHERE
        if conditions is not None and len(conditions) > 0:
            conds_str = " WHERE " + self._generate_conditions_str(conditions)
        else:
            conds_str = ""

        # Generate string for ORDER BY
        if orderby is not None and len(orderby) > 0:
            orderby_str = "ORDER BY "
            for column in orderby:
                orderby_str += f"{column.column_name} {column.direction.value}"

                # Add comma if it's not the last dictionary element
                if column is not orderby[-1]:
                    orderby_str += ", "
        else:
            orderby_str = ""

        # Generate string for LIMIT
        if limit is not None and limit > 0:
            limit_str = f"LIMIT {limit}"
        else:
            limit_str = ""

        # Generate string for OFFSET
        if offset is not None and offset > 0:
            offset_str = f"OFFSET {offset}"
        else:
            offset_str = ""

        # SQL query
        sql = f"SELECT {cols_str} FROM {table}"  # SELECT ... FROM ...
        sql += conds_str                         # WHERE
        sql += " " + orderby_str                 # ORDER BY ...
        sql += " " + limit_str                   # LIMIT ...
        sql += " " + offset_str                  # OFFSET ...
        self.query(sql)

        # Return a list of dictionaries (one for each row)
        rows: list[sqlite3.Row] = self.cursor.fetchall()
        result = [dict(row) for row in rows]

        return result

    def insert(self, table: str, data: list[dict[str, object]]) \
    -> list[dict[str, str | int | float | bytes | None]]:
        """
        Inserts rows into the table.

        Parameters
        ----------
        table : str
            Name of the table.
        data : list[dict[str, object]]
            List of dictionaries, e.g.:
            data = [{'col1': 'val1', 'col2': 'val2'}, ...]

        Returns
        -------
        list[dict[str, str | int | float | bytes | None]]
            List of dictionaries containing the inserted rows, e.g.:
            [{'id': 1, 'col1': 'val1', 'col2': 'val2'}, ...]
        """
        inserted: list[dict[str, str | int | float | bytes | None]] = []

        # Loop rows in data
        for row in data:
            # Generate columns string
            cols = ", ".join(list(row.keys()))

            # Generate values string, check if type == str
            vals = ""
            for col, val in row.items():
                vals += self.tostr(val)

                # Add comma if it's not the last dictionary element
                if col is not list(row.keys())[-1]:
                    vals += ", "

            # SQL query
            sql = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
            self.query(sql)

            # Get last inserted row
            last_id = self.cursor.lastrowid
            self.connection.commit()
            result = self.fetch(
                table,
                conditions=[
                    Condition("id", SQLComparisonOperator.EQ, last_id or 0)
                ]
            )
            if result:
                inserted.append(result[0])

        return inserted

    def update(self, table: str, data: list[dict[str, object]]) -> None:
        """
        Updates rows.

        The parameter data is a list of dictionaries (one
        dictionary for each row) containing the new data and the conditions for
        the WHERE statement. It has the following structure::

            data = [
                       {
                           'col1': 'val1',
                           'col2': 'val2',
                           '@conds': [Condition(...), Condition(...), ...]
                       },
                       ...
                   ]

        The dictionary key that begins with an @ points at the list of
        conditions.

        Parameters
        ----------
        table : str
            Name of the table.
        data : list[dict[str, object]]
            List of dictionaries.
        """
        # Loop rows in data
        for i in range(0, len(data)):
            conditions: list[Condition] = []
            cols_str = ""

            # Create a deep copy of the dict for this row, so it can be looped
            # (the original dictionary changes size in the following loop)
            row = copy.deepcopy(data[i])

            # Loop columns in row
            for col, val in row.items():
                if col[0] == "@":
                    # Get conditions for this row and remove them from data dict
                    conditions = cast(list[Condition], val)
                    del data[i][col]

            # Loop columns in row (again, without entry for conditions)
            row = data[i]
            for col, val in row.items():
                # Add "col = val"
                cols_str += f"{col}={self.tostr(val)}"

                # Add comma if it's not the last dictionary element
                if col is not list(row.keys())[-1]:
                    cols_str += ", "

            # Generate conditions string
            cond_str = self._generate_conditions_str(conditions)

            # SQL query
            sql = f"UPDATE {table} SET {cols_str} WHERE {cond_str}"
            self.query(sql)
            self.connection.commit()

    def remove(self, table: str, conditions: list[Condition]) -> None:
        """
        Removes the rows from the table which match the list of conditions.

        Parameters
        ----------
        table : str
            Name of the table.
        conditions : list[Condition]
            List of conditions.
        """
        # Generate conditions string
        cond_str = self._generate_conditions_str(conditions)

        # SQL query
        sql = f"DELETE FROM {table} WHERE {cond_str}"
        self.query(sql)
        self.connection.commit()

    def _generate_conditions_str(self, conditions: list[Condition]) -> str:
        """
        Creates a string out of a list of conditions, so it can be used for the WHERE statement.

        Parameters
        ----------
        conditions : list[Condition]
            List of instances of Condition.

        Returns
        -------
        str
            String representation of the conditions for WHERE clause.
        """
        cond_str = ""

        # Loop conditions
        cond: Condition
        for cond in conditions:
            # Add "AND"/"OR" if it's not the first condition
            if cond is not conditions[0]:
                cond_str += " " + cond.combination.value + " "

            # Add "col = val"/"col > val"/...
            cond_str += (f"{cond.column_name}{cond.operator.value}"
                         f"{self.tostr(cond.value)}")

        return cond_str

    @staticmethod
    def tostr(value: object) -> str:
        """
        Creates a string from the given value.

        Value is None           --> return "NULL"
        Value is str            --> return escaped string
        Value is something else --> return value

        Parameters
        ----------
        value : object
            Value that is to be converted to a string.

        Returns
        -------
        str
            The converted value.
        """
        if value is None:
            # None -> NULL
            return "NULL"
        elif isinstance(value, str):
            # Add quotes to string
            return "'" + str(value).replace("'", "''") + "'"
        else:
            return str(value)

    def save(self) -> None:
        """
        Commits the current transaction.
        """
        self.connection.commit()
