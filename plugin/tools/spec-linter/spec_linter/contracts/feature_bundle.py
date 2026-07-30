"""Cross-artifact validation for one SDD feature bundle."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..markdown import parse_tables
from ..verdict import Finding, Level
from .pr_readiness import PrReadyArtifactContract

_FENCE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)
_REQ = re.compile(r"\bREQ-\d+\b")
_TASK = re.compile(r"\bTASK-[A-Z0-9_-]+\b")


@dataclass(frozen=True, slots=True)
class FeatureBundle:
    define: str
    design: str
    build_report: str
    shipped: str | None = None
    pr_ready: str | None = None


@dataclass(frozen=True, slots=True)
class _ParsedBundle:
    define_must: set[str]
    design_requirements: set[str]
    design_tasks: set[str]
    build_tasks: set[str]
    build_requirements: set[str]
    shipped_requirements: set[str] | None
    pr_ready_requirements: set[str] | None
    structural_findings: tuple[Finding, ...]
    identities: tuple[tuple[str, str], ...]
    pr_ready_findings: tuple[Finding, ...]


def _table_ids(text: str, column: str, token: re.Pattern[str]) -> set[str]:
    found: set[str] = set()
    for table in parse_tables("feature bundle", text):
        index = table.header_index(column)
        if index is None:
            continue
        for row in table.rows:
            found.update(token.findall(row.cell(index)))
    return found


def _define_must(text: str) -> set[str]:
    found: set[str] = set()
    for table in parse_tables("DEFINE", text):
        id_index = table.header_index("ID")
        priority_index = table.header_index("Priority")
        if id_index is None or priority_index is None:
            continue
        for row in table.rows:
            if row.cell(priority_index).strip("* ").upper() == "MUST":
                found.update(_REQ.findall(row.cell(id_index)))
    return found


def _manifest_tasks(text: str) -> set[str]:
    found: set[str] = set()
    for match in _FENCE.finditer(text):
        try:
            document = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            continue
        manifest = document.get("task_manifest") if isinstance(document, dict) else None
        tasks = manifest.get("tasks") if isinstance(manifest, dict) else None
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            task_id = task.get("id") if isinstance(task, dict) else None
            if isinstance(task_id, str) and _TASK.fullmatch(task_id):
                found.add(task_id)
    return found


def _feature_identity(name: str, text: str) -> tuple[str | None, list[Finding]]:
    findings: list[Finding] = []
    if not text.strip():
        findings.append(
            Finding(
                level=Level.FAIL,
                rule="FB.empty_artifact",
                field=name,
                message=f"{name} artifact must not be empty",
            )
        )
        return None, findings

    title = {
        "DEFINE": "DEFINE",
        "DESIGN": "DESIGN",
        "BUILD_REPORT": "BUILD REPORT",
        "SHIPPED": "SHIPPED",
        "PR_READY": "PR READY",
    }[name]
    if re.search(rf"^#\s+{re.escape(title)}\s*:", text, re.MULTILINE | re.IGNORECASE) is None:
        findings.append(
            Finding(
                level=Level.FAIL,
                rule="FB.artifact_structure",
                field=name,
                message=f"{name} must contain its canonical '# {title}: …' heading",
            )
        )

    identities: set[str] = set()
    for table in parse_tables(name, text):
        attribute = table.header_index("Attribute")
        value = table.header_index("Value")
        if attribute is None or value is None:
            continue
        for row in table.rows:
            if row.cell(attribute).strip("* ").casefold() == "feature":
                candidate = row.cell(value).strip()
                if candidate and not ("{" in candidate or "}" in candidate):
                    identities.add(candidate.upper())
    if len(identities) != 1:
        findings.append(
            Finding(
                level=Level.FAIL,
                rule="FB.artifact_structure",
                field=name,
                message=f"{name} must declare exactly one non-empty Feature metadata value",
                found=", ".join(sorted(identities)) or "(none)",
            )
        )
        return None, findings
    return next(iter(identities)), findings


class FeatureBundleContract:
    """Validate identity propagation across DEFINE → DESIGN → BUILD → release."""

    name = "feature-bundle"

    def __init__(self, *, release: bool = False) -> None:
        self.release = release

    def parse(self, bundle: FeatureBundle) -> _ParsedBundle:
        documents = [
            ("DEFINE", bundle.define),
            ("DESIGN", bundle.design),
            ("BUILD_REPORT", bundle.build_report),
        ]
        if bundle.shipped is not None:
            documents.append(("SHIPPED", bundle.shipped))
        if bundle.pr_ready is not None:
            documents.append(("PR_READY", bundle.pr_ready))
        identities: list[tuple[str, str]] = []
        structural_findings: list[Finding] = []
        for name, text in documents:
            identity, findings = _feature_identity(name, text)
            structural_findings.extend(findings)
            if identity is not None:
                identities.append((name, identity))

        pr_ready_findings: list[Finding] = []
        if bundle.pr_ready is not None:
            contract = PrReadyArtifactContract()
            try:
                parsed_pr_ready = contract.parse(bundle.pr_ready)
            except Exception as exc:
                pr_ready_findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="PR.artifact.unparseable",
                        field="PR_READY",
                        message=str(exc),
                    )
                )
            else:
                pr_ready_findings.extend(contract.check(parsed_pr_ready))
                machine_feature = parsed_pr_ready.data.get("feature")
                if isinstance(machine_feature, str) and machine_feature:
                    identities.append(("PR_READY.machine", machine_feature.upper()))

        return _ParsedBundle(
            define_must=_define_must(bundle.define),
            design_requirements=_table_ids(bundle.design, "REQ", _REQ),
            design_tasks=_manifest_tasks(bundle.design),
            build_tasks=(
                _table_ids(bundle.build_report, "Task ID", _TASK)
                | _table_ids(bundle.build_report, "Task", _TASK)
            ),
            build_requirements=_table_ids(bundle.build_report, "REQ", _REQ),
            shipped_requirements=(
                set(_REQ.findall(bundle.shipped)) if bundle.shipped is not None else None
            ),
            pr_ready_requirements=(
                set(_REQ.findall(bundle.pr_ready)) if bundle.pr_ready is not None else None
            ),
            structural_findings=tuple(structural_findings),
            identities=tuple(identities),
            pr_ready_findings=tuple(pr_ready_findings),
        )

    def check(self, parsed: _ParsedBundle) -> list[Finding]:
        findings = [*parsed.structural_findings, *parsed.pr_ready_findings]
        for field, values, description in (
            ("DEFINE", parsed.define_must, "at least one MUST requirement"),
            ("DESIGN", parsed.design_requirements, "a populated traceability matrix"),
            ("DESIGN", parsed.design_tasks, "a populated task manifest"),
            ("BUILD_REPORT", parsed.build_requirements, "verified requirements"),
            ("BUILD_REPORT", parsed.build_tasks, "executed tasks"),
        ):
            if not values:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="FB.artifact_structure",
                        field=field,
                        message=f"{field} must contain {description}",
                    )
                )
        identity_values = {identity for _, identity in parsed.identities}
        if len(identity_values) > 1:
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="FB.feature_identity_drift",
                    field="Feature Bundle",
                    message="all artifacts must declare the same feature identity",
                    expected=parsed.identities[0][1] if parsed.identities else None,
                    found=", ".join(f"{name}={identity}" for name, identity in parsed.identities),
                )
            )
        if self.release and parsed.shipped_requirements is None:
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="FB.release_shipped_required",
                    field="SHIPPED",
                    message="release bundles require a SHIPPED artifact",
                )
            )
        if self.release and parsed.pr_ready_requirements is None:
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="FB.release_pr_ready_required",
                    field="PR_READY",
                    message="release bundles require an explicit PR_READY artifact",
                )
            )
        self._same_or_find(
            findings,
            "FB.define_requirement_missing_in_design",
            parsed.define_must,
            parsed.design_requirements,
            "DEFINE MUST requirement(s) absent from DESIGN",
        )
        self._same_or_find(
            findings,
            "FB.design_task_missing_in_build",
            parsed.design_tasks,
            parsed.build_tasks,
            "DESIGN task(s) absent from BUILD report",
        )
        self._same_or_find(
            findings,
            "FB.build_requirement_drift",
            parsed.design_requirements,
            parsed.build_requirements,
            "BUILD requirement set differs from DESIGN",
            exact=True,
        )
        for name, values in (
            ("SHIPPED", parsed.shipped_requirements),
            ("PR_READY", parsed.pr_ready_requirements),
        ):
            if values is not None:
                self._same_or_find(
                    findings,
                    f"FB.{name.lower()}_requirement_drift",
                    parsed.build_requirements,
                    values,
                    f"{name} requirement set differs from BUILD",
                    exact=True,
                )
        return findings

    @staticmethod
    def _same_or_find(
        findings: list[Finding],
        rule: str,
        expected: set[str],
        found: set[str],
        message: str,
        *,
        exact: bool = False,
    ) -> None:
        missing = expected - found
        extra = found - expected if exact else set()
        if not missing and not extra:
            return
        details = [*(f"missing {item}" for item in sorted(missing))]
        details.extend(f"extra {item}" for item in sorted(extra))
        findings.append(
            Finding(
                level=Level.FAIL,
                rule=rule,
                field="Feature Bundle",
                message=f"{message}: {', '.join(details)}",
                expected=", ".join(sorted(expected)) or "(empty)",
                found=", ".join(sorted(found)) or "(empty)",
            )
        )


def load_feature_bundle(directory: Path, *, pr_ready: Path | None = None) -> FeatureBundle:
    """Load the unique canonical artifacts from an active/archive feature dir."""

    def one(prefix: str, *, optional: bool = False) -> str | None:
        matches = sorted(directory.glob(f"{prefix}*.md"))
        if not matches and optional:
            return None
        if len(matches) != 1:
            raise ValueError(
                f"{directory}: expected exactly one {prefix}*.md, found {len(matches)}"
            )
        return matches[0].read_text(encoding="utf-8")

    return FeatureBundle(
        define=one("DEFINE_") or "",
        design=one("DESIGN_") or "",
        build_report=one("BUILD_REPORT_") or "",
        shipped=one("SHIPPED_", optional=True),
        pr_ready=pr_ready.read_text(encoding="utf-8") if pr_ready is not None else None,
    )
