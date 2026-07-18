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
- Uses UTF-8 encoding for compatibility with various text formats.
- Ensures proper file handling by automatically closing files after operations.
"""

from pathlib import Path


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
        is removed.

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
