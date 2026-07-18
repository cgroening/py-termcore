
"""
Reading, writing and managing files and folders.

It offers a simple and lightweight interface for handling
text-based file operations.

This module includes functions and classes to work with text files, such as
reading content, writing data, appending text and performing basic file
manipulations. It is designed to simplify text file handling in Python projects
by providing an easy-to-use API.

Features:

- Read content from text files.
- Write content to text files.
- Append data to existing files.
- Handle file encoding issues.
- Support for line-by-line reading to optimize memory usage.

This module is particularly useful for applications requiring efficient and
straightforward text file operations, such as logging systems, data processing
and configuration management.
"""
import shutil
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "File",
    "FolderItem",
]


@dataclass(slots=True)
class FolderItem:
    """
    Internal class: Represents an item (file or folder) within a directory.

    Attributes
    ----------
    type : str
        Type of the item, either 'file' or 'folder'.
    name : str
        Name of the file or folder (without extension for files).
    level : int
        Depth level of the item in the directory tree
        (0 for root items, 1 for sub-items, etc.).
        Items in a sub folder level 1 etc.
    extension : str or None, optional
        File extension without leading dot (None for folders).

    Notes
    -----
    TODO: Support more pieces of information like size, modified, etc.
    TODO: Method to copy/move/delete a file (one method "copy" that copies
          folders and files)
    """

    type: str
    name: str
    level: int
    extension: str | None = None


class File:
    """
    A collection of static methods for performing file and folder operations.

    Provides functionalities to list folder contents, copy files and folders,
    retrieve file extensions, modify file extensions, and extract folder paths
    from file paths.
    """

    @staticmethod
    def folder_content(
        path: str, extfilter: str | None = None
    ) -> dict[str, FolderItem]:
        """
        Retrieves the contents of a given folder, without its subfolders.

        Parameters
        ----------
        path : str
            The directory path to list contents from.
        extfilter : str or None, optional
            A specific file extension to filter results
            (e.g., "txt").

        Returns
        -------
        dict[str, FolderItem]
            A dictionary where the keys are item paths and the values are
            FolderItem instances containing metadata about each item.
        """
        return File._folder_content(path, extfilter, with_subfolders=False)

    @staticmethod
    def folder_content_recursive(
        path: str, extfilter: str | None = None
    ) -> dict[str, FolderItem]:
        """
        Retrieves the contents of a given folder and of every subfolder.

        Each `FolderItem` carries its depth below `path` in `level`.

        Parameters
        ----------
        path : str
            The directory path to list contents from.
        extfilter : str or None, optional
            A specific file extension to filter results
            (e.g., "txt").

        Returns
        -------
        dict[str, FolderItem]
            A dictionary where the keys are item paths and the values are
            FolderItem instances containing metadata about each item.
        """
        return File._folder_content(path, extfilter, with_subfolders=True)

    @staticmethod
    def _folder_content(  # noqa: PLR0913 - level is carried by recursion
        path: str, extfilter: str | None = None, level: int = 0,
        *, with_subfolders: bool
    ) -> dict[str, FolderItem]:
        """
        Lists a folder, descending into subfolders when asked to.

        Notes
        -----
        TODO: also return a sorted list of the keys of the dictionary
        """
        # Get all items of the folder and create a dictionary
        items_list: list[str] = [p.name for p in Path(path).iterdir()]
        items_dict: dict[str, FolderItem] = {}

        # Loop folder items
        for item in items_list:
            item_path = path + "/" + item

            # Recursion if the item is a folder
            if Path(item_path).is_dir() and with_subfolders:
                items_dict = {**items_dict, **File._folder_content(
                    item_path + "/", extfilter, level + 1,
                    with_subfolders=with_subfolders)}
                item_type = "folder"
            else:
                item_type = "file"

            # Add item to dictionary
            if File.extension(item) == extfilter or extfilter is None:
                # Create FolderItem instance
                items_dict[item_path] = FolderItem(
                    type=item_type,
                    name=item,
                    extension=File.extension(item),
                    level=level
                )

        # TODO: also return a sorted list of the keys of the dictionary

        return items_dict

    @staticmethod
    def copy_folder(source: str, target: str) -> None:
        """
        Copies a folder and its contents to a new location.

        Creates the target folder if it does not exist.

        Parameters
        ----------
        source : str
            The path of the source folder to copy.
        target : str
            The destination path where the folder should be copied.

        Notes
        -----
        TODO: Add functionality for moving or deleting folders.
        """
        # Create target folder if it doesn't exist
        Path(target).mkdir(parents=True, exist_ok=True)

        # Copy each file
        # TODO: Also copy sub folder (-> recursion)
        for entry in Path(source).iterdir():
            shutil.copyfile(entry, Path(target) / entry.name)

    @staticmethod
    def extension(file_name: str) -> str | None:
        """
        Extracts and returns the file extension from a given file name.

        Parameters
        ----------
        file_name : str
            The name of the file (including extension).

        Returns
        -------
        str or None
            The file extension (without a leading dot) or None if the file has
            no extension.
        """
        # Dateiname anhand von . in Liste splitten
        file_name_split = file_name.split(".")
        count = len(file_name_split)

        # Das letzte Element der Liste (= Dateiendung) zurückgeben
        if count > 1:
            return file_name.split(".")[count - 1]
        return None

    @staticmethod
    def change_extension(file_name: str, extension: str) -> str:
        """
        Replaces the extension of a given file name with a new extension.

        Parameters
        ----------
        file_name : str
            The original file name.
        extension : str
            The new file extension (without a leading dot).

        Returns
        -------
        str
            The file name with the updated extension.
        """
        # Split file name into list by "."
        file_name_split = file_name.split(".")
        count = len(file_name_split)

        # Replace the last element of the list (old extension) and replace it
        # with the new extension
        if count > 1:
            file_name_split[count-1] = extension
            file_name = ".".join(file_name_split)

        return file_name

    @staticmethod
    def path(file_path: str) -> str:
        """
        Extracts and returns the folder path from a full file path.

        Parameters
        ----------
        file_path : str
            The full file path.

        Returns
        -------
        str
            The folder path without the file name.
        """
        file_path_list: list[str] = file_path.split("/")
        file_path_list.remove(file_path_list[len(file_path_list) - 1])
        return "/".join(file_path_list)
