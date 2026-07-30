"""Tests for the repo-local Codex adapter generator."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate-codex-adapters.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("codex_adapter_generator", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["codex_adapter_generator"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gen():
    return _load_generator()


def _write_source(path: Path, name: str, description: str = "Example skill.") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# Canonical body\n",
        encoding="utf-8",
    )


def test_real_inventory_has_one_adapter_per_skill_and_command(gen):
    adapters = gen.build_expected(REPO_ROOT)
    skill_sources = sorted((REPO_ROOT / ".claude" / "skills").glob("*/SKILL.md"))
    command_sources = sorted(
        path
        for path in (REPO_ROOT / ".claude" / "commands").rglob("*.md")
        if path.name != "README.md"
    )

    assert len(adapters) == len(skill_sources) + len(command_sources)
    assert "sdd-design/SKILL.md" in adapters
    assert "agentspec-design/SKILL.md" in adapters
    assert "agentspec-schema/SKILL.md" in adapters
    assert all(
        len(gen.parse_frontmatter(content)["description"]) <= 1024
        for content in adapters.values()
    )


def test_adapter_has_minimal_frontmatter_and_canonical_reference(gen, tmp_path):
    source = tmp_path / ".claude" / "skills" / "sample" / "SKILL.md"
    _write_source(source, "sample", "Use for sample work.")

    adapters = gen.build_expected(tmp_path)
    rendered = adapters["sample/SKILL.md"]

    frontmatter = rendered.split("---", 2)[1]
    assert set(gen.parse_frontmatter(rendered)) == {"name", "description"}
    assert "name: sample" in frontmatter
    assert ".claude/skills/sample/SKILL.md" in rendered
    assert "read it completely" in rendered
    assert "Canonical body" not in rendered


def test_commands_are_prefixed_and_catalogs_are_excluded(gen, tmp_path):
    _write_source(
        tmp_path / ".claude" / "commands" / "workflow" / "build.md",
        "build",
    )
    _write_source(
        tmp_path / ".claude" / "commands" / "workflow" / "README.md",
        "catalog",
    )

    adapters = gen.build_expected(tmp_path)

    assert set(adapters) == {"agentspec-build/SKILL.md"}


def test_duplicate_output_name_fails_closed(gen, tmp_path):
    _write_source(tmp_path / ".claude" / "skills" / "one" / "SKILL.md", "duplicate")
    _write_source(tmp_path / ".claude" / "skills" / "two" / "SKILL.md", "duplicate")

    with pytest.raises(gen.GenerationError, match="duplicate"):
        gen.build_expected(tmp_path)


@pytest.mark.parametrize("name", ["Bad_Name", "../escape", "", "white space"])
def test_invalid_skill_name_fails_closed(gen, tmp_path, name):
    _write_source(tmp_path / ".claude" / "skills" / "bad" / "SKILL.md", name)

    with pytest.raises(gen.GenerationError, match="invalid|missing"):
        gen.build_expected(tmp_path)


def test_write_removes_stale_adapter_and_check_detects_drift(gen, tmp_path):
    _write_source(tmp_path / ".claude" / "skills" / "sample" / "SKILL.md", "sample")
    stale = tmp_path / ".agents" / "skills" / "stale" / "SKILL.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale", encoding="utf-8")

    gen.write_adapters(tmp_path, gen.build_expected(tmp_path))

    assert not stale.exists()
    assert gen.find_drift(tmp_path, gen.build_expected(tmp_path)) == []

    generated = tmp_path / ".agents" / "skills" / "sample" / "SKILL.md"
    generated.write_text("edited", encoding="utf-8")
    assert gen.find_drift(tmp_path, gen.build_expected(tmp_path)) == [
        "changed: sample/SKILL.md"
    ]


def test_cli_check_passes_for_committed_tree():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


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
