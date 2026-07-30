"""Build-report contract (loaded as data).

Built from the `build` block of WORKFLOW_CONTRACTS.yaml, validates a
BUILD_REPORT_{FEATURE}.md against structural rules (required sections, same
heading-presence check as SddPhaseContract) and semantic `BR.*` rules derived
from `build.execution.final_review` and `build.report_contract`. WHAT is
checked — required sections, allowed verdicts, the fix-round budget, the TDD
mode vocabulary, the schema version — is data handed in by the caller;
severity is this contract's own choice.

A report with no `Schema Version` metadata row predates the contract and is
legacy: every rule below is skipped except the fail-closed dirty/missing
verdict check, and the sole finding carries the caller-supplied
`legacy_level` (WARN or FAIL, resolved by the CLI from
`build.report_contract.legacy`). Dirty and missing verdicts stay fail-closed
in both legacy modes — legacy status changes how loudly a report's age is
flagged, never whether a dirty/missing verdict blocks.

Two more `BR.*` rules — sourced from the top-level `tdd_policy` block — are
opt-in via the constructor (`None` disables each, backward compatible):
`BR.tdd_required_by_risk` reads the echoed `Risk Level` metadata row and
fails high/critical risk with `TDD Mode: off` (fail-closed, § no skipping
TDD), warns medium risk with the same combination (judgment-scoped, logic
vs. non-logic changes), and stays silent for low risk or a missing Risk
Level row — the latter is the pre-Increment-2 adoption path, not a defect.
`BR.tdd_exception_invalid` fails every `exception: <token>` in the TDD
Evidence section whose token is not a sanctioned exception category.

A third opt-in pair — sourced from the top-level `task_review` block — is
enabled via the constructor's `task_review_verdicts` (`None` disables both):
`BR.task_review_missing` reuses the Risk Level token to fail high/critical
risk (warn medium; silent on low, an unrecognized token, or a missing row)
for every executed task (Task ID column of Task Execution) lacking a
matching `## Task Reviews` row — a wholly absent section behaves exactly
like an empty one, since both reduce to the same task-id set difference.
`BR.task_review_dirty` fails every review row whose verdict is outside the
vocabulary or equals `dirty`, at any risk level, independent of the missing
rule's severity gate. Neither rule touches `build.execution.final_review`:
the whole-branch final review stays mandatory regardless of task outcomes.

A fourth opt-in pair — sourced from the top-level `traceability` block
(Increment 6) — arms via the constructor's `matrix_must_coverage` (`False`
default disables both): `BR.must_uncovered` fails every MUST row of the
filled `## Traceability Matrix` (exact-slug scoped, mirroring
`## Task Reviews`) whose Tests cell is empty/`-` or whose Result cell lacks
`pass`, unless the Tests cell records the sanctioned `exception: <reason>`
grammar (Increment 4 precedent) — recorded, auditable, exempt.
`BR.matrix_missing` warns a wholly absent matrix, but only at high/critical
Risk Level (the same token `BR.tdd_required_by_risk`/`BR.task_review_missing`
read) — the adoption ramp for this new artifact; medium/low/an unrecognized
token/a missing Risk Level row all stay silent.

A fifth opt-in set — sourced from the top-level `workflow_metrics` block
(Increment 9) — arms via the constructor's `metrics_config` (`None` default
disables all five): the report's `## Workflow Metrics` fenced-yaml block
(exact-slug scoped) must exist (`BR.metrics_missing`, at the
caller-supplied legacy level — the mid-migration adoption path), parse to a
mapping rooted at `workflow_metrics` (`BR.metrics_parseable`, FAIL), declare
the contract's exact `schema_version` (`BR.metrics_schema_version`, FAIL),
carry every catalog key and nothing outside it (`BR.metrics_key_shape`,
FAIL — a typo'd key must not silently fork the schema), and hold only
measured values or the CLOSED availability mapping `{value: null, reason:
<why>}` (`BR.metrics_fabricated`, FAIL): a bare null, a missing/empty
reason, an extra key riding the availability mapping, an unfilled
`{placeholder}` string anywhere (the template copied verbatim — the same
brace guard the matrix/overall parsers use), or an estimate marker
(`~`-prefix / `approx` / `estimat…`) in a measured string all block. The
reason-prose marker exemption is shape-aware — it applies only to the
`reason` of a genuine availability mapping, never to arbitrary
`*reason`-named keys. Disclosed trade-off (shared with the matrix/overall
brace guards): a legitimate string containing a literal `{...}` pair is
rejected as a placeholder — fails safe; keep literal braces out of measured
strings and reasons.

Section ADDRESSING is exact and shared (`..sections`): every fixed-name section
above is located by exact slug equality at `##` level, all matches are kept,
and row/finding scans read their UNION — so no heading variation can redefine a
gate's scope (spec §6, the Critical bypass: a `## Review Verdict Notes` decoy
ahead of the real section used to hide an OPEN Critical finding). A section
located more than once is `MD.duplicate_contract_section` (FAIL, always-on),
and a demoted heading is simply not the section, surfacing as a missing
required section instead of an empty scan scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from ..sections import find_sections, heading_slugs, slug
from ..verdict import Finding, Level

# Section presence and section scoping both bind on exactly ##-level headings
# via the shared addressing module (`..sections`) — one heading vocabulary, so
# the presence check and every findings-scan scope agree by construction about
# what "the Review Verdict section" is. A demoted "### Review Verdict" is a
# missing required section (fail-closed), never a silently-empty scan scope.
_METADATA_ROW = re.compile(r"^\s*\|\s*\*\*([^*|]+)\*\*\s*\|\s*([^|]*)\|", re.MULTILINE)
_NUMBERED_ROW = re.compile(r"^\|\s*\d+\s*\|.*$", re.MULTILINE)
_TABLE_ROW = re.compile(r"^\|.*\|\s*$", re.MULTILINE)
_SEPARATOR_ROW = re.compile(r"^\|[\s:|-]+\|\s*$")
_OVERALL_LINE = re.compile(r"^###\s+Overall:.*$", re.MULTILINE)
# Fail-closed: a blocking finding counts as resolved ONLY when its resolution
# cell is template-shaped — "fixed in {sha}" / "resolved in {ref}". Anything
# else blocks: OPEN, pending, deferred, empty, negations ("Not resolved"),
# and verb-prefixed hedges ("fixed? no", "Fixed - actually not").
_RESOLVED = re.compile(r"^(?:fixed|resolved)\s+in\s+\S+", re.IGNORECASE)
_FRACTION = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")
_INCOMPLETE_MARKERS = ("⏳", "🔄", "❌")
_BLOCKING_SEVERITIES = {"critical", "important"}
# Anchored to a table-cell boundary (start-of-line or '|'), optionally prefixed
# by the template's "n/a —": a cell DECLARING an exception matches, while
# incidental "exception:" text buried mid-sentence in a RED/GREEN excerpt
# (e.g. inside a quoted traceback) never does.
_TDD_EXCEPTION = re.compile(
    r"(?:^|\|)\s*(?:n/?a\s*[—–-]\s*)?exception:\s*([a-z0-9_]+)",
    re.IGNORECASE | re.MULTILINE,
)
# Same fence grammar as the design-side task-manifest parser: the block is
# the first ```yaml fence inside the exact-slug section.
_YAML_FENCE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)
# Estimate markers in MEASURED string values (never in `reason` prose):
# a leading `~`, or any `approx`/`estimate(d)`/`estimation` token.
_ESTIMATE_MARKER = re.compile(r"^\s*~|approx|estimat", re.IGNORECASE)


# Every fixed-name section this contract reads, mapped to its CLOSED set of
# sanctioned exact slugs. Prefix matching is gone (spec §6.4 items 1–2): a
# heading either has one of these exact addresses or it is not the section.
# `TDD Evidence` carries two sanctioned spellings — the template's
# parenthetical heading and the bare one; the archived corpus uses the former.
_FIXED_SECTIONS: dict[str, frozenset[str]] = {
    "Review Verdict": frozenset({"review_verdict"}),
    "Task Execution with Agent Attribution": frozenset(
        {"task_execution_with_agent_attribution"}
    ),
    "TDD Evidence": frozenset({"tdd_evidence", "tdd_evidence_required_when_tdd_mode_off"}),
    "Task Reviews": frozenset({"task_reviews"}),
    "Traceability Matrix": frozenset({"traceability_matrix"}),
    "Workflow Metrics": frozenset({"workflow_metrics"}),
}


def _table_data_rows(section: str) -> int:
    rows = [m.group(0) for m in _TABLE_ROW.finditer(section)]
    data_rows = [row for row in rows if not _SEPARATOR_ROW.match(row)]
    return max(len(data_rows) - 1, 0)


@dataclass(frozen=True, slots=True)
class _MatrixRow:
    req: str
    priority: str
    tests: str
    result: str


def _parse_matrix_rows(section: str) -> tuple[list[_MatrixRow], list[str]]:
    """Numbered rows of a filled `## Traceability Matrix` section —
    build-side shape: `| # | REQ | Priority | Tasks | Tests | Verification
    Type | Result | Review |`. Rows with fewer than 8 cells, or an unfilled
    template placeholder (`{` in the REQ or Priority cell), are returned in
    the second list and become `BR.matrix_row_malformed` FAIL findings —
    fail-closed: a truncated MUST row must never evade the coverage rules."""
    rows: list[_MatrixRow] = []
    malformed: list[str] = []
    for m in _NUMBERED_ROW.finditer(section):
        raw = m.group(0).strip()
        cells = [c.strip() for c in raw.strip("|").split("|")]
        if len(cells) < 8 or "{" in cells[1] or "{" in cells[2]:
            malformed.append(raw)
            continue
        rows.append(
            _MatrixRow(
                req=cells[1], priority=cells[2].lower(), tests=cells[4], result=cells[6].lower()
            )
        )
    return rows, malformed


@dataclass(frozen=True, slots=True)
class _ParsedBuildReport:
    headings: set[str]
    metadata: dict[str, str]
    blocking_open: list[str]
    task_rows_incomplete: int
    overall_line: str | None
    tdd_evidence_rows: int
    tdd_evidence_text: str
    task_ids_executed: set[str]
    task_review_rows: list[tuple[str, str]]
    task_review_rows_malformed: list[str]
    task_reviews_section_present: bool
    matrix_rows: list[_MatrixRow]
    matrix_rows_malformed: list[str]
    matrix_present: bool
    metrics_fence_present: bool
    # (section display name, heading line numbers) for every fixed-name section
    # located more than once — MD.duplicate_contract_section's input.
    duplicate_sections: list[tuple[str, list[int]]]
    # Fence present + block None == the fence failed to parse to a mapping
    # rooted at workflow_metrics — no separate "broken" flag needed.
    metrics_block: dict | None


class BuildReportContract:
    def __init__(
        self,
        required_sections: list[str],
        verdicts: list[str],
        fix_budget: int,
        schema_version: int,
        tdd_mode_values: list[str],
        legacy_level: Level,
        risk_tdd_policy: dict[str, str] | None = None,
        tdd_exception_categories: list[str] | None = None,
        task_review_verdicts: list[str] | None = None,
        matrix_must_coverage: bool = False,
        metrics_config: dict | None = None,
    ) -> None:
        self.name = "sdd-phase:build"
        self._required = required_sections
        self._verdicts = verdicts
        self._fix_budget = fix_budget
        self._schema_version = schema_version
        self._tdd_mode_values = tdd_mode_values
        self._legacy_level = legacy_level
        self._risk_tdd_policy = risk_tdd_policy
        self._tdd_exception_categories = tdd_exception_categories
        self._task_review_verdicts = task_review_verdicts
        # Opt-in, armed by the CLI only when the top-level `traceability`
        # block exists: `False` (default) leaves both `BR.*` matrix rules
        # off — backward compatible with contracts files that predate
        # Increment 6.
        self._matrix_must_coverage = matrix_must_coverage
        # Opt-in the same way, from the top-level `workflow_metrics` block:
        # {"schema_version": int, "catalog": list[str]} arms the five
        # BR.metrics_* rules; `None` (default) leaves them all off.
        self._metrics_config = metrics_config

    def parse(self, artifact: str) -> _ParsedBuildReport:
        headings = heading_slugs(artifact)

        metadata: dict[str, str] = {}
        for m in _METADATA_ROW.finditer(artifact):
            metadata.setdefault(m.group(1).strip().lower(), m.group(2).strip())

        # Exact addressing for every fixed-name section, all matches kept.
        # Row/finding scans read the UNION of matches: a duplicated section is
        # reported by MD.duplicate_contract_section AND still fully scanned, so
        # it can never become a hiding place for an open blocking finding.
        located = {
            name: find_sections(artifact, slugs) for name, slugs in _FIXED_SECTIONS.items()
        }
        duplicate_sections = [
            (name, [section.line for section in sections])
            for name, sections in located.items()
            if len(sections) > 1
        ]

        def union(name: str) -> str:
            return "\n".join(section.body for section in located[name])

        blocking_open = self._blocking_open(union("Review Verdict"))

        task_section = union("Task Execution with Agent Attribution")
        task_rows_incomplete = sum(
            1
            for m in _NUMBERED_ROW.finditer(task_section)
            if any(marker in m.group(0) for marker in _INCOMPLETE_MARKERS)
        )

        overall_match = _OVERALL_LINE.search(artifact)
        overall_line = overall_match.group(0).strip() if overall_match else None

        tdd_section = union("TDD Evidence")
        tdd_evidence_rows = _table_data_rows(tdd_section) if located["TDD Evidence"] else 0
        tdd_evidence_text = tdd_section

        task_ids_executed: set[str] = set()
        for m in _NUMBERED_ROW.finditer(task_section):
            cells = [c.strip() for c in m.group(0).strip("|").split("|")]
            if len(cells) < 2:
                continue
            task_id = cells[1]
            if task_id in ("", "-") or "{" in task_id:
                continue
            task_ids_executed.add(task_id)

        task_reviews_section_present = bool(located["Task Reviews"])
        task_review_rows: list[tuple[str, str]] = []
        task_review_rows_malformed: list[str] = []
        if task_reviews_section_present:
            for m in _NUMBERED_ROW.finditer(union("Task Reviews")):
                raw = m.group(0).strip()
                cells = [c.strip() for c in raw.strip("|").split("|")]
                # Fail-closed: a truncated or placeholder-bearing row becomes
                # a BR.task_review_row_malformed FAIL — never a silent drop
                # that could hide a dirty verdict at a severity-gated risk.
                if len(cells) < 5 or "{" in cells[1] or "{" in cells[4]:
                    task_review_rows_malformed.append(raw)
                    continue
                task_review_rows.append((cells[1], cells[4].lower()))

        matrix_present = bool(located["Traceability Matrix"])
        matrix_rows, matrix_rows_malformed = (
            _parse_matrix_rows(union("Traceability Matrix")) if matrix_present else ([], [])
        )

        # First fence of the FIRST matching section decides (the task-manifest
        # precedent); a workflow_metrics fence under any OTHER heading is
        # invisible here — the section is the contract's address. Unlike the
        # row scans, unioning is meaningless for a yaml document, so duplicates
        # resolve deterministically to the first while MD.duplicate_* blocks.
        metrics_sections = located["Workflow Metrics"]
        metrics_fence = _YAML_FENCE.search(metrics_sections[0].body) if metrics_sections else None
        metrics_fence_present = metrics_fence is not None
        metrics_block: dict | None = None
        if metrics_fence is not None:
            try:
                document = yaml.safe_load(metrics_fence.group(1))
            except yaml.YAMLError:
                document = None
            root = document.get("workflow_metrics") if isinstance(document, dict) else None
            if isinstance(root, dict):
                metrics_block = root

        return _ParsedBuildReport(
            headings=headings,
            metadata=metadata,
            blocking_open=blocking_open,
            task_rows_incomplete=task_rows_incomplete,
            overall_line=overall_line,
            tdd_evidence_rows=tdd_evidence_rows,
            tdd_evidence_text=tdd_evidence_text,
            task_ids_executed=task_ids_executed,
            task_review_rows=task_review_rows,
            task_review_rows_malformed=task_review_rows_malformed,
            task_reviews_section_present=task_reviews_section_present,
            matrix_rows=matrix_rows,
            matrix_rows_malformed=matrix_rows_malformed,
            matrix_present=matrix_present,
            metrics_fence_present=metrics_fence_present,
            metrics_block=metrics_block,
            duplicate_sections=duplicate_sections,
        )

    @staticmethod
    def _blocking_open(review_verdict_section: str) -> list[str]:
        """Unresolved Critical/Important rows of the Review Verdict findings
        table only — other numbered tables (tasks, autonomous decisions) never
        feed this rule."""
        entries: list[str] = []
        for m in _NUMBERED_ROW.finditer(review_verdict_section):
            cells = [c.strip() for c in m.group(0).strip("|").split("|")]
            if len(cells) < 4 or cells[1].lower() not in _BLOCKING_SEVERITIES:
                continue
            if _RESOLVED.match(cells[-1]):
                continue
            resolution = cells[-1] or "empty"
            entries.append(f"{cells[1]}: {cells[2]} ({cells[3]}) — resolution: {resolution}")
        return entries

    def check(self, parsed: _ParsedBuildReport) -> list[Finding]:
        if "schema version" not in parsed.metadata:
            return self._check_legacy(parsed)

        findings: list[Finding] = self._check_duplicate_sections(parsed)
        findings.extend(self._check_schema_version(parsed))
        findings.extend(self._check_required_sections(parsed))
        findings.extend(self._check_verdict(parsed))
        findings.extend(self._check_blocking_open(parsed))
        findings.extend(self._check_fix_rounds(parsed))
        findings.extend(self._check_tdd_evidence(parsed))
        findings.extend(self._check_tasks_incomplete(parsed))
        if self._risk_tdd_policy is not None:
            findings.extend(self._check_tdd_required_by_risk(parsed))
        if self._tdd_exception_categories is not None:
            findings.extend(self._check_tdd_exception_invalid(parsed))
        if self._task_review_verdicts is not None:
            findings.extend(self._check_task_review_row_malformed(parsed))
            findings.extend(self._check_task_review_missing(parsed))
            findings.extend(self._check_task_review_dirty(parsed))
        if self._matrix_must_coverage:
            findings.extend(self._check_matrix_row_malformed(parsed))
            findings.extend(self._check_matrix_must_uncovered(parsed))
            findings.extend(self._check_matrix_missing(parsed))
        if self._metrics_config is not None:
            findings.extend(self._check_metrics(parsed))
        return findings

    def _check_duplicate_sections(self, parsed: _ParsedBuildReport) -> list[Finding]:
        """`MD.duplicate_contract_section` (spec §6.4 item 6) — a fixed-name
        contract section located more than once. Always-on: it guards the
        ADDRESSING of sections the core rules read, so it cannot depend on any
        opt-in family's arming. The scans themselves still read the union of
        copies, so this finding reports a structural defect without ever
        turning a duplicate into a hiding place."""
        return [
            Finding(
                level=Level.FAIL,
                rule="MD.duplicate_contract_section",
                field=name,
                message=(
                    f"'{name}' appears {len(lines)} times — a contract section "
                    "must have exactly one address; every copy is scanned "
                    "(fail-closed), but the duplication itself blocks"
                ),
                expected=f"exactly one '## {name}' heading",
                found="heading lines " + ", ".join(str(line) for line in lines),
            )
            for name, lines in parsed.duplicate_sections
        ]

    def _check_legacy(self, parsed: _ParsedBuildReport) -> list[Finding]:
        findings = [
            Finding(
                level=self._legacy_level,
                rule="BR.legacy_report",
                field="Schema Version",
                message=(
                    "report predates the build contract (no 'Schema Version' "
                    "metadata row) — migrate by adding Schema Version/TDD Mode "
                    "rows per BUILD_REPORT_TEMPLATE.md"
                ),
                expected=f"Schema Version {self._schema_version}",
                found="absent",
            )
        ]
        verdict_value = parsed.metadata.get("verdict")
        if verdict_value is not None and verdict_value.strip().lower() in ("dirty", "missing"):
            findings.append(self._dirty_verdict_finding(verdict_value.strip().lower()))
        return findings

    def _check_schema_version(self, parsed: _ParsedBuildReport) -> list[Finding]:
        declared = parsed.metadata["schema version"].strip()
        if declared == str(self._schema_version):
            return []
        return [
            Finding(
                level=Level.FAIL,
                rule="BR.schema_version",
                field="Schema Version",
                message=(
                    f"unsupported Schema Version '{declared}' — this contract "
                    f"enforces schema v{self._schema_version}"
                ),
                expected=str(self._schema_version),
                found=declared,
            )
        ]

    def _check_required_sections(self, parsed: _ParsedBuildReport) -> list[Finding]:
        findings: list[Finding] = []
        for section in self._required:
            if slug(section) not in parsed.headings:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="L2.required_section",
                        field=section,
                        message=f"required section '{section}' is missing",
                        expected="section present as a heading",
                        found="absent",
                    )
                )
        return findings

    def _dirty_verdict_finding(self, value: str) -> Finding:
        return Finding(
            level=Level.FAIL,
            rule="BR.review_verdict_dirty",
            field="Verdict",
            message=f"review verdict '{value}' blocks — ship refuses dirty/missing verdicts",
            found=value,
        )

    def _check_verdict(self, parsed: _ParsedBuildReport) -> list[Finding]:
        verdict_value = parsed.metadata.get("verdict")
        if verdict_value is None:
            return [
                Finding(
                    level=Level.FAIL,
                    rule="BR.review_verdict_missing",
                    field="Verdict",
                    message="Review Verdict section carries no parseable verdict value",
                    expected=" | ".join(self._verdicts),
                    found="absent",
                )
            ]
        value = verdict_value.strip().lower()
        findings: list[Finding] = []
        if value not in self._verdicts:
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="BR.review_verdict_value",
                    field="Verdict",
                    message=f"review verdict '{value}' is not one of the contract's allowed values",
                    expected=" | ".join(self._verdicts),
                    found=value,
                )
            )
        if value in ("dirty", "missing"):
            findings.append(self._dirty_verdict_finding(value))
        return findings

    def _check_blocking_open(self, parsed: _ParsedBuildReport) -> list[Finding]:
        return [
            Finding(
                level=Level.FAIL,
                rule="BR.open_blocking_finding",
                field="Review Verdict",
                message=f"blocking finding not resolved: {entry}",
                expected="resolution of the form 'fixed in <sha>' for Critical/Important findings",
                found=entry,
            )
            for entry in parsed.blocking_open
        ]

    def _check_fix_rounds(self, parsed: _ParsedBuildReport) -> list[Finding]:
        raw = parsed.metadata.get("fix rounds used")
        match = _FRACTION.match(raw) if raw is not None else None
        if match is None:
            return [
                Finding(
                    level=Level.FAIL,
                    rule="BR.fix_rounds_budget",
                    field="Fix rounds used",
                    message="Fix rounds used row absent or not of the form used/budget",
                    expected="X/N",
                    found=raw if raw is not None else "absent",
                )
            ]
        used, budget = int(match.group(1)), int(match.group(2))
        findings: list[Finding] = []
        if used > budget:
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="BR.fix_rounds_budget",
                    field="Fix rounds used",
                    message=f"fix rounds used ({used}) exceeds the declared budget ({budget})",
                    expected=f"used <= {budget}",
                    found=str(used),
                )
            )
        if budget != self._fix_budget:
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="BR.fix_rounds_budget",
                    field="Fix rounds used",
                    message=(
                        f"declared fix-round budget ({budget}) diverges from the "
                        f"contract's fix_loop_budget ({self._fix_budget})"
                    ),
                    expected=str(self._fix_budget),
                    found=str(budget),
                )
            )
        return findings

    def _check_tdd_evidence(self, parsed: _ParsedBuildReport) -> list[Finding]:
        mode = parsed.metadata.get("tdd mode")
        if mode is None:
            return [
                Finding(
                    level=Level.FAIL,
                    rule="BR.tdd_evidence_missing",
                    field="TDD Mode",
                    message="TDD Mode metadata row absent (required for schema v2)",
                    expected=" | ".join(self._tdd_mode_values),
                    found="absent",
                )
            ]
        value = mode.strip().lower()
        if value not in self._tdd_mode_values:
            return [
                Finding(
                    level=Level.FAIL,
                    rule="BR.tdd_evidence_missing",
                    field="TDD Mode",
                    message=f"TDD Mode '{value}' is not one of the contract's allowed values",
                    expected=" | ".join(self._tdd_mode_values),
                    found=value,
                )
            ]
        if value == "off":
            return []
        has_section = any(h.startswith("tdd_evidence") for h in parsed.headings)
        if not has_section or parsed.tdd_evidence_rows < 1:
            return [
                Finding(
                    level=Level.FAIL,
                    rule="BR.tdd_evidence_missing",
                    field="TDD Evidence",
                    message=(
                        f"TDD Mode is '{value}' but the TDD Evidence section is "
                        "missing or has no evidence rows"
                    ),
                    expected="TDD Evidence section with >= 1 row",
                    found="present" if has_section else "absent",
                )
            ]
        return []

    @staticmethod
    def _risk_level_token(parsed: _ParsedBuildReport) -> str | None:
        """First whitespace-delimited token of the Risk Level metadata row,
        lowercased; `None` when the row is absent or blank — the shared
        silent pre-Increment-2 adoption path for every risk-gated rule
        (`BR.tdd_required_by_risk`, `BR.task_review_missing`)."""
        risk_row = parsed.metadata.get("risk level")
        if not risk_row or not risk_row.strip():
            return None
        return risk_row.strip().split()[0].lower()

    def _check_tdd_required_by_risk(self, parsed: _ParsedBuildReport) -> list[Finding]:
        """Fail-closed on high/critical risk skipping TDD; WARN medium risk
        skipping TDD (judgment-scoped: logic-bearing changes only). A
        missing Risk Level row or an unrecognized level token is the
        pre-Increment-2 adoption path — silent, not a defect."""
        level = self._risk_level_token(parsed)
        if level is None:
            return []
        obligation = self._risk_tdd_policy.get(level)
        if obligation not in ("required", "required_for_logic"):
            return []
        mode = (parsed.metadata.get("tdd mode") or "").strip().lower()
        if mode != "off":
            return []
        if obligation == "required":
            return [
                Finding(
                    level=Level.FAIL,
                    rule="BR.tdd_required_by_risk",
                    field="TDD Mode",
                    message=(
                        f"Risk Level '{level}' cannot skip TDD (fail-closed) — "
                        "high/critical risk requires TDD Mode opt-in or required"
                    ),
                    expected="TDD Mode: opt-in or required",
                    found="off",
                )
            ]
        return [
            Finding(
                level=Level.WARN,
                rule="BR.tdd_required_by_risk",
                field="TDD Mode",
                message=(
                    f"Risk Level '{level}' expects TDD for logic-bearing changes "
                    "(judgment call) but TDD Mode is off"
                ),
                expected="TDD Mode: opt-in or required",
                found="off",
            )
        ]

    def _check_tdd_exception_invalid(self, parsed: _ParsedBuildReport) -> list[Finding]:
        findings: list[Finding] = []
        for m in _TDD_EXCEPTION.finditer(parsed.tdd_evidence_text):
            token = m.group(1).lower()
            if token in self._tdd_exception_categories:
                continue
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="BR.tdd_exception_invalid",
                    field="TDD Evidence",
                    message=(
                        f"TDD exception '{token}' is not a sanctioned exception "
                        "category"
                    ),
                    expected=" | ".join(self._tdd_exception_categories),
                    found=token,
                )
            )
        return findings

    def _check_task_review_missing(self, parsed: _ParsedBuildReport) -> list[Finding]:
        """Fail-closed on high/critical risk: every executed task (Task ID
        column of Task Execution) without a matching `## Task Reviews` row
        is one finding. WARN medium risk the same way; silent on low risk,
        an unrecognized risk token, or a missing Risk Level row. A wholly
        absent Task Reviews section needs no special case — `task_review_rows`
        is already empty, so every executed task id falls out of the same
        set difference (absence == nothing reviewed)."""
        level = self._risk_level_token(parsed)
        if level in ("high", "critical"):
            severity = Level.FAIL
        elif level == "medium":
            severity = Level.WARN
        else:
            return []  # None, "low", or an unrecognized token — all silent
        reviewed = {task_id for task_id, _ in parsed.task_review_rows}
        return [
            Finding(
                level=severity,
                rule="BR.task_review_missing",
                field="Task Reviews",
                message=(
                    f"task '{task_id}' has no Task Reviews row — Risk Level "
                    f"'{level}' requires a per-task review "
                    "(WORKFLOW_CONTRACTS.yaml -> task_review.enforcement)"
                ),
                expected="a Task Reviews row for every executed task",
                found="absent",
            )
            for task_id in sorted(parsed.task_ids_executed - reviewed)
        ]

    def _check_task_review_dirty(self, parsed: _ParsedBuildReport) -> list[Finding]:
        """Every Task Reviews row is checked regardless of risk level or the
        missing-rule's severity gate: an invalid verdict token FAILs (not in
        the contract's vocabulary), and verdict `dirty` FAILs outright —
        dependents built on dirty work must not ship."""
        findings: list[Finding] = []
        for task_id, verdict in parsed.task_review_rows:
            if verdict not in self._task_review_verdicts:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="BR.task_review_dirty",
                        field="Task Reviews",
                        message=(
                            f"task '{task_id}' review verdict '{verdict}' is not "
                            "one of the contract's allowed values"
                        ),
                        expected=" | ".join(self._task_review_verdicts),
                        found=verdict,
                    )
                )
            elif verdict == "dirty":
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="BR.task_review_dirty",
                        field="Task Reviews",
                        message=(
                            f"task '{task_id}' review verdict is 'dirty' — "
                            "dependents built on dirty work must not ship"
                        ),
                        expected="clean | clean-with-minors | skipped-by-policy",
                        found="dirty",
                    )
                )
        return findings

    @staticmethod
    def _check_matrix_must_uncovered(parsed: _ParsedBuildReport) -> list[Finding]:
        """FAIL every MUST row of the filled Traceability Matrix whose Tests
        cell is empty/`-` or whose Result cell doesn't contain `pass` —
        unless the Tests cell records the sanctioned `exception:` grammar
        (Increment 4 precedent), which exempts the row outright."""
        findings: list[Finding] = []
        for row in parsed.matrix_rows:
            if row.priority != "must":
                continue
            tests = row.tests.strip()
            if tests.lower().startswith("exception:"):
                continue
            # Unfilled template placeholders on a MUST row fail closed: the
            # literal "{Pass / Fail}" contains "pass" and would otherwise
            # slip through the exact gate built to catch unfilled coverage.
            if "{" in tests or "{" in row.result:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="BR.must_uncovered",
                        field=row.req,
                        message=(
                            f"requirement '{row.req}' is MUST but its Tests/Result "
                            "cells are unfilled template placeholders"
                        ),
                        expected="Tests and Result filled with real values",
                        found=f"Tests={tests} Result={row.result}",
                    )
                )
                continue
            if tests in ("", "-") or "pass" not in row.result:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="BR.must_uncovered",
                        field=row.req,
                        message=(
                            f"requirement '{row.req}' is MUST but is not covered "
                            "(empty Tests cell or Result not containing 'pass')"
                        ),
                        expected="Tests cell filled and Result containing 'pass'",
                        found=f"Tests={tests or 'empty'} Result={row.result or 'empty'}",
                    )
                )
        return findings

    def _check_matrix_missing(self, parsed: _ParsedBuildReport) -> list[Finding]:
        """WARN a wholly absent filled Traceability Matrix, but only at
        high/critical Risk Level — the adoption ramp for this new artifact
        (medium/low, an unrecognized token, or a missing Risk Level row all
        stay silent)."""
        if parsed.matrix_present:
            return []
        level = self._risk_level_token(parsed)
        if level not in ("high", "critical"):
            return []
        return [
            Finding(
                level=Level.WARN,
                rule="BR.matrix_missing",
                field="Traceability Matrix",
                message=(
                    f"Risk Level '{level}' expects a filled Traceability Matrix "
                    "section but none is present (adoption ramp)"
                ),
                expected="## Traceability Matrix section with filled rows",
                found="absent",
            )
        ]

    def _check_task_review_row_malformed(self, parsed: _ParsedBuildReport) -> list[Finding]:
        """Fail-closed row grammar (Codex review finding 3): every numbered
        Task Reviews row with <5 cells or an unfilled placeholder in
        Task ID/Verdict is a FAIL at ANY risk level — the risk-severity gate
        scopes `task_review_missing`, never malformation."""
        return [
            Finding(
                level=Level.FAIL,
                rule="BR.task_review_row_malformed",
                field="Task Reviews",
                message=(
                    "numbered row is truncated (<5 cells) or carries an unfilled "
                    "placeholder in Task ID/Verdict — a malformed row is a FAIL, "
                    "never a silent drop that could hide a dirty verdict"
                ),
                expected="| # | Task ID | Risk | Reviewer | Verdict |",
                found=raw,
            )
            for raw in parsed.task_review_rows_malformed
        ]

    def _check_matrix_row_malformed(self, parsed: _ParsedBuildReport) -> list[Finding]:
        """Fail-closed row grammar (Codex review finding 2): every numbered
        Traceability Matrix row with <8 cells or an unfilled placeholder in
        REQ/Priority is a FAIL at ANY risk level — a truncated MUST row must
        never vanish from `BR.must_uncovered`'s input."""
        return [
            Finding(
                level=Level.FAIL,
                rule="BR.matrix_row_malformed",
                field="Traceability Matrix",
                message=(
                    "numbered row is truncated (<8 cells) or carries an unfilled "
                    "placeholder in REQ/Priority — a malformed row is a FAIL, "
                    "never a silent drop that hides a MUST from coverage"
                ),
                expected=(
                    "| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |"
                ),
                found=raw,
            )
            for raw in parsed.matrix_rows_malformed
        ]

    def _check_metrics(self, parsed: _ParsedBuildReport) -> list[Finding]:
        """The five `BR.metrics_*` rules (module docstring, Increment 9).
        Precedence mirrors the block's failure ladder: absent → missing;
        present-but-unparseable → parseable; parsed → version, key shape,
        and the fabrication walk all report independently."""
        if not parsed.metrics_fence_present:
            return [
                Finding(
                    level=self._legacy_level,
                    rule="BR.metrics_missing",
                    field="Workflow Metrics",
                    message=(
                        "workflow_metrics is configured but the report has no "
                        "'## Workflow Metrics' fenced yaml block — emit it per "
                        "BUILD_REPORT_TEMPLATE.md (adoption path for reports "
                        "predating Increment 9)"
                    ),
                    expected="## Workflow Metrics section with a ```yaml workflow_metrics: block",
                    found="absent",
                )
            ]
        if parsed.metrics_block is None:
            return [
                Finding(
                    level=Level.FAIL,
                    rule="BR.metrics_parseable",
                    field="Workflow Metrics",
                    message=(
                        "the Workflow Metrics yaml fence does not parse to a "
                        "mapping rooted at 'workflow_metrics'"
                    ),
                    expected="valid yaml with a workflow_metrics mapping at the root",
                    found="unparseable or missing root key",
                )
            ]

        block = parsed.metrics_block
        findings: list[Finding] = []

        expected_version = self._metrics_config["schema_version"]
        declared = block.get("schema_version")
        if declared != expected_version:
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="BR.metrics_schema_version",
                    field="Workflow Metrics",
                    message=(
                        f"block declares schema_version {declared!r} — this contract "
                        f"enforces schema v{expected_version}; consumers compare only "
                        "same-version blocks, so a mismatch is never coerced"
                    ),
                    expected=str(expected_version),
                    found=str(declared),
                )
            )

        catalog = set(self._metrics_config["catalog"])
        present = set(block.keys())
        missing = sorted(catalog - present)
        unknown = sorted(present - catalog - {"schema_version"})
        if missing or unknown:
            parts = []
            if missing:
                parts.append(f"missing catalog key(s): {', '.join(missing)}")
            if unknown:
                parts.append(f"unknown key(s): {', '.join(unknown)}")
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="BR.metrics_key_shape",
                    field="Workflow Metrics",
                    message=(
                        f"{'; '.join(parts)} — the catalog is closed: every key "
                        "present, none invented (an unmeasured key holds "
                        "{value: null, reason: ...}, it is never dropped)"
                    ),
                    expected="exactly schema_version + the contract catalog keys",
                    found=f"{len(present)} key(s)",
                )
            )

        for key, value in block.items():
            if key == "schema_version":
                continue
            self._walk_metric_value(key, value, findings)
        return findings

    def _walk_metric_value(self, path: str, value: object, findings: list[Finding]) -> None:
        """Recursive fabrication scan. An unmeasured value is legal ONLY as
        the closed two-key availability mapping {value: null, reason:
        <non-empty str>}; a bare null, an extra key riding that mapping, an
        unfilled {placeholder} anywhere (the template copied verbatim — the
        same brace guard `_parse_matrix_rows`/`_check_tasks_incomplete` use),
        and an estimate-marked measured string all block. The reason-prose
        exemption from the marker scan lives ONLY in the availability branch
        (explaining WHY a value is null legitimately says 'estimated') — it
        is shape-aware, never a key-name suffix match, so a sibling
        `*_reason` key cannot smuggle an estimate through."""

        def fabricated(found: str, message: str) -> Finding:
            return Finding(
                level=Level.FAIL,
                rule="BR.metrics_fabricated",
                field="Workflow Metrics",
                message=f"{path}: {message}",
                expected="a measured value, or {value: null, reason: <why>}",
                found=found,
            )

        if value is None:
            findings.append(fabricated("bare null", "bare null — record the availability mapping instead"))
            return
        if isinstance(value, dict):
            if "value" in value and value["value"] is None:
                extra = sorted(set(value) - {"value", "reason"})
                if extra:
                    findings.append(
                        fabricated(
                            f"extra key(s): {', '.join(extra)}",
                            f"availability mapping is closed to exactly "
                            f"{{value, reason}} — extra key(s): {', '.join(extra)}",
                        )
                    )
                reason = value.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    findings.append(
                        fabricated(
                            "null without a reason",
                            "availability mapping needs a non-empty reason",
                        )
                    )
                elif "{" in reason and "}" in reason:
                    findings.append(
                        fabricated(reason, "unfilled template placeholder in the reason")
                    )
                return
            for key, item in value.items():
                self._walk_metric_value(f"{path}.{key}", item, findings)
            return
        if isinstance(value, list):
            for i, item in enumerate(value):
                self._walk_metric_value(f"{path}[{i}]", item, findings)
            return
        if isinstance(value, str):
            if "{" in value and "}" in value:
                findings.append(
                    fabricated(value, "unfilled template placeholder — fill it or record "
                               "{value: null, reason: ...}")
                )
            elif _ESTIMATE_MARKER.search(value):
                findings.append(
                    fabricated(
                        value,
                        "estimate marker in a measured value — measure it or record "
                        "{value: null, reason: ...}",
                    )
                )

    def _check_tasks_incomplete(self, parsed: _ParsedBuildReport) -> list[Finding]:
        overall = parsed.overall_line or ""
        if "{" in overall and "}" in overall:
            return [
                Finding(
                    level=Level.FAIL,
                    rule="BR.tasks_incomplete",
                    field="Final Status",
                    message="Final Status Overall line is an unfilled template placeholder",
                    expected="### Overall: one chosen status, no {placeholder}",
                    found=overall,
                )
            ]
        if "COMPLETE" not in overall or "IN PROGRESS" in overall:
            return []
        findings: list[Finding] = []
        if parsed.task_rows_incomplete > 0:
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="BR.tasks_incomplete",
                    field="Task Execution with Agent Attribution",
                    message=(
                        f"Overall status is COMPLETE but {parsed.task_rows_incomplete} "
                        "task row(s) are still pending/in-progress/blocked"
                    ),
                    expected="0 pending/in-progress/blocked task rows",
                    found=str(parsed.task_rows_incomplete),
                )
            )
        raw = parsed.metadata.get("tasks completed")
        match = _FRACTION.match(raw) if raw is not None else None
        if match is not None:
            completed, total = int(match.group(1)), int(match.group(2))
            if completed < total:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="BR.tasks_incomplete",
                        field="Tasks Completed",
                        message=(
                            f"Overall status is COMPLETE but Tasks Completed reports "
                            f"{completed}/{total}"
                        ),
                        expected=f"{total}/{total}",
                        found=f"{completed}/{total}",
                    )
                )
        return findings
