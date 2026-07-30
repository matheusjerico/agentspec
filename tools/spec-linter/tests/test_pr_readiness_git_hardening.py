"""Adversarial Git/runtime checks required by remediation §13."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml

from spec_linter.contracts.pr_readiness import (
    PrReadyArtifactContract,
    PrReadinessRuntimeValidator,
)
from spec_linter.engine import lint
from spec_linter.verdict import Level


_CHECKS = {
    name: {
        "result": result,
        "evidence": {"source": "artifact", "reference": f"BUILD_REPORT.md#{name}"},
    }
    for name, result in {
        "working_tree_clean": "pass",
        "base_resolved": "pass",
        "lint": "pass",
        "types": "not_configured",
        "tests": "pass",
        "build": "pass",
        "must_requirements_covered": "pass",
        "branch_verdict": "clean",
        "blocking_findings_open": "pass",
        "verdict_unchanged": "pass",
        "migration_plan": "not_applicable",
        "rollback_plan": "not_applicable",
        "residual_risks": "pass",
    }.items()
}


def _artifact(
    sha: str,
    target: str = "main",
    *,
    target_tip_sha: str | None = None,
) -> str:
    payload = {
        "pr_ready": {
            "schema_version": 1,
            "feature": "GIT_HARDENING",
            "generated_at": datetime.now(UTC).isoformat(),
            "ship_head_sha": sha,
            "target_branch": target,
            "checks": _CHECKS,
        }
    }
    payload["pr_ready"]["target_tip_sha"] = target_tip_sha or sha
    return f"```yaml\n{yaml.safe_dump(payload, sort_keys=False)}```"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()


def _repo(path: Path) -> str:
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    (path / "tracked").write_text("base\n")
    _git(path, "add", "tracked")
    _git(path, "commit", "-m", "base")
    _git(path, "switch", "-c", "feature")
    (path / "feature").write_text("feature\n")
    _git(path, "add", "feature")
    _git(path, "commit", "-m", "feature")
    return _git(path, "rev-parse", "HEAD")


def _rules(repo: Path, artifact_text: str, **kwargs: object) -> set[str]:
    parsed = PrReadyArtifactContract().parse(artifact_text)
    validator = PrReadinessRuntimeValidator(repo, **kwargs)
    return {finding.rule for finding in validator.check(parsed)}


def test_artifact_rejects_abbreviated_ship_sha() -> None:
    verdict = lint(_artifact("a"), PrReadyArtifactContract())
    assert verdict.level == Level.FAIL
    assert any(f.rule == "PR.ship_head_sha" for f in verdict.findings)


def test_commit_after_ship_invalidates_readiness(tmp_path: Path) -> None:
    shipped = _repo(tmp_path)
    (tmp_path / "later").write_text("later\n")
    _git(tmp_path, "add", "later")
    _git(tmp_path, "commit", "-m", "after ship")

    assert "PR.head_changed" in _rules(
        tmp_path, _artifact(shipped), test_command="test -f tracked"
    )


def test_amend_after_ship_invalidates_readiness(tmp_path: Path) -> None:
    shipped = _repo(tmp_path)
    (tmp_path / "feature").write_text("amended feature\n")
    _git(tmp_path, "add", "feature")
    _git(tmp_path, "commit", "--amend", "--no-edit")

    assert "PR.head_changed" in _rules(
        tmp_path, _artifact(shipped), test_command="test -f tracked"
    )


def test_authorized_target_must_match_frozen_target(tmp_path: Path) -> None:
    shipped = _repo(tmp_path)
    _git(tmp_path, "branch", "release")

    assert "PR.target_changed" in _rules(
        tmp_path,
        _artifact(shipped, target="main"),
        target_branch="release",
        test_command="test -f tracked",
    )


def test_runtime_fails_closed_without_test_command(tmp_path: Path) -> None:
    shipped = _repo(tmp_path)

    assert "PR.tests_not_run" in _rules(tmp_path, _artifact(shipped))


def test_current_target_conflict_blocks_readiness(tmp_path: Path) -> None:
    shipped = _repo(tmp_path)
    _git(tmp_path, "switch", "main")
    (tmp_path / "tracked").write_text("base change\n")
    _git(tmp_path, "add", "tracked")
    _git(tmp_path, "commit", "-m", "conflicting base change")
    _git(tmp_path, "switch", "feature")
    (tmp_path / "tracked").write_text("feature change\n")
    _git(tmp_path, "add", "tracked")
    _git(tmp_path, "commit", "-m", "conflicting feature change")
    current = _git(tmp_path, "rev-parse", "HEAD")

    assert "PR.merge_conflict" in _rules(
        tmp_path, _artifact(current), test_command="test -f tracked"
    )


def test_remote_target_tip_is_preferred_and_remote_only_conflict_blocks(
    tmp_path: Path,
) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    remote.mkdir()
    work.mkdir()
    _git(remote, "init", "--bare")
    shipped = _repo(work)
    _git(work, "remote", "add", "origin", str(remote))
    _git(work, "push", "-u", "origin", "main", "feature")
    _git(work, "switch", "main")
    (work / "tracked").write_text("remote change\n")
    _git(work, "add", "tracked")
    _git(work, "commit", "-m", "remote-only conflict")
    _git(work, "push", "origin", "main")
    _git(work, "switch", "feature")
    (work / "tracked").write_text("feature change\n")
    _git(work, "add", "tracked")
    _git(work, "commit", "-m", "feature conflict")
    current = _git(work, "rev-parse", "HEAD")
    # Preserve stale local and tracking refs; validation must refresh origin/main.
    _git(work, "branch", "-f", "main", f"{shipped}^")
    _git(work, "update-ref", "refs/remotes/origin/main", f"{shipped}^")

    assert "PR.merge_conflict" in _rules(
        work,
        _artifact(current),
        test_command="test -f tracked",
    )


def test_frozen_target_tip_must_match_current_authorized_tip(tmp_path: Path) -> None:
    shipped = _repo(tmp_path)
    frozen_tip = _git(tmp_path, "rev-parse", "main")
    _git(tmp_path, "switch", "main")
    (tmp_path / "target-later").write_text("later\n")
    _git(tmp_path, "add", "target-later")
    _git(tmp_path, "commit", "-m", "move target")
    _git(tmp_path, "switch", "feature")

    assert "PR.target_tip_changed" in _rules(
        tmp_path,
        _artifact(shipped, target_tip_sha=frozen_tip),
        test_command="test -f tracked",
    )


def test_local_target_fallback_is_reported(tmp_path: Path) -> None:
    shipped = _repo(tmp_path)

    rules = _rules(
        tmp_path,
        _artifact(shipped),
        test_command="test -f tracked",
    )

    assert "PR.target_local_fallback" in rules
