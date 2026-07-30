"""Machine-readable PR readiness artifact and mutable Git/runtime validation."""

from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import yaml

from ..verdict import Finding, Level

_FENCE = re.compile(r"```ya?ml\s*\n(?P<body>.*?)\n```", re.DOTALL | re.IGNORECASE)
_CHECKS = {
    "working_tree_clean",
    "base_resolved",
    "lint",
    "types",
    "tests",
    "build",
    "must_requirements_covered",
    "branch_verdict",
    "blocking_findings_open",
    "verdict_unchanged",
    "migration_plan",
    "rollback_plan",
    "residual_risks",
}
_PASS = {"pass", "clean", "clean-with-minors", "not_applicable", "not_configured"}
_RESULTS_BY_CHECK = {
    "working_tree_clean": {"pass"},
    "base_resolved": {"pass"},
    "lint": {"pass"},
    "types": {"pass", "not_configured"},
    "tests": {"pass"},
    "build": {"pass"},
    "must_requirements_covered": {"pass"},
    "branch_verdict": {"clean", "clean-with-minors"},
    "blocking_findings_open": {"pass"},
    "verdict_unchanged": {"pass"},
    "migration_plan": {"pass", "not_applicable"},
    "rollback_plan": {"pass", "not_applicable"},
    "residual_risks": {"pass"},
}
_ROOT_KEYS = {
    "schema_version",
    "feature",
    "generated_at",
    "ship_head_sha",
    "target_branch",
    "target_tip_sha",
    "checks",
}
_CHECK_KEYS = {"result", "evidence"}
_EVIDENCE_SOURCES = {"artifact", "command", "declaration", "git"}
_MAX_ARTIFACT_AGE = timedelta(hours=24)
_MAX_CLOCK_SKEW = timedelta(minutes=5)
_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


@dataclass(frozen=True)
class PrReadyArtifact:
    data: dict[str, Any]


def _fail(rule: str, message: str, *, field: str | None = None, found: Any = None) -> Finding:
    return Finding(
        level=Level.FAIL,
        rule=rule,
        message=message,
        field=field,
        found=None if found is None else str(found),
    )


def _is_trivial_command(command: str | None) -> bool:
    if not command or not command.strip():
        return True
    try:
        words = shlex.split(command)
    except ValueError:
        return True
    if not words:
        return True
    executable = words[0].rsplit("/", 1)[-1].lower()
    if executable in {"true", ":", "echo", "printf"}:
        return True
    return executable == "exit" and words[1:] in ([], ["0"])


