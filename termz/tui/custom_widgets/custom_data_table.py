"""
Extension of Textual's DataTable with support for flexible column resizing.

This module defines `CustomDataTable`, a subclass of Textual's `DataTable`
with additional capabilities for handling dynamic resizing of table columns
based on available space.

The primary enhancement is the introduction of *flexible columns* - a list of
column keys that automatically adjust their widths when the table is resized.
This allows developers to create responsive and adaptive data tables where
certain columns expand or contract depending on the widget size, while others
remain fixed.

The class overrides the `on_resize` method to calculate the total available
width and distribute it proportionally among the flexible columns. It also
provides helper methods for determining fixed column widths and adjusting
layout accordingly.

This is particularly useful for applications with tabular data in dynamic
layouts or where users resize windows and expect columns to adapt gracefully.
"""
from typing import Any, TypeVar

from textual.coordinate import Coordinate
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable
from textual.widgets._data_table import Column, ColumnKey

__all__ = [
    "CustomDataTable",
]

_CellType = TypeVar("_CellType")


class CustomDataTable(DataTable[_CellType]):
    """
    A DataTable with columns that stretch to fill the available width.

    Attributes
    ----------
    MIN_FLEX_COL_WIDTH : int
        Minimum width for flexible columns.
    flexible_columns : list[ColumnKey]
        List of column keys that should be flexible in width
        (will be adjusted according to window width).
    """

    MIN_FLEX_COL_WIDTH = 5
    flexible_columns: list[ColumnKey]


    class Mounted(Message):
        """Posted once the table has been mounted and can be filled."""

        def __init__(self, sender: Widget) -> None:
            """Records which widget was mounted."""
            super().__init__()
            self.sender = sender


    def __init__(self, **kwargs: Any) -> None:  # noqa: ANN401
        """
        Initializes the table with an empty set of flexible columns.

        The arguments are whatever `DataTable` takes, which is what Any
        says here; naming them would mean restating fifteen parameters
        and re-stating them again on every Textual release.
        """
        super().__init__(**kwargs)

        # Per instance: as a class attribute every table in the process
        # shared one list and inherited the columns of all the others.
        self.flexible_columns = []


    def on_mount(self) -> None:
        """
        Handles the mount event of the DataTable.

        This method is called when the DataTable is mounted in the application.
        It posts a Mounted message to notify that the DataTable is ready.
        This is useful for initializing any additional functionality that
        depends on the DataTable being fully mounted.

        Examples
        --------
        >>> @on(CustomDataTable.Mounted)
        >>> async def on_table_mounted(self, event: CustomDataTable.Mounted):
        ...     # Add columns and rows to the table
        ...     pass
        """
        self.post_message(self.Mounted(self))

    def on_resize(self) -> None:
        """
        Handles the resize event of the DataTable.

        Adjusts the widths of the flexible columns based on the new size of
        the table.
        """
        scrollbar_width = 2 if self.show_vertical_scrollbar else 0
        table_width = self.size.width - len(self.columns) * 2 - scrollbar_width
        fixed_widths = self.get_fixed_column_widths()
        self.adjust_flexible_columns(table_width, fixed_widths)
        self.refresh()

    def get_fixed_column_widths(self) -> int:
        """
        Returns the total width of all fixed-width columns in the table.

        This is used to calculate the available width for flexible columns.

        Returns
        -------
        int
            The total width of all fixed-width columns.
        """
        fixed_widths = 0

        for column_key in self.columns:
            column: Column = self.columns[column_key]

            if column_key not in self.flexible_columns:
                fixed_widths += column.width

        return fixed_widths

    def adjust_flexible_columns(self, table_width: int, fixed_width: int) \
    -> None:
        """
        Adjusts the flexible columns to the width the table has.

        Parameters
        ----------
        table_width : int
            The total width of the table.
        fixed_width : int
            The total width of all fixed-width columns.
        """
        for column_key in self.columns:
            column: Column = self.columns[column_key]

            if column_key in self.flexible_columns:
                column.auto_width = False
                column.width = int(
                    (table_width - fixed_width) / len(self.flexible_columns)
                )

                # Don't allow column width to be less than MIN_FLEX_COL_WIDTH
                column.width = max(column.width, self.MIN_FLEX_COL_WIDTH)

        self.update_virtual_size()

    def update_virtual_size(self) -> None:
        """
        Updates the virtual size from the current column widths.

        This is what makes the horizontal scrollbar appear only when it is
        actually needed.

        The effect of this method is that the DataTable has the correct width
        (no hidden column at the right side "compensating" the reduced widths
        of the flexible columns) and that the horizontal scrollbar only appears
        when the total width of all columns exceeds the visible width of
        the DataTable widget.

        The actual total width of all columns including separators is
        calculated by the following formula:

        ```
        total_width = sum(column_widths) + (num_columns * 2 - 2)
        ```

        Notes
        -----
        Explanation:

            - Each column has 2 pixels of spacing (padding/border)
            - With n columns, there are (n-1) separators between columns
            - The first column has left padding and the last has right padding
            - This results in: `2 * (n-1) + 2 = 2n - 2 + 2 = 2n` pixels total
            - However, empirically it's necessary to subtract 2 pixels to
              account for the table's own border/padding, giving: `2n - 2`

            Example with 4 columns: `4 * 2 - 2 = 6` pixels for separators
        """
        # Calculate total width of all columns including separators
        total_column_width = sum(col.width for col in self.columns.values())
        total_width_with_separators = total_column_width \
                                      + (len(self.columns) * 2 - 2)

        # Update virtual size of the DataTable to reflect new width
        self.virtual_size = self.virtual_size._replace(
            width=total_width_with_separators
        )

    def update_scrollbar_visibility(self) -> None:
        """
        Shows or hides the horizontal scrollbar based on the content width.

        .. deprecated::
            This method is no longer needed.

        Scrollbar visibility is now automatically managed by the
        `update_virtual_size()` method, which correctly sets the virtual
        size of the table. The horizontal scrollbar will only appear when
        the content width exceeds the table width.

        Notes
        -----
        TODO: Remove this method in future versions.
        """
        total_content_width = sum(col.width for col in self.columns.values())

        self.styles.scrollbar_size_horizontal = (
            None if total_content_width > self.size.width else 0
        )

    def select_first_row(self) -> None:
        """Selects the first row and posts a RowHighlighted event."""
        if self.row_count == 0:
            return

        # Set cursor to first row
        self.cursor_coordinate = Coordinate(0, 0)
        self.move_cursor(row=0, column=0)  # Same as above, just to be sure

        # Manually post RowHighlighted event
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
        self.post_message(
            DataTable.RowHighlighted(self, self.cursor_row, row_key)
        )

    def delete_selected_row(self) -> None:
        """Deletes the currently selected row from the table."""
        if self.row_count > 0:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            self.remove_row(row_key)

    # def get_current_id(self) -> int:
    #     Returns the ID of the currently selected topic.

    #     Returns:
    #         int: The ID of the currently selected topic.

