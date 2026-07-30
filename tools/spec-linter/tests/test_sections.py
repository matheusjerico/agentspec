"""Shared exact-section addressing module (remediation spec §6, PR A).

Written RED-first: `spec_linter.sections` does not exist yet. The module is the
single addressing authority for fixed-name contract sections — exact slug
equality, `##`-level only, EVERY match returned in document order with the
heading's line number so findings can point at it.
"""

from __future__ import annotations

import pytest

from spec_linter.sections import Section, find_sections, slug

DOC = """\
# Title

## Alpha

alpha body

## Alpha Notes

decoy body

### Alpha

demoted body

## Beta

beta body
"""


def test_slug_lowercases_and_collapses_non_alphanumerics() -> None:
    assert slug("Review Verdict") == "review_verdict"
    assert slug("Task Execution with Agent Attribution") == (
        "task_execution_with_agent_attribution"
    )
    assert slug("TDD Evidence (required when TDD Mode != off)") == (
        "tdd_evidence_required_when_tdd_mode_off"
    )


def test_slug_strips_leading_and_trailing_separators() -> None:
    assert slug("  ...Alpha!!  ") == "alpha"
    assert slug("(Alpha)") == "alpha"


def test_exact_match_only_prefix_decoy_never_matches() -> None:
    sections = find_sections(DOC, {"alpha"})
    assert [s.title for s in sections] == ["Alpha"]
    assert sections[0].body.strip() == "alpha body"


def test_decoy_is_addressable_under_its_own_slug() -> None:
    sections = find_sections(DOC, {"alpha_notes"})
    assert [s.title for s in sections] == ["Alpha Notes"]


def test_demoted_heading_is_not_a_level_two_section() -> None:
    # `### Alpha` must never be returned for a level-2 lookup — that is what
    # makes a demoted heading surface as a missing required section instead.
    assert [s.title for s in find_sections(DOC, {"alpha"})] == ["Alpha"]
    assert all(s.line != DOC[: DOC.index("### Alpha")].count("\n") + 1 for s in find_sections(DOC, {"alpha"}))


def test_body_ends_at_the_next_level_two_heading_but_keeps_subheadings() -> None:
    body = find_sections(DOC, {"alpha_notes"})[0].body
    assert "decoy body" in body
    assert "### Alpha" in body  # subheadings belong to their parent section
    assert "beta body" not in body


def test_every_match_is_returned_in_document_order() -> None:
    doc = "## Dup\n\nfirst\n\n## Other\n\nx\n\n## Dup\n\nsecond\n"
    sections = find_sections(doc, {"dup"})
    assert len(sections) == 2
    assert [s.body.strip() for s in sections] == ["first", "second"]
    assert sections[0].line < sections[1].line


def test_multiple_slugs_resolve_as_one_sanctioned_set() -> None:
    doc = "## TDD Evidence\n\nbare\n\n## Beta\n\nx\n"
    sections = find_sections(doc, {"tdd_evidence", "tdd_evidence_required_when_tdd_mode_off"})
    assert [s.slug for s in sections] == ["tdd_evidence"]


def test_line_numbers_are_one_indexed_heading_lines() -> None:
    doc = "# Title\n\n## Alpha\n\nbody\n"
    assert find_sections(doc, {"alpha"})[0].line == 3


def test_absent_section_returns_empty_list() -> None:
    assert find_sections(DOC, {"nowhere"}) == []


def test_section_with_empty_body_still_matches() -> None:
    doc = "## Alpha\n## Beta\n\nx\n"
    sections = find_sections(doc, {"alpha"})
    assert len(sections) == 1
    assert sections[0].body.strip() == ""


def test_section_is_frozen() -> None:
    section = find_sections(DOC, {"alpha"})[0]
    with pytest.raises(Exception):
        section.title = "mutated"  # type: ignore[misc]


def test_level_parameter_addresses_other_heading_levels() -> None:
    sections = find_sections(DOC, {"alpha"}, level=3)
    assert [s.body.strip() for s in sections] == ["demoted body"]


def test_trailing_whitespace_in_heading_is_tolerated() -> None:
    doc = "## Alpha   \n\nbody\n"
    assert [s.title for s in find_sections(doc, {"alpha"})] == ["Alpha"]
