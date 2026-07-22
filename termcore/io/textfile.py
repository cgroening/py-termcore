"""
Reading and writing text files.

This module provides a convenient interface for working with text files,
allowing users to read entire file contents, retrieve lines as a list,
and write new content efficiently.

It is designed to simplify file operations by providing a class-based
approach for handling text files. It ensures proper file handling using context
managers and includes essential methods to perform common file operations.

Features:

- Read the entire content of a text file as a string.
- Read a text file line by line, returning a list of lines.
- Write new content to a text file, replacing any existing content.
- Write atomically, so a crash cannot leave a half-written file.
- Uses UTF-8 encoding for compatibility with various text formats.
- Ensures proper file handling by automatically closing files after operations.
"""

import os
import stat
import tempfile
from pathlib import Path

__all__ = [
    "Textfile",
]

# The permission bits of a file, without the type bits stat() also returns.
_PERMISSION_BITS = stat.S_IMODE(0o777)


class Textfile:
    """
    Reads and writes text files.

    This class provides methods to read the entire content of a text file,
    read individual lines, and write new content to the file. It is designed for
    simple file manipulation tasks and ensures that file streams are properly
    handled using context managers.
    """

    @staticmethod
    def readlines(path: str) -> list[str]:
        """
        Reads the text file and returns its lines as a list.

        Parameters
        ----------
        path : str
            The path to the text file that will be read.

        Returns
        -------
        list[str]
            A list containing all lines from the text file.
        """
        with Path(path).open("r+", encoding="utf-8") as f:
            return f.readlines()

    @staticmethod
    def read(path: str) -> str:
        """
        Reads the whole text file into a single string.

        Parameters
        ----------
        path : str
            The path to the text file that will be read.

        Returns
        -------
        str
            The complete content of the text file as a string.
        """
        with Path(path).open("r+", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def write(path: str, text: str) -> None:
        """
        Writes the given text to the file, overwriting any existing content.

        The file is truncated before writing, ensuring that any previous content
        is removed. That truncation is also the risk: a crash between it and
        the write leaves the file empty. Use `write_atomic` where losing the
        old content would matter.

        Parameters
        ----------
        path : str
            The path to the text file that will be written.
        text : str
            Content of the text file.
        """
        with Path(path).open("w", encoding="utf-8") as f:
            f.seek(0)               # Set stream to the beginning of the file
            f.write("".join(text))  # Write text to file
            f.truncate()            # Remove old text

    @staticmethod
    def write_atomic(path: str | Path, text: str) -> None:
        """
        Writes the text so that a crash can never leave a partial file.

        The content goes to a temporary file beside the target, is flushed and
        synced to disk, and only then replaces the target in one step. A file
        written this way holds either its old content or its new content, never
        half of either - which matters for anything that is rewritten whole,
        because a plain write truncates first and loses everything before it
        writes anything.

        The temporary file is created in the target's own directory, so the
        replacement stays on one filesystem and is therefore atomic. It is
        removed again if anything goes wrong.

        Parameters
        ----------
        path : str or Path
            The path to the text file that will be written. Its directory is
            created if it does not exist.
        text : str
            Content of the text file.

        Raises
        ------
        OSError
            If the directory cannot be created, or the file cannot be written,
            synced or replaced.
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        handle, name = tempfile.mkstemp(
            dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
        )
        temporary = Path(name)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as file:
                _ = file.write(text)
                file.flush()
                # The rename is atomic, but only the sync makes the content
                # durable: without it a power loss can leave the new name
                # pointing at blocks that were never written.
                os.fsync(file.fileno())

            # mkstemp creates the file private to the user. Where the target
            # already exists its mode is carried over, so writing a file does
            # not silently change who may read it.
            if target.exists():
                temporary.chmod(target.stat().st_mode & _PERMISSION_BITS)

            _ = temporary.replace(target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
