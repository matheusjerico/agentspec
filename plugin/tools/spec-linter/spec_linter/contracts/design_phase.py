"""Design-phase contract (loaded as data).

Built from `design.required_sections` (FAIL semantics, unchanged) and the
top-level `task_manifest` block of WORKFLOW_CONTRACTS.yaml, validates a
DESIGN_{FEATURE}.md against structural section presence plus semantic `TM.*`
executable-task-manifest rules. WHAT is checked — the section list, the
required task fields, the files/verification key vocabularies — is data
handed in by the caller; severity is this contract's own choice.

The v2 task manifest is opt-in: a DESIGN with no `## Task Manifest (v2)`
section (or a section with no ```yaml fence) is v1 — ZERO `TM.*` findings,
never a WARN. This is not an observe/warn rollout like risk_profiles; it is a
silence contract. But once a DESIGN DOES declare a manifest, every `TM.*`
rule below is `Level.FAIL` except `TM.missing_requirements` — fail-closed for
adopters, because an executable plan that is malformed (unparseable, a cycle,
a write conflict, an unverifiable task) must not reach Build. A fence that
exists but fails to parse — or parses to something that is not a mapping —
is `manifest_broken`, distinct from an absent manifest: broken is FAIL
(`TM.unparseable`), absent is v1-silent.

`L2.required_section` keeps its existing FAIL semantics, exactly mirroring
`SddPhaseContract` — this preserves current exit-1 behavior for missing
required sections; the Task Manifest section itself is deliberately NOT one
of them (the manifest stays opt-in).

A second opt-in family — sourced from the top-level `traceability` block
(Increment 6) — arms via the constructor's `verification_types` (`None`
disables all three `TX.*` rules): `TX.must_without_task` FAILs a MUST-priority
`## Traceability Matrix` row whose Tasks cell is empty; `TX.unknown_type`
FAILs any comma-separated Verification Type token outside the configured
vocabulary; `TX.orphan_reference` WARNs both directions of the REQ<->task
cross-reference against a present v2 manifest (matrix Tasks citing an unknown
manifest id, or a manifest task's REQ-ID-grammar `requirements` entry absent
from the matrix — legacy MUST-n/SC-n refs never flag). Like the manifest
above, an absent Traceability Matrix section is silent — zero `TX.*`
findings — and both parsers use `_section_exact` (equality, not prefix) on
the template-fixed "Traceability Matrix" heading, so a decoy section can
never shadow the real one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from ..markdown import TableError, parse_tables
from ..sections import find_sections, heading_slugs, slug
from ..verdict import Finding, Level

# Two deliberately different heading vocabularies:
# - Section PRESENCE uses any ATX level (#{1,6}) — mirroring SddPhaseContract
#   exactly, so routing design to this contract changes NO existing FAIL
#   behavior for section presence.
# - The Task Manifest SCAN is ##-only: the template places it at `##`, and
#   this restriction keeps the section-scoping unambiguous with the
#   `_section_after` slicing below.
_YAML_FENCE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)
# Traceability Matrix rows (Increment 6): design-side rows carry 6 cells
# (#, REQ, Priority, Tasks, Tests, Verification Type) — the same
# numbered-row grammar `BuildReportContract` uses for its task/review
# tables, reused here verbatim.
# A manifest task's `requirements` entry is orphan-checked against the
# matrix only when it is a REQ-ID — legacy MUST-n/SC-n refs are tolerated
# (never orphan-flagged), per DEFINE A-002's pre-REQ-ID adoption path.
_REQ_TOKEN = re.compile(r"^REQ-\d+$")


def _slug(text: str) -> str:
    return slug(text)


def _candidate_sections(artifact: str, slug_prefix: str) -> list[str]:
    """Every `##` section whose heading slug starts with `slug_prefix`, in
    document order — ALL candidates, not just the first: a fence-less decoy
    ("## Task Manifest Notes") must never shadow the real manifest section."""
    accepted = {slug_prefix, f"{slug_prefix}_v2"}
    return [
        section.body
        for section in find_sections(artifact, accepted, level=2)
    ]


def _section_exact(artifact: str, slug: str) -> str | None:
    """Text between the first `##` heading whose slug EQUALS `slug` and the
    next `##` heading (or end of document); `None` if no such heading
    exists. Mirrors `BuildReportContract._section_exact` — a template-fixed
    heading ("Traceability Matrix") must never let a decoy ("## Traceability
    Matrix Notes") shadow the real section in either scan direction
    (Increment 5's decoy lesson, applied here from birth)."""
    matches = find_sections(artifact, {slug}, level=2)
    return matches[0].body if matches else None


def _parse_manifest(artifact: str) -> tuple[dict | None, bool]:
    """The `task_manifest` mapping from the first candidate section that
    carries a ```yaml fence, plus a `broken` flag.

    Candidate sections are scanned in order; the FIRST one containing a yaml
    fence decides (fence-less candidates — prose "Notes" sections — are
    skipped, never shadowing the real manifest). Returns `(None, False)` when
    no candidate carries a fence — the v1-silent case. Returns `(None, True)`
    when the deciding fence fails to parse, its top level isn't a mapping, or
    the `task_manifest` key isn't itself a mapping — the broken case (FAIL,
    distinct from absent; fail-closed for adopters). This parser never
    raises."""
    for section in _candidate_sections(artifact, "task_manifest"):
        fence = _YAML_FENCE.search(section)
        if fence is None:
            continue
        try:
            document = yaml.safe_load(fence.group(1))
        except yaml.YAMLError:
            # Unparseable YAML under a Task Manifest heading: fail closed —
            # its keys cannot be inspected, so it may be the real manifest.
            return None, True
        if not isinstance(document, dict) or "task_manifest" not in document:
            # An unrelated example fence (no task_manifest key) never decides —
            # keep scanning so it cannot shadow a valid manifest further down.
            continue
        manifest = document["task_manifest"]
        if not isinstance(manifest, dict):
            return None, True
        return manifest, False
    return None, False


@dataclass(frozen=True, slots=True)
class _MatrixRow:
    req: str
    priority: str
    tasks: str
    verification_type: str


@dataclass(frozen=True, slots=True)
class _ParsedDesignPhase:
    headings: set[str]
    manifest: dict | None
    manifest_broken: bool
    matrix_rows: list[_MatrixRow]
    matrix_errors: list[TableError]
    matrix_present: bool


class DesignPhaseContract:
    def __init__(
        self,
        required_sections: list[str],
        required_task_fields: list[str],
        files_keys: list[str],
        verification_keys: list[str],
        verification_types: list[str] | None = None,
        manifest_configured: bool = True,
        require_manifest: bool = False,
        require_matrix: bool = False,
    ) -> None:
        self.name = "sdd-phase:design"
        self._required = required_sections
        self._required_task_fields = required_task_fields
        self._files_keys = files_keys
        self._verification_keys = verification_keys
        # Opt-in, mirroring the v2 manifest's own posture: `None` disables
        # the whole `TX.*` traceability-matrix rule family — a DESIGN with
        # no configured vocabulary stays silent, never a WARN/FAIL.
        self._verification_types = verification_types
        # A consumer who configured `traceability` but NOT `task_manifest`
        # must never see TM.* findings — even when a document happens to
        # contain a manifest-shaped section. The CLI passes False in that
        # cross-adopter configuration; True preserves every existing call.
        self._manifest_configured = manifest_configured
        self._require_manifest = require_manifest
        self._require_matrix = require_matrix

    def parse(self, artifact: str) -> _ParsedDesignPhase:
        headings = set().union(*(heading_slugs(artifact, level=n) for n in range(1, 7)))
        manifest, broken = _parse_manifest(artifact)
        matrix_section = _section_exact(artifact, "traceability_matrix")
        matrix_present = matrix_section is not None
        matrix_rows: list[_MatrixRow] = []
        matrix_errors: list[TableError] = []
        if matrix_section is not None:
            # The SHARED parser (§7.9): design and build read rows the same way,
            # so the two sides can no longer drift — and a malformed row is
            # reported here instead of vanishing.
            for table in parse_tables(
                "Traceability Matrix", matrix_section, required_columns={"req", "priority"}
            ):
                matrix_errors.extend(table.errors)
                index = {
                    name: table.header_index(name)
                    for name in ("REQ", "Priority", "Tasks", "Verification Type")
                }
                for row in table.rows:
                    req = row.cell(index["REQ"] if index["REQ"] is not None else 1)
                    if "{" in req:
                        continue  # reported by the parser as a placeholder
                    matrix_rows.append(
                        _MatrixRow(
                            req=req,
                            priority=row.cell(
                                index["Priority"] if index["Priority"] is not None else 2
                            ).lower(),
                            tasks=row.cell(index["Tasks"] if index["Tasks"] is not None else 3),
                            verification_type=row.cell(
                                index["Verification Type"]
                                if index["Verification Type"] is not None
                                else 5
                            ),
                        )
                    )
        return _ParsedDesignPhase(
            headings=headings,
            manifest=manifest,
            manifest_broken=broken,
            matrix_rows=matrix_rows,
            matrix_errors=matrix_errors,
            matrix_present=matrix_present,
        )

    def check(self, parsed: _ParsedDesignPhase) -> list[Finding]:
        findings = self._check_required_sections(parsed)
        if self._require_matrix and not parsed.matrix_present:
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="TX.matrix_missing",
                    field="Traceability Matrix",
                    message="an enforced Design must declare a Traceability Matrix",
                    expected="## Traceability Matrix section",
                    found="absent",
                )
            )
        findings.extend(self._check_matrix(parsed))

        if not self._manifest_configured:
            return findings

        if parsed.manifest_broken:
            findings.append(
                Finding(
                    level=Level.FAIL,
                    rule="TM.unparseable",
                    field="Task Manifest (v2)",
                    message=(
                        "Task Manifest section carries a ```yaml fence that fails "
                        "to parse into a task_manifest mapping — an executable "
                        "plan that cannot parse must not reach Build"
                    ),
                    expected="valid YAML with a task_manifest mapping",
                    found="unparseable",
                )
            )
            return findings

        if parsed.manifest is None:
            if self._require_manifest:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="TM.manifest_missing",
                        field="Task Manifest (v2)",
                        message="an enforced Design must declare an executable v2 task manifest",
                        expected="## Task Manifest (v2) with task_manifest.manifest_version: 2",
                        found="absent",
                    )
                )
            return findings

        findings.extend(self._check_manifest(parsed.manifest))
        return findings

    def _check_required_sections(self, parsed: _ParsedDesignPhase) -> list[Finding]:
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

    def _check_matrix(self, parsed: _ParsedDesignPhase) -> list[Finding]:
        """`TX.*` traceability-matrix rules — opt-in via `verification_types`
        (`None` disables the whole family, same posture as v1/v2 above) and
        further gated on the matrix section actually being present: an
        absent `## Traceability Matrix` is the v1-silent path, zero `TX.*`
        findings. `TX.orphan_reference` additionally needs a non-broken
        manifest to trust its task ids — a broken manifest is treated as
        absent for this rule only (`TM.unparseable` still fires separately,
        in `check()`)."""
        if self._verification_types is None or not parsed.matrix_present:
            return []
        findings = [
            Finding(
                level=Level.FAIL,
                rule="TX.matrix_row_malformed",
                field="Traceability Matrix",
                message=error.render(),
                expected=(
                    f"{error.expected_cells} cells"
                    if error.expected_cells is not None
                    else "a well-formed table row"
                ),
                found=error.raw.strip(),
            )
            for error in parsed.matrix_errors
        ]
        findings.extend(self._check_matrix_must_without_task(parsed.matrix_rows))
        findings.extend(self._check_matrix_unknown_type(parsed.matrix_rows))
        if not parsed.manifest_broken:
            findings.extend(
                self._check_matrix_orphan_reference(parsed.matrix_rows, parsed.manifest)
            )
        return findings

    @staticmethod
    def _check_matrix_must_without_task(rows: list[_MatrixRow]) -> list[Finding]:
        findings: list[Finding] = []
        for row in rows:
            if row.priority != "must":
                continue
            tasks = row.tasks.strip()
            if tasks in ("", "-"):
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="TX.must_without_task",
                        field=row.req,
                        message=(
                            f"requirement '{row.req}' is MUST but the Traceability "
                            "Matrix Tasks cell is empty"
                        ),
                        expected="at least one task id in the Tasks cell",
                        found=tasks or "empty",
                    )
                )
        return findings

    def _check_matrix_unknown_type(self, rows: list[_MatrixRow]) -> list[Finding]:
        findings: list[Finding] = []
        for row in rows:
            for raw_token in row.verification_type.split(","):
                token = raw_token.strip().lower()
                if not token:
                    continue
                if token not in self._verification_types:
                    findings.append(
                        Finding(
                            level=Level.FAIL,
                            rule="TX.unknown_type",
                            field=row.req,
                            message=(
                                f"requirement '{row.req}' verification type '{token}' "
                                "is not in the contract's vocabulary"
                            ),
                            expected=" | ".join(self._verification_types),
                            found=token,
                        )
                    )
        return findings

    @staticmethod
    def _check_matrix_orphan_reference(
        rows: list[_MatrixRow], manifest: dict | None
    ) -> list[Finding]:
        """WARN both directions of the REQ<->task cross-reference — matrix
        Tasks cells citing an id absent from the (present) v2 manifest, and
        manifest task `requirements` entries (REQ-ID grammar only; legacy
        MUST-n/SC-n refs never flag) absent from the matrix's REQ cells. A
        v1 DESIGN (no manifest) skips both directions — nothing to
        cross-reference."""
        if manifest is None:
            return []
        tasks = manifest.get("tasks")
        if not isinstance(tasks, list):
            return []

        manifest_task_ids = {
            task["id"]
            for task in tasks
            if isinstance(task, dict) and isinstance(task.get("id"), str) and task["id"]
        }

        findings: list[Finding] = []
        for row in rows:
            for raw_token in row.tasks.split(","):
                token = raw_token.strip()
                if not token or token == "-" or token in manifest_task_ids:
                    continue
                findings.append(
                    Finding(
                        level=Level.WARN,
                        rule="TX.orphan_reference",
                        field=row.req,
                        message=(
                            f"requirement '{row.req}' Tasks cell references "
                            f"'{token}', which is not a task id in the v2 manifest"
                        ),
                        expected="a task id declared in the Task Manifest (v2)",
                        found=token,
                    )
                )

        matrix_reqs = {row.req for row in rows}
        for task in tasks:
            if not isinstance(task, dict):
                continue
            task_id = task.get("id")
            label = task_id if isinstance(task_id, str) and task_id else "?"
            requirements = task.get("requirements")
            if not isinstance(requirements, list):
                continue
            for req in requirements:
                if not isinstance(req, str) or not _REQ_TOKEN.match(req) or req in matrix_reqs:
                    continue
                findings.append(
                    Finding(
                        level=Level.WARN,
                        rule="TX.orphan_reference",
                        field=label,
                        message=(
                            f"task '{label}' requirement '{req}' is not a REQ in "
                            "the Traceability Matrix"
                        ),
                        expected="a REQ cell present in the Traceability Matrix",
                        found=req,
                    )
                )
        return findings

    def _check_manifest(self, manifest: dict) -> list[Finding]:
        tasks = manifest.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            found = "absent" if tasks is None else ("empty" if not tasks else str(tasks))
            return [
                Finding(
                    level=Level.FAIL,
                    rule="TM.invalid_task",
                    field="tasks",
                    message="v2 manifest declares no tasks",
                    expected="tasks: a non-empty list of task mappings",
                    found=found,
                )
            ]

        findings: list[Finding] = []
        by_id: dict[str, list[dict]] = {}
        labels: dict[int, str] = {}
        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="TM.invalid_task",
                        field=f"tasks[{index}]",
                        message=f"task at index {index} is not a mapping",
                        expected="a task mapping",
                        found=str(task),
                    )
                )
                continue
            task_id = task.get("id")
            has_id = isinstance(task_id, str) and task_id
            label = task_id if has_id else f"index {index}"
            labels[index] = label
            if has_id:
                by_id.setdefault(task_id, []).append(task)

        findings.extend(self._check_duplicate_ids(by_id))

        valid_tasks = [
            (index, task) for index, task in enumerate(tasks) if isinstance(task, dict)
        ]
        for index, task in valid_tasks:
            findings.extend(self._check_task_fields(labels[index], task))

        known_ids = set(by_id.keys())
        for index, task in valid_tasks:
            findings.extend(self._check_dependencies(labels[index], task, known_ids))

        # Duplicated ids already FAIL above; feeding them to the graph rules
        # would union their depends_on edges and emit misleading cycles.
        duplicated_ids = {tid for tid, occ in by_id.items() if len(occ) > 1}
        graph_tasks = [
            (index, task)
            for index, task in valid_tasks
            if task.get("id") not in duplicated_ids
        ]
        findings.extend(self._check_cycle(graph_tasks, known_ids - duplicated_ids))
        findings.extend(self._check_write_conflicts(graph_tasks, labels))

        for index, task in valid_tasks:
            findings.extend(self._check_requirements(labels[index], task))

        return findings

    def _check_duplicate_ids(self, by_id: dict[str, list[dict]]) -> list[Finding]:
        findings: list[Finding] = []
        for task_id, occurrences in by_id.items():
            if len(occurrences) > 1:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="TM.duplicate_id",
                        field=task_id,
                        message=(
                            f"task id '{task_id}' is declared by "
                            f"{len(occurrences)} tasks"
                        ),
                        expected="each task id unique",
                        found=f"{len(occurrences)} declarations",
                    )
                )
        return findings

    def _check_task_fields(self, label: str, task: dict) -> list[Finding]:
        findings: list[Finding] = []
        for field in self._required_task_fields:
            value = task.get(field)
            # id/title must be non-empty strings — a numeric `id: 42` would
            # otherwise pass presence yet silently drop out of the graph.
            if field in ("id", "title") and field in task and not isinstance(value, str):
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="TM.invalid_task",
                        field=f"{label}.{field}",
                        message=f"task '{label}' field '{field}' must be a string",
                        expected="a non-empty string",
                        found=str(value),
                    )
                )
                continue
            if field in task and value not in (None, "", [], {}):
                continue
            if field == "verification":
                findings.append(self._missing_verification_finding(label, "absent"))
            else:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="TM.invalid_task",
                        field=f"{label}.{field}",
                        message=f"task '{label}' is missing required field '{field}'",
                        expected=", ".join(self._required_task_fields),
                        found="absent",
                    )
                )

        if "files" in task:
            findings.extend(self._check_files(label, task.get("files")))

        verification = task.get("verification")
        if "verification" in task and verification not in (None, "", [], {}):
            findings.extend(self._check_verification(label, verification))

        return findings

    def _missing_verification_finding(self, label: str, found: str) -> Finding:
        return Finding(
            level=Level.FAIL,
            rule="TM.missing_verification",
            field=f"{label}.verification",
            message=(
                f"task '{label}' carries no non-empty verification value under "
                f"{', '.join(self._verification_keys)}"
            ),
            expected=" | ".join(self._verification_keys),
            found=found,
        )

    def _check_files(self, label: str, files: object) -> list[Finding]:
        if not isinstance(files, dict):
            return [
                Finding(
                    level=Level.FAIL,
                    rule="TM.invalid_task",
                    field=f"{label}.files",
                    message=f"task '{label}' field 'files' is not a mapping",
                    expected="mapping of " + ", ".join(self._files_keys),
                    found=str(files),
                )
            ]
        findings: list[Finding] = []
        for key, value in files.items():
            if key not in self._files_keys:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="TM.invalid_task",
                        field=f"{label}.files.{key}",
                        message=f"task '{label}' files key '{key}' is not recognized",
                        expected=", ".join(self._files_keys),
                        found=str(key),
                    )
                )
                continue
            is_str_list = isinstance(value, list) and all(
                isinstance(v, str) for v in value
            )
            if not is_str_list:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="TM.invalid_task",
                        field=f"{label}.files.{key}",
                        message=f"task '{label}' files.{key} must be a list of strings",
                        expected="list of strings",
                        found=str(value),
                    )
                )
        return findings

    def _check_verification(self, label: str, verification: object) -> list[Finding]:
        if not isinstance(verification, dict):
            return [
                Finding(
                    level=Level.FAIL,
                    rule="TM.invalid_task",
                    field=f"{label}.verification",
                    message=f"task '{label}' field 'verification' is not a mapping",
                    expected="mapping of " + ", ".join(self._verification_keys),
                    found=str(verification),
                )
            ]
        findings: list[Finding] = []
        has_value = False
        for key, value in verification.items():
            if key not in self._verification_keys:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="TM.invalid_task",
                        field=f"{label}.verification.{key}",
                        message=(
                            f"task '{label}' verification key '{key}' is not "
                            "recognized"
                        ),
                        expected=", ".join(self._verification_keys),
                        found=str(key),
                    )
                )
                continue
            if isinstance(value, str) and value.strip():
                has_value = True
        if not has_value:
            findings.append(self._missing_verification_finding(label, str(verification)))
        return findings

    def _check_dependencies(
        self, label: str, task: dict, known_ids: set[str]
    ) -> list[Finding]:
        depends_on = task.get("depends_on")
        if not isinstance(depends_on, list):
            return []
        findings: list[Finding] = []
        for dep in depends_on:
            if not isinstance(dep, str) or dep not in known_ids:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="TM.unknown_dependency",
                        field=f"{label}.depends_on",
                        message=f"task '{label}' depends_on unknown id '{dep}'",
                        expected="a declared task id",
                        found=str(dep),
                    )
                )
        return findings

    def _check_cycle(
        self, valid_tasks: list[tuple[int, dict]], known_ids: set[str]
    ) -> list[Finding]:
        edges: dict[str, set[str]] = {task_id: set() for task_id in known_ids}
        for _, task in valid_tasks:
            task_id = task.get("id")
            if not isinstance(task_id, str) or task_id not in known_ids:
                continue
            depends_on = task.get("depends_on")
            if not isinstance(depends_on, list):
                continue
            for dep in depends_on:
                if isinstance(dep, str) and dep in known_ids:
                    edges[task_id].add(dep)

        # Kahn's algorithm: an edge task_id -> dep means dep must run first,
        # so in-degree counts how many OTHER ids still depend on this one.
        in_degree: dict[str, int] = {task_id: 0 for task_id in known_ids}
        for task_id, deps in edges.items():
            for dep in deps:
                in_degree[dep] += 1

        queue = sorted(task_id for task_id, degree in in_degree.items() if degree == 0)
        processed: set[str] = set()
        while queue:
            current = queue.pop(0)
            processed.add(current)
            for dep in edges[current]:
                in_degree[dep] -= 1
                if in_degree[dep] == 0 and dep not in processed:
                    queue.append(dep)
            queue.sort()

        remainder = sorted(known_ids - processed)
        if not remainder:
            return []
        return [
            Finding(
                level=Level.FAIL,
                rule="TM.cycle",
                field="depends_on",
                message=f"dependency cycle among tasks: {', '.join(remainder)}",
                expected="a DAG (no cycles)",
                found=", ".join(remainder),
            )
        ]

    def _check_write_conflicts(
        self, valid_tasks: list[tuple[int, dict]], labels: dict[int, str]
    ) -> list[Finding]:
        groups: dict[str, list[tuple[str, set[str]]]] = {}
        for index, task in valid_tasks:
            execution = task.get("execution")
            group = (
                execution.get("parallel_group") if isinstance(execution, dict) else None
            )
            if not isinstance(group, str) or not group:
                continue
            label = labels[index]
            files = task.get("files")
            write_set: set[str] = set()
            if isinstance(files, dict):
                for key in ("create", "modify"):
                    value = files.get(key)
                    if isinstance(value, list):
                        write_set.update(v for v in value if isinstance(v, str))
            groups.setdefault(group, []).append((label, write_set))

        findings: list[Finding] = []
        for group, entries in groups.items():
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    label_a, files_a = entries[i]
                    label_b, files_b = entries[j]
                    overlap = sorted(files_a & files_b)
                    if overlap:
                        findings.append(
                            Finding(
                                level=Level.FAIL,
                                rule="TM.write_conflict",
                                field=group,
                                message=(
                                    f"tasks '{label_a}' and '{label_b}' in "
                                    f"parallel_group '{group}' write to "
                                    f"overlapping files: {', '.join(overlap)}"
                                ),
                                expected="disjoint create+modify within a parallel_group",
                                found=", ".join(overlap),
                            )
                        )
        return findings

    def _check_requirements(self, label: str, task: dict) -> list[Finding]:
        requirements = task.get("requirements")
        if isinstance(requirements, list) and requirements:
            return []
        return [
            Finding(
                level=Level.WARN,
                rule="TM.missing_requirements",
                field=f"{label}.requirements",
                message=f"task '{label}' carries no requirements traceability",
                expected="non-empty list of requirement ids",
                found="absent" if requirements is None else str(requirements),
            )
        ]
