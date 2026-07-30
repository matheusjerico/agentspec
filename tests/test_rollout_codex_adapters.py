"""Integration tests for Codex adapter generation inside the vendored rollout.

Each test builds a throwaway target tree containing the minimum a target
needs -- a .claude/ directory with a skill and a command -- and runs the
real script against it with an explicit target argument, so the developer's
own .agentspec-rollout-targets is never consulted.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ROLLOUT = REPO_ROOT / "scripts" / "rollout-agentspec.sh"


def _write_skill(root: Path, name: str, description: str = "Example skill.") -> Path:
    path = root / ".claude" / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# Body\n",
        encoding="utf-8",
    )
    return path


def _write_command(root: Path, command_set: str, name: str) -> Path:
    path = root / ".claude" / "commands" / command_set / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: Example command.\n---\n\n# Body\n",
        encoding="utf-8",
    )
    return path


def _run(target: Path, *flags: str, home: Path) -> subprocess.CompletedProcess[str]:
    # Inherit the developer's environment so python3 keeps the pyyaml the
    # script's require_python gate demands; only HOME is redirected, which is
    # what relocates BACKUP_ROOT into the test's tmp tree.
    return subprocess.run(
        ["bash", str(ROLLOUT), *flags, str(target)],
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        env={**os.environ, "HOME": str(home)},
    )


@pytest.fixture
def home(tmp_path: Path) -> Path:
    path = tmp_path / "home"
    path.mkdir()
    return path


@pytest.fixture
def target(tmp_path: Path) -> Path:
    root = tmp_path / "target"
    _write_skill(root, "local-only")
    _write_command(root, "workflow", "build")
    _write_command(root, "vendor", "apply")
    return root


def test_dry_run_reports_adapters_without_writing(target: Path, home: Path):
    result = _run(target, home=home)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "adapters: would generate" in result.stdout
    assert not (target / ".agents").exists()


def test_apply_generates_adapters_for_skills_and_agentspec_commands(
    target: Path, home: Path
):
    result = _run(target, "--apply", home=home)

    assert result.returncode == 0, result.stdout + result.stderr
    skills = target / ".agents" / "skills"
    assert (skills / "local-only" / "SKILL.md").exists()
    assert (skills / "agentspec-build" / "SKILL.md").exists()
    assert not (skills / "agentspec-apply").exists()


def test_every_generated_adapter_points_at_a_file_present_in_the_target(
    target: Path, home: Path
):
    result = _run(target, "--apply", home=home)
    assert result.returncode == 0, result.stdout + result.stderr

    adapters = sorted((target / ".agents" / "skills").rglob("SKILL.md"))
    assert adapters
    for adapter in adapters:
        body = adapter.read_text(encoding="utf-8")
        referenced = re.search(r"source of truth is `([^`]+)`", body)
        assert referenced, f"{adapter} names no canonical source"
        assert (target / referenced.group(1)).is_file(), (
            f"{adapter} points at missing {referenced.group(1)}"
        )


def test_apply_preserves_codex_native_entries(target: Path, home: Path):
    native = target / ".agents" / "skills" / "native" / "SKILL.md"
    native.parent.mkdir(parents=True)
    native.write_text("codex-native", encoding="utf-8")

    result = _run(target, "--apply", home=home)

    assert result.returncode == 0, result.stdout + result.stderr
    assert native.read_text(encoding="utf-8") == "codex-native"
    assert "preserved: native" in result.stdout


def test_malformed_local_skill_marks_target_partial_and_leaves_agents_intact(
    target: Path, home: Path
):
    broken = target / ".claude" / "skills" / "broken" / "SKILL.md"
    broken.parent.mkdir(parents=True)
    broken.write_text("---\nname: broken\n---\n", encoding="utf-8")
    existing = target / ".agents" / "skills" / "existing" / "SKILL.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("untouched", encoding="utf-8")

    result = _run(target, "--apply", home=home)

    assert result.returncode == 1
    assert "adapters: FAILED" in result.stdout
    assert "missing description" in result.stdout
    assert existing.read_text(encoding="utf-8") == "untouched"
    assert not (target / ".agents" / "skills" / "local-only").exists()


def test_target_without_claude_gets_no_agents_directory(tmp_path: Path, home: Path):
    empty = tmp_path / "empty"
    empty.mkdir()

    result = _run(empty, "--apply", home=home)

    assert result.returncode == 1
    assert not (empty / ".agents").exists()


def test_backup_captures_agents_and_rollback_restores_it(target: Path, home: Path):
    native = target / ".agents" / "skills" / "native" / "SKILL.md"
    native.parent.mkdir(parents=True)
    native.write_text("codex-native", encoding="utf-8")

    applied = _run(target, "--apply", "--stamp", "teststamp", home=home)
    assert applied.returncode == 0, applied.stdout + applied.stderr

    backup = home / ".agentspec-rollout-backups" / "teststamp" / "target"
    assert (backup / ".agents" / "skills" / "native" / "SKILL.md").exists()
    assert (target / ".agents" / "skills" / "local-only").exists()

    restored = _run(target, "--rollback", "--stamp", "teststamp", home=home)
    assert restored.returncode == 0, restored.stdout + restored.stderr
    assert not (target / ".agents" / "skills" / "local-only").exists()
    assert native.read_text(encoding="utf-8") == "codex-native"


def test_non_directory_agents_round_trips_through_backup_and_rollback(
    target: Path, home: Path
):
    # .agents is a plain file here, not a directory. Adapter generation can't
    # run against it (write_adapters' mkdir fails), but backup_target already
    # backs up .agents on `-e` (any type) before that runs, and rollback_target
    # must restore it on the same test -- not silently skip it because it
    # isn't a directory.
    agents_file = target / ".agents"
    agents_file.write_text("not a directory", encoding="utf-8")

    applied = _run(target, "--apply", "--stamp", "filestamp", home=home)
    assert applied.returncode == 1, applied.stdout + applied.stderr
    assert "adapters: FAILED" in applied.stdout

    backup = home / ".agentspec-rollout-backups" / "filestamp" / "target" / ".agents"
    assert backup.is_file()
    assert backup.read_text(encoding="utf-8") == "not a directory"
    # write_adapters raises before mutating anything, so the target's own
    # .agents survives the failed apply untouched.
    assert agents_file.read_text(encoding="utf-8") == "not a directory"

    agents_file.write_text("mutated after apply", encoding="utf-8")

    restored = _run(target, "--rollback", "--stamp", "filestamp", home=home)
    assert restored.returncode == 0, restored.stdout + restored.stderr
    assert "restored:" in restored.stdout
    assert ".agents" in restored.stdout
    assert agents_file.is_file()
    assert agents_file.read_text(encoding="utf-8") == "not a directory"


def test_rollback_from_a_claude_only_stamp_succeeds(target: Path, home: Path):
    stamp_dir = home / ".agentspec-rollout-backups" / "legacy" / "target"
    (stamp_dir / ".claude" / "skills" / "restored").mkdir(parents=True)
    (stamp_dir / ".claude" / "skills" / "restored" / "SKILL.md").write_text(
        "---\nname: restored\ndescription: Example skill.\n---\n", encoding="utf-8"
    )

    applied = _run(target, "--apply", "--stamp", "current", home=home)
    assert applied.returncode == 0, applied.stdout + applied.stderr

    restored = _run(target, "--rollback", "--stamp", "legacy", home=home)

    assert restored.returncode == 0, restored.stdout + restored.stderr
    assert (target / ".claude" / "skills" / "restored").exists()
    assert (target / ".agents" / "skills" / "local-only").exists()
