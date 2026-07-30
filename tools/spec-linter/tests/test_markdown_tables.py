"""Structural table parser (remediation spec §7.4, PR B).

Written RED-first: `spec_linter.markdown` does not exist yet.

The invariant under test is the whole point of the increment: **every
recognised table line becomes a ParsedRow, a TableError, or both — never
nothing.** These tests are therefore written to assert *presence*, not
absence: a malformed row must still appear in `rows`, so a consumer can never
mistake "malformed" for "not there".
"""

from __future__ import annotations

import pytest

from spec_linter.markdown import (
    ParsedRow,
    ParsedTable,
    TableError,
    TableErrorKind,
    parse_tables,
)

HEADER = "| # | REQ | Priority | Tests |"
SEPARATOR = "|---|-----|----------|-------|"


def _table(*rows: str) -> str:
    return "\n".join([HEADER, SEPARATOR, *rows]) + "\n"


def _kinds(table: ParsedTable) -> list[TableErrorKind]:
    return [error.kind for error in table.errors]


def _only(section_body: str) -> ParsedTable:
    tables = parse_tables("Traceability Matrix", section_body)
    assert len(tables) == 1
    return tables[0]


# --- the invariant ------------------------------------------------------------


def test_well_formed_rows_parse_with_no_errors() -> None:
    table = _only(_table("| 1 | REQ-1 | MUST | tests/test_a.py |"))
    assert table.headers == ["#", "REQ", "Priority", "Tests"]
    assert [row.cells for row in table.rows] == [["1", "REQ-1", "MUST", "tests/test_a.py"]]
    assert table.errors == []


def test_short_row_is_reported_AND_kept() -> None:
    table = _only(_table("| 1 | REQ-1 | MUST |"))
    assert TableErrorKind.COLUMN_COUNT in _kinds(table)
    # The invariant: the row is still there. Dropping it is what let a MUST
    # row vanish from coverage in every previous incarnation of this code.
    assert len(table.rows) == 1
    assert table.rows[0].cells[:2] == ["1", "REQ-1"]


def test_long_row_is_reported_AND_kept() -> None:
    table = _only(_table("| 1 | REQ-1 | MUST | tests/test_a.py | extra |"))
    assert TableErrorKind.UNEXPECTED_EXTRA_COLUMN in _kinds(table)
    assert len(table.rows) == 1


def test_error_carries_section_line_and_counts() -> None:
    table = _only(_table("| 1 | REQ-1 | MUST |"))
    error = table.errors[0]
    assert error.section == "Traceability Matrix"
    assert error.line == 3  # header, separator, row
    assert (error.expected_cells, error.found_cells) == (4, 3)
    assert "REQ-1" in error.raw


def test_missing_middle_column_is_a_column_count_error() -> None:
    table = _only(_table("| 1 | MUST | tests/test_a.py |"))
    assert TableErrorKind.COLUMN_COUNT in _kinds(table)


def test_row_without_a_trailing_pipe_is_still_a_row() -> None:
    # Previously invisible to `^\|.*\|\s*$`; invisibility is a hiding place.
    table = _only(_table("| 1 | REQ-1 | MUST | tests/test_a.py"))
    assert len(table.rows) == 1


def test_row_without_a_leading_number_is_still_a_row() -> None:
    # R-2 from the PR A handoff: `_NUMBERED_ROW` required a digit cell, so
    # stripping it made the row vanish from every scan.
    table = _only(_table("| REQ-1 | MUST | tests/test_a.py |"))
    assert len(table.rows) == 1
    assert TableErrorKind.COLUMN_COUNT in _kinds(table)


# --- cell grammar -------------------------------------------------------------


def test_escaped_pipe_stays_inside_one_cell() -> None:
    table = _only(_table(r"| 1 | REQ-1 | MUST | a \| b |"))
    assert table.rows[0].cells == ["1", "REQ-1", "MUST", "a | b"]
    assert table.errors == []


def test_cells_are_stripped() -> None:
    table = _only(_table("|   1   |  REQ-1 | MUST   | t.py |"))
    assert table.rows[0].cells == ["1", "REQ-1", "MUST", "t.py"]


def test_placeholder_in_an_identifier_column_is_reported() -> None:
    table = parse_tables(
        "Matrix", _table("| 1 | {REQ id} | MUST | t.py |"), required_columns={"REQ"}
    )[0]
    assert TableErrorKind.PLACEHOLDER in _kinds(table)
    assert len(table.rows) == 1


def test_braces_in_free_text_are_not_a_placeholder() -> None:
    # Findings legitimately quote braces: "mapping closed to {value, reason}".
    table = _only(_table("| 1 | REQ-1 | MUST | closed to {value, reason} |"))
    assert TableErrorKind.PLACEHOLDER not in _kinds(table)


def test_empty_cell_in_a_required_column_is_reported() -> None:
    # WHICH columns are required is contract policy (Decision 5), so the
    # caller names them; the parser only reports what it finds.
    table = parse_tables(
        "Matrix", _table("| 1 |  | MUST | t.py |"), required_columns={"REQ"}
    )[0]
    assert TableErrorKind.EMPTY_REQUIRED_CELL in _kinds(table)


def test_empty_cell_outside_the_required_set_is_not_an_error() -> None:
    table = _only(_table("| 1 | REQ-1 | MUST |  |"))
    assert TableErrorKind.EMPTY_REQUIRED_CELL not in _kinds(table)


# --- header validation --------------------------------------------------------


def test_duplicate_header_is_reported() -> None:
    body = "| # | REQ | REQ |\n|---|-----|-----|\n| 1 | a | b |\n"
    table = parse_tables("Matrix", body)[0]
    assert TableErrorKind.DUPLICATE_HEADER in _kinds(table)