class PrReadyArtifactContract:
    """Validate the frozen, machine-readable handoff written by Ship."""

    name = "pr-readiness"

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
        max_artifact_age: timedelta = _MAX_ARTIFACT_AGE,
    ) -> None:
        self._now = now or (lambda: datetime.now(UTC))
        self._max_artifact_age = max_artifact_age

    def parse(self, artifact: Any) -> PrReadyArtifact:
        if not isinstance(artifact, str):
            raise ValueError("PR_READY artifact must be Markdown text")
        roots: list[dict[str, Any]] = []
        for match in _FENCE.finditer(artifact):
            value = yaml.safe_load(match.group("body"))
            if isinstance(value, dict) and "pr_ready" in value:
                roots.append(value)
        if len(roots) != 1:
            raise ValueError(
                f"PR_READY must contain exactly one YAML fence rooted at pr_ready; found {len(roots)}"
            )
        root = roots[0]["pr_ready"]
        if not isinstance(root, dict):
            raise ValueError("pr_ready must be a mapping")
        return PrReadyArtifact(root)

    def check(self, parsed: PrReadyArtifact) -> list[Finding]:
        data = parsed.data
        findings: list[Finding] = []
        extra_root_keys = sorted(set(data) - _ROOT_KEYS)
        if extra_root_keys:
            findings.append(
                _fail(
                    "PR.extra_keys",
                    "pr_ready contains unknown keys",
                    field="pr_ready",
                    found=extra_root_keys,
                )
            )
        required_scalars = {
            "schema_version": int,
            "feature": str,
            "generated_at": str,
            "ship_head_sha": str,
            "target_branch": str,
            "target_tip_sha": str,
        }
        for key, expected_type in required_scalars.items():
            value = data.get(key)
            if not isinstance(value, expected_type) or isinstance(value, bool) or value == "":
                findings.append(
                    _fail(
                        "PR.artifact_field",
                        f"{key} is required with type {expected_type.__name__}",
                        field=key,
                        found=value,
                    )
                )
        generated_at = data.get("generated_at")
        if isinstance(generated_at, str):
            timestamp: datetime | None = None
            if _RFC3339.fullmatch(generated_at):
                try:
                    timestamp = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                except ValueError:
                    pass
            if timestamp is None or timestamp.utcoffset() is None:
                findings.append(
                    _fail(
                        "PR.generated_at",
                        "generated_at must be a timezone-aware RFC3339 timestamp",
                        field="generated_at",
                        found=generated_at,
                    )
                )
            else:
                now = self._now()
                if now.tzinfo is None:
                    raise ValueError("PR readiness clock must return a timezone-aware datetime")
                age = now.astimezone(UTC) - timestamp.astimezone(UTC)
                if age > self._max_artifact_age:
                    findings.append(
                        _fail(
                            "PR.artifact_stale",
                            "PR_READY is older than the allowed freshness window",
                            field="generated_at",
                            found=generated_at,
                        )
                    )
                elif age < -_MAX_CLOCK_SKEW:
                    findings.append(
                        _fail(
                            "PR.generated_at",
                            "generated_at is implausibly far in the future",
                            field="generated_at",
                            found=generated_at,
                        )
                    )
        if data.get("schema_version") != 1:
            findings.append(
                _fail(
                    "PR.schema_version",
                    "unsupported PR_READY schema version",
                    field="schema_version",
                    found=data.get("schema_version"),
                )
            )
        target_tip_sha = data.get("target_tip_sha")
        if target_tip_sha is not None and (
            not isinstance(target_tip_sha, str)
            or re.fullmatch(r"[0-9a-fA-F]{40}", target_tip_sha) is None
        ):
            findings.append(
                _fail(
                    "PR.target_tip_sha",
                    "target_tip_sha must be a full 40-character Git object id",
                    field="target_tip_sha",
                    found=target_tip_sha,
                )
            )
        sha = data.get("ship_head_sha")
        if not isinstance(sha, str) or re.fullmatch(r"[0-9a-fA-F]{40}", sha) is None:
            findings.append(
                _fail(
                    "PR.ship_head_sha",
                    "ship_head_sha must be a full 40-character Git object id",
                    field="ship_head_sha",
                    found=sha,
                )
            )
        checks = data.get("checks")
        if not isinstance(checks, dict):
            findings.append(_fail("PR.checks_shape", "checks must be a mapping", field="checks"))
            return findings
        missing = sorted(_CHECKS - set(checks))
        extra = sorted(set(checks) - _CHECKS)
        if missing or extra:
            findings.append(
                _fail(
                    "PR.checks_shape",
                    "checks must contain the frozen 13-item catalog",
                    field="checks",
                    found={"missing": missing, "extra": extra},
                )
            )
        for name in sorted(_CHECKS & set(checks)):
            check = checks[name]
            if not isinstance(check, dict):
                findings.append(
                    _fail("PR.check_shape", "check must be a mapping", field=f"checks.{name}")
                )
                continue
            extra_check_keys = sorted(set(check) - _CHECK_KEYS)
            if extra_check_keys:
                findings.append(
                    _fail(
                        "PR.extra_keys",
                        "check contains unknown keys",
                        field=f"checks.{name}",
                        found=extra_check_keys,
                    )
                )
            result = check.get("result")
            evidence = check.get("evidence")
            if result not in _RESULTS_BY_CHECK[name]:
                findings.append(
                    _fail(
                        "PR.check_failed",
                        "readiness check is not passing",
                        field=f"checks.{name}.result",
                        found=result,
                    )
                )
            if not self._valid_evidence(evidence):
                findings.append(
                    _fail(
                        "PR.evidence_invalid",
                        "passing checks require structured, verifiable evidence",
                        field=f"checks.{name}.evidence",
                        found=evidence,
                    )
                )
        return findings

    @staticmethod
    def _valid_evidence(evidence: Any) -> bool:
        if not isinstance(evidence, dict):
            return False
        source = evidence.get("source")
        if source not in _EVIDENCE_SOURCES:
            return False
        if source == "command":
            if set(evidence) != {"source", "command", "exit_code"}:
                return False
            command = evidence.get("command")
            return (
                isinstance(command, str)
                and bool(command.strip())
                and evidence.get("exit_code") == 0
                and not isinstance(evidence.get("exit_code"), bool)
                and not _is_trivial_command(command)
            )
        if set(evidence) != {"source", "reference"}:
            return False
        reference = evidence.get("reference")
        return isinstance(reference, str) and bool(reference.strip())


