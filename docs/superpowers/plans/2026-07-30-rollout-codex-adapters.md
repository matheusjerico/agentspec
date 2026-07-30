# Codex Adapters in the Vendored Rollout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `scripts/rollout-agentspec.sh` generate a working `.agents/skills/` Codex adapter tree in every vendored target, without disturbing anything the target owns.

**Architecture:** `scripts/generate-codex-adapters.py` grows a target mode — an arbitrary `--root`, a restricted command scope, skipping of Codex-native skills, and a write mode that preserves entries it did not produce. The rollout script calls it once per target after the `.claude/` sync, and extends backup and rollback to cover `.agents/`.

**Tech Stack:** Python 3 (stdlib only), Bash 3.2 (macOS default), pytest.

## Global Constraints

- Repo-local generator behaviour, including `python3 scripts/generate-codex-adapters.py --check` in `make check`, must stay byte-identical. `tests/test_generate_codex_adapters.py::test_real_inventory_has_one_adapter_per_skill_and_command` is the guard.
- Command sources in target mode are restricted to these six directories, matching `COMMAND_SETS` in `scripts/rollout-agentspec.sh`: `workflow`, `data-engineering`, `core`, `knowledge`, `review`, `visual-explainer`.
- Adapters are generated for skills in `<target>/.claude/skills/*/SKILL.md`, except any whose resolved path lies inside `.agents/`.
- Generation validates every adapter in memory before writing. On any `GenerationError` the target's `.agents/` is left byte-identical, the `.claude/` sync stands, remaining targets still process, and the run exits 1.
- Entries under `<target>/.agents/skills/` the generator did not produce are preserved and reported.
- A target with no `.claude/` is skipped and gets no `.agents/`.
- This repository is public. No target names, absolute user paths, or third-party repo names in any committed file.
- Bash must stay `set -euo pipefail`-safe and shellcheck-clean per `.shellcheckrc`.
- Run pytest as `rtk proxy python3 -m pytest` — the rtk hook breaks direct invocations.

---

### Task 1: Generator target scope — `--root`, command sets, Codex-native skip

**Files:**
- Modify: `scripts/generate-codex-adapters.py:58-70` (`_canonical_sources`), `:110-137` (`build_expected`), `:187-219` (`main`)
- Test: `tests/test_generate_codex_adapters.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `_is_within(path: Path, root: Path) -> bool`
  - `_canonical_sources(repo_root: Path, command_sets: list[str] | None = None) -> list[tuple[Path, bool]]`
  - `build_expected(repo_root: Path, command_sets: list[str] | None = None) -> dict[str, str]`
  - CLI flags `--root PATH` and `--command-sets a,b,c`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate_codex_adapters.py`:

```python
def test_command_sets_restrict_command_sources(gen, tmp_path):
    _write_source(tmp_path / ".claude" / "commands" / "workflow" / "build.md", "build")
    _write_source(tmp_path / ".claude" / "commands" / "vendor" / "apply.md", "apply")

    adapters = gen.build_expected(tmp_path, command_sets=["workflow"])

    assert set(adapters) == {"agentspec-build/SKILL.md"}


def test_command_sets_none_keeps_every_command_directory(gen, tmp_path):
    _write_source(tmp_path / ".claude" / "commands" / "workflow" / "build.md", "build")
    _write_source(tmp_path / ".claude" / "commands" / "vendor" / "apply.md", "apply")

    adapters = gen.build_expected(tmp_path)

    assert set(adapters) == {"agentspec-build/SKILL.md", "agentspec-apply/SKILL.md"}


def test_loose_command_files_produce_no_adapters(gen, tmp_path):
    _write_source(tmp_path / ".claude" / "commands" / "workflow" / "build.md", "build")
    _write_source(tmp_path / ".claude" / "commands" / "loose.md", "loose")

    adapters = gen.build_expected(tmp_path, command_sets=["workflow"])

    assert set(adapters) == {"agentspec-build/SKILL.md"}


def test_missing_command_set_directory_is_not_an_error(gen, tmp_path):
    _write_source(tmp_path / ".claude" / "skills" / "sample" / "SKILL.md", "sample")

    adapters = gen.build_expected(tmp_path, command_sets=["workflow", "review"])

    assert set(adapters) == {"sample/SKILL.md"}


def test_skill_resolving_into_agents_is_skipped_as_codex_native(gen, tmp_path):
    native = tmp_path / ".agents" / "skills" / "native"
    _write_source(native / "SKILL.md", "native")
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "native").symlink_to(
        native, target_is_directory=True
    )
    _write_source(tmp_path / ".claude" / "skills" / "regular" / "SKILL.md", "regular")

    adapters = gen.build_expected(tmp_path)

    assert set(adapters) == {"regular/SKILL.md"}


def test_cli_root_generates_against_another_tree(tmp_path):
    _write_source(tmp_path / ".claude" / "skills" / "sample" / "SKILL.md", "sample")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--root",
            str(tmp_path),
            "--command-sets",
            "workflow,review",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / ".agents" / "skills" / "sample" / "SKILL.md").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `rtk proxy python3 -m pytest tests/test_generate_codex_adapters.py -q`
Expected: FAIL — `build_expected() got an unexpected keyword argument 'command_sets'`, and the CLI test fails on `unrecognized arguments: --root`.

- [ ] **Step 3: Implement the scoped source selection**

Replace `_canonical_sources` in `scripts/generate-codex-adapters.py` with:

```python
def _is_within(path: Path, root: Path) -> bool:
    """Return True when path is root itself or lies beneath it."""
    return path == root or root in path.parents


