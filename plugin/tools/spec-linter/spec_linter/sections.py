"""Exact section addressing — the single authority for locating fixed-name
contract sections inside a Markdown artifact.

Remediation spec §4.2/§6: a contract section has an ADDRESS, not a name
prefix. Before this module, `Review Verdict` was located by prefix, so a
`## Review Verdict Notes` heading placed ahead of the real section silently
became the scanned scope and an OPEN Critical finding in the real section
produced PASS. Addressing here is exact-slug equality at a fixed heading
level, and EVERY match is returned: a contract that expects one section can
therefore report a duplicate instead of silently reading the first.

Boundary rule: a section's body runs to the next heading of the same or a
higher level, so subheadings stay with their parent section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


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


def _heading_pattern(level: int) -> re.Pattern[str]:
    # Matches headings of level 1..`level`: any of them ends the previous
    # section's body, while only exact-level ones can BE a section.
    return re.compile(rf"^(#{{1,{level}}})\s+(.*\S)\s*$", re.MULTILINE)


def find_sections(artifact: str, slugs: set[str] | frozenset[str], *, level: int = 2) -> list[Section]:
    """Every heading at exactly `level` whose slug is in `slugs`, in document
    order. Exact equality only: a prefix (`review_verdict_notes`) is a
    different section, and a demoted heading (`### Review Verdict` for a
    level-2 lookup) is not this section at all — which is what makes a
    demotion surface as a missing required section rather than an empty scope.
    """
    matches = list(_heading_pattern(level).finditer(artifact))
    found: list[Section] = []
    for i, match in enumerate(matches):
        if len(match.group(1)) != level:
            continue
        section_slug = slug(match.group(2))
        if section_slug not in slugs:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(artifact)
        found.append(
            Section(
                slug=section_slug,
                title=match.group(2).strip(),
                line=artifact.count("\n", 0, match.start()) + 1,
                body=artifact[match.end() : end],
            )
        )
    return found


def heading_slugs(artifact: str, *, level: int = 2) -> set[str]:
    """Slugs of every heading at exactly `level` — the presence vocabulary the
    required-section check binds on."""
    return {
        slug(match.group(2))
        for match in _heading_pattern(level).finditer(artifact)
        if len(match.group(1)) == level
    }
