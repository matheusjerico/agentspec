"""Shared exact-section addressing module (remediation spec §6, PR A).

Written RED-first: `spec_linter.sections` does not exist yet. The module is the
single addressing authority for fixed-name contract sections — exact slug
equality, `##`-level only, EVERY match returned in document order with the
heading's line number so findings can point at it.
"""

from __future__ import annotations

import pytest

from spec_linter.sections import Section, find_sections, heading_slugs, slug

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
    assert len(sections) == 1
    # Conservative same-level boundary: a level-3 section runs to the next
    # level-3 heading, so it may overrun its parent — a larger scope can only
    # add findings, never hide one.
    assert sections[0].body.strip().startswith("demoted body")


def test_trailing_whitespace_in_heading_is_tolerated() -> None:
    doc = "## Alpha   \n\nbody\n"
    assert [s.title for s in find_sections(doc, {"alpha"})] == ["Alpha"]


# --- fail-closed boundary + fenced-code awareness -----------------------------
# Both rules exist because this module's first draft used a same-or-higher-level
# boundary with no fence awareness, which let a stray `#` line (even a comment
# inside a quoted snippet) truncate a section and drop findings from the scan.


def test_stray_higher_level_heading_does_not_end_a_section() -> None:
    doc = "## Alpha\n\nfirst\n\n# Stray Top Level\n\nstill alpha\n\n## Beta\n\nx\n"
    body = find_sections(doc, {"alpha"})[0].body
    assert "first" in body
    assert "still alpha" in body  # a larger scope can add findings, never hide them
    assert "x" not in body.split("## Beta")[0]


def test_hash_comment_inside_a_fenced_block_is_not_a_heading() -> None:
    doc = "## Alpha\n\n```bash\n# TODO: unsafe eval\n```\n\nafter snippet\n\n## Beta\n\nx\n"
    body = find_sections(doc, {"alpha"})[0].body
    assert "after snippet" in body


def test_fenced_pseudo_heading_never_creates_a_section() -> None:
    doc = "# Doc\n\n```markdown\n## Alpha\n```\n\n## Beta\n\nx\n"
    assert find_sections(doc, {"alpha"}) == []
    assert "alpha" not in heading_slugs(doc)


def test_tilde_fences_are_honoured_too() -> None:
    doc = "## Alpha\n\n~~~text\n## Beta\n~~~\n\nafter\n\n## Gamma\n\nx\n"
    sections = find_sections(doc, {"alpha", "beta"})
    assert [s.slug for s in sections] == ["alpha"]
    assert "after" in sections[0].body


def test_indented_fence_and_heading_are_recognised() -> None:
    doc = "## Alpha\n\n   ```\n   # not a heading\n   ```\n\ntail\n\n## Beta\n\nx\n"
    assert "tail" in find_sections(doc, {"alpha"})[0].body


# --- closed boundary vocabulary (the structural defence) ----------------------
# Enumerated from "CommonMark constructs that can carry a literal `#` line" PLUS
# the plainest attack of all: a legitimate-looking unrecognised heading. Only
# recognised contract sections may end a section, so all of these are content.

BOUNDS = {"alpha", "beta"}


def _alpha_body(middle: str) -> str:
    doc = f"## Alpha\n\nhead\n\n{middle}\n\ntail\n\n## Beta\n\nbeta body\n"
    return find_sections(doc, {"alpha"}, boundary_slugs=BOUNDS)[0].body


@pytest.mark.parametrize(
    "middle",
    [
        "## Notes",                                  # plain unrecognised heading
        "# Stray Top Level",                         # higher level
        "### Subsection",                            # lower level
        "<!--\n## superseded\n-->",                  # multi-line HTML comment
        "<!-- ## Beta -->",                          # a REAL boundary name, commented out
        "```bash\n# TODO: unsafe eval\n```",         # fenced comment
        "````\n```\n## Beta\n```\n````",             # nested shorter fence run
        "~~~text\n## Beta\n~~~",                     # tilde fence
        "    # indented code comment",               # 4-space indented code
    ],
)
def test_no_unrecognised_construct_can_truncate_a_section(middle: str) -> None:
    body = _alpha_body(middle)
    assert "head" in body
    assert "tail" in body, "the section was truncated — a scan scope could hide findings"
    assert "beta body" not in body, "the real boundary must still end the section"


def test_recognised_boundary_still_ends_the_section() -> None:
    body = _alpha_body("## Beta\n\nbeta body\n\n## Alpha Notes")
    assert "head" in body
    assert "beta body" not in body


def test_closer_shorter_than_opener_does_not_close_the_fence() -> None:
    doc = "## Alpha\n\n````\n```\n## Beta\n````\n\ntail\n\n## Beta\n\nx\n"
    body = find_sections(doc, {"alpha"}, boundary_slugs=BOUNDS)[0].body
    assert "tail" in body


def test_crlf_artifacts_are_handled() -> None:
    doc = "## Alpha\r\n\r\nhead\r\n\r\n## Notes\r\n\r\ntail\r\n\r\n## Beta\r\n\r\nx\r\n"
    body = find_sections(doc, {"alpha"}, boundary_slugs=BOUNDS)[0].body
    assert "head" in body and "tail" in body and "x" not in body


def test_without_boundary_slugs_every_peer_still_bounds() -> None:
    # Backwards-compatible default for callers that have no vocabulary.
    doc = "## Alpha\n\nhead\n\n## Notes\n\ntail\n"
    body = find_sections(doc, {"alpha"})[0].body
    assert "head" in body and "tail" not in body