def _canonical_sources(
    repo_root: Path, command_sets: list[str] | None = None
) -> list[tuple[Path, bool]]:
    skill_root = repo_root / ".claude" / "skills"
    command_root = repo_root / ".claude" / "commands"
    agents_root = (repo_root / ".agents").resolve()

    skills: list[tuple[Path, bool]] = []
    for path in sorted(skill_root.glob("*/SKILL.md")):
        if _is_within(path.resolve(), agents_root):
            continue
        skills.append((path, False))

    if command_sets is None:
        command_paths = sorted(command_root.rglob("*.md"))
    else:
        command_paths = sorted(
            path
            for command_set in command_sets
            for path in (command_root / command_set).rglob("*.md")
        )
    commands = [(path, True) for path in command_paths if path.name != "README.md"]

    sources = skills + commands
    if not sources:
        raise GenerationError("canonical source inventory is empty")
    return sources
```

Change the `build_expected` signature and its single call site:

```python
def build_expected(
    repo_root: Path, command_sets: list[str] | None = None
) -> dict[str, str]:
    """Return relative adapter paths and their deterministic contents."""
    repo_root = repo_root.resolve()
    expected: dict[str, str] = {}
    owners: dict[str, Path] = {}
    for source, is_command in _canonical_sources(repo_root, command_sets):
```

- [ ] **Step 4: Add the CLI flags**

In `main`, add the arguments and thread them through:

```python
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root to generate against (default: this repository)",
    )
    parser.add_argument(
        "--command-sets",
        default=None,
        help="comma-separated command directories to include (default: all)",
    )
    args = parser.parse_args(argv)
    repo_root = args.root if args.root is not None else Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()
    command_sets = (
        [item for item in args.command_sets.split(",") if item]
        if args.command_sets is not None
        else None
    )
```

Then replace both `build_expected(repo_root)` calls in `main` with `build_expected(repo_root, command_sets)`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `rtk proxy python3 -m pytest tests/test_generate_codex_adapters.py -q`
Expected: PASS, including the pre-existing `test_real_inventory_has_one_adapter_per_skill_and_command` and `test_cli_check_passes_for_committed_tree`.

- [ ] **Step 6: Verify repo-local generation is unchanged**

Run: `python3 scripts/generate-codex-adapters.py --check`
Expected: `Codex adapters are current (54 files).` and exit 0.

- [ ] **Step 7: Commit**

```bash
git add scripts/generate-codex-adapters.py tests/test_generate_codex_adapters.py
git commit -m "feat(codex): scope adapter generation to a root and command sets

Target trees hold command directories authored for Claude's slash-command
surface, whose name field is a human-readable title rather than a skill
slug. Feeding those to the generator aborts the whole target, so target
mode restricts commands to AgentSpec-owned sets.

Skills resolving inside .agents/ are Codex-native already; generating an
adapter for one would overwrite the skill it came from.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Generator write mode — preserve unknown entries, replace symlinks, `--plan`

**Files:**
- Modify: `scripts/generate-codex-adapters.py:166-184` (`write_adapters`), `:187-219` (`main`)
- Test: `tests/test_generate_codex_adapters.py`

