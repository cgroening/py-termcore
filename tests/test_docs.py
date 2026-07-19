"""Keeps the project documentation honest.

`docs/DEVELOPMENT.md` and `docs/CLEAN-UP.md` point at modules, commands and
fixtures by name. A path that no longer exists is not a typo, it is an
instruction that sends the next reader somewhere else - and a relative link
breaks without a sound as soon as either end of it moves. These tests fail
when the documents and the tree drift apart, instead of letting the drift go
unnoticed.
"""

import re
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
PACKAGE_ROOT = REPO_ROOT / "termcore"

# The documents that name paths as instructions rather than as prose.
INSTRUCTION_DOCS = (
    "docs/DEVELOPMENT.md",
    "docs/CLEAN-UP.md",
)

_BACKTICK = re.compile(r"`([^`\n]+)`")
_HEADING = re.compile(r"^#{1,6} ")
_FENCE = re.compile(r"^\s*(```|~~~)")
_MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# Paths that are deliberately absent from a clean checkout: build artefacts
# and the throwaway environment the release instructions create.
ALLOWED_MISSING = frozenset(
    {
        ".pytest_cache/",
        ".ruff_cache/",
        "__pycache__/",
        "build/",
        "dist/",
        "dist/*.whl",
        # The throwaway environment the release instructions create.
        f"{tempfile.gettempdir()}/termcore-check",
    }
)


def markdown_files() -> list[Path]:
    """Returns the project's own markdown files, root and docs alike."""
    found = [*REPO_ROOT.glob("*.md"), *(REPO_ROOT / "docs").glob("*.md")]
    return [path for path in found if not path.name.startswith(".")]


def lines_outside_code(doc: Path) -> Iterator[tuple[int, str]]:
    """
    Yields the numbered lines of a document that are not inside a fence.

    A Python comment in a code block starts with "# " just as a heading
    does, and several of this project's examples carry backticks in one.
    Reading the whole file line by line reports those as headings.
    """
    inside = False
    for number, line in enumerate(
        doc.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if _FENCE.match(line):
            inside = not inside
            continue
        if not inside:
            yield number, line


def referenced_paths(doc: Path) -> set[str]:
    """
    Returns the backticked tokens in a document that denote a real path.

    A bare file name such as `theme.py` is prose - the surrounding sentence
    says where it lives - so only tokens containing a separator count.
    Placeholders like `themes/<name>/` describe a shape, not a location.
    """
    tokens = _BACKTICK.findall(doc.read_text(encoding="utf-8"))
    return {
        token.strip()
        for token in tokens
        if "/" in token
        and "<" not in token
        and " " not in token
        and token.strip() not in ALLOWED_MISSING
    }


def relative_links(doc: Path) -> set[str]:
    """
    Returns the link targets in a document that point at a local file.

    External links and pure anchors point nowhere in this repository, so
    there is nothing here to verify about them.
    """
    targets = _MARKDOWN_LINK.findall(doc.read_text(encoding="utf-8"))
    return {
        target.split("#")[0]
        for target in targets
        if not target.startswith(("http://", "https://", "#", "mailto:"))
        and target.split("#")[0]
    }


def exists(candidate: str) -> bool:
    """Resolves a documented path against the repo root or the package."""
    return (REPO_ROOT / candidate).exists() or (
        PACKAGE_ROOT / candidate
    ).exists()


class TestDocumentedPathsExist:
    @pytest.mark.parametrize("doc_name", INSTRUCTION_DOCS)
    def test_document_exists(self, doc_name: str) -> None:
        assert (REPO_ROOT / doc_name).is_file()

    @pytest.mark.parametrize("doc_name", INSTRUCTION_DOCS)
    def test_document_references_some_paths(self, doc_name: str) -> None:
        # Guards the extraction itself: if it silently stopped matching,
        # every other test here would pass vacuously.
        assert referenced_paths(REPO_ROOT / doc_name)

    @pytest.mark.parametrize("doc_name", INSTRUCTION_DOCS)
    def test_every_referenced_path_exists(self, doc_name: str) -> None:
        doc = REPO_ROOT / doc_name
        missing = sorted(p for p in referenced_paths(doc) if not exists(p))

        assert not missing, f"{doc_name} points at paths that do not exist"


class TestRelativeLinksResolve:
    """Links are the other way a document points at a file.

    They carry no backticks, so the path checks above never see them, and
    they break as soon as either end of the link moves.
    """

    def test_some_links_are_checked(self) -> None:
        assert any(relative_links(path) for path in markdown_files())

    def test_every_relative_link_resolves(self) -> None:
        broken: list[str] = []
        for path in markdown_files():
            for target in relative_links(path):
                if not (path.parent / target).exists():
                    broken.append(f"{path.name} -> {target}")

        assert not broken, f"broken relative links: {broken}"


class TestMarkdownConventions:
    """Style guide 1.5: no inline code in headings, no horizontal rules."""

    def test_project_has_markdown_files(self) -> None:
        assert markdown_files()

    def test_no_heading_contains_inline_code(self) -> None:
        # A backtick in a heading ends up in its anchor verbatim, so any link
        # to that section has to reproduce it exactly or go nowhere.
        offenders: list[str] = []
        for path in markdown_files():
            for number, line in lines_outside_code(path):
                if _HEADING.match(line) and "`" in line:
                    offenders.append(f"{path.name}:{number}")

        assert not offenders, f"inline code in headings: {offenders}"

    def test_no_file_uses_a_horizontal_rule(self) -> None:
        # Section 1.5.1: structure with headings, not with rules.
        offenders: list[str] = []
        for path in markdown_files():
            for number, line in lines_outside_code(path):
                if line.strip() in ("---", "***", "___"):
                    offenders.append(f"{path.name}:{number}")

        assert not offenders, f"horizontal rules: {offenders}"

    def test_exactly_one_top_level_heading_per_file(self) -> None:
        # Section 1.5.2: one H1 as the title, everything else below it.
        offenders: list[str] = []
        for path in markdown_files():
            titles = [
                number for number, line in lines_outside_code(path)
                if line.startswith("# ")
            ]
            if len(titles) != 1:
                offenders.append(f"{path.name}: {len(titles)}")

        assert not offenders, f"not exactly one H1: {offenders}"
