"""
termz.io.app_state_storage
==========================

A simple JSON-based storage system that allows reading, writing and modifying
key-value pairs in a JSON file. This is useful for persisting application states
like the last scroll position or command history. The class `AppStateStorage`
follows a singleton pattern to ensure a single instance across the application.

Features:

- Reads a JSON file and loads its content into a dictionary.
- Provides methods to retrieve (`get`) and update (`set`) key-value pairs.
- Supports modifying lists within the JSON file, including:
  - Inserting elements at a specific index (`list_insert`)
  - Editing individual elements within a list (`edit_list_item`)
  - Deleting elements from a list (`delete_list_item`)
  - Moving elements within a list (`move_list_item`)
- Ensures data persistence by saving changes to the JSON file automatically.
- Manages file creation and error handling for missing or corrupted JSON files.
"""
import sys
import json
import os
from pathlib import Path
from typing import cast
from termz.util.singleton import Singleton


class AppStateStorage(metaclass=Singleton):
    """
    This class opens a JSON file and saves the content in a dictionary which can
    be accessed with `get()`.

    Changed values or new key-value pairs can be stored within the Dictionary
    and the JSON file with the method `set()`.

    Attributes
    ----------
    _json_file : Path or str or None
        Path to the JSON file.
    _json_dict : dict[str, object]
        Content of the JSON file as a dictionary.
    """
    _json_file_path: Path | str | None
    _json_dict: dict[str, object] = {}


    def __init__(
        self,
        package_name: str | None = None,
        state_file_path: Path | str | None = None
    ) -> None:
        """
        Opens the JSON file and stores the key-value pairs in `self.json_dict`.

        Raises
        ------
        Exception
            If no JSON file is given and the class instance is None.
        """
        if state_file_path is None and package_name is not None:
            state_dir = Path.home() / ".local" / "state" / package_name
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file_path = state_dir / "state.json"
        elif state_file_path is None and AppStateStorage.instance is None:
            raise Exception(
                "Either state_file_path or package_name must be given."
            )
        self._json_file_path = state_file_path
        self._read_json_file()

    def _read_json_file(self) -> None:
        """
        Opens the JSON file and stores the content in `self.json_dict`.

        Raises
        ------
        FileNotFoundError
            If the JSON file cannot be found and cannot be created.
        json.JSONDecodeError
            If the JSON file contains invalid JSON.
        """
        if self._json_file_path is None:
            raise Exception("No JSON file given.")
        abs_path = os.path.abspath(self._json_file_path)

        try:
            with open(self._json_file_path, encoding="utf-8") as file:
                self._json_dict = json.load(file)
        except FileNotFoundError:
            # File not found -> try to create a new one
            try:
                with open(self._json_file_path, "w") as file:
                    _ = file.write("{}")
            except FileNotFoundError:
                print(f"ERROR: Could not find or create \"{abs_path}\".")
                sys.exit()
        except json.JSONDecodeError:
            print(f"Error: File \"{abs_path}\" contains invalid JSON.")
            sys.exit()

    def _save_json_file(self) -> None:
        """Stores the content of self.json_dict in the JSON file."""
        if self._json_file_path is None:
            raise Exception("No JSON file given.")
        abs_path = os.path.abspath(self._json_file_path)

        try:
            with open(self._json_file_path, "w", encoding="utf-8") as file:
                json.dump(self._json_dict, file, indent=4)
        except IOError:
            print(f"Fehler: File {abs_path} could not be written.")

    def get(self, key: str, default_value: object = None) -> object | None:
        """
        Returns a value from the JSON file.
        If the given key cannot be found the given default value is returned.
        """
        if key in self._json_dict:
            return self._json_dict[key]
        else:
            return default_value  # type: ignore

    def set(self, key: str, value: object) -> None:
        """Saves a key-value pair in the JSON file."""
        self._json_dict.update({key: value})
        self._save_json_file()

    def list_insert(
        self, list_name: str, list_index: int, value: object
    ) -> None:
        """Adds a new entry to a list at the given index."""
        # Create list if it doesn't exist
        if list_name not in self._json_dict:
            self._json_dict.update({list_name: []})

        # Create empty list if value is empty
        if self._json_dict[list_name] is None:
            self._json_dict[list_name] = []

        # Add given data to dict and write to JSON file
        lst = self._json_dict[list_name]
        if isinstance(lst, list):
            cast(list[object], lst).insert(list_index, value)
            self._json_dict[list_name] = lst
            self._save_json_file()
        else:
            raise TypeError(f"Value of \"{list_name}\" is not a list.")

    def edit_list_item(
        self, list_name: str, list_index: int, dict_key: str, value: object
    ) -> None:
        """ Changes the value of a list item."""
        lst = cast(list[dict[str, object]], self._json_dict[list_name])
        lst[list_index][dict_key] = value
        self._json_dict[list_name] = lst
        self._save_json_file()

    def delete_list_item(self, list_name: str, list_index: int) -> None:
        """Deletes an element of a list."""
        lst = cast(list[dict[str, object]], self._json_dict[list_name])
        del lst[list_index]
        self._save_json_file()

    def move_list_item(
        self, list_name: str, list_index: int, list_index_new: int
    ) -> None:
        """
        Moves a list item by deleting and re-inserting it at a new position.
        """
        lst = cast(list[object], self._json_dict[list_name])
        list_element: object = lst[list_index]
        del lst[list_index]
        lst.insert(list_index_new, list_element)
        self._json_dict[list_name] = lst
        self._save_json_file()
