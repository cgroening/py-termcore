"""Domain exceptions raised by the `termz.io` modules."""

__all__ = [
    "DatabaseError",
    "EmptyConditionsError",
    "UnknownIdentifierError",
]


class DatabaseError(Exception):
    """Base class for every error raised while talking to a database."""


class UnknownIdentifierError(DatabaseError):
    """
    Raised when a table or column name is not part of the schema.

    Identifiers cannot be passed as query parameters, so they are checked
    against the schema before they are put into a statement. Rejecting an
    unknown name here means a typo is reported as a typo, and a name that
    was never a column cannot become a fragment of SQL.
    """
    name: str
    known: tuple[str, ...]

    def __init__(self, name: str, known: tuple[str, ...]) -> None:
        """Stores the rejected name and what would have been accepted."""
        super().__init__(
            f"Unknown identifier {name!r}. "
            f"Known identifiers: {', '.join(known) or '(none)'}"
        )
        self.name = name
        self.known = known


class EmptyConditionsError(DatabaseError):
    """
    Raised when an update or a delete is asked to run without conditions.

    An empty condition list almost always means the caller built it from
    something that turned out to be empty, and carrying on would rewrite or
    delete every row in the table.
    """
    operation: str

    def __init__(self, operation: str) -> None:
        """Stores the operation that was refused."""
        super().__init__(
            f"Refusing to {operation} every row of the table: no conditions "
            f"were given. Use query() if that is genuinely intended."
        )
        self.operation = operation
