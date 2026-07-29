"""Tests for the CLI: file/dir linting, exit codes, and JSON Schema emission."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from spec_linter import cli
from spec_linter.verdict import Level


def _write_spec(path: Path, spec: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(spec))
    return path


def test_valid_file_passes_with_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], valid_spec: dict[str, Any]
) -> None:
    spec_file = _write_spec(tmp_path / "agent.yaml", valid_spec)
    assert cli.main([str(spec_file)]) == 0
    assert "VERDICT: PASS" in capsys.readouterr().out


def test_failing_file_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], valid_spec: dict[str, Any]
) -> None:
    valid_spec["observability"] = None
    spec_file = _write_spec(tmp_path / "agent.yaml", valid_spec)
    assert cli.main([str(spec_file)]) == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "L2.maturity_observability" in out


def test_dir_lint_reports_overall_and_exits_one_on_any_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], valid_spec: dict[str, Any]
) -> None:
    _write_spec(tmp_path / "good.yaml", valid_spec)
    failing = {**valid_spec, "id": "another-agent", "publish": True, "security_review": False}
    _write_spec(tmp_path / "bad.yaml", failing)
    assert cli.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "== good.yaml ==" in out
    assert "== bad.yaml ==" in out
    assert "OVERALL: FAIL" in out


def test_duplicate_id_across_dir_is_fail(tmp_path: Path, valid_spec: dict[str, Any]) -> None:
    _write_spec(tmp_path / "a.yaml", valid_spec)
    _write_spec(tmp_path / "b.yaml", valid_spec)  # same id in both files

    verdicts = cli._lint_dir(tmp_path)
    assert set(verdicts) == {"a.yaml", "b.yaml"}
    for name in ("a.yaml", "b.yaml"):
        assert verdicts[name].level == Level.FAIL
        dupes = [f for f in verdicts[name].findings if f.rule == "L4.duplicate_id"]
        assert len(dupes) == 1
        assert "a.yaml" in dupes[0].found and "b.yaml" in dupes[0].found


def test_emit_schema_writes_file_creating_parent_dirs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_path = tmp_path / "nested" / "agent_spec.schema.json"
    assert cli.main(["--emit-schema", str(out_path)]) == 0
    schema = json.loads(out_path.read_text())
    assert "output_contract" in schema["properties"]
    assert f"Wrote JSON Schema to {out_path}" in capsys.readouterr().out


def test_missing_file_is_error_exit_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "does_not_exist.yaml"
    assert cli.main([str(missing)]) == 2
    assert "ERROR:" in capsys.readouterr().err


def test_malformed_yaml_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "broken.yaml"
    bad.write_text("id: [unterminated\n")
    assert cli.main([str(bad)]) == 2
    assert "ERROR:" in capsys.readouterr().err


def test_non_mapping_yaml_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("just a string\n")
    assert cli.main([str(scalar)]) == 2
    assert "ERROR:" in capsys.readouterr().err


def test_error_exit_two_is_distinct_from_fail_exit_one(
    tmp_path: Path, valid_spec: dict[str, Any]
) -> None:
    valid_spec["observability"] = None  # loadable mapping, contract FAIL -> exit 1
    fail_file = _write_spec(tmp_path / "fail.yaml", valid_spec)
    assert cli.main([str(fail_file)]) == 1
    assert cli.main([str(tmp_path / "nope.yaml")]) == 2  # operational ERROR -> exit 2


def _write_phase_doc(path: Path, headings: list[str]) -> Path:
    path.write_text("\n\n".join(f"## {h}" for h in headings) + "\n")
    return path


def test_phase_doc_passes_with_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(
        yaml.safe_dump({"define": {"required_sections": ["Problem Statement", "Goals"]}})
    )
    doc = _write_phase_doc(tmp_path / "DEFINE_X.md", ["Problem Statement", "Goals"])
    code = cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)])
    assert code == 0
    assert "VERDICT: PASS" in capsys.readouterr().out


def test_phase_doc_missing_section_fails_with_exit_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(
        yaml.safe_dump({"define": {"required_sections": ["Problem Statement", "Goals"]}})
    )
    doc = _write_phase_doc(tmp_path / "DEFINE_X.md", ["Problem Statement"])
    code = cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)])
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "L2.required_section" in out


def test_phase_unknown_phase_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump({"define": {"required_sections": ["Problem Statement"]}}))
    doc = _write_phase_doc(tmp_path / "DOC.md", ["Problem Statement"])
    code = cli.main([str(doc), "--phase", "nonexistent", "--contracts-file", str(contracts)])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err


def test_default_contracts_file_prefers_repo_layout(tmp_path: Path) -> None:
    repo_file = tmp_path / ".claude" / "sdd" / "architecture" / "WORKFLOW_CONTRACTS.yaml"
    repo_file.parent.mkdir(parents=True)
    repo_file.write_text("{}")
    assert cli._resolve_default_contracts_file(tmp_path) == repo_file


def test_default_contracts_file_falls_back_to_plugin_layout(tmp_path: Path) -> None:
    # No .claude/ prefix — this is the installed-plugin layout (the fixed bug).
    plugin_file = tmp_path / "sdd" / "architecture" / "WORKFLOW_CONTRACTS.yaml"
    plugin_file.parent.mkdir(parents=True)
    plugin_file.write_text("{}")
    assert cli._resolve_default_contracts_file(tmp_path) == plugin_file


# --- --phase build (BuildReportContract) ------------------------------------


def _build_contracts_data() -> dict[str, Any]:
    return {
        "build": {
            "required_sections": [
                "metadata",
                "summary",
                "task_execution_with_agent_attribution",
                "files_created",
                "verification_results",
                "review_verdict",
                "acceptance_test_verification",
                "final_status",
            ],
            "execution": {
                "final_review": {
                    "verdicts": ["clean", "clean-with-minors", "dirty", "missing"],
                    "fix_loop_budget": 2,
                }
            },
            "report_contract": {
                "schema_version": 2,
                "tdd_mode_values": ["off", "opt-in", "required"],
                "legacy": {"manual": "WARN", "autopilot": "FAIL"},
            },
        }
    }


def _write_build_contracts(path: Path) -> Path:
    path.write_text(yaml.safe_dump(_build_contracts_data()))
    return path


def _write_report(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


_VALID_BUILD_REPORT = """\
# BUILD REPORT: CLI_SAMPLE

