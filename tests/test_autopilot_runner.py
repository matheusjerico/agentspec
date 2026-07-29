"""Integration tests for plugin-extras/scripts/autopilot.sh (headless Autopilot runner).

Every test stubs `claude` on PATH -- no real Claude Code invocation, no
network access beyond the intentionally-unreachable webhook case, and no
dependency on the developer's own ~/.claude. Each test builds a fresh tmp
git repo and a minimal PATH containing only the binaries autopilot.sh needs
(git, bash, sed, grep, cat, mkdir, uname, curl, tee) plus a no-op `osascript`
stub so macOS never fires a real desktop notification during the suite.

The script's single positional argument is a path to a pre-validated
DEFINE_{FEATURE}.md document (basename matching ^DEFINE_[A-Z0-9_]+\\.md$),
resolved relative to the repository root -- not a raw intent string. Use
`_write_define_file`/the `define_path` fixture to build a valid one.
"""
from __future__ import annotations

import json
import shlex
import stat
import subprocess
from pathlib import Path
from typing import Sequence

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
AUTOPILOT_SCRIPT = _REPO_ROOT / "plugin-extras" / "scripts" / "autopilot.sh"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "autopilot"
BASE_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
FAKE_HOME = "/nonexistent-autopilot-test-home"
DEFINE_RELATIVE_DIR = ".claude/sdd/features"
DEFAULT_DEFINE_BASENAME = "DEFINE_TESTFEATURE.md"


def _make_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _write_claude_stub(bin_dir: Path, argv_file: Path, status_row: str | None) -> None:
    """Write a fake `claude` on bin_dir that records its argv (NUL-separated,
    for exact-content assertions) and, unless status_row is None, drops a
    fake AUTOPILOT_RUN_TESTFEATURE.md report before exiting 0.
    """
    if status_row is None:
        report_block = ""
    else:
        report_block = (
            "mkdir -p .claude/sdd/reports\n"
            "cat > .claude/sdd/reports/AUTOPILOT_RUN_TESTFEATURE.md <<'REPORT_EOF'\n"
            "# Autopilot Run Report: TESTFEATURE\n"
            "\n"
            "| Field | Value |\n"
            "|---|---|\n"
            "| **Feature** | TESTFEATURE |\n"
            f"{status_row}\n"
            "REPORT_EOF\n"
        )
    script = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\0' \"$@\" > {shlex.quote(str(argv_file))}\n"
        f"{report_block}"
        "exit 0\n"
    )
    _make_executable(bin_dir / "claude", script)


def _read_recorded_argv(argv_file: Path) -> list[str]:
    parts = argv_file.read_bytes().split(b"\x00")
    if parts and parts[-1] == b"":
        parts = parts[:-1]
    return [part.decode() for part in parts]


def _escape_for_double_quotes(value: str) -> str:
    """Mirror autopilot.sh's escape_for_double_quotes bash function."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _write_define_file(repo: Path, basename: str = DEFAULT_DEFINE_BASENAME) -> str:
    """Write a minimal DEFINE_{FEATURE}.md fixture under repo and return its
    repo-relative path, ready to pass as autopilot.sh's positional argument.
    """
    define_dir = repo / DEFINE_RELATIVE_DIR
    define_dir.mkdir(parents=True, exist_ok=True)
    define_file = define_dir / basename
    define_file.write_text(
        "# DEFINE: TESTFEATURE\n\nMinimal DEFINE document for autopilot runner tests.\n"
    )
    return f"{DEFINE_RELATIVE_DIR}/{basename}"


def _run(
    cwd: Path,
    args: Sequence[str],
    path_dirs: str,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {"PATH": path_dirs, "HOME": FAKE_HOME}
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(AUTOPILOT_SCRIPT), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def intent_complete() -> str:
    return (FIXTURES_DIR / "intent_complete.txt").read_text().strip()


@pytest.fixture
def stub_bin_dir(tmp_path: Path) -> Path:
    """A PATH-prependable directory with a no-op osascript, so Darwin's
    best-effort desktop notification never pops a real banner in CI.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_executable(bin_dir / "osascript", "#!/usr/bin/env bash\nexit 0\n")
    return bin_dir


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A tmp git repo with the /auto command vendored and an empty reports
    dir -- the layout autopilot.sh's preflight checks expect.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    auto_md = repo / ".claude" / "commands" / "workflow" / "auto.md"
    auto_md.parent.mkdir(parents=True)
    auto_md.touch()
    (repo / ".claude" / "sdd" / "reports").mkdir(parents=True)
    return repo


