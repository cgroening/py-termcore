import logging
from pathlib import Path


def setup_logging(appname: str, level: int = logging.DEBUG) -> None:
    """
    Sets up logging for the application. Logs are stored in the user's
    home directory under `.local/state/{appname}/app.log`.

    Parameters
    ----------
    appname : str
        The name of the application, used to create a unique log directory.
    level : int, optional
        The logging level (e.g., logging.DEBUG, logging.INFO),
        by default logging.DEBUG.
    """
    log_dir = Path.home() / ".local" / "state" / appname
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "app.log"

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )
