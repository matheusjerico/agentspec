"""Tests for DesignPhaseContract, run through `engine.lint`.

Built on a single module-level VALID_DESIGN fixture — a minimal but fully
conformant design doc carrying all 6 required sections plus a valid
`## Task Manifest (v2)` block declaring three tasks (TASK-A with no
dependencies, TASK-B depending on TASK-A in the same `parallel_group`
(`alpha`), TASK-C depending on TASK-A with no group) — mutated per test via
the `mutate` helper so each test's intent (what changed, what should break)
stays legible, mirroring `test_define_phase_contract.py`.

The v2 task manifest is opt-in: a DESIGN with no `## Task Manifest (v2)`
section (or no ```yaml fence within it) is v1 — ZERO `TM.*` findings, never a
WARN, never a FAIL. Once a DESIGN DOES declare a manifest, every `TM.*` rule
is `Level.FAIL` except `TM.missing_requirements`, which is `Level.WARN`. A
fence that exists but fails to parse into a `task_manifest` mapping is
`TM.unparseable` (FAIL), distinct from an absent manifest (silent).

`L2.required_section` keeps its pre-existing FAIL semantics, exactly
mirroring `SddPhaseContract`.
"""

from __future__ import annotations

from spec_linter.contracts.design_phase import DesignPhaseContract
from spec_linter.engine import lint
from spec_linter.verdict import Level, Verdict

REQUIRED_SECTIONS = [
    "architecture_overview",
    "components",
    "key_decisions",
    "file_manifest",
    "code_patterns",
    "testing_strategy",
]
REQUIRED_TASK_FIELDS = ["id", "title", "files", "verification"]
FILES_KEYS = ["create", "modify", "tests"]
VERIFICATION_KEYS = ["red", "green", "regression"]


def _contract() -> DesignPhaseContract:
    return DesignPhaseContract(
        required_sections=REQUIRED_SECTIONS,
        required_task_fields=REQUIRED_TASK_FIELDS,
        files_keys=FILES_KEYS,
        verification_keys=VERIFICATION_KEYS,
    )


def _lint(doc: str) -> Verdict:
    return lint(doc, _contract())


def _rules(verdict: Verdict) -> list[str]:
    return [f.rule for f in verdict.findings]


def mutate(doc: str, old: str, new: str) -> str:
    """Replace `old` with `new`, asserting `old` is actually present in
    `doc` — a guard against silently-green fixtures if VALID_DESIGN drifts
    and a mutation stops mutating anything."""
    assert old in doc, f"fixture drift: {old!r} not found in doc"
    return doc.replace(old, new)


# Each task block is kept as its own constant so mutations can be anchored on
# a whole, uniquely-identified block (via its `- id: TASK-*` line) rather than
# on small fragments that collide across tasks (e.g. TASK-B and TASK-C both
# `depends_on: ["TASK-A"]`; TASK-A and TASK-B are both `parallel_group: alpha`).
TASK_A = """\
    - id: TASK-A
      title: Implement module A
      requirements: ["REQ-1"]
      depends_on: []
      files:
        create: ["fileA.py"]
        modify: []
        tests: ["test_fileA.py"]
      execution:
        parallel_group: alpha
      verification:
        green: "pytest tests/test_fileA.py"
"""

TASK_B = """\
    - id: TASK-B
      title: Implement module B
      requirements: ["REQ-2"]
      depends_on: ["TASK-A"]
      files:
        create: ["fileB.py"]
        modify: []
        tests: ["test_fileB.py"]
      execution:
        parallel_group: alpha
      verification:
        green: "pytest tests/test_fileB.py"
"""

TASK_C = """\
    - id: TASK-C
      title: Implement module C
      requirements: ["REQ-3"]
      depends_on: ["TASK-A"]
      files:
        create: ["fileC.py"]
        modify: []
        tests: ["test_fileC.py"]
      verification:
        green: "pytest tests/test_fileC.py"
"""

TASKS_BLOCK = "  tasks:\n" + TASK_A + TASK_B + TASK_C

VALID_DESIGN = f"""\
# DESIGN: SAMPLE_FEATURE

## Architecture Overview

Sample architecture overview.

## Components

Sample components.

## Key Decisions

Sample key decisions.

## File Manifest

Sample file manifest.

## Task Manifest (v2)

> Derived from the file manifest: a task is a verifiable change; dependencies
> form a DAG; tasks in the same `parallel_group` never write the same file.

```yaml
task_manifest:
  manifest_version: 2
{TASKS_BLOCK}```

## Code Patterns

Sample code patterns.

## Testing Strategy

Sample testing strategy.
"""