## Metadata

| Field | Value |
|-------|-------|
| **Schema Version** | 2 |
| **TDD Mode** | off |

## Summary

CLI-level fixture for build-phase contract tests.

## Task Execution with Agent Attribution

| # | Task | Agent | Status |
|---|------|-------|--------|
| 1 | Implement feature | python-pro | ✅ |

## Files Created

- `src/cli_sample.py`

## Verification Results

- `pytest tests/` - 1 passed

## Review Verdict

| Field | Value |
|-------|-------|
| **Verdict** | clean |
| **Fix rounds used** | 0/2 |

## Acceptance Test Verification

| Acceptance Test | Status |
|------------------|--------|
| Sample behaves correctly | ✅ Verified |

## Final Status

### Overall: ✅ COMPLETE
"""


def test_build_phase_valid_v2_report_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_build_contracts(tmp_path / "contracts.yaml")
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _VALID_BUILD_REPORT)
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 0
    assert "VERDICT: PASS" in capsys.readouterr().out


def test_build_phase_dirty_verdict_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_build_contracts(tmp_path / "contracts.yaml")
    dirty = _VALID_BUILD_REPORT.replace("| **Verdict** | clean |", "| **Verdict** | dirty |")
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", dirty)
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "BR.review_verdict_dirty" in out


def test_build_phase_legacy_report_defaults_to_warn_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_build_contracts(tmp_path / "contracts.yaml")
    legacy = _VALID_BUILD_REPORT.replace("| **Schema Version** | 2 |\n", "")
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", legacy)
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 0
    out = capsys.readouterr().out
    assert "VERDICT: WARN" in out
    assert "BR.legacy_report" in out


def test_build_phase_legacy_report_with_legacy_mode_fail_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_build_contracts(tmp_path / "contracts.yaml")
    legacy = _VALID_BUILD_REPORT.replace("| **Schema Version** | 2 |\n", "")
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", legacy)
    code = cli.main(
        [
            str(report),
            "--phase",
            "build",
            "--contracts-file",
            str(contracts),
            "--legacy-mode",
            "fail",
        ]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "BR.legacy_report" in out


def test_build_phase_invalid_legacy_mode_is_argparse_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(
            [
                str(tmp_path / "irrelevant.md"),
                "--phase",
                "build",
                "--legacy-mode",
                "banana",
            ]
        )
    assert exc_info.value.code == 2


def test_build_phase_missing_report_contract_block_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _build_contracts_data()
    del data["build"]["report_contract"]
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _VALID_BUILD_REPORT)
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err
