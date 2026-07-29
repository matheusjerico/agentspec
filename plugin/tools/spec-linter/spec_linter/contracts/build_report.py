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
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..verdict import Finding, Level

# Section presence and section scoping both bind on exactly ##-level headings
# (the template's section level) — a single heading vocabulary, so the
# presence check and the findings-scan scope can never disagree about what
# "the Review Verdict section" is. A demoted "### Review Verdict" is a
# missing required section (fail-closed), never a silently-empty scan scope.
_H2 = re.compile(r"^##\s+(.*\S)\s*$", re.MULTILINE)
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


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _section_after(artifact: str, slug_prefix: str) -> str | None:
    """Text between the first `##` heading whose slug starts with
    `slug_prefix` and the next `##` heading (or end of document); `None` if
    no such heading exists."""
    matches = list(_H2.finditer(artifact))
    for i, m in enumerate(matches):
        if _slug(m.group(1)).startswith(slug_prefix):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(artifact)
            return artifact[start:end]
    return None


def _table_data_rows(section: str) -> int:
    rows = [m.group(0) for m in _TABLE_ROW.finditer(section)]
    data_rows = [row for row in rows if not _SEPARATOR_ROW.match(row)]
    return max(len(data_rows) - 1, 0)


@dataclass(frozen=True, slots=True)
class _ParsedBuildReport:
    headings: set[str]
    metadata: dict[str, str]
    blocking_open: list[str]
    task_rows_incomplete: int
    overall_line: str | None
    tdd_evidence_rows: int
    tdd_evidence_text: str


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

    def parse(self, artifact: str) -> _ParsedBuildReport:
        headings = {_slug(m.group(1)) for m in _H2.finditer(artifact)}

        metadata: dict[str, str] = {}
        for m in _METADATA_ROW.finditer(artifact):
            metadata.setdefault(m.group(1).strip().lower(), m.group(2).strip())

        blocking_open = self._blocking_open(_section_after(artifact, "review_verdict") or "")

        task_section = _section_after(artifact, "task_execution_with_agent_attribution") or ""
        task_rows_incomplete = sum(
            1
            for m in _NUMBERED_ROW.finditer(task_section)
            if any(marker in m.group(0) for marker in _INCOMPLETE_MARKERS)
        )

        overall_match = _OVERALL_LINE.search(artifact)
        overall_line = overall_match.group(0).strip() if overall_match else None

        tdd_section = _section_after(artifact, "tdd_evidence")
        tdd_evidence_rows = _table_data_rows(tdd_section) if tdd_section is not None else 0
        tdd_evidence_text = tdd_section if tdd_section is not None else ""

        return _ParsedBuildReport(
            headings=headings,
            metadata=metadata,
            blocking_open=blocking_open,
            task_rows_incomplete=task_rows_incomplete,
            overall_line=overall_line,
            tdd_evidence_rows=tdd_evidence_rows,
            tdd_evidence_text=tdd_evidence_text,
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

        findings: list[Finding] = []
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
        return findings

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
            if _slug(section) not in parsed.headings:
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

    def _check_tdd_required_by_risk(self, parsed: _ParsedBuildReport) -> list[Finding]:
        """Fail-closed on high/critical risk skipping TDD; WARN medium risk
        skipping TDD (judgment-scoped: logic-bearing changes only). A
        missing Risk Level row or an unrecognized level token is the
        pre-Increment-2 adoption path — silent, not a defect."""
        risk_row = parsed.metadata.get("risk level")
        if not risk_row or not risk_row.strip():
            return []
        level = risk_row.strip().split()[0].lower()
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