def test_valid_design_passes() -> None:
    verdict = _lint(VALID_DESIGN)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_missing_task_manifest_section_is_v1_silent() -> None:
    start = VALID_DESIGN.index("## Task Manifest (v2)")
    end = VALID_DESIGN.index("## Code Patterns")
    section = VALID_DESIGN[start:end]
    report = mutate(VALID_DESIGN, section, "")
    verdict = _lint(report)
    assert verdict.level == Level.PASS
    assert not any(f.rule.startswith("TM.") for f in verdict.findings)


def test_malformed_yaml_fails_unparseable_only() -> None:
    report = mutate(
        VALID_DESIGN, "  manifest_version: 2\n", ":{bad\n  manifest_version: 2\n"
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert _rules(verdict) == ["TM.unparseable"]


def test_duplicate_id_fails() -> None:
    report = mutate(VALID_DESIGN, "    - id: TASK-C", "    - id: TASK-A")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "TM.duplicate_id" in _rules(verdict)


def test_cycle_fails_naming_both_ids() -> None:
    new_task_a = TASK_A.replace("depends_on: []", 'depends_on: ["TASK-B"]')
    report = mutate(VALID_DESIGN, TASK_A, new_task_a)
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    cycles = [f for f in verdict.findings if f.rule == "TM.cycle"]
    assert len(cycles) == 1
    assert "TASK-A" in cycles[0].message
    assert "TASK-B" in cycles[0].message


def test_unknown_dependency_fails() -> None:
    new_task_c = TASK_C.replace('depends_on: ["TASK-A"]', 'depends_on: ["TASK-GHOST"]')
    report = mutate(VALID_DESIGN, TASK_C, new_task_c)
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "TM.unknown_dependency" in _rules(verdict)


def test_write_conflict_same_group_fails_naming_both_ids() -> None:
    new_task_b = TASK_B.replace('create: ["fileB.py"]', 'create: ["fileA.py"]')
    report = mutate(VALID_DESIGN, TASK_B, new_task_b)
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    conflicts = [f for f in verdict.findings if f.rule == "TM.write_conflict"]
    assert len(conflicts) == 1
    assert "TASK-A" in conflicts[0].message
    assert "TASK-B" in conflicts[0].message


def test_write_conflict_different_groups_does_not_fire() -> None:
    new_task_b = TASK_B.replace('create: ["fileB.py"]', 'create: ["fileA.py"]').replace(
        "parallel_group: alpha", "parallel_group: beta"
    )
    report = mutate(VALID_DESIGN, TASK_B, new_task_b)
    verdict = _lint(report)
    assert "TM.write_conflict" not in _rules(verdict)


def test_missing_verification_mapping_fails() -> None:
    report = mutate(
        VALID_DESIGN, '      verification:\n        green: "pytest tests/test_fileC.py"\n', ""
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "TM.missing_verification" in _rules(verdict)


def test_verification_present_but_all_values_empty_fails() -> None:
    report = mutate(
        VALID_DESIGN,
        '        green: "pytest tests/test_fileC.py"\n',
        '        green: ""\n',
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "TM.missing_verification" in _rules(verdict)


def test_missing_required_field_fails_invalid_task() -> None:
    report = mutate(VALID_DESIGN, "      title: Implement module C\n", "")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "TM.invalid_task" in _rules(verdict)


def test_unknown_verification_key_fails_invalid_task() -> None:
    report = mutate(
        VALID_DESIGN,
        '        green: "pytest tests/test_fileC.py"\n',
        '        green: "pytest tests/test_fileC.py"\n        smoke: "cmd"\n',
    )
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "TM.invalid_task" in _rules(verdict)


def test_empty_requirements_warns_but_stays_below_fail() -> None:
    report = mutate(VALID_DESIGN, '      requirements: ["REQ-3"]\n', "      requirements: []\n")
    verdict = _lint(report)
    assert verdict.level == Level.WARN
    assert "TM.missing_requirements" in _rules(verdict)


def test_required_section_at_other_heading_level_still_counts() -> None:
    report = mutate(VALID_DESIGN, "## Components", "### Components")
    verdict = _lint(report)
    assert verdict.level == Level.PASS
    assert not any(f.rule == "L2.required_section" for f in verdict.findings)


def test_empty_tasks_list_fails_invalid_task() -> None:
    report = mutate(VALID_DESIGN, TASKS_BLOCK, "  tasks: []\n")
    verdict = _lint(report)
    assert verdict.level == Level.FAIL
    assert "TM.invalid_task" in _rules(verdict)


def test_bare_task_manifest_heading_also_parses() -> None:
    # `_section_after` matches on a slug PREFIX ("task_manifest"): both
    # "Task Manifest (v2)" (slug "task_manifest_v2") and the bare "Task
    # Manifest" (slug "task_manifest") satisfy `.startswith("task_manifest")`
    # — real behavior, not a documentation claim.
    report = mutate(VALID_DESIGN, "## Task Manifest (v2)", "## Task Manifest")
    verdict = _lint(report)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_fenceless_decoy_section_does_not_shadow_the_manifest() -> None:
    decoy = "## Task Manifest Notes\n\nProse only — no yaml fence here.\n\n"
    doc = mutate(
        VALID_DESIGN,
        "## Task Manifest (v2)",
        decoy + "## Task Manifest (v2)",
    )
    doc = mutate(doc, 'depends_on: ["TASK-A"]', 'depends_on: ["TASK-GHOST"]')
    verdict = _lint(doc)
    assert verdict.level == Level.FAIL
    assert "TM.unknown_dependency" in _rules(verdict)


def test_non_string_id_is_invalid_task() -> None:
    doc = mutate(VALID_DESIGN, "id: TASK-C", "id: 42")
    verdict = _lint(doc)
    assert verdict.level == Level.FAIL
    assert "TM.invalid_task" in _rules(verdict)


def test_tests_key_overlap_does_not_conflict() -> None:
    doc = mutate(VALID_DESIGN, 'tests: ["test_fileB.py"]', 'tests: ["test_fileA.py"]')
    verdict = _lint(doc)
    assert "TM.write_conflict" not in _rules(verdict)


def test_duplicate_ids_do_not_emit_misleading_cycles() -> None:
    doc = mutate(VALID_DESIGN, "id: TASK-C", "id: TASK-A")
    verdict = _lint(doc)
    rules = _rules(verdict)
    assert "TM.duplicate_id" in rules
    assert "TM.cycle" not in rules


def test_unrelated_fence_in_decoy_section_does_not_decide() -> None:
    decoy = (
        "## Task Manifest Background\n\n"
        "```yaml\n"
        "some_unrelated_config:\n"
        "  example: true\n"
        "```\n\n"
    )
    doc = mutate(VALID_DESIGN, "## Task Manifest (v2)", decoy + "## Task Manifest (v2)")
    verdict = _lint(doc)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_task_manifest_key_that_is_not_a_mapping_is_unparseable() -> None:
    start = VALID_DESIGN.index("```yaml")
    end = VALID_DESIGN.index("```", start + 7) + 3
    fence = VALID_DESIGN[start:end]
    doc = mutate(VALID_DESIGN, fence, "```yaml\ntask_manifest: broken-scalar\n```")
    verdict = _lint(doc)
    assert verdict.level == Level.FAIL
    assert "TM.unparseable" in _rules(verdict)


# --- Traceability matrix (TX.must_without_task / TX.unknown_type / ---------
# TX.orphan_reference) -------------------------------------------------------
#
# Opt-in via the constructor's `verification_types` param (`None` by default,
# exercised above by every plain `_contract()`-built test — a DESIGN with a
# Traceability Matrix section but no configured vocabulary stays TX-silent).
# This block arms it with the real WORKFLOW_CONTRACTS.yaml
# `traceability.verification_types` 10-type vocabulary, covering the
# must-without-task / unknown-type / orphan-reference rule family layered on
# top of VALID_DESIGN's existing TASK-A/B/C v2 manifest.

VERIFICATION_TYPES = [
    "unit",
    "integration",
    "contract",
    "e2e",
    "browser_accessibility",
    "security",
    "migration_rollback",
    "data_quality",
    "observability",
    "deterministic_inspection",
]


def _contract_with_traceability() -> DesignPhaseContract:
    return DesignPhaseContract(
        required_sections=REQUIRED_SECTIONS,
        required_task_fields=REQUIRED_TASK_FIELDS,
        files_keys=FILES_KEYS,
        verification_keys=VERIFICATION_KEYS,
        verification_types=VERIFICATION_TYPES,
    )


def _lint_with_traceability(doc: str) -> Verdict:
    return lint(doc, _contract_with_traceability())


def _matrix_section(rows: list[tuple[str, str, str, str]]) -> str:
    """Render a `## Traceability Matrix` section: design-side 6-cell rows
    `| # | REQ | Priority | Tasks | Tests | Verification Type |` — only
    cells 1/2/3/5 (REQ/Priority/Tasks/Verification Type) are read by the
    parser; the Tests cell (4) is filled with a placeholder to mirror the
    template shape. `rows` is `(req, priority, tasks, verification_type)`."""
    lines = [
        "\n## Traceability Matrix\n",
        "| # | REQ | Priority | Tasks | Tests | Verification Type |",
        "|---|-----|----------|-------|-------|-------------------|",
    ]
    lines.extend(
        f"| {i} | {req} | {priority} | {tasks} | tests | {vtype} |"
        for i, (req, priority, tasks, vtype) in enumerate(rows, start=1)
    )
    return "\n".join(lines) + "\n"


# Refs resolve to VALID_DESIGN's existing manifest: TASK-A/B/C, whose
# `requirements` are REQ-1/REQ-2/REQ-3 respectively — a matrix that neither
# direction of `TX.orphan_reference` flags.
VALID_MATRIX_ROWS = [
    ("REQ-1", "MUST", "TASK-A", "unit"),
    ("REQ-2", "MUST", "TASK-B", "integration"),
    ("REQ-3", "SHOULD", "TASK-C", "contract"),
]

VALID_DESIGN_WITH_MATRIX = mutate(
    VALID_DESIGN,
    "## Code Patterns",
    _matrix_section(VALID_MATRIX_ROWS) + "\n## Code Patterns",
)


def test_valid_matrix_passes_with_zero_findings() -> None:
    verdict = _lint_with_traceability(VALID_DESIGN_WITH_MATRIX)
    assert verdict.level == Level.PASS
    assert verdict.findings == []


def test_must_row_with_dash_tasks_fails_must_without_task() -> None:
    doc = mutate(
        VALID_DESIGN_WITH_MATRIX,
        "| 1 | REQ-1 | MUST | TASK-A | tests | unit |",
        "| 1 | REQ-1 | MUST | - | tests | unit |",
    )
    verdict = _lint_with_traceability(doc)
    assert verdict.level == Level.FAIL
    assert "TX.must_without_task" in _rules(verdict)


def test_unknown_verification_type_fails() -> None:
    doc = mutate(
        VALID_DESIGN_WITH_MATRIX,
        "| 1 | REQ-1 | MUST | TASK-A | tests | unit |",
        "| 1 | REQ-1 | MUST | TASK-A | tests | vibes |",
    )
    verdict = _lint_with_traceability(doc)
    assert verdict.level == Level.FAIL
    assert "TX.unknown_type" in _rules(verdict)


def test_tasks_cell_citing_unknown_task_id_warns_not_fails() -> None:
    doc = mutate(
        VALID_DESIGN_WITH_MATRIX,
        "| 1 | REQ-1 | MUST | TASK-A | tests | unit |",
        "| 1 | REQ-1 | MUST | TASK-GHOST | tests | unit |",
    )
    verdict = _lint_with_traceability(doc)
    assert verdict.level == Level.WARN
    assert "TX.orphan_reference" in _rules(verdict)
    assert "TX.must_without_task" not in _rules(verdict)


def test_manifest_requirement_not_in_matrix_warns_but_legacy_ref_does_not() -> None:
    doc = mutate(
        VALID_DESIGN_WITH_MATRIX,
        'requirements: ["REQ-3"]',
        'requirements: ["REQ-3", "REQ-999", "MUST-1"]',
    )
    verdict = _lint_with_traceability(doc)
    assert verdict.level == Level.WARN
    orphans = [f for f in verdict.findings if f.rule == "TX.orphan_reference"]
    assert len(orphans) == 1
    assert orphans[0].found == "REQ-999"


def test_no_matrix_section_is_tx_silent() -> None:
    verdict = _lint_with_traceability(VALID_DESIGN)
    assert verdict.level == Level.PASS
    assert not any(f.rule.startswith("TX.") for f in verdict.findings)


def test_rules_disarmed_with_broken_matrix_stays_tx_silent() -> None:
    doc = mutate(
        VALID_DESIGN_WITH_MATRIX,
        "| 1 | REQ-1 | MUST | TASK-A | tests | unit |",
        "| 1 | REQ-1 | MUST | - | tests | vibes |",
    )
    verdict = _lint(doc)  # plain _contract(): verification_types=None
    assert verdict.level == Level.PASS
    assert not any(f.rule.startswith("TX.") for f in verdict.findings)


def test_manifest_not_configured_keeps_tm_silent_even_with_manifest_section() -> None:
    doc = mutate(VALID_DESIGN, 'id: TASK-C', 'id: TASK-A')  # duplicate id — would FAIL if armed
    contract = DesignPhaseContract(
        required_sections=REQUIRED_SECTIONS,
        required_task_fields=[],
        files_keys=[],
        verification_keys=[],
        verification_types=None,
        manifest_configured=False,
    )
    verdict = lint(doc, contract)
    assert not any(f.rule.startswith("TM.") for f in verdict.findings)
    assert verdict.level == Level.PASS


def test_decoy_traceability_matrix_heading_does_not_shadow() -> None:
    decoy = (
        "\n## Traceability Matrix Notes\n\n"
        "| 1 | REQ-999 | MUST | - | - | vibes |\n"
    )
    doc = VALID_DESIGN_WITH_MATRIX.replace("## Traceability Matrix", decoy + "## Traceability Matrix", 1)
    verdict = lint(doc, _contract_with_traceability())
    assert not any(f.rule.startswith("TX.") for f in verdict.findings)
