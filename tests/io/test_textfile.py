"""
Tests for reading and writing text files.

The atomic write is the reason this file exists. Everything it promises is a
promise about a crash, which a test cannot stage directly - so what is pinned
here is the observable shape of that promise: nothing is truncated before the
new content is complete, no temporary file survives, and a failure leaves the
old content exactly as it was.
"""

import os
import stat
from pathlib import Path
from unittest import mock

import pytest

from termcore.io.textfile import Textfile


def temporaries(directory: Path) -> list[Path]:
    """Returns the helper's leftover temporary files, if any."""
    return [path for path in directory.iterdir() if path.suffix == ".tmp"]


class TestReading:
    def test_read_returns_the_whole_file(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"
        path.write_text("one\ntwo\n", encoding="utf-8")

        assert Textfile.read(str(path)) == "one\ntwo\n"

    def test_readlines_keeps_the_line_endings(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"
        path.write_text("one\ntwo\n", encoding="utf-8")

        assert Textfile.readlines(str(path)) == ["one\n", "two\n"]

    def test_reading_a_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(OSError):
            Textfile.read(str(tmp_path / "absent.txt"))


class TestWrite:
    def test_it_replaces_the_content(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"
        path.write_text("a much longer previous content", encoding="utf-8")

        Textfile.write(str(path), "short")

        assert path.read_text(encoding="utf-8") == "short"


class TestWriteAtomic:
    def test_it_writes_the_content(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"

        Textfile.write_atomic(path, "hello")

        assert path.read_text(encoding="utf-8") == "hello"

    def test_it_replaces_existing_content_entirely(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "notes.txt"
        path.write_text("a much longer previous content", encoding="utf-8")

        Textfile.write_atomic(path, "short")

        assert path.read_text(encoding="utf-8") == "short"

    def test_it_creates_the_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "deeper" / "notes.txt"

        Textfile.write_atomic(path, "hello")

        assert path.read_text(encoding="utf-8") == "hello"

    def test_it_accepts_a_string_path(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"

        Textfile.write_atomic(str(path), "hello")

        assert path.read_text(encoding="utf-8") == "hello"

    def test_it_leaves_no_temporary_file_behind(self, tmp_path: Path) -> None:
        Textfile.write_atomic(tmp_path / "notes.txt", "hello")

        assert temporaries(tmp_path) == []

    def test_it_handles_text_with_wide_characters(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "notes.txt"

        Textfile.write_atomic(path, "日本語 · ✔")

        assert path.read_text(encoding="utf-8") == "日本語 · ✔"


class TestWriteAtomicOnFailure:
    """
    A failed write must lose neither the old content nor the disk.

    This is the whole point of the exercise: `write` truncates first, so a
    failure between truncating and writing leaves an empty file. The atomic
    version cannot, because the target is only touched by the final rename.
    """

    def test_the_old_content_survives(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"
        path.write_text("precious", encoding="utf-8")

        with (
            mock.patch("os.fsync", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            Textfile.write_atomic(path, "new content")

        assert path.read_text(encoding="utf-8") == "precious"

    def test_no_temporary_file_is_left(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"
        path.write_text("precious", encoding="utf-8")

        with (
            mock.patch("os.fsync", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            Textfile.write_atomic(path, "new content")

        assert temporaries(tmp_path) == []

    def test_a_target_that_did_not_exist_is_not_created(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "notes.txt"

        with (
            mock.patch("os.fsync", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            Textfile.write_atomic(path, "new content")

        assert not path.exists()


class TestWriteAtomicPermissions:
    def test_an_existing_file_keeps_its_mode(self, tmp_path: Path) -> None:
        # mkstemp creates its file private to the user, so without carrying
        # the mode over a readable file would quietly become unreadable to
        # everyone else the first time it was written.
        path = tmp_path / "notes.txt"
        path.write_text("old", encoding="utf-8")
        path.chmod(0o644)

        Textfile.write_atomic(path, "new")

        assert stat.S_IMODE(path.stat().st_mode) == 0o644

    def test_a_new_file_is_private(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"

        Textfile.write_atomic(path, "new")

        assert stat.S_IMODE(path.stat().st_mode) == 0o600


class TestWriteAtomicIsDurable:
    def test_the_content_is_synced_before_the_rename(
        self, tmp_path: Path
    ) -> None:
        # The rename is atomic on its own, but only the sync makes the bytes
        # durable; without it a power loss can leave the new name pointing at
        # blocks that were never written.
        path = tmp_path / "notes.txt"
        calls: list[str] = []

        real_fsync = os.fsync
        real_replace = Path.replace

        def record_fsync(fileno: int) -> None:
            calls.append("fsync")
            real_fsync(fileno)

        def record_replace(self: Path, target: object) -> Path:
            calls.append("replace")
            return real_replace(self, target)  # pyright: ignore[reportArgumentType]

        with (
            mock.patch("os.fsync", record_fsync),
            mock.patch.object(Path, "replace", record_replace),
        ):
            Textfile.write_atomic(path, "hello")

        assert calls == ["fsync", "replace"]