class PrReadinessRuntimeValidator:
    """Revalidate mutable facts immediately before PR publication."""

    def __init__(
        self,
        repo: Path,
        *,
        target_branch: str | None = None,
        test_command: str | None = None,
        build_command: str | None = None,
    ) -> None:
        self.repo = repo
        self.target_branch = target_branch
        self.test_command = test_command
        self.build_command = build_command

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

    def _shell(self, command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            shlex.split(command),
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

    def check(self, artifact: PrReadyArtifact) -> list[Finding]:
        findings: list[Finding] = []
        data = artifact.data
        artifact_target = str(data.get("target_branch", ""))
        if self.target_branch is not None and self.target_branch != artifact_target:
            findings.append(
                _fail(
                    "PR.target_changed",
                    "authorized target differs from the target frozen at Ship",
                    field="target_branch",
                    found=f"artifact={artifact_target}, runtime={self.target_branch}",
                )
            )
        status = self._run(["git", "status", "--short"])
        if status.returncode != 0:
            findings.append(_fail("PR.git_error", status.stderr.strip() or "git status failed"))
        elif status.stdout.strip():
            findings.append(
                _fail("PR.working_tree_dirty", "working tree is not clean", found=status.stdout)
            )

        head = self._run(["git", "rev-parse", "HEAD"])
        expected_head = str(data.get("ship_head_sha", ""))
        if head.returncode != 0:
            findings.append(_fail("PR.git_error", head.stderr.strip() or "HEAD resolution failed"))
        elif head.stdout.strip() != expected_head:
            findings.append(
                _fail(
                    "PR.head_changed",
                    "HEAD no longer equals ship_head_sha; a fresh re-review is required",
                    field="ship_head_sha",
                    found=head.stdout.strip(),
                )
            )

        target = self.target_branch or str(data.get("target_branch", ""))
        local_ref = target
        remote_ref = f"origin/{target}"
        origin = self._run(["git", "remote", "get-url", "origin"])
        if origin.returncode == 0:
            fetched = self._run(["git", "fetch", "--quiet", "origin", target])
            if fetched.returncode != 0:
                findings.append(
                    _fail(
                        "PR.target_fetch_failed",
                        "could not refresh the authorized remote target tip",
                        found=fetched.stderr.strip() or fetched.stdout.strip(),
                    )
                )
        local_exists = self._run(["git", "rev-parse", "--verify", local_ref]).returncode == 0
        remote_exists = self._run(["git", "rev-parse", "--verify", remote_ref]).returncode == 0
        target_ref = ""
        if remote_exists:
            target_ref = remote_ref
        elif local_exists:
            target_ref = local_ref
            findings.append(
                Finding(
                    level=Level.PASS,
                    rule="PR.target_local_fallback",
                    message="origin target is unavailable; validated the local target tip",
                    field="target_branch",
                    found=target,
                )
            )
        else:
            findings.append(
                _fail("PR.base_unresolved", "target branch cannot be resolved", found=target)
            )
        if target_ref:
            target_tip = self._run(["git", "rev-parse", target_ref])
            frozen_tip = data.get("target_tip_sha")
            if target_tip.returncode != 0:
                findings.append(
                    _fail("PR.git_error", target_tip.stderr.strip() or "target tip resolution failed")
                )
            elif isinstance(frozen_tip, str) and target_tip.stdout.strip() != frozen_tip:
                findings.append(
                    _fail(
                        "PR.target_tip_changed",
                        "authorized target tip no longer equals target_tip_sha",
                        field="target_tip_sha",
                        found=target_tip.stdout.strip(),
                    )
                )
            merge_base = self._run(["git", "merge-base", "HEAD", target_ref])
            if merge_base.returncode != 0:
                findings.append(_fail("PR.merge_base", "no valid merge-base with target"))
            tree = self._run(["git", "merge-tree", "--write-tree", "HEAD", target_ref])
            if tree.returncode != 0:
                findings.append(
                    _fail(
                        "PR.merge_conflict",
                        "merge-tree reports a conflict with the current target",
                        found=tree.stderr or tree.stdout,
                    )
                )

        if _is_trivial_command(self.test_command):
            findings.append(
                _fail(
                    "PR.tests_not_run",
                    "a non-trivial test command is required for runtime readiness",
                    found=self.test_command,
                )
            )
        elif self._shell(self.test_command).returncode != 0:
            findings.append(_fail("PR.tests_failed", f"runtime command failed: {self.test_command}"))

        checks = data.get("checks")
        build_result = None
        if isinstance(checks, dict) and isinstance(checks.get("build"), dict):
            build_result = checks["build"].get("result")
        build_is_configured = build_result not in {"not_configured", "not_applicable"}
        if build_is_configured != bool(self.build_command):
            findings.append(
                _fail(
                    "PR.build_incoherent",
                    "runtime build command must agree with the frozen build result",
                    field="checks.build.result",
                    found=f"result={build_result}, command={self.build_command!r}",
                )
            )
        elif self.build_command and _is_trivial_command(self.build_command):
            findings.append(
                _fail(
                    "PR.build_incoherent",
                    "configured build command must be non-trivial",
                    found=self.build_command,
                )
            )
        elif self.build_command and self._shell(self.build_command).returncode != 0:
            findings.append(
                _fail("PR.build_failed", f"runtime command failed: {self.build_command}")
            )
        return findings
