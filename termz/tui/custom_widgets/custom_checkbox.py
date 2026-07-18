"""A Textual Checkbox that shows a check mark instead of an X."""

from textual.events import Callback, Mount
from textual.widgets import Checkbox


class CustomCheckbox(Checkbox):
    """
    A custom Textual Checkbox that displays a check mark when selected.

    When nothing is selected, it shows an empty box - instead of the default
    behavior of showing an "X".

    Attributes
    ----------
    CUSTOM_BUTTON_INNER : str
        The character to display when the checkbox is checked.
    """

    CUSTOM_BUTTON_INNER = "✔"


    def _on_mount(self, event: Mount) -> None:
        """Applies the custom glyph as soon as the widget is mounted."""
        self.toggle_button_inner()
        return super()._on_mount(event)

    def on_checkbox_changed(self, _event: Callback) -> None:
        """Swaps the glyph whenever the checkbox is toggled."""
        self.toggle_button_inner()

    def toggle_button_inner(self) -> None:
        """Sets the inner glyph to match the current value."""
        if self.value:
            self.BUTTON_INNER = self.CUSTOM_BUTTON_INNER
        else:
            self.BUTTON_INNER = " "  # pyright:ignore[reportConstantRedefinition]
