# DESIGN: Build Report Contract Enforcement

> Technical design for wiring a deterministic Build Report contract gate: a `BuildReportContract` in spec-linter, contract data in WORKFLOW_CONTRACTS.yaml, gate hooks in sdd-build/sdd-ship/sdd-autopilot, and plugin parity proof.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | BUILD_REPORT_CONTRACT_ENFORCEMENT |
| **Date** | 2026-07-29 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_BUILD_REPORT_CONTRACT_ENFORCEMENT.md](./DEFINE_BUILD_REPORT_CONTRACT_ENFORCEMENT.md) |
| **Status** | ✅ Shipped |
| **Design Confidence** | 0.95 — KB patterns (`python`, `testing`) + specialist matches (`python-developer`, `test-generator`, `shell-script-specialist`) |

---

## Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────┐
│                BUILD REPORT CONTRACT GATE — SYSTEM DIAGRAM              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  BUILD_REPORT_{FEATURE}.md                                             │
│          │                                                             │
│          ▼                                                             │
│  tools/spec-linter/spec-lint <report> --phase build                    │
│                              [--legacy-mode warn|fail]                 │
│          │                                                             │
│          │  loads contract data from WORKFLOW_CONTRACTS.yaml:          │
│          │    build.required_sections        (section presence)        │
│          │    build.execution.final_review   (verdicts, fix budget)    │
│          │    build.report_contract          (schema ver, legacy pol.) │
│          ▼                                                             │
│  BuildReportContract (new, spec_linter/contracts/build_report.py)      │
│    parse():  headings + metadata rows + verdict fields + task rows     │
│    check():  L2 section rules  +  BR.* semantic rules                  │
│          │                                                             │
│          ▼                                                             │
│  engine.lint() → Verdict(PASS|WARN|FAIL) → exit 0 / 1 / 2              │
│          │                                                             │
│          ├──→ sdd-build Step 6.5 (Contract Gate: FAIL = not complete)  │
│          ├──→ sdd-ship verification step 2 (FAIL = cannot ship)        │
│          └──→ autopilot Gate L, build artifact (--legacy-mode fail)    │
│                                                                        │
│  PARITY (independent leg):                                             │
│  .claude/** policies ──build-plugin.sh──→ plugin/** copies             │
│          └───── tests/test_plugin_parity.py (post-package) ─────┘      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `BuildReportContract` | New contract class: section presence + 5 semantic rule families (`BR.*`) for BUILD_REPORT documents | Python 3.12, implements existing `Contract` protocol (`parse`/`check` → `list[Finding]`) |
| Contract data (`build.*` in WORKFLOW_CONTRACTS.yaml) | `required_sections`, `report_contract` (schema version, legacy policy), reuses `execution.final_review` (verdicts, fix budget) | YAML, loaded-as-data |
| CLI routing (`cli.py`) | `--phase build` selects `BuildReportContract`; new `--legacy-mode {warn,fail}` flag (default `warn`) | argparse, existing exit-code contract 0/1/2 unchanged |
| Report metadata markers | `Schema Version` and `TDD Mode` rows in BUILD_REPORT Metadata table — deterministic inputs for legacy detection and the TDD rule | Markdown template |
| Gate hooks | Contract Gate in sdd-build (Step 6.5), re-validation in sdd-ship, Gate L extension in sdd-autopilot | Skill markdown (policy, mirrors sdd-define/sdd-design gate text) |
| Plugin parity test | Compares canonical policy files with `plugin/` copies, normalizing documented path rewrites; runs post-package | pytest |

---

## Key Decisions

### Decision 1: A dedicated `BuildReportContract`, parameterized from contract YAML

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |

**Context:** `SddPhaseContract` only checks heading presence. The five semantic rule families (verdict value, open blocking findings, fix-round budget, TDD evidence, task completeness) need field-level parsing of the report. Something must own those rules.

**Choice:** Create `spec_linter/contracts/build_report.py` with a `BuildReportContract(required_sections, verdicts, fix_budget, schema_version, legacy_mode)` class implementing the existing `Contract` protocol. It runs the same section-presence check (reusing the `_slug`/heading regex approach) *plus* `BR.*` semantic rules. Rule parameters (allowed verdicts, fix budget) are read by the CLI from `build.execution.final_review` — the same YAML block `tests/test_build_quality_gates.py` already anchors — never hardcoded in Python.

**Rationale:** Keeps the engine pure (one artifact, one contract, one verdict), keeps WHAT-is-checked as data (the repo's `loaded_as_data` contract source), and leaves `SddPhaseContract` untouched for the other phases.

**Alternatives Rejected:**
1. Extend `SddPhaseContract` with build-specific branches — rejected: pollutes a generic contract with one phase's semantics; other phases would carry dead code.
2. Add functions to `rules.py` — rejected: `rules.py` is the AgentSpec (L2-L4) rule set for agent YAML specs, a different artifact family; mixing them blurs the contract boundary.
3. Two lint passes (sections, then semantics) — rejected: two verdicts for one artifact forces consumers to merge results; the engine contract is one verdict per artifact.

**Consequences:**
- One more contract module to maintain; CLI gains a build-specific branch.
- Semantic thresholds stay editable in YAML without touching Python; the existing documental test keeps YAML and skills aligned.

---

### Decision 2: Deterministic report markers — `Schema Version` and `TDD Mode` metadata rows

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |

**Context:** Two rules need inputs today's report cannot provide deterministically: legacy detection (DEFINE A-002/A-003) and "TDD evidence required" — the template's only TDD signal is section *absence* ("Omit this section entirely when the build ran without `--tdd`"), which cannot distinguish "ran without TDD" from "forgot the evidence".

**Choice:** Add two rows to the BUILD_REPORT Metadata table:
- `**Schema Version** | 2` — reports carrying `Schema Version >= 2` get full enforcement; reports without the row are *legacy*.
- `**TDD Mode** | off / opt-in / required` — sdd-build writes `opt-in` when `--tdd` was passed, `off` otherwise (`required` is reserved for Increment 4's risk policy). Rule: mode ≠ `off` → TDD Evidence section with ≥1 row is mandatory.

**Rationale:** Plan §17.1 already mandates `schema_version` on templates/reports; making TDD mode an explicit declared value is the only way a deterministic linter can fire the evidence rule without guessing (DEFINE open question 1 resolved). Both fields are additive — legacy reports stay readable (plan §4.6).

**Alternatives Rejected:**
1. Infer TDD obligation from the presence of the TDD Evidence section — rejected: circular; a report that omits the section evades the rule it exists to enforce.
2. Pass "TDD was required" as a CLI flag — rejected: the report must be self-describing; Ship and Autopilot re-validate the artifact later without the build's invocation context.

**Consequences:**
- `BUILD_REPORT_TEMPLATE.md` and sdd-build gain two small obligations.
- `TDD Mode: opt-in` also requires evidence (the run did TDD; evidence must exist) — stricter than the DEFINE minimum, intentionally.

---

### Decision 3: Legacy policy via `--legacy-mode {warn,fail}`, both severities declared in the contract YAML

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |

**Context:** The DEFINE requires divergent legacy behavior: manual runs WARN with migration guidance; Autopilot fails closed. But the repo's rule is "a contract assigns the severity of its own rules; consumers MUST NOT reinterpret a verdict" — so Autopilot cannot upgrade a WARN it received.

**Choice:** The contract YAML declares both severities (`build.report_contract.legacy: {manual: WARN, autopilot: FAIL}`). The CLI flag `--legacy-mode {warn,fail}` (default `warn`) selects which *declared* context applies; `BuildReportContract` emits `BR.legacy_report` at the declared level. sdd-build and sdd-ship use the default; sdd-autopilot invokes with `--legacy-mode fail`.

**Rationale:** The consumer names its context, not the severity — both severities remain contract-owned. Exit codes keep their existing meaning (WARN → 0, FAIL → 1), so Gate L's existing exit-code policy works unchanged.

**Alternatives Rejected:**
1. Always WARN; Autopilot pattern-matches `BR.legacy_report` in output — rejected: that is exactly the verdict reinterpretation the contracts file forbids.
2. Always FAIL — rejected: breaks the DEFINE's manual-mode requirement and plan §17.2 (only `dirty`/`missing`/secrets/data-loss are fail-closed from day one).

**Consequences:**
- One new CLI flag to document in USAGE.md; invalid values are an argparse error (exit 2, operational).
- Fail-closed rules (`BR.review_verdict_dirty`, verdict section missing on a v2 report) stay FAIL in **both** modes — legacy-mode only governs the `BR.legacy_report` finding on pre-contract reports.

---

### Decision 4: Parity runs post-package; the pre-build test run excludes it

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-29 |

**Context:** `build-plugin.sh` Step 0 runs `pytest tests/ -q` *before* regenerating `plugin/`. A parity test in that suite deadlocks the build: edit `.claude/` → stale `plugin/` fails parity → Step 0 aborts → plugin can never be regenerated.

**Choice:** `tests/test_plugin_parity.py` compares canonical policy files against their `plugin/` copies after normalizing the documented Step 4/5 path rewrites (`${CLAUDE_PLUGIN_ROOT}/…` ↔ `.claude/…`, `tools/spec-linter/`), skipping with a visible reason when `plugin/` is absent. `build-plugin.sh` Step 0 adds `--ignore=tests/test_plugin_parity.py`; a new post-package step runs exactly that test and fails the build on divergence. `make test` keeps running the full suite including parity (it validates the *committed* state).

**Rationale:** Pre-build tests verify behavior; parity is a property of the packaged output, so it can only be honestly asserted after packaging. Committed-state parity in `make test` enforces plan §4.3 (edits to `.claude/` must be re-packaged before landing).

**Alternatives Rejected:**
1. pytest marker + `-m "not parity"` — rejected: same effect as `--ignore` but requires registering a marker (new root pytest config) for one file.
2. Staleness auto-detection via mtimes — rejected: fragile across git operations; silent skips hide real divergence.

**Consequences:**
- Any canonical policy edit now fails `make test` until `make build` is re-run — intended friction, stated in the test's failure message.
- Parity scope starts with this feature's policy files plus the linter sources (list in the test, extensible).

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | Modify | Add `build.required_sections` + `build.report_contract`; flip Build binding to `wired (document-level)`; update the bindings note; version 3.7.0 → 3.8.0 + history | (general) | None |
| 2 | `tools/spec-linter/spec_linter/contracts/build_report.py` | Create | `BuildReportContract` — section presence + `BR.*` semantic rules | @python-developer | 1 |
| 3 | `tools/spec-linter/spec_linter/cli.py` | Modify | Route `--phase build` to `BuildReportContract`; add `--legacy-mode`; load `final_review`/`report_contract` params | @python-developer | 2 |
| 4 | `tools/spec-linter/tests/test_build_report_contract.py` | Create | Unit tests: ≥1 PASS-path + ≥1 FAIL-path per rule family (fixture report + mutators) | @test-generator | 2 |
| 5 | `tools/spec-linter/tests/test_cli.py` | Modify | CLI build-phase exit codes: valid→0, dirty/missing/open/budget/TDD/incomplete→1, legacy warn→0, legacy fail→1, bad flag→2 | @test-generator | 3 |
| 6 | `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md` | Modify | Add `Schema Version` + `TDD Mode` metadata rows; note the contract gate under Final Status | (general) | 1 |
| 7 | `.claude/skills/sdd-build/SKILL.md` | Modify | New Step 6.5 Contract Gate (mirrors sdd-define/sdd-design gate text); metadata-row obligations; TDD Mode value rule | (general) | 1 |
| 8 | `.claude/skills/sdd-ship/SKILL.md` | Modify | Verification step 2 runs the same spec-lint command; FAIL added to the blocking list beside dirty/missing | (general) | 1 |
| 9 | `.claude/skills/sdd-autopilot/SKILL.md` | Modify | Gate L row: build artifact now lintable; autopilot invokes with `--legacy-mode fail` | (general) | 1 |
| 10 | `tests/test_build_quality_gates.py` | Modify | New documental anchors: binding status `wired`, `build.required_sections` exists, template markers, skills reference the gate + flag | @test-generator | 1, 6, 7, 8, 9 |
| 11 | `tests/test_plugin_parity.py` | Create | Canonical ↔ plugin parity with rewrite normalization; visible skip when `plugin/` absent | @test-generator | None |
| 12 | `build-plugin.sh` | Modify | Step 0 gains `--ignore=tests/test_plugin_parity.py`; new post-package step runs the parity test and fails the build on divergence | @shell-script-specialist | 11 |
| 13 | `tools/spec-linter/USAGE.md` | Modify | Document the build phase contract, `--legacy-mode`, unchanged exit-code semantics | (general) | 3 |

**Total Files:** 13

**`build.required_sections` (contract content, file 1):** `metadata`, `summary`, `task_execution_with_agent_attribution`, `files_created`, `verification_results`, `review_verdict`, `acceptance_test_verification`, `final_status`. (TDD Evidence and Data Quality Results stay conditional — enforced semantically, not as required sections.)

**`BR.*` rule inventory (file 2):**

| Rule | Fires when | Level |
|------|-----------|-------|
| `BR.review_verdict_missing` | v2 report: no verdict value parseable in Review Verdict | FAIL |
| `BR.review_verdict_value` | Verdict not in `final_review.verdicts` | FAIL |
| `BR.review_verdict_dirty` | Verdict is `dirty` or `missing` (fail-closed, both modes) | FAIL |
| `BR.open_blocking_finding` | Findings row with severity Critical/Important and resolution `OPEN` | FAIL |
| `BR.fix_rounds_budget` | `Fix rounds used: X/N` with X > N, or N ≠ `fix_loop_budget` | FAIL |
| `BR.tdd_evidence_missing` | `TDD Mode` ≠ `off` and TDD Evidence section absent or row-less | FAIL |
| `BR.tasks_incomplete` | `Overall: ✅ COMPLETE` but task rows not all ✅ / `Tasks Completed X/Y` with X < Y | FAIL |
| `BR.legacy_report` | No `Schema Version` row (pre-contract report) | WARN (`--legacy-mode warn`) / FAIL (`fail`) |

---

## Agent Assignment Rationale

> Agents discovered from `.claude/agents/` — every row cites the routing oracle per `specialist-autoprovision`. No gaps; no provisioning events.

| Agent | Files Assigned | Citation (routing.json) |
|-------|----------------|-------------------------|
| @python-developer | 2, 3 | `python-developer` — "Python code architect … clean patterns, dataclasses, type hints", `kb_domains: [python, pydantic, testing]` — covers linter contract code |
| @test-generator | 4, 5, 10, 11 | `test-generator` — "Test automation expert for Python. Generates pytest unit tests, integration tests, and fixtures", `kb_domains: […, testing]` |
| @shell-script-specialist | 12 | `shell-script-specialist` — "Elite shell scripting specialist for production-grade Bash scripts" — owns `build-plugin.sh` edits |
| (general) | 1, 6, 7, 8, 9, 13 | Skill citation: `component-model` (layer governance for skill/contract/template edits) — policy markdown/YAML edits fully specified by this DESIGN; no code specialist applies |

**Agent Discovery:**
- Scanned: `.claude/skills/agent-router/routing.json` (the oracle; regenerated from agent frontmatter)
- Matched by: file type, purpose keywords, KB domains

---

## Code Patterns

### Pattern 1: Contract class shape (from `Contract` protocol + `SddPhaseContract`)

```python
# tools/spec-linter/spec_linter/contracts/build_report.py
# parse() extracts everything once; check() is pure rules over the parsed value.
from __future__ import annotations

import re
from dataclasses import dataclass

from ..verdict import Finding, Level

_HEADING = re.compile(r"^#{1,6}\s+(.*\S)\s*$", re.MULTILINE)
_META_ROW = re.compile(r"^\|\s*\*\*(?P<key>[^|*]+?)\*\*\s*\|\s*(?P<value>[^|]+?)\s*\|", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class ParsedReport:
    headings: set[str]
    metadata: dict[str, str]       # e.g. {"schema version": "2", "tdd mode": "off"}
    verdict: str | None            # from the Review Verdict table
    fix_rounds: tuple[int, int] | None   # (used, budget) from "{X}/{N}"
    open_blocking: list[str]       # Critical/Important rows with OPEN resolution
    tasks_incomplete: bool         # any non-✅ task row while Final Status is COMPLETE


class BuildReportContract:
    def __init__(self, required_sections: list[str], verdicts: list[str],
                 fix_budget: int, schema_version: int, legacy_level: Level) -> None:
        self.name = "sdd-phase:build"
        ...

    def parse(self, artifact: str) -> ParsedReport: ...
    def check(self, parsed: ParsedReport) -> list[Finding]: ...
```

### Pattern 2: Finding emission (exact existing vocabulary — frozen models, `expected`/`found`)

```python
Finding(
    level=Level.FAIL,
    rule="BR.review_verdict_value",
    field="Review Verdict",
    message=f"verdict '{value}' is not an allowed review verdict",
    expected=" | ".join(self._verdicts),
    found=value,
)
```

### Pattern 3: CLI routing (extends `_lint_phase` in `cli.py`, params from YAML)

```python
def _build_report_contract(contracts: dict, legacy_mode: str) -> BuildReportContract:
    review = contracts["build"]["execution"]["final_review"]      # verdicts, fix_loop_budget
    report = contracts["build"]["report_contract"]                # schema_version, legacy levels
    legacy_level = Level[report["legacy"]["autopilot" if legacy_mode == "fail" else "manual"]]
    return BuildReportContract(
        required_sections=contracts["build"]["required_sections"],
        verdicts=review["verdicts"],
        fix_budget=review["fix_loop_budget"],
        schema_version=report["schema_version"],
        legacy_level=legacy_level,
    )
# In _lint_phase: `if phase == "build": contract = _build_report_contract(...)`
# else: SddPhaseContract(phase, required) — unchanged for every other phase.
```

### Pattern 4: Fixture + mutator test style (KB `testing`: parametrized failure paths)

```python
# tools/spec-linter/tests/test_build_report_contract.py
import pytest

VALID_REPORT = """\
## Metadata
| **Schema Version** | 2 |
| **TDD Mode** | off |
...full minimal v2 report with clean verdict, 0/2 rounds, all tasks ✅...
"""

def mutate(report: str, old: str, new: str) -> str:
    assert old in report          # guard against silently green fixtures
    return report.replace(old, new)

@pytest.mark.parametrize("old,new,rule", [
    ("| **Verdict** | clean |", "| **Verdict** | dirty |", "BR.review_verdict_dirty"),
    ("| **Fix rounds used** | 0/2 |", "| **Fix rounds used** | 3/2 |", "BR.fix_rounds_budget"),
    # ... one row per rule family
])
def test_rule_fails(old, new, rule):
    verdict = lint(mutate(VALID_REPORT, old, new), contract())
    assert verdict.level is Level.FAIL
    assert any(f.rule == rule for f in verdict.findings)
```

### Pattern 5: Parity normalization (test file 11)

```python
REWRITES = [("${CLAUDE_PLUGIN_ROOT}/kb/", ".claude/kb/"),
            ("${CLAUDE_PLUGIN_ROOT}/skills/", ".claude/skills/"),
            ("${CLAUDE_PLUGIN_ROOT}/sdd/architecture/", ".claude/sdd/architecture/"),
            ("${CLAUDE_PLUGIN_ROOT}/tools/spec-linter/", "tools/spec-linter/")]
# normalize(plugin_text) == canonical_text  → parity holds
# plugin/ absent → pytest.skip("plugin/ not built — run make build for parity proof")
```

### Contract data shape (file 1, YAML)

```yaml
build:
  required_sections:
    - metadata
    - summary
    - task_execution_with_agent_attribution
    - files_created
    - verification_results
    - review_verdict
    - acceptance_test_verification
    - final_status
  report_contract:
    schema_version: 2
    legacy:                # both severities contract-declared (Decision 3)
      detection: "metadata row 'Schema Version' absent"
      manual: WARN         # --legacy-mode warn (default)
      autopilot: FAIL      # --legacy-mode fail
```

---

## Data Flow

```text
1. sdd-build Step 6 writes BUILD_REPORT (now with Schema Version + TDD Mode rows)
   │
   ▼
2. Step 6.5 Contract Gate: spec-lint <report> --phase build
   │   exit 0 → proceed to Step 7 (statuses, handoff)
   │   exit 1 → build does NOT declare completion: fix report/state, re-lint once;
   │            still FAIL → Final Status BLOCKED, findings recorded as Blockers
   │   exit 2 → VISIBLE SKIP recorded in the report; proceed (never assume PASS)
   ▼
3. sdd-ship verification step 2 re-runs the identical command on the same artifact
   │   FAIL → Cannot ship (same reasons as Build; readiness matrix row)
   ▼
4. Autopilot Gate L (build artifact): same sensor with --legacy-mode fail
   │   exit-code policy unchanged: 0 proceed / 1 regenerate once then ABORT / ≥2 VISIBLE SKIP
   ▼
5. build-plugin.sh packages; post-package step runs tests/test_plugin_parity.py
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| None | — | — |

All integration is intra-repo: linter CLI (subprocess, exit codes), WORKFLOW_CONTRACTS.yaml (read-only data), pytest.

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit (rules) | Each `BR.*` family: ≥1 PASS + ≥1 FAIL path | `tools/spec-linter/tests/test_build_report_contract.py` | pytest, fixture+mutator | AT-001…AT-007; ≥10 tests |
| Integration (CLI) | Exit codes incl. legacy modes and bad flag | `tools/spec-linter/tests/test_cli.py` | pytest, `main(argv)` | AT-001, AT-002, AT-008, AT-009 |
| Contract (documental) | YAML↔skills↔template anchors: binding `wired`, sections list, markers, `--legacy-mode fail` in autopilot | `tests/test_build_quality_gates.py` | pytest substring/YAML | Drift guard for files 1, 6-9 |
| Parity | Canonical ↔ plugin, rewrite-normalized; divergence detection | `tests/test_plugin_parity.py` | pytest | AT-010 |
| E2E (manual, dogfood) | This feature's own Build Report passes the new gate | Build phase itself | spec-lint | Full flow |

Acceptance-test mapping: AT-001→CLI+unit valid fixture · AT-002/003→verdict rules · AT-004→open-finding rule · AT-005→budget rule · AT-006→TDD rule · AT-007→completeness rule · AT-008→CLI legacy warn (exit 0 + WARN output) · AT-009→CLI legacy fail (exit 1) + documental anchor that sdd-autopilot passes the flag · AT-010→parity test with injected mutation asserting the normalizer catches it.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Report file missing / unreadable | Existing CLI behavior: exit 2 (operational), stderr message | No — consumer records VISIBLE SKIP |
| `build.report_contract` absent from contracts file | `_OperationalError` → exit 2 (mirrors "phase has no required_sections") | No |
| Unparseable verdict/metadata table on a v2 report | Not exit 2 — the artifact loaded; emit `BR.review_verdict_missing` (FAIL): a v2 report that can't state its verdict is non-compliant, not "unavailable" | No |
| Invalid `--legacy-mode` value | argparse error → exit 2 | No |
| Contract Gate FAIL during build | One fix+re-lint round; still FAIL → Final Status BLOCKED, findings → Blockers table | 1 round |
| Parity divergence | Test failure names the divergent file + "re-run make build" guidance | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `build.required_sections` | list[str] | 8 sections (above) | Section-presence contract for BUILD_REPORT |
| `build.report_contract.schema_version` | int | `2` | Marker value new reports must carry; absence ⇒ legacy |
| `build.report_contract.legacy.manual` / `.autopilot` | Level | `WARN` / `FAIL` | Contract-declared severities for `BR.legacy_report` |
| `build.execution.final_review.verdicts` | list[str] | existing | Allowed verdict values (reused, not duplicated) |
| `build.execution.final_review.fix_loop_budget` | int | `2` (existing) | Budget for `BR.fix_rounds_budget` |
| `--legacy-mode` (CLI) | enum | `warn` | Selects which declared legacy severity applies |

---

## Security Considerations

- The linter reads local files only; no network, no model calls, no secrets — deterministic by constraint (DEFINE).
- Fail-closed preserved: `dirty`/`missing` verdicts FAIL in every mode; exit 2 is never treated as PASS by any consumer (existing anti-pattern rule).
- Parity test prevents silently shipping plugin policies that diverge from audited canonical sources.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Existing Verdict rendering: `VERDICT: {level}` + per-finding `rule/expected/found` on stdout; operational errors on stderr |
| Gate visibility | sdd-build records the gate outcome (PASS / FAIL+rounds / VISIBLE SKIP) in the report; autopilot ledger rows per Gate L contract |
| Build tooling | `build-plugin.sh` summary line gains parity step status |

---

## Pipeline Architecture (if applicable)

Not applicable — no data pipelines; the DEFINE carries no Data Contract.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | design-agent | Initial version — 4 decisions, 13-file manifest, BR rule inventory |
| 1.1 | 2026-07-29 | ship-agent | Shipped and archived |

---

## Next Step

**Shipped** — cycle closed; see `SHIPPED_2026-07-29.md`