**Interfaces:**
- Consumes: `build_expected(repo_root, command_sets)` from Task 1.
- Produces:
  - `preserved_entries(repo_root: Path, expected: dict[str, str]) -> list[str]`
  - `write_adapters(repo_root: Path, expected: dict[str, str], preserve_unknown: bool = False) -> None`
  - CLI flags `--preserve-unknown` and `--plan`
  - stdout contract consumed by Task 3: one `generated N adapters` or `would generate N adapters` line, optionally followed by one `preserved: a b c` line.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_generate_codex_adapters.py`:

```python
def test_preserve_unknown_keeps_entries_the_generator_did_not_produce(gen, tmp_path):
    _write_source(tmp_path / ".claude" / "skills" / "sample" / "SKILL.md", "sample")
    native = tmp_path / ".agents" / "skills" / "native" / "SKILL.md"
    native.parent.mkdir(parents=True)
    native.write_text("codex-native", encoding="utf-8")

    expected = gen.build_expected(tmp_path)
    assert gen.preserved_entries(tmp_path, expected) == ["native"]
    gen.write_adapters(tmp_path, expected, preserve_unknown=True)

    assert native.read_text(encoding="utf-8") == "codex-native"
    assert (tmp_path / ".agents" / "skills" / "sample" / "SKILL.md").exists()


def test_preserve_unknown_still_replaces_a_generated_name(gen, tmp_path):
    _write_source(tmp_path / ".claude" / "skills" / "sample" / "SKILL.md", "sample")
    stale = tmp_path / ".agents" / "skills" / "sample" / "SKILL.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("hand-written", encoding="utf-8")

    gen.write_adapters(tmp_path, gen.build_expected(tmp_path), preserve_unknown=True)

    assert "hand-written" not in stale.read_text(encoding="utf-8")
    assert "Generated AgentSpec adapter" in stale.read_text(encoding="utf-8")


def test_symlinked_output_root_is_replaced_by_a_real_directory(gen, tmp_path):
    _write_source(tmp_path / ".claude" / "skills" / "sample" / "SKILL.md", "sample")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "skills").symlink_to(elsewhere, target_is_directory=True)

    gen.write_adapters(tmp_path, gen.build_expected(tmp_path), preserve_unknown=True)

    output_root = tmp_path / ".agents" / "skills"
    assert output_root.is_dir() and not output_root.is_symlink()
    assert (output_root / "sample" / "SKILL.md").exists()
    assert elsewhere.is_dir()


def test_malformed_source_leaves_the_tree_byte_identical(gen, tmp_path):
    _write_source(tmp_path / ".claude" / "skills" / "good" / "SKILL.md", "good")
    (tmp_path / ".claude" / "skills" / "bad").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "bad" / "SKILL.md").write_text(
        "---\nname: bad\n---\n", encoding="utf-8"
    )
    existing = tmp_path / ".agents" / "skills" / "existing" / "SKILL.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("untouched", encoding="utf-8")

    with pytest.raises(gen.GenerationError, match="missing description"):
        gen.build_expected(tmp_path)

    assert existing.read_text(encoding="utf-8") == "untouched"
    assert not (tmp_path / ".agents" / "skills" / "good").exists()
    assert list((tmp_path / ".agents" / "skills").iterdir()) == [existing.parent]


