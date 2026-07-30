"""Packaging parity: proves plugin/ has not diverged from the canonical
.claude/ + tools/ sources.

Parity is a property of the *packaged output*, not of work-in-progress edits
to the canonical tree. This module is therefore deliberately excluded from
build-plugin.sh's pre-build test run (Step 0, which runs `pytest tests/ -q`
before plugin/ is regenerated) — at that point in the build, plugin/ is
stale by definition, so a parity check would fail for the wrong reason. A
post-package step is expected to run exactly this file
(`pytest tests/test_plugin_parity.py`) once plugin/ has been rebuilt,
confirming the build actually produced a plugin/ that matches
.claude/ + tools/.

`make test` (the full suite, run against the committed tree) includes this
file so committed-state parity is always enforced: if the plugin/ checked
into the repo has fallen behind .claude/ or tools/, `make test` fails here.
A failure means "re-run ./build-plugin.sh (make build) so plugin/ matches
the canonical source" — not that the canonical source is wrong.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = Path(os.environ.get("AGENTSPEC_PLUGIN_ROOT", ROOT / "plugin"))

# Reverse (plugin-form -> canonical-form) path rewrites, mirroring the sed
# pairs build-plugin.sh Step 4 ("Path rewriting") applies in the forward
# direction. Ordered longest-prefix-first so no earlier substitution can
# accidentally clobber text a later, more specific pattern was meant to
# match.
REWRITES: list[tuple[str, str]] = [
    ("${CLAUDE_PLUGIN_ROOT}/sdd/architecture/", ".claude/sdd/architecture/"),
    ("${CLAUDE_PLUGIN_ROOT}/sdd/templates/", ".claude/sdd/templates/"),
    ("${CLAUDE_PLUGIN_ROOT}/sdd/_index.md", ".claude/sdd/_index.md"),
    ("${CLAUDE_PLUGIN_ROOT}/sdd/README.md", ".claude/sdd/README.md"),
    ("${CLAUDE_PLUGIN_ROOT}/kb/", ".claude/kb/"),
    ("${CLAUDE_PLUGIN_ROOT}/agents/", ".claude/agents/"),
    ("${CLAUDE_PLUGIN_ROOT}/commands/", ".claude/commands/"),
    ("${CLAUDE_PLUGIN_ROOT}/skills/", ".claude/skills/"),
    ("${CLAUDE_PLUGIN_ROOT}/tools/spec-linter/", "tools/spec-linter/"),
    ("${CLAUDE_PLUGIN_ROOT}/tools/spec-judge/", "tools/spec-judge/"),
]


def normalize(text: str) -> str:
    """Map plugin-form path references back to their canonical .claude/ form.

    Applies the reverse of build-plugin.sh Step 4's sed rewrites so a
    packaged file's text can be diffed, byte-for-byte, against its
    canonical source.
    """
    for plugin_form, canonical_form in REWRITES:
        text = text.replace(plugin_form, canonical_form)
    return text


# Explicit, hand-picked parity pairs (canonical path, plugin path), both
# relative to the repo root. Extend this list as new packaged artifacts need
# a parity guarantee.
_HANDPICKED_PAIRS: list[tuple[str, str]] = [
    (
        ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml",
        "plugin/sdd/architecture/WORKFLOW_CONTRACTS.yaml",
    ),
    (".claude/skills/sdd-build/SKILL.md", "plugin/skills/sdd-build/SKILL.md"),
    (".claude/skills/sdd-ship/SKILL.md", "plugin/skills/sdd-ship/SKILL.md"),
    (
        ".claude/skills/sdd-autopilot/SKILL.md",
        "plugin/skills/sdd-autopilot/SKILL.md",
    ),
    (
        ".claude/sdd/templates/BUILD_REPORT_TEMPLATE.md",
        "plugin/sdd/templates/BUILD_REPORT_TEMPLATE.md",
    ),
]

# spec_linter is a pure-Python package: build-plugin.sh's Step 2c copies it
# verbatim (Step 4's sed rewrites only touch *.md/*.yaml/*.yml/*.json), so
# every module must be byte-identical between the canonical and packaged
# copies. Note: the plugin build prunes tools/spec-linter/tests/, so only
# the spec_linter package dir is in scope here, not its test suite.
_SPEC_LINTER_SRC = ROOT / "tools" / "spec-linter" / "spec_linter"
_SPEC_LINTER_PAIRS: list[tuple[str, str]] = [
    (
        str(py_file.relative_to(ROOT)),
        str(
            Path("plugin/tools/spec-linter/spec_linter")
            / py_file.relative_to(_SPEC_LINTER_SRC)
        ),
    )
    for py_file in sorted(_SPEC_LINTER_SRC.rglob("*.py"))
]

PARITY_PAIRS: list[tuple[str, str]] = _HANDPICKED_PAIRS + _SPEC_LINTER_PAIRS


def _pair_id(pair: tuple[str, str]) -> str:
    canonical_rel, _plugin_rel = pair
    return canonical_rel


@pytest.mark.parametrize("pair", PARITY_PAIRS, ids=_pair_id)
def test_plugin_matches_canonical(pair: tuple[str, str]) -> None:
    """The packaged copy of each file must equal its canonical source.

    Skips only when plugin/ has not been built at all (no packaged output
    exists to compare against). If plugin/ exists but this particular file
    is missing from it, that is a divergence — the canonical file exists but
    was never packaged — so it fails rather than skips.
    """
    if not PLUGIN_ROOT.is_dir():
        pytest.skip("plugin/ not built — run ./build-plugin.sh")

    canonical_rel, plugin_rel = pair
    canonical_path = ROOT / canonical_rel
    plugin_path = PLUGIN_ROOT / Path(plugin_rel).relative_to("plugin")

    assert canonical_path.is_file(), f"canonical source missing: {canonical_rel}"

    if not plugin_path.is_file():
        pytest.fail(f"{plugin_rel} missing from plugin/ — re-package with ./build-plugin.sh")

    canonical_text = canonical_path.read_text()
    plugin_text = plugin_path.read_text()

    # Both sides are normalized: a canonical file may legitimately contain
    # plugin-form literals (e.g. the agent_resolution comment documenting the
    # ${CLAUDE_PLUGIN_ROOT}/ layout), which the packaging sed leaves unchanged.
    # Comparing canonical forms neutralizes exactly the path rewrites and
    # nothing else — content drift still compares unequal.
    assert normalize(plugin_text) == normalize(canonical_text), (
        f"{plugin_rel} has diverged from {canonical_rel} — "
        "re-run ./build-plugin.sh (make build) so plugin/ matches the canonical source"
    )


def test_normalize_round_trips_forward_rewrite() -> None:
    """AT-010: normalize() must invert build-plugin.sh's forward sed rewrite.

    Take a canonical-form reference, apply the same forward substitution
    build-plugin.sh Step 4 performs, and confirm normalize() maps the
    resulting plugin-form text back to the original canonical text.
    """
    canonical_line = "See `.claude/skills/sdd-build/SKILL.md` for the methodology."
    plugin_line = canonical_line.replace(".claude/skills/", "${CLAUDE_PLUGIN_ROOT}/skills/")

    assert plugin_line != canonical_line  # forward rewrite actually changed the text
    assert normalize(plugin_line) == canonical_line


def test_normalize_still_detects_real_divergence() -> None:
    """AT-010: normalize() must not paper over genuine content drift.

    Path-noise normalization should never make an actually-diverged plugin
    file compare equal to its canonical source — only path-reference
    differences are neutralized, not content changes.
    """
    canonical_text = "Step 1: run the linter.\nStep 2: verify the verdict.\n"
    diverged_plugin_text = "Step 1: run the linter.\nStep 2: SKIP the verdict.\n"

    assert normalize(diverged_plugin_text) != canonical_text
