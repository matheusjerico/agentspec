"""Exact section addressing — the single authority for locating fixed-name
contract sections inside a Markdown artifact, and the single scanner that
decides which lines are live document structure at all.

Remediation spec §4.2/§6: a contract section has an ADDRESS, not a name
prefix. Before this module, `Review Verdict` was located by prefix, so a
`## Review Verdict Notes` heading placed ahead of the real section silently
became the scanned scope and an OPEN Critical finding in the real section
produced PASS. Addressing here is exact-slug equality at a fixed heading
level, and EVERY match is returned: a contract that expects one section can
therefore report a duplicate instead of silently reading the first.

Three rules make a scope FAIL-CLOSED. Each was learned from a reproduced
bypass of this module's own drafts, where an OPEN Critical finding dropped
silently out of a scanned body:

0. **Closed boundary vocabulary** (`boundary_slugs`). Only headings a caller
   RECOGNISES as contract sections may end a section. This is the structural
   defence: without it ANY same-level heading truncates — including a plain,
   innocent-looking `## Notes` that needs no Markdown trickery at all — so
   heading detection alone can never be made safe by enumerating opaque
   regions one incident at a time. An unrecognised heading is content.
1. **Same-level boundary.** Among recognised boundaries, a body runs to the
   next heading at EXACTLY the same level. A stray higher-level heading
   (`# whatever`) does not end it: erring toward a LARGER scope can only add
   findings, never hide them.
2. **Opaque regions are never live structure.** Lines inside ``` / ~~~ fences
   (tracked by marker character AND run length — CommonMark requires a closer
   at least as long as its opener, so a nested shorter run stays content) and
   inside `<!-- ... -->` HTML comments are skipped. Reports quote shell, YAML
   and even Markdown constantly; a `# TODO: ...` comment or an illustrative
   `## Heading` inside a snippet is quotation, not structure.

`content_lines()` exports rule 2 so row-level scanners share this one
primitive instead of running their own unaware raw scan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# Up to three leading spaces, per CommonMark's fence and ATX-heading rules.
_FENCE_LINE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_COMMENT_OPEN = re.compile(r"<!--")
_COMMENT_CLOSE = re.compile(r"-->")
_HEADING_LINE = re.compile(r"^ {0,3}(#{1,6})\s+(.*\S)\s*$")


def slug(text: str) -> str:
    """Canonical section slug: lowercase, non-alphanumeric runs collapsed to
    `_`, separators trimmed. `TDD Evidence (required when TDD Mode != off)`
    becomes `tdd_evidence_required_when_tdd_mode_off`."""
    return _NON_ALNUM.sub("_", text.lower()).strip("_")


@dataclass(frozen=True, slots=True)
class Section:
    """One located section. `line` is the 1-indexed heading line, kept so a
    finding can point a human at the exact heading (spec §6.4 item 5)."""

    slug: str
    title: str
    line: int
    body: str


@dataclass(frozen=True, slots=True)
class _ScannedLine:
    number: int  # 1-indexed
    text: str  # without the line terminator
    offset: int  # offset of the line start
    width: int  # length including the line terminator
    opaque: bool  # inside a fence or an HTML comment


@dataclass(frozen=True, slots=True)
class _Heading:
    level: int
    title: str
    line: int
    start: int  # offset where the heading line begins
    body_start: int  # offset just past the heading line


def _scan(artifact: str) -> list[_ScannedLine]:
    """Every line, tagged with whether it sits inside an opaque region."""
    scanned: list[_ScannedLine] = []
    offset = 0
    fence: str | None = None  # the OPENING run, e.g. "````"
    in_comment = False
    for number, raw in enumerate(artifact.splitlines(keepends=True), start=1):
        text = raw.rstrip("\n").rstrip("\r")
        opaque = True
        if in_comment:
            if _COMMENT_CLOSE.search(text):
                in_comment = False
        else:
            fence_match = _FENCE_LINE.match(text)
            if fence_match is not None:
                run = fence_match.group(1)
                if fence is None:
                    fence = run
                elif run[0] == fence[0] and len(run) >= len(fence):
                    fence = None
            elif fence is None:
                if _COMMENT_OPEN.search(text) and not _COMMENT_CLOSE.search(text):
                    in_comment = True
                else:
                    opaque = False
        scanned.append(
            _ScannedLine(
                number=number, text=text, offset=offset, width=len(raw), opaque=opaque
            )
        )
        offset += len(raw)
    return scanned


def content_lines(artifact: str) -> list[tuple[int, str]]:
    """`(1-indexed line number, line)` for every line OUTSIDE fenced code
    blocks and HTML comments — rule 2 of the module docstring, exported so
    row-level scanners inherit the same opacity as heading detection. A
    findings table quoted inside a ```markdown fence is illustration, exactly
    like a quoted heading, and must not be read as live structure."""
    return [(line.number, line.text) for line in _scan(artifact) if not line.opaque]


def _headings(artifact: str) -> list[_Heading]:
    """Every ATX heading that is live document structure, in document order."""
    headings: list[_Heading] = []
    for line in _scan(artifact):
        if line.opaque:
            continue
        heading = _HEADING_LINE.match(line.text)
        if heading is not None:
            headings.append(
                _Heading(
                    level=len(heading.group(1)),
                    title=heading.group(2).strip(),
                    line=line.number,
                    start=line.offset,
                    body_start=line.offset + line.width,
                )
            )
    return headings


def find_sections(
    artifact: str,
    slugs: set[str] | frozenset[str],
    *,
    level: int = 2,
    boundary_slugs: set[str] | frozenset[str] | None = None,
) -> list[Section]:
    """Every heading at exactly `level` whose slug is in `slugs`, in document
    order. Exact equality only: a prefix (`review_verdict_notes`) is a
    different section, and a demoted heading (`### Review Verdict` for a
    level-2 lookup) is not this section at all — which is what makes a
    demotion surface as a missing required section rather than an empty scope.
    Boundaries follow the three fail-closed rules in the module docstring;
    `boundary_slugs=None` falls back to "every same-level peer bounds" for
    callers with no vocabulary of their own."""
    peers = [heading for heading in _headings(artifact) if heading.level == level]
    bounds = (
        peers
        if boundary_slugs is None
        else [heading for heading in peers if slug(heading.title) in boundary_slugs]
    )
    found: list[Section] = []
    for heading in peers:
        section_slug = slug(heading.title)
        if section_slug not in slugs:
            continue
        later = [bound.start for bound in bounds if bound.start > heading.start]
        end = later[0] if later else len(artifact)
        found.append(
            Section(
                slug=section_slug,
                title=heading.title,
                line=heading.line,
                body=artifact[heading.body_start : end],
            )
        )
    return found


def heading_slugs(artifact: str, *, level: int = 2) -> set[str]:
    """Slugs of every heading at exactly `level` — the presence vocabulary the
    required-section check binds on. Opaque regions are excluded, so a snippet
    can never satisfy a required section either."""
    return {
        slug(heading.title) for heading in _headings(artifact) if heading.level == level
    }