def test_cli_plan_reports_without_writing(tmp_path):
    _write_source(tmp_path / ".claude" / "skills" / "sample" / "SKILL.md", "sample")
    native = tmp_path / ".agents" / "skills" / "native" / "SKILL.md"
    native.parent.mkdir(parents=True)
    native.write_text("codex-native", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--root",
            str(tmp_path),
            "--preserve-unknown",
            "--plan",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "would generate 1 adapters" in result.stdout
    assert "preserved: native" in result.stdout
    assert not (tmp_path / ".agents" / "skills" / "sample").exists()


def test_cli_reports_error_to_stderr_with_exit_2(tmp_path):
    (tmp_path / ".claude" / "skills" / "bad").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "bad" / "SKILL.md").write_text(
        "---\nname: bad\n---\n", encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--root", str(tmp_path), "--plan"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "missing description" in result.stderr
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `rtk proxy python3 -m pytest tests/test_generate_codex_adapters.py -q`
Expected: FAIL — `module has no attribute 'preserved_entries'` and `unrecognized arguments: --preserve-unknown`.

- [ ] **Step 3: Implement preservation and the symlink-safe replace**

Replace `write_adapters` in `scripts/generate-codex-adapters.py` with:

```python
def preserved_entries(repo_root: Path, expected: dict[str, str]) -> list[str]:
    """Return top-level entries under the output root the generator does not own."""
    output_root = repo_root / ".agents" / "skills"
    if output_root.is_symlink() or not output_root.is_dir():
        return []
    generated = {Path(relative).parts[0] for relative in expected}
    return sorted(
        entry.name for entry in output_root.iterdir() if entry.name not in generated
    )


def write_adapters(
    repo_root: Path, expected: dict[str, str], preserve_unknown: bool = False
) -> None:
    """Replace the generated skills tree only after all output is validated."""
    agents_root = repo_root / ".agents"
    agents_root.mkdir(parents=True, exist_ok=True)
    output_root = agents_root / "skills"
    temporary = Path(tempfile.mkdtemp(prefix="skills.", dir=agents_root))
    try:
        if preserve_unknown:
            for name in preserved_entries(repo_root, expected):
                source = output_root / name
                destination = temporary / name
                if source.is_dir() and not source.is_symlink():
                    shutil.copytree(source, destination, symlinks=True)
                else:
                    shutil.copy2(source, destination, follow_symlinks=False)

        for relative_path, content in expected.items():
            destination = temporary / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")

        if output_root.is_symlink() or output_root.is_file():
            output_root.unlink()
        elif output_root.exists():
            shutil.rmtree(output_root)
        temporary.replace(output_root)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
```

- [ ] **Step 4: Add the `--preserve-unknown` and `--plan` flags**

In `main`, add the arguments alongside those from Task 1:

```python
    parser.add_argument(
        "--preserve-unknown",
        action="store_true",
        help="keep entries under .agents/skills/ the generator did not produce",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="report what would be generated without writing",
    )
```

Replace the write branch of `main` (everything after the `--check` branch) with:

```python
        preserved = (
            preserved_entries(repo_root, expected) if args.preserve_unknown else []
        )
        if args.plan:
            print(f"would generate {len(expected)} adapters")
        else:
            write_adapters(repo_root, expected, args.preserve_unknown)
            print(f"generated {len(expected)} adapters")
        if preserved:
            print(f"preserved: {' '.join(preserved)}")
        return 0
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `rtk proxy python3 -m pytest tests/test_generate_codex_adapters.py -q`
Expected: PASS — all tests, old and new.

- [ ] **Step 6: Verify repo-local generation is still unchanged**

Run: `python3 scripts/generate-codex-adapters.py --check`
Expected: `Codex adapters are current (54 files).` and exit 0.

- [ ] **Step 7: Commit**

```bash
git add scripts/generate-codex-adapters.py tests/test_generate_codex_adapters.py
git commit -m "feat(codex): preserve unrecognised entries under the output root

A target can host genuine Codex skills under .agents/skills/ and expose
them to Claude by symlinking .claude/skills/<name> into that directory.
Wholesale replacement would delete them and orphan the inbound symlink.

Adds --plan so a caller can report the outcome without writing, and
replaces a symlinked output root with a real directory so adapters and
preserved entries can coexist.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Rollout generates adapters per target

**Files:**
- Modify: `scripts/rollout-agentspec.sh` — header block `:9-52`, new function before `sync_target`, call site inside `sync_target` after the KB index merge
- Test: `tests/test_rollout_codex_adapters.py` (create)

**Interfaces:**
- Consumes: the generator CLI from Tasks 1 and 2 — `--root`, `--command-sets`, `--preserve-unknown`, `--plan`; exit 0 on success, 2 on `GenerationError`; stdout lines `generated N adapters` / `would generate N adapters` / `preserved: ...`.
- Produces: `sync_codex_adapters(target)`, emitting `    adapters: <line>` for each generator stdout line, or `    adapters: FAILED — <reason>` and one increment of `FAILURES`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_rollout_codex_adapters.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `rtk proxy python3 -m pytest tests/test_rollout_codex_adapters.py -q`
Expected: FAIL — no `adapters:` line appears in stdout and no `.agents/` is created.

- [ ] **Step 3: Add the generation step to the rollout script**

Insert this function in `scripts/rollout-agentspec.sh` immediately before `sync_target` (after `backup_target`):

```bash
sync_codex_adapters() {
    local target="$1"
    local sets out rc line
    sets="$(IFS=,; printf '%s' "${COMMAND_SETS[*]}")"

    local args=(--root "$target" --command-sets "$sets" --preserve-unknown)
    [[ "$MODE" == "dry-run" ]] && args+=(--plan)

    rc=0
    out="$(python3 "${SOURCE_DIR}/scripts/generate-codex-adapters.py" "${args[@]}" 2>&1)" || rc=$?

    if [[ "$rc" -ne 0 ]]; then
        log "    adapters: FAILED — ${out#error: }"
        FAILURES=$((FAILURES + 1))
        return 0
    fi
    while IFS= read -r line; do
        [[ -n "$line" ]] && log "    adapters: ${line}"
    done <<< "$out"
    return 0
}
```

- [ ] **Step 4: Call it from `sync_target`**

In `sync_target`, immediately after the KB index merge block and before `report_preserved "$tc"`, add:

```bash
    sync_codex_adapters "$target"
```

- [ ] **Step 5: Document the new managed path in the header**

In the header comment block, extend the REPLACED section (currently ending at the `scripts/judge.py  scripts/autopilot.sh` line) with:

```bash
#     .agents/skills/<adapter per target skill and AgentSpec command>
#
#   GENERATED:
#     .agents/skills/ — Codex adapters derived from the target's own post-sync
#     .claude/ tree. Entries the generator does not produce (Codex-native
#     skills) are preserved. A validation failure leaves .agents/ untouched,
#     reports the offending source, and marks the run partial.
#     Dry-run counts reflect the target's current tree; a validation error
#     predicted there is authoritative, because payload components are
#     validated by `make check`.
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `rtk proxy python3 -m pytest tests/test_rollout_codex_adapters.py -q`
Expected: PASS — all six tests.

- [ ] **Step 7: Verify the script still lints**

Run: `make lint`
Expected: shellcheck reports no findings for `scripts/rollout-agentspec.sh`.

- [ ] **Step 8: Commit**

```bash
git add scripts/rollout-agentspec.sh tests/test_rollout_codex_adapters.py
git commit -m "feat(rollout): generate Codex adapters in each vendored target

The rollout synced .claude/ only, so vendored installs never received the
adapter tree that makes AgentSpec discoverable by Codex. Adapters are now
generated from each target's own post-sync .claude/, covering payload and
target-local skills alike.

A target whose local component fails validation keeps its .claude/ upgrade
and its existing .agents/, is reported, and marks the run partial.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Backup and rollback cover `.agents/`

**Files:**
- Modify: `scripts/rollout-agentspec.sh:282-288` (`backup_target`), `:421-437` (`rollback_target`), header lines `:44` and `:51`
- Test: `tests/test_rollout_codex_adapters.py`

**Interfaces:**
- Consumes: `sync_codex_adapters` from Task 3.
- Produces: backups at `<BACKUP_ROOT>/<stamp>/<name>/.claude` and `<BACKUP_ROOT>/<stamp>/<name>/.agents`; rollback restoring whichever of the two the stamp contains.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rollout_codex_adapters.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `rtk proxy python3 -m pytest tests/test_rollout_codex_adapters.py -q -k "backup or rollback"`
Expected: FAIL — the backup contains no `.agents`, and rollback leaves the generated adapters in place.

- [ ] **Step 3: Extend `backup_target`**

Replace `backup_target` with:

```bash
backup_target() {
    local target="$1" name="$2"
    local dest="${BACKUP_ROOT}/${STAMP}/${name}"
    mkdir -p "$dest"
    cp -R "${target}/.claude" "${dest}/.claude"
    log "    backup: ${dest}/.claude"
    if [[ -e "${target}/.agents" ]]; then
        cp -R "${target}/.agents" "${dest}/.agents"
        log "    backup: ${dest}/.agents"
    fi
}
```

- [ ] **Step 4: Extend `rollback_target`**

Replace `rollback_target` with:

```bash
rollback_target() {
    local target="$1"
    local name src restored
    name="$(basename "$target")"
    src="${BACKUP_ROOT}/${STAMP}/${name}"

    log ""
    info "Rollback: ${target} from ${src}"
    if [[ ! -d "${src}/.claude" && ! -d "${src}/.agents" ]]; then
        warn "no backup for ${name} at stamp ${STAMP} — skipping"
        FAILURES=$((FAILURES + 1))
        return 0
    fi

    restored=""
    local part
    for part in .claude .agents; do
        [[ -d "${src}/${part}" ]] || continue
        rm -rf "${target:?}/${part}"
        cp -R "${src}/${part}" "${target}/${part}"
        restored="${restored} ${part}"
    done
    log "    restored:${restored}"
    return 0
}
```

- [ ] **Step 5: Update the header documentation**

Change the `--rollback` option line and the Backups line in the header block:

```bash
#   --rollback       Restore each target's .claude and .agents from --stamp
```

```bash
# Backups: ~/.agentspec-rollout-backups/<stamp>/<target-name>/{.claude,.agents}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `rtk proxy python3 -m pytest tests/test_rollout_codex_adapters.py -q`
Expected: PASS — all eight tests.

- [ ] **Step 7: Run lint**

Run: `make lint`
Expected: shellcheck reports no findings for `scripts/rollout-agentspec.sh`.

- [ ] **Step 8: Commit**

```bash
git add scripts/rollout-agentspec.sh tests/test_rollout_codex_adapters.py
git commit -m "feat(rollout): back up and roll back .agents alongside .claude

A rollout now writes into .agents/, so a stamp that captures only .claude
can no longer undo a run. Rollback restores whichever paths the stamp
holds, keeping stamps taken before this change usable.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Skill documentation and end-to-end verification

**Files:**
- Modify: `.claude/skills/rollout-agentspec/SKILL.md`
- Verify: whole suite plus a real dry-run against the configured targets

**Interfaces:**
- Consumes: the finished behaviour from Tasks 1-4.
- Produces: no code; the operator-facing description of the new plan lines.

- [ ] **Step 1: Document the adapter lines in the skill**

In `.claude/skills/rollout-agentspec/SKILL.md`, under "Reading the plan", add two bullets after the existing `WARNING: no .claude directory` bullet:

```markdown
- `adapters: would generate N adapters` / `generated N adapters` — the Codex
  adapter tree written to `<target>/.agents/skills/`, derived from that target's
  own post-sync `.claude/`. Dry-run counts reflect the target's current tree.
- `adapters: FAILED — <source>: <reason>` — a component in that target could not
  produce a valid adapter. Its `.claude/` upgrade stands and its `.agents/` is
  untouched; the run exits 1. Fix the reported source and rerun.
```

In the opening paragraph, replace "replaces AgentSpec-owned paths with a scoped
delete-then-copy and preserves everything target-owned" with:

```markdown
replaces AgentSpec-owned paths with a scoped delete-then-copy, regenerates the
Codex adapter tree under `.agents/skills/`, and preserves everything
target-owned
```

- [ ] **Step 2: Run the full blocking suite**

Run: `make check`
Expected: PASS — root, spec-linter and spec-judge suites, plus both generators in `--check` mode reporting no drift.

- [ ] **Step 3: Confirm the public-repo sanitization gate**

This repository is public and target names are machine-specific, so the gate
derives its search terms from the gitignored targets file rather than naming
anything in a committed file:

```bash
terms="$(sed 's/#.*//' .agentspec-rollout-targets \
  | awk -F/ 'NF && $NF != "" {print $NF}' \
  | paste -sd'|' -)"
git diff main --name-only \
  | xargs grep -niE "${terms}|/Users/|\\\$HOME/" \
  || echo "clean"
```

Expected: `clean`.

- [ ] **Step 4: Dry-run against the real targets**

Run: `make build && scripts/rollout-agentspec.sh`
Expected: exit 0, and every target shows an `adapters: would generate N adapters` line with no `FAILED`. One target additionally shows `preserved:` naming its Codex-native skills.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/rollout-agentspec/SKILL.md
git commit -m "docs(rollout): describe the adapter lines in the rollout plan

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Verification

The feature is done when, from a clean tree on this branch:

1. `make check` passes.
2. `scripts/rollout-agentspec.sh` exits 0 and reports an `adapters:` line for every target.
3. `scripts/rollout-agentspec.sh --apply` produces, in each target, an adapter for every skill in that target's `.claude/skills/` and every command in the six AgentSpec sets, and no adapter for target-local command directories.
4. Codex-native skills under `.agents/skills/` and the `.claude/skills/` symlinks pointing into them are unchanged after an apply.
5. `scripts/rollout-agentspec.sh --rollback --stamp <stamp>` returns both `.claude/` and `.agents/` to their pre-run state.
