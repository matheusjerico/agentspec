"""Executable contracts for atomic, attributable plugin builds."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_SCRIPT = ROOT / "build-plugin.sh"
MAKEFILE = ROOT / "Makefile"


def test_help_documents_explicit_dev_and_release_modes() -> None:
    result = subprocess.run(
        [str(BUILD_SCRIPT), "--help"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--dev" in result.stdout
    assert "--release" in result.stdout
    assert "clean Git worktree" in result.stdout


def test_build_uses_staging_transaction_and_records_commit_manifest() -> None:
    text = BUILD_SCRIPT.read_text()

    assert 'mktemp -d "${SCRIPT_DIR}/.plugin-build.XXXXXX"' in text
    assert 'git -C "${SCRIPT_DIR}" rev-parse --verify HEAD' in text
    assert "BUILD-MANIFEST.json" in text
    assert '"commit": commit' in text
    assert '"files": files' in text
    assert '"tree_state": tree_state' in text
    assert '"mode": format(path.stat().st_mode & 0o777, "04o")' in text
    assert 'mv "${FINAL_PLUGIN_DIR}" "${BACKUP_DIR}"' in text
    assert 'mv "${STAGED_PLUGIN_DIR}" "${FINAL_PLUGIN_DIR}"' in text
    assert "release source changed after preflight" in text
    assert 'generate-agent-router.py" --check' in text


def test_release_mode_rejects_dirty_worktree_before_building(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "tracked").write_text("clean\n")
    subprocess.run(["git", "add", "tracked"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
    (repo / ".claude").mkdir()
    plugin_manifest = repo / "plugin" / ".claude-plugin"
    plugin_manifest.mkdir(parents=True)
    (plugin_manifest / "plugin.json").write_text("{}\n")
    (repo / "tracked").write_text("dirty\n")
    script = repo / "build-plugin.sh"
    script.write_text(BUILD_SCRIPT.read_text())
    script.chmod(0o755)

    result = subprocess.run(
        [str(script), "--release"],
        cwd=repo,
        env={**os.environ, "NO_COLOR": "1"},
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "clean Git worktree" in result.stderr
    assert not list(repo.glob(".plugin-build.*"))


def test_makefile_exposes_release_build_separately_from_dev_build() -> None:
    text = MAKEFILE.read_text()

    assert "build-release:" in text
    assert "./build-plugin.sh --release" in text
    assert "./build-plugin.sh --dev" in text
