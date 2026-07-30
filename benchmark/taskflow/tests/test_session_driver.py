import json
import subprocess
from pathlib import Path

import pytest

from benchmark.taskflow.session_driver import (
    ALLOWED_TOOLS,
    RunConfig,
    _parse_events,
    build_command,
    run,
)


def config(tmp_path: Path, budget: float = 30.0) -> RunConfig:
    return RunConfig(
        framework="agentspec",
        workdir=tmp_path,
        plugin=Path("/plugins/agentspec"),
        prompt=Path("/brief.md"),
        model="sonnet",
        effort="high",
        budget_usd=budget,
    )


def test_build_command_loads_only_selected_plugin(tmp_path: Path):
    command = build_command(config(tmp_path))
    assert command.count("--plugin-dir") == 1
    assert command[command.index("--plugin-dir") + 1] == "/plugins/agentspec"
    assert command[command.index("--output-format"):command.index("--output-format") + 2] == [
        "--output-format",
        "stream-json",
    ]
    assert command[command.index("--input-format"):command.index("--input-format") + 2] == [
        "--input-format",
        "text",
    ]
    assert command[command.index("--setting-sources"):command.index("--setting-sources") + 2] == [
        "--setting-sources",
        "project",
    ]
    assert "--dangerously-skip-permissions" not in command


def test_build_command_preapproves_identical_tool_set(tmp_path: Path):
    command = build_command(config(tmp_path))
    allowed = command[command.index("--allowedTools") + 1]
    assert allowed == ",".join(ALLOWED_TOOLS)
    assert "Bash" in ALLOWED_TOOLS and "Task" in ALLOWED_TOOLS


def test_resume_keeps_plugin_and_uses_session_id(tmp_path: Path):
    command = build_command(config(tmp_path), "session-123")
    assert command[-2:] == ["--resume", "session-123"]
    assert command.count("--plugin-dir") == 1


def test_malformed_json_is_retained_as_error():
    events, malformed = _parse_events('{"type":"system"}\nnot-json\n')
    assert events == [{"type": "system"}]
    assert malformed == ["not-json"]


def _fake_result(stdout: str, returncode: int = 0):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=returncode,
                                           stdout=stdout, stderr="")
    return fake_run


def test_run_records_nonzero_exit_and_appends_turns(tmp_path: Path, monkeypatch):
    prompt = tmp_path / "brief.md"
    prompt.write_text("hello")
    cfg = RunConfig(
        framework="agentspec", workdir=tmp_path, plugin=Path("/plugins/agentspec"),
        prompt=prompt, model="sonnet", effort="high", budget_usd=30.0,
    )
    output = tmp_path / "runs"
    result_line = json.dumps({
        "type": "result", "session_id": "abc", "total_cost_usd": 1.5,
        "usage": {}, "num_turns": 3, "is_error": False,
    })
    monkeypatch.setattr(subprocess, "run", _fake_result(result_line + "\nnot-json\n"))
    assert run(cfg, output) == 0
    monkeypatch.setattr(subprocess, "run", _fake_result("", returncode=7))
    assert run(cfg, output, session_id="abc") == 7

    turn1 = json.loads((output / "turn-01" / "metadata.json").read_text())
    turn2 = json.loads((output / "turn-02" / "metadata.json").read_text())
    assert turn1["session_id"] == "abc"
    assert turn1["malformed_lines"] == 1
    assert (output / "turn-01" / "malformed.log").read_text() == "not-json"
    assert turn2["exit_code"] == 7
    assert turn2["is_error"] is True

    session = json.loads((output / "metadata.json").read_text())
    assert [turn["dir"] for turn in session["turns"]] == ["turn-01", "turn-02"]
    assert session["total_cost_usd"] == 1.5
    assert session["session_id"] == "abc"


def test_run_refuses_to_exceed_budget(tmp_path: Path, monkeypatch):
    prompt = tmp_path / "brief.md"
    prompt.write_text("hello")
    cfg = config(tmp_path, budget=1.0)
    cfg = RunConfig(**{**cfg.__dict__, "prompt": prompt})
    output = tmp_path / "runs"
    output.mkdir()
    (output / "metadata.json").write_text(json.dumps(
        {"turns": [], "total_cost_usd": 1.2, "session_id": "abc"}))
    monkeypatch.setattr(subprocess, "run", _fake_result(""))
    with pytest.raises(RuntimeError, match="budget exhausted"):
        run(cfg, output)


def test_run_uses_fresh_persistent_claude_config_dir(tmp_path: Path, monkeypatch):
    prompt = tmp_path / "brief.md"
    prompt.write_text("hello")
    cfg = RunConfig(**{**config(tmp_path).__dict__, "prompt": prompt})
    captured: dict = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout='{"type":"result"}\n', stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    output = tmp_path / "runs"
    assert run(cfg, output) == 0
    assert captured["env"]["CLAUDE_CONFIG_DIR"] == str(
        (output / ".claude-config").resolve()
    )
    assert (output / ".claude-config").is_dir()
