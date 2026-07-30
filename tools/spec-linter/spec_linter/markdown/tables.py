"""The one table parser (remediation spec §7.3–7.4).

**Invariant — parse, never filter.** Every recognised table line becomes a
`ParsedRow`, a `TableError`, or both. There is no third outcome and no code
path that discards a line silently. This is deliberate and structural: the
previous generation of hand-rolled scanners returned only the rows they liked,
so a contract could never tell "malformed" from "absent" — and four
consecutive adversarial review rounds each found another shape that vanished
that way. With the discard behaviour deleted, there is no shape left to find.

**Totality.** No input may raise. Malformed, truncated, adversarial or binary
input yields errors, never a stack trace: a crash turns a lint into an
*unknown* verdict, which is the same failure as a silent drop one level up.

**Opacity is not ours.** Which lines are live structure is decided by
`..sections.content_lines` (fences with CommonMark run-length, HTML comments).
A table quoted inside a fence is illustration and is never parsed here.

The parser reports STRUCTURE only — it never assigns a severity. Mapping a
`TableError` to a FAIL or a WARN is contract policy, so this module stays
reusable by every phase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from ..sections import content_lines

_SEPARATOR_CELL = re.compile(r"^:?-+:?$")
_PLACEHOLDER = re.compile(r"\{[^{}]*\}")


class TableErrorKind(StrEnum):
    """The §7.4 error vocabulary. Closed: a new structural failure gets a new
    member here rather than being folded into an existing one."""

    COLUMN_COUNT = "column_count"
    MISSING_HEADER = "missing_header"
    DUPLICATE_HEADER = "duplicate_header"
    EMPTY_REQUIRED_CELL = "empty_required_cell"
    PLACEHOLDER = "placeholder"
    INVALID_IDENTIFIER = "invalid_identifier"
    DUPLICATE_IDENTIFIER = "duplicate_identifier"
    UNEXPECTED_EXTRA_COLUMN = "unexpected_extra_column"


@dataclass(frozen=True, slots=True)
class TableError:
    """A structural defect, with everything a human needs to fix the line
    (§7.4: section, line, expected/found cells, original content, kind)."""

    kind: TableErrorKind
    section: str
    line: int
    raw: str
    expected_cells: int | None = None
    found_cells: int | None = None
    detail: str = ""

    def render(self) -> str:
        counts = ""
        if self.expected_cells is not None and self.found_cells is not None:
            counts = f" (expected {self.expected_cells} cells, found {self.found_cells})"
        return f"{self.section}:{self.line} {self.kind}{counts}: {self.detail or self.raw.strip()}"


@dataclass(frozen=True, slots=True)
class ParsedRow:
    """One data row. `cells` is whatever the line actually contained — a row
    with the wrong width is still returned, paired with its error."""

    line: int
    cells: list[str]
    raw: str

    def cell(self, index: int) -> str:
        """Positional access that never raises — a short row reads as empty
        rather than exploding a consumer that assumed the template width."""
        return self.cells[index] if 0 <= index < len(self.cells) else ""


@dataclass(frozen=True, slots=True)
class ParsedTable:
    section: str
    header_line: int
    headers: list[str]
    rows: list[ParsedRow] = field(default_factory=list)
    errors: list[TableError] = field(default_factory=list)

    def header_index(self, name: str) -> int | None:
        """Index of a header by case-insensitive name, or None."""
        wanted = name.strip().lower()
        for index, header in enumerate(self.headers):
            if header.strip().lower() == wanted:
                return index
        return None


def _split_cells(raw: str) -> list[str]:
    """Split a table line into cells, honouring `\\|` escapes.

    The ONLY cell splitter in the codebase: seven hand-rolled copies of
    `strip("|").split("|")` existed before, and every one of them broke an
    escaped pipe into two cells."""
    text = raw.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    cells: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text) and text[index + 1] == "|":
            current.append("|")
            index += 2
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    cells.append("".join(current).strip())
    return cells


def _column_index(headers: list[str], name: str) -> int | None:
    wanted = name.strip().lower()
    return next(
        (i for i, header in enumerate(headers) if header.strip().lower() == wanted), None
    )


def _is_table_line(text: str) -> bool:
    """A line that opens with a pipe is a table line. Deliberately permissive:
    a row missing its trailing pipe used to be invisible, and invisibility is
    a hiding place."""
    return text.strip().startswith("|")


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(_SEPARATOR_CELL.match(cell) for cell in cells if cell != "")


def _blocks(body: str) -> list[list[tuple[int, str]]]:
    """Contiguous runs of live table lines, each `(line number, text)`."""
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for number, text in content_lines(body):
        if _is_table_line(text):
            current.append((number, text))
            continue
        if current:
            blocks.append(current)
        current = []
    if current:
        blocks.append(current)
    return blocks


def _header_errors(section: str, line: int, raw: str, headers: list[str]) -> list[TableError]:
    errors: list[TableError] = []
    seen: set[str] = set()
    for header in headers:
        key = header.strip().lower()
        if not key:
            continue
        if key in seen:
            errors.append(
                TableError(
                    kind=TableErrorKind.DUPLICATE_HEADER,
                    section=section,
                    line=line,
                    raw=raw,
                    detail=f"duplicate column name {header!r}",
                )
            )
        seen.add(key)
    return errors


def _row_errors(
    section: str,
    row: ParsedRow,
    width: int,
    *,
    required: set[str] | None,
    headers: list[str],
) -> list[TableError]:
    errors: list[TableError] = []
    found = len(row.cells)
    if found < width:
        errors.append(
            TableError(
                kind=TableErrorKind.COLUMN_COUNT,
                section=section,
                line=row.line,
                raw=row.raw,
                expected_cells=width,
                found_cells=found,
                detail="row is narrower than its header",
            )
        )
    elif found > width:
        errors.append(
            TableError(
                kind=TableErrorKind.UNEXPECTED_EXTRA_COLUMN,
                section=section,
                line=row.line,
                raw=row.raw,
                expected_cells=width,
                found_cells=found,
                detail="row is wider than its header",
            )
        )
    # Placeholders are only a defect in IDENTIFIER columns. Free-text cells
    # legitimately quote braces — a finding that reads "mapping closed to
    # {value, reason}" is prose, not an unfilled template — and flagging those
    # is exactly the cry-wolf failure that gets a gate routed around.
    for name in sorted(required or ()):
        index = _column_index(headers, name)
        if index is not None and _PLACEHOLDER.search(row.cell(index)):
            errors.append(
                TableError(
                    kind=TableErrorKind.PLACEHOLDER,
                    section=section,
                    line=row.line,
                    raw=row.raw,
                    detail=f"unfilled placeholder in column {name!r}: {row.cell(index)!r}",
                )
            )
    for name in sorted(required or ()):
        index = _column_index(headers, name)
        if index is not None and row.cell(index) == "":
            errors.append(
                TableError(
                    kind=TableErrorKind.EMPTY_REQUIRED_CELL,
                    section=section,
                    line=row.line,
                    raw=row.raw,
                    detail=f"required column {name!r} is empty",
                )
            )
    return errors


def parse_tables(
    section: str, body: str, *, required_columns: set[str] | None = None
) -> list[ParsedTable]:
    """Every table in `body`, with rows AND structural errors.

    `required_columns` names the columns whose cells may not be empty. WHICH
    columns those are is contract policy, so it is supplied by the caller
    rather than assumed here (Decision 5): plenty of legitimate tables carry
    an intentionally blank Notes cell.

    Total: any string is accepted and yields a (possibly empty) list."""
    tables: list[ParsedTable] = []
    for block in _blocks(body):
        header_line, header_raw = block[0]
        headers = _split_cells(header_raw)
        errors = list(_header_errors(section, header_line, header_raw, headers))

        data = block[1:]
        header_is_data = not _is_separator(_split_cells(data[0][1])) if data else True
        if header_is_data and _is_separator(headers):
            # A block that opens with a separator has no header at all.
            errors.append(
                TableError(
                    kind=TableErrorKind.MISSING_HEADER,
                    section=section,
                    line=header_line,
                    raw=header_raw,
                    detail="table opens with a delimiter row",
                )
            )

        rows: list[ParsedRow] = []
        width = len([cell for cell in headers]) if headers else 0
        for number, text in data:
            cells = _split_cells(text)
            if _is_separator(cells):
                continue
            row = ParsedRow(line=number, cells=cells, raw=text)
            rows.append(row)
            errors.extend(
                _row_errors(section, row, width, required=required_columns, headers=headers)
            )

        if header_is_data and not _is_separator(headers):
            # No delimiter row anywhere: the first line is data, not a header.
            errors.append(
                TableError(
                    kind=TableErrorKind.MISSING_HEADER,
                    section=section,
                    line=header_line,
                    raw=header_raw,
                    detail="table has no delimiter row; first line read as data",
                )
            )
            first = ParsedRow(line=header_line, cells=headers, raw=header_raw)
            rows.insert(0, first)

        tables.append(
            ParsedTable(
                section=section,
                header_line=header_line,
                headers=headers,
                rows=rows,
                errors=errors,
            )
        )
    return tables
