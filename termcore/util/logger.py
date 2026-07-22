"""
Sets up file logging for an application.

Deliberately file-only. A console handler would write into the terminal an
application draws its interface on, so a single log line would scatter the
layout - and the lines that matter most arrive exactly when something has
already gone wrong. Diagnostics belong in the file; what the user should read
goes through `termcore.cli.output`.
"""

import logging
import os
from pathlib import Path

__all__ = [
    "setup_logging",
    "state_dir",
]

_LOG_FILE = "app.log"


def state_dir(appname: str) -> Path:
    """
    Returns the directory for an application's discardable state.

    Follows the XDG Base Directory specification: `XDG_STATE_HOME` when it
    holds an absolute path, `~/.local/state` otherwise. The specification
    calls an empty or relative value invalid, so such a value is ignored
    rather than honoured.

    Parameters
    ----------
    appname : str
        The application's name, used as the directory below the state root.

    Returns
    -------
    Path
        The application's state directory. This call does not create it.

    Examples
    --------
    >>> state_dir("demo").name
    'demo'
    """
    configured = os.environ.get("XDG_STATE_HOME", "")
    root = (
        Path(configured)
        if configured.startswith("/")
        else Path.home() / ".local" / "state"
    )

    return root / appname


def setup_logging(
    appname: str,
    level: int = logging.DEBUG,
    log_dir: Path | None = None,
) -> None:
    """
    Sets up file logging for the application.

    Parameters
    ----------
    appname : str
        The name of the application, used to name the log directory when
        none is given.
    level : int, optional
        The logging level (e.g., logging.DEBUG, logging.INFO),
        by default logging.DEBUG.
    log_dir : Path or None, optional
        Where `app.log` is written. An application that resolves its own
        paths should pass that directory, so that every file it owns comes
        from one place. Without it the XDG state directory for `appname` is
        used.
    """
    directory = log_dir if log_dir is not None else state_dir(appname)
    directory.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(directory / _LOG_FILE, encoding="utf-8")
        ],
    )
