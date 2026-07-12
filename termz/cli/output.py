"""
termz.cli.output
================

Provides utility functions for styled CLI output using Rich.

Includes helpers for printing color-coded panels (error, warning, success and
info) and a function to clear previously printed lines from the terminal.
"""
import sys
from rich.console import Console
from rich.panel import Panel


console = Console()


def get_console() -> Console:
    """Returns the Rich Console instance."""
    return console


def print_error(message: str) -> None:
    """Prints an error message in a red panel using Rich."""
    print_panel(f"✗ {message}", "red")


def print_warning(message: str) -> None:
    """Prints a warning message in a yellow panel using Rich."""
    print_panel(f"⚠ {message}", "yellow")


def print_success(message: str) -> None:
    """Prints a success message in a green panel using Rich."""
    print_panel(f"✓ {message}", "green")


def print_info(message: str) -> None:
    """Prints an info message in a cyan panel using Rich."""
    print_panel(f"ℹ {message}", "cyan")


def print_panel(message: str, color: str) -> None:
    """Prints a message in a red panel with the given color using Rich."""
    formatted_message = f"[{color} bold]{message}[/{color} bold]"
    print_custom_panel(formatted_message, color)


def print_custom_panel(formatted_message: str, panel_color: str) -> None:
    """
    Prints a custom formatted message in a panel with the given color
    using Rich.
    """
    console.print(Panel(
        formatted_message,
        border_style=panel_color,
        padding=(1, 2)
    ))


def clear_lines(count: int) -> None:
    """Move cursor up `count` lines and clear everything below."""
    _ = sys.stdout.write(f"\033[{count}A\033[0J")
    _ = sys.stdout.flush()