@pytest.fixture
def define_path(git_repo: Path) -> str:
    """Repo-relative path to a valid DEFINE_{FEATURE}.md fixture inside git_repo."""
    return _write_define_file(git_repo)


def _full_path(stub_bin_dir: Path) -> str:
    return f"{stub_bin_dir}:{BASE_PATH}"


# ── --help ───────────────────────────────────────────────────────────────────

class TestHelp:
    def test_help_exits_zero_and_documents_flags(self, tmp_path: Path):
        result = _run(tmp_path, ["--help"], BASE_PATH)
        assert result.returncode == 0
        for flag in (
            "--no-judge", "--no-ship", "--no-pr", "--max-iterations",
        ):
            assert flag in result.stdout
        for var in ("AUTOPILOT_TIMEOUT_MIN", "AUTOPILOT_WEBHOOK_URL", "AUTOPILOT_LOG"):
            assert var in result.stdout


# ── argument validation ──────────────────────────────────────────────────────

class TestArgumentValidation:
    def test_missing_intent_exits_nonzero_with_usage_on_stderr(self, tmp_path: Path):
        result = _run(tmp_path, [], BASE_PATH)
        assert result.returncode != 0
        assert "Usage:" in result.stderr
        assert "missing required" in result.stderr

    def test_raw_prose_intent_argument_exits_2_without_invoking_claude(
        self, git_repo: Path, stub_bin_dir: Path, intent_complete: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(stub_bin_dir, argv_file, status_row=None)
        result = _run(git_repo, [intent_complete], _full_path(stub_bin_dir))
        assert result.returncode == 2
        assert "DEFINE" in result.stderr
        assert "/auto" in result.stderr
        assert not argv_file.exists()

    def test_nonexistent_define_path_exits_2_without_invoking_claude(
        self, git_repo: Path, stub_bin_dir: Path
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(stub_bin_dir, argv_file, status_row=None)
        result = _run(
            git_repo,
            [f"{DEFINE_RELATIVE_DIR}/DEFINE_MISSING.md"],
            _full_path(stub_bin_dir),
        )
        assert result.returncode == 2
        assert "no file found" in result.stderr
        assert not argv_file.exists()

    @pytest.mark.parametrize("basename", ["notes.md", "define_lower.md"])
    def test_non_define_basename_exits_2_without_invoking_claude(
        self, git_repo: Path, stub_bin_dir: Path, basename: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(stub_bin_dir, argv_file, status_row=None)
        bad_file = git_repo / DEFINE_RELATIVE_DIR / basename
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_text("# Not a DEFINE document\n")
        result = _run(
            git_repo, [f"{DEFINE_RELATIVE_DIR}/{basename}"], _full_path(stub_bin_dir)
        )
        assert result.returncode == 2
        assert basename in result.stderr
        assert not argv_file.exists()


# ── preflight checks ─────────────────────────────────────────────────────────

class TestPreflight:
    def test_no_claude_on_path_exits_2_with_actionable_message(
        self, git_repo: Path, stub_bin_dir: Path
    ):
        result = _run(git_repo, ["do a thing"], _full_path(stub_bin_dir))
        assert result.returncode == 2
        assert "claude CLI not found on PATH" in result.stderr

    def test_not_a_git_repo_exits_2(self, tmp_path: Path, stub_bin_dir: Path):
        argv_file = tmp_path / "argv.bin"
        _write_claude_stub(stub_bin_dir, argv_file, status_row=None)
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()
        result = _run(non_repo, ["do a thing"], _full_path(stub_bin_dir))
        assert result.returncode == 2
        assert "not inside a git repository" in result.stderr

    def test_auto_command_not_resolvable_exits_2(self, tmp_path: Path, stub_bin_dir: Path):
        argv_file = tmp_path / "argv.bin"
        _write_claude_stub(stub_bin_dir, argv_file, status_row=None)
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
        define_relpath = _write_define_file(repo)
        result = _run(repo, [define_relpath], _full_path(stub_bin_dir))
        assert result.returncode == 2
        assert "AgentSpec /auto command not found" in result.stderr


# ── RUN REPORT status → exit code mapping ────────────────────────────────────

class TestStatusMapping:
    def test_success_status_maps_to_exit_0(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(
            stub_bin_dir, argv_file,
            status_row="| **Status** | ✅ Success (PR: https://example.com/pr/1) |",
        )
        result = _run(git_repo, [define_path], _full_path(stub_bin_dir))
        assert result.returncode == 0

    def test_partial_success_status_maps_to_exit_3(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(
            stub_bin_dir, argv_file,
            status_row="| **Status** | ⚠ Partial Success |",
        )
        result = _run(git_repo, [define_path], _full_path(stub_bin_dir))
        assert result.returncode == 3

    @pytest.mark.parametrize(
        "status_row",
        [
            "| **Status** | ❌ Aborted (Gate 0) |",
            "| **Status** | ❌ Aborted (I) |",
            "| **Status** | ❌ Aborted (D) |",
        ],
        ids=["gate-0", "ignition-rescored", "design-decision-pending"],
    )
    def test_aborted_status_maps_to_exit_1(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str, status_row: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(stub_bin_dir, argv_file, status_row=status_row)
        result = _run(git_repo, [define_path], _full_path(stub_bin_dir))
        assert result.returncode == 1

    def test_missing_report_exits_2(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(stub_bin_dir, argv_file, status_row=None)
        result = _run(git_repo, [define_path], _full_path(stub_bin_dir))
        assert result.returncode == 2

    def test_stale_success_report_is_not_reused_when_current_run_writes_none(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        stale_report = git_repo / ".claude/sdd/reports/AUTOPILOT_RUN_OLD.md"
        stale_report.write_text(
            "| **Status** | ✅ Success (PR: https://example.com/pr/old) |\n"
        )
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(stub_bin_dir, argv_file, status_row=None)

        result = _run(git_repo, [define_path], _full_path(stub_bin_dir))

        assert result.returncode == 2
        assert "no AUTOPILOT_RUN report found" in result.stderr

    def test_unreadable_status_row_exits_2(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(
            stub_bin_dir, argv_file,
            status_row="Status: totally not a table row",
        )
        result = _run(git_repo, [define_path], _full_path(stub_bin_dir))
        assert result.returncode == 2


# ── prompt construction ──────────────────────────────────────────────────────

class TestPromptConstruction:
    def test_define_path_with_quotes_and_backslashes_reaches_stub_intact(
        self, git_repo: Path, stub_bin_dir: Path
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(
            stub_bin_dir, argv_file, status_row="| **Status** | ✅ Success |",
        )
        weird_dir = git_repo / 'weird "dir" \\with\\backslash'
        weird_dir.mkdir(parents=True)
        define_file = weird_dir / DEFAULT_DEFINE_BASENAME
        define_file.write_text("# DEFINE: TESTFEATURE\n")
        define_relpath = str(define_file.relative_to(git_repo))
        result = _run(git_repo, [define_relpath], _full_path(stub_bin_dir))
        assert result.returncode == 0
        argv = _read_recorded_argv(argv_file)
        assert argv[0] == "-p"
        expected_prompt = f'/auto "{_escape_for_double_quotes(define_relpath)}"'
        assert argv[1] == expected_prompt

    def test_valid_define_path_prompt_is_exact_and_status_maps_to_exit_code(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(
            stub_bin_dir, argv_file, status_row="| **Status** | ✅ Success |",
        )
        result = _run(git_repo, [define_path], _full_path(stub_bin_dir))
        assert result.returncode == 0
        argv = _read_recorded_argv(argv_file)
        assert argv[0] == "-p"
        assert argv[1] == f'/auto "{define_path}"'

    def test_passthrough_flags_appear_in_recorded_prompt(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(
            stub_bin_dir, argv_file, status_row="| **Status** | ✅ Success |",
        )
        result = _run(
            git_repo,
            [define_path, "--no-judge", "--max-iterations", "3"],
            _full_path(stub_bin_dir),
        )
        assert result.returncode == 0
        argv = _read_recorded_argv(argv_file)
        prompt = argv[1]
        assert "--no-judge" in prompt
        assert "--max-iterations 3" in prompt

    def test_passthrough_flags_appended_verbatim_after_quoted_define_path(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(
            stub_bin_dir, argv_file, status_row="| **Status** | ✅ Success |",
        )
        result = _run(
            git_repo,
            [define_path, "--no-judge", "--max-iterations", "2"],
            _full_path(stub_bin_dir),
        )
        assert result.returncode == 0
        argv = _read_recorded_argv(argv_file)
        expected_prompt = f'/auto "{define_path}" --no-judge --max-iterations 2'
        assert argv[1] == expected_prompt


# ── notifications ─────────────────────────────────────────────────────────────

class TestNotifications:
    def test_unreachable_webhook_does_not_affect_exit_code(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(
            stub_bin_dir, argv_file, status_row="| **Status** | ✅ Success |",
        )
        result = _run(
            git_repo, [define_path], _full_path(stub_bin_dir),
            env_overrides={"AUTOPILOT_WEBHOOK_URL": "http://127.0.0.1:9"},
        )
        assert result.returncode == 0

    def test_webhook_url_never_printed(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        _write_claude_stub(
            stub_bin_dir, argv_file, status_row="| **Status** | ✅ Success |",
        )
        webhook_url = "http://127.0.0.1:9/unique-marker-path"
        result = _run(
            git_repo, [define_path], _full_path(stub_bin_dir),
            env_overrides={"AUTOPILOT_WEBHOOK_URL": webhook_url},
        )
        assert webhook_url not in result.stdout
        assert webhook_url not in result.stderr

    def test_webhook_payload_matches_documented_contract(
        self, git_repo: Path, stub_bin_dir: Path, define_path: str
    ):
        argv_file = git_repo.parent / "argv.bin"
        curl_argv_file = git_repo.parent / "curl-argv.bin"
        _write_claude_stub(
            stub_bin_dir, argv_file,
            status_row="| **Status** | ✅ Success (PR: https://example.com/pr/7) |",
        )
        _make_executable(
            stub_bin_dir / "curl",
            "#!/usr/bin/env bash\n"
            f"printf '%s\\0' \"$@\" > {shlex.quote(str(curl_argv_file))}\n",
        )

        result = _run(
            git_repo, [define_path], _full_path(stub_bin_dir),
            env_overrides={"AUTOPILOT_WEBHOOK_URL": "https://hooks.example.test/autopilot"},
        )

        assert result.returncode == 0
        curl_argv = _read_recorded_argv(curl_argv_file)
        payload = json.loads(curl_argv[curl_argv.index("-d") + 1])
        assert payload == {
            "feature": "TESTFEATURE",
            "status": "✅ Success (PR: https://example.com/pr/7)",
            "pr_url": "https://example.com/pr/7",
            "report_path": ".claude/sdd/reports/AUTOPILOT_RUN_TESTFEATURE.md",
        }
