"""Run one-plugin Claude Code sessions and retain auditable event streams.

Isolation model: every session gets a fresh CLAUDE_CONFIG_DIR so no user-level
plugins, skills, hooks, or global CLAUDE.md contaminate the run. Exactly one
--plugin-dir is passed. Both frameworks receive the identical --allowedTools
set; --dangerously-skip-permissions is never used.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal


# Identical for both frameworks. Headless sessions cannot answer permission
# prompts, so the tools a native workflow legitimately needs are pre-approved.
ALLOWED_TOOLS = (
    "Bash",
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "Glob",
    "Grep",
    "TodoWrite",
    "Task",
    "Skill",
    "SlashCommand",
    "AskUserQuestion",
    "WebFetch",
    "WebSearch",
)


@dataclass(frozen=True)
class RunConfig:
    framework: Literal["agentspec", "superpowers"]
    workdir: Path
    plugin: Path
    prompt: Path
    model: str
    effort: str
    budget_usd: float


def build_command(config: RunConfig, session_id: str | None = None) -> list[str]:
    command = [
        "claude",
        "-p",
        "--input-format",
        "text",
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-hook-events",
        "--permission-mode",
        "acceptEdits",
        "--model",
        config.model,
        "--effort",
        config.effort,
        "--max-budget-usd",
        str(config.budget_usd),
        "--setting-sources",
        "project",
        "--allowedTools",
        ",".join(ALLOWED_TOOLS),
        "--plugin-dir",
        str(config.plugin),
    ]
    if session_id:
        command.extend(["--resume", session_id])
    return command


def _parse_events(raw: str) -> tuple[list[dict], list[str]]:
    events: list[dict] = []
    malformed: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            malformed.append(line)
            continue
        if isinstance(event, dict):
            events.append(event)
        else:
            malformed.append(line)
    return events, malformed


def _next_turn_dir(output_dir: Path) -> Path:
    existing = sorted(output_dir.glob("turn-*"))
    return output_dir / f"turn-{len(existing) + 1:02d}"


def _load_session_metadata(output_dir: Path) -> dict:
    path = output_dir / "metadata.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"turns": [], "total_cost_usd": 0.0, "session_id": None}


def run(
    config: RunConfig,
    output_dir: Path,
    session_id: str | None = None,
    prompt_text: str | None = None,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    session = _load_session_metadata(output_dir)
    known_cost = session.get("total_cost_usd") or 0.0
    if known_cost >= config.budget_usd:
        raise RuntimeError(
            f"budget exhausted: {known_cost:.2f} USD >= {config.budget_usd:.2f} USD"
        )

    turn_dir = _next_turn_dir(output_dir)
    turn_dir.mkdir(parents=True)
    prompt = prompt_text if prompt_text is not None else config.prompt.read_text()
    (turn_dir / "prompt.md").write_text(prompt)

    started = datetime.now(UTC)
    config_dir = output_dir / ".claude-config"
    config_dir.mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment["CLAUDE_CONFIG_DIR"] = str(config_dir.resolve())
    result = subprocess.run(
        build_command(config, session_id),
        cwd=config.workdir,
        env=environment,
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
    )
    ended = datetime.now(UTC)

    events, malformed = _parse_events(result.stdout)
    (turn_dir / "stdout.log").write_text(result.stdout)
    (turn_dir / "events.jsonl").write_text(result.stdout)
    (turn_dir / "stderr.log").write_text(result.stderr)
    (turn_dir / "malformed.log").write_text("\n".join(malformed))

    result_events = [event for event in events if event.get("type") == "result"]
    final = result_events[-1] if result_events else {}
    turn_cost = final.get("total_cost_usd")
    turn_metadata = {
        "config": {**asdict(config), "workdir": str(config.workdir),
                   "plugin": str(config.plugin), "prompt": str(config.prompt)},
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_seconds": (ended - started).total_seconds(),
        "exit_code": result.returncode,
        "session_id": final.get("session_id", session_id),
        "cost_usd": turn_cost if turn_cost is not None else "unavailable",
        "usage": final.get("usage", "unavailable"),
        "num_turns": final.get("num_turns", "unavailable"),
        "is_error": final.get("is_error", result.returncode != 0),
        "malformed_lines": len(malformed),
    }
    (turn_dir / "metadata.json").write_text(
        json.dumps(turn_metadata, indent=2, default=str) + "\n"
    )

    session["turns"].append(
        {
            "dir": turn_dir.name,
            "exit_code": result.returncode,
            "cost_usd": turn_metadata["cost_usd"],
            "duration_seconds": turn_metadata["duration_seconds"],
        }
    )
    if isinstance(turn_cost, (int, float)):
        session["total_cost_usd"] = known_cost + turn_cost
    if turn_metadata["session_id"]:
        session["session_id"] = turn_metadata["session_id"]
    session["framework"] = config.framework
    session["budget_usd"] = config.budget_usd
    (output_dir / "metadata.json").write_text(
        json.dumps(session, indent=2, default=str) + "\n"
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework", choices=("agentspec", "superpowers"), required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--plugin", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--budget-usd", type=float, default=30.0)
    parser.add_argument("--resume")
    args = parser.parse_args()
    config = RunConfig(
        framework=args.framework,
        workdir=args.workdir.resolve(),
        plugin=args.plugin.resolve(),
        prompt=args.prompt.resolve(),
        model=args.model,
        effort=args.effort,
        budget_usd=args.budget_usd,
    )
    return run(config, args.output_dir, args.resume)


if __name__ == "__main__":
    raise SystemExit(main())