def test_missing_header_is_reported_when_the_block_opens_with_data() -> None:
    body = "| 1 | REQ-1 | MUST |\n"
    table = parse_tables("Matrix", body)[0]
    assert TableErrorKind.MISSING_HEADER in _kinds(table)
    # Still parsed: the line is data we must be able to see.
    assert len(table.rows) == 1


def test_a_header_and_delimiter_with_no_data_is_reported_not_trusted() -> None:
    """The other side of the ambiguity rule: a table that is nothing but a
    header and a delimiter does not occur in any real artifact (measured: zero
    across every archived document and template), while a swallowed data row is
    a proven bypass. So this shape is read as data and reported, rather than
    silently trusted as an empty table."""
    body = f"{HEADER}\n{SEPARATOR}\n"
    table = parse_tables("Matrix", body)[0]
    assert len(table.rows) == 2
    assert any(error.kind is TableErrorKind.MISSING_HEADER for error in table.errors)


def test_separator_row_is_not_data() -> None:
    table = _only(_table("| 1 | REQ-1 | MUST | t.py |"))
    assert all(":---" not in "".join(row.cells) for row in table.rows)
    assert len(table.rows) == 1


def test_alignment_separators_are_recognised() -> None:
    body = "| a | b |\n|:--|--:|\n| 1 | 2 |\n"
    table = parse_tables("Matrix", body)[0]
    assert len(table.rows) == 1


# --- blocks and opacity -------------------------------------------------------


def test_two_blocks_separated_by_prose_are_two_tables() -> None:
    body = _table("| 1 | REQ-1 | MUST | t.py |") + "\nprose\n\n" + _table(
        "| 1 | REQ-2 | MUST | t.py |"
    )
    assert len(parse_tables("Matrix", body)) == 2


def test_tables_inside_a_fence_are_not_parsed() -> None:
    # Opacity is owned by sections.content_lines; the parser must not
    # re-implement it, and must not see quoted illustrations either.
    body = "```markdown\n" + _table("| 1 | REQ-1 | MUST | t.py |") + "```\n"
    assert parse_tables("Matrix", body) == []


def test_tables_inside_an_html_comment_are_not_parsed() -> None:
    body = "<!--\n" + _table("| 1 | REQ-1 | MUST | t.py |") + "-->\n"
    assert parse_tables("Matrix", body) == []


# --- totality (adopted from the Gate J advisory) ------------------------------


@pytest.mark.parametrize(
    "hostile",
    [
        "",
        "|",
        "||||",
        "|\n|\n|\n",
        "| a |\n| b | c | d |\n",
        "\\|\\|\\|",
        "| " + "x" * 5000 + " |",
        "|\x00|\n",
        "| a |\r\n|---|\r\n| b |\r\n",
        "| a | b |\n|---|\n| c |\n",
        "-|-|-",
        "|--|--|\n|--|--|\n",
    ],
)
def test_parser_is_total_and_never_raises(hostile: str) -> None:
    """A parser that crashes turns a lint into an UNKNOWN verdict — the same
    failure mode as a silent drop, one level up. Nothing may propagate."""
    tables = parse_tables("Matrix", hostile)
    assert isinstance(tables, list)
    for table in tables:
        assert isinstance(table, ParsedTable)
        assert all(isinstance(row, ParsedRow) for row in table.rows)
        assert all(isinstance(error, TableError) for error in table.errors)


def test_render_is_one_line_and_names_section_and_line() -> None:
    error = _only(_table("| 1 | REQ-1 | MUST |")).errors[0]
    rendered = error.render()
    assert "\n" not in rendered
    assert "Traceability Matrix" in rendered and ":3" in rendered


# --- round-1 review fixes (PR B) ----------------------------------------------


def test_all_dash_data_row_is_kept_not_swallowed() -> None:
    """Review finding 3: a separator is a DELIMITER only in the position right
    after the header. Further down it is data, and the invariant says data is
    never silently dropped."""
    body = "| a | b | c |\n|---|---|---|\n| 1 | x | y |\n| - | - | - |\n| 2 | z | w |\n"
    table = parse_tables("Matrix", body)[0]
    assert len(table.rows) == 3


def test_escaped_backslash_before_a_pipe_is_a_real_delimiter() -> None:
    """Review finding 4: `\\\\` is a complete self-escape, so the pipe that
    follows delimits. A cell ending in a backslash (a Windows path) used to
    swallow the next column."""
    from spec_linter.markdown.tables import _split_cells

    assert _split_cells(r"| a | b\\| c | d |") == ["a", "b\\", "c", "d"]


def test_ambiguous_two_line_block_always_resolves_toward_data() -> None:
    """Review findings 5 and 7 (Critical): `[data row, all-dash row]` is
    structurally identical to `[header, delimiter]`, and reading it as a header
    made the data line vanish. Resolved for EVERY caller with no vocabulary —
    the first attempt used caller-supplied hint words and was wired into one of
    six call sites, leaving the same bypass live in the other five."""
    body = "| 2 | Critical | SQL injection | db.py |  |\n| - | - | - | - | - |\n"
    table = parse_tables("Review Verdict", body)[0]
    assert len(table.rows) == 2
    assert any(error.kind is TableErrorKind.MISSING_HEADER for error in table.errors)


def test_a_header_containing_an_innocent_substring_is_unaffected() -> None:
    """The substring false positive the vocabulary approach carried: a header
    reading "Deemed Unimportant" contains "important". With no vocabulary there
    is nothing to match against, so the class cannot exist."""
    body = "| # | Deemed Unimportant | Owner |\n|---|---|---|\n| 1 | x | y |\n"
    table = parse_tables("Matrix", body)[0]
    assert table.headers == ["#", "Deemed Unimportant", "Owner"]
    assert len(table.rows) == 1
    assert table.errors == []
