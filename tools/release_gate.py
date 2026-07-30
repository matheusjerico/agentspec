"""Fail-closed production release evidence validator."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

_FENCE = re.compile(r"```ya?ml\s*\n(?P<body>.*?)\n```", re.DOTALL | re.IGNORECASE)
_SHA = re.compile(r"^[0-9a-f]{40}$")
_SCORE_FLOORS = {
    "correctness": 100,
    "requirements_planning": 95,
    "tests": 95,
    "code_quality": 94,
    "review_pr": 100,
    "efficiency": 80,
}
_MAX_DURATION_SECONDS = 3826.5
_EVIDENCE_ONLY_PATHS = (
    ".claude/sdd/reports/PR_READY_",
    "docs/superpowers/reports/",
    "benchmark/taskflow/runs/",
)


class ReleaseEvidenceError(ValueError):
    pass


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseEvidenceError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _load_report(path: Path) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for match in _FENCE.finditer(path.read_text(encoding="utf-8")):
        value = yaml.safe_load(match.group("body"))
        if isinstance(value, dict) and "production_readiness" in value:
            matches.append(value)
    if len(matches) != 1:
        raise ReleaseEvidenceError(
            "report must contain exactly one YAML block rooted at production_readiness"
        )
    root = matches[0]["production_readiness"]
    if not isinstance(root, dict):
        raise ReleaseEvidenceError("production_readiness must be a mapping")
    return root


def _load_pr_ready(path: Path) -> dict[str, Any]:
    roots: list[dict[str, Any]] = []
    for match in _FENCE.finditer(path.read_text(encoding="utf-8")):
        value = yaml.safe_load(match.group("body"))
        if isinstance(value, dict) and isinstance(value.get("pr_ready"), dict):
            roots.append(value["pr_ready"])
    if len(roots) != 1:
        raise ReleaseEvidenceError(f"{path} must contain exactly one pr_ready block")
    return roots[0]


def _run_release_commands(repo: Path) -> None:
    for command in (["make", "check"], ["./build-plugin.sh", "--release"]):
        result = subprocess.run(
            command, cwd=repo, text=True, capture_output=True, check=False
        )
        if result.returncode != 0:
            raise ReleaseEvidenceError(
                f"release verification command failed: {' '.join(command)}\n"
                f"{result.stdout}\n{result.stderr}".strip()
            )


def _is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=repo,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def _commit_changed_paths(repo: Path, commit: str) -> set[str]:
    parents = _git(repo, "rev-list", "--parents", "-n", "1", commit).split()
    if len(parents) > 2:
        # A normal merge contains both parent trees but introduces no new
        # changes of its own. --remerge-diff exposes only manual/conflict
        # resolutions, which must still satisfy the evidence-only policy.
        output = _git(
            repo,
            "show",
            "--remerge-diff",
            "--format=",
            "--name-only",
            commit,
        )
    else:
        output = _git(
            repo,
            "diff-tree",
            "--root",
            "--no-commit-id",
            "--name-only",
            "-r",
            commit,
        )
    return {path for path in output.splitlines() if path}


def _verify_release_binding(
    repo: Path, source_commit: str, target_tip: str
) -> None:
    if _is_ancestor(repo, target_tip, "HEAD"):
        commits = _git(
            repo,
            "rev-list",
            f"{source_commit}..HEAD",
            f"^{target_tip}",
        ).splitlines()
        changed = sorted(
            {
                path
                for commit in commits
                for path in _commit_changed_paths(repo, commit)
            }
        )
    else:
        # Before merge, the authorized target is a sibling of the release
        # branch. Preserve the original binding check on the release branch.
        changed = _git(repo, "diff", "--name-only", source_commit, "HEAD").splitlines()
    disallowed = [
        path
        for path in changed
        if not any(path.startswith(prefix) for prefix in _EVIDENCE_ONLY_PATHS)
    ]
    if disallowed:
        raise ReleaseEvidenceError(
            "release_source_commit is followed by non-evidence changes: "
            + ", ".join(disallowed)
        )


def _verify_live_target(
    repo: Path,
    *,
    frozen_tip: str,
    live_tip: str,
    source_commit: str,
) -> None:
    if live_tip == frozen_tip:
        return
    head = _git(repo, "rev-parse", "HEAD")
    if (
        live_tip != head
        or not _is_ancestor(repo, frozen_tip, live_tip)
        or not _is_ancestor(repo, source_commit, live_tip)
    ):
        raise ReleaseEvidenceError("target tip changed")


def _bound_path(
    repo: Path, raw: Any, *, kind: str, require_tracked: bool
) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise ReleaseEvidenceError(f"{kind} path must be repository-relative")
    lexical = repo / raw
    current = repo
    for part in Path(raw).parts:
        current = current / part
        if current.is_symlink():
            raise ReleaseEvidenceError(f"{kind} path must not contain symlinks")
    candidate = lexical.resolve()
    try:
        candidate.relative_to(repo.resolve())
    except ValueError as exc:
        raise ReleaseEvidenceError(f"{kind} path escapes the repository") from exc
    if require_tracked:
        tracked = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", raw],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        if tracked.returncode != 0 or not tracked.stdout.strip():
            raise ReleaseEvidenceError(f"{kind} path is not bound to the HEAD tree")
    return candidate


def _require_exact_keys(value: dict[str, Any], expected: set[str], field: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ReleaseEvidenceError(
            f"{field} keys mismatch: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def validate_release_evidence(
    path: Path,
    repo: Path,
    *,
    execute_commands: bool = False,
    authorized_target: str = "main",
) -> None:
    report_path = path if path.is_absolute() else repo / path
    if execute_commands:
        try:
            report_relative = str(report_path.resolve().relative_to(repo.resolve()))
        except ValueError as exc:
            raise ReleaseEvidenceError("production report escapes the repository") from exc
        report_path = _bound_path(
            repo,
            report_relative,
            kind="production report",
            require_tracked=True,
        )
    root = _load_report(report_path)
    _require_exact_keys(
        root,
        {
            "schema_version",
            "decision",
            "generated_at",
            "release_source_commit",
            "target_tip",
            "benchmark",
            "dogfoods",
        },
        "production_readiness",
    )
    if root["schema_version"] != 1:
        raise ReleaseEvidenceError("schema_version must equal 1")
    if root["decision"] != "go":
        raise ReleaseEvidenceError("decision must be exactly 'go'")
    try:
        generated_at = datetime.fromisoformat(str(root["generated_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReleaseEvidenceError("generated_at must be RFC3339") from exc
    if generated_at.tzinfo is None or generated_at > datetime.now(UTC):
        raise ReleaseEvidenceError("generated_at must be timezone-aware and not in the future")

    source_commit = str(root["release_source_commit"])
    if _SHA.fullmatch(source_commit) is None:
        raise ReleaseEvidenceError("release_source_commit must be a full lowercase SHA")
    _git(repo, "cat-file", "-e", f"{source_commit}^{{commit}}")
    if not _is_ancestor(repo, source_commit, "HEAD"):
        raise ReleaseEvidenceError("release_source_commit is not an ancestor of HEAD")
    target_tip = str(root["target_tip"])
    if _SHA.fullmatch(target_tip) is None:
        raise ReleaseEvidenceError("target_tip must be a full lowercase SHA")
    _git(repo, "cat-file", "-e", f"{target_tip}^{{commit}}")
    _verify_release_binding(repo, source_commit, target_tip)

    benchmark = root["benchmark"]
    if not isinstance(benchmark, dict):
        raise ReleaseEvidenceError("benchmark must be a mapping")
    _require_exact_keys(
        benchmark,
        {"report", "framework", "scores", "duration_seconds", "acceptance_passed"},
        "benchmark",
    )
    benchmark_path = _bound_path(
        repo,
        benchmark["report"],
        kind="benchmark",
        require_tracked=execute_commands,
    )
    if not benchmark_path.is_file():
        raise ReleaseEvidenceError(f"benchmark report missing: {benchmark_path}")
    if benchmark["framework"] != "agentspec":
        raise ReleaseEvidenceError("benchmark.framework must equal agentspec")
    if benchmark["acceptance_passed"] is not True:
        raise ReleaseEvidenceError("benchmark acceptance must pass")
    duration = benchmark["duration_seconds"]
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or not math.isfinite(duration)
        or duration < 0
    ):
        raise ReleaseEvidenceError("benchmark.duration_seconds must be numeric")
    if duration > _MAX_DURATION_SECONDS:
        raise ReleaseEvidenceError(
            f"benchmark duration {duration} exceeds {_MAX_DURATION_SECONDS} seconds"
        )
    scores = benchmark["scores"]
    if not isinstance(scores, dict) or set(scores) != set(_SCORE_FLOORS):
        raise ReleaseEvidenceError("benchmark scores must use the frozen category catalog")
    for name, floor in _SCORE_FLOORS.items():
        value = scores[name]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < floor
            or value > 100
        ):
            raise ReleaseEvidenceError(f"benchmark score {name}={value!r} is below {floor}")
    try:
        benchmark_evidence = json.loads(benchmark_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ReleaseEvidenceError("benchmark report must be parseable JSON evidence") from exc
    if benchmark_evidence.get("framework") != "agentspec":
        raise ReleaseEvidenceError("benchmark evidence framework mismatch")
    if benchmark_evidence.get("framework_source_commit") != source_commit:
        raise ReleaseEvidenceError("benchmark evidence is not bound to release_source_commit")
    run = benchmark_evidence.get("run")
    acceptance = benchmark_evidence.get("acceptance")
    if not isinstance(run, dict) or not isinstance(acceptance, dict):
        raise ReleaseEvidenceError("benchmark evidence requires run and acceptance mappings")
    if run.get("scores") != scores or run.get("duration_seconds") != duration:
        raise ReleaseEvidenceError("benchmark summary does not match raw evidence")
    if acceptance.get("all_passed") is not True:
        raise ReleaseEvidenceError("benchmark raw acceptance evidence did not pass")
    for surface in ("api", "ui"):
        result = acceptance.get(surface)
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("passed"), int)
            or isinstance(result.get("passed"), bool)
            or not isinstance(result.get("total"), int)
            or isinstance(result.get("total"), bool)
            or result.get("passed") != result.get("total")
            or result.get("total", 0) <= 0
        ):
            raise ReleaseEvidenceError(f"benchmark {surface} acceptance is incomplete")

    dogfoods = root["dogfoods"]
    if not isinstance(dogfoods, list) or len(dogfoods) != 5:
        raise ReleaseEvidenceError("exactly five dogfoods are required")
    seen: set[str] = set()
    for index, item in enumerate(dogfoods):
        if not isinstance(item, dict):
            raise ReleaseEvidenceError(f"dogfoods[{index}] must be a mapping")
        _require_exact_keys(
            item,
            {"feature", "bundle", "pr_ready", "verification_commit", "bundle_verdict"},
            f"dogfoods[{index}]",
        )
        feature = item["feature"]
        if not isinstance(feature, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]+", feature):
            raise ReleaseEvidenceError(f"dogfoods[{index}].feature is invalid")
        if feature in seen:
            raise ReleaseEvidenceError(f"duplicate dogfood feature: {feature}")
        seen.add(feature)
        if item["bundle_verdict"] != "pass":
            raise ReleaseEvidenceError(f"dogfood {feature} did not pass its bundle gate")
        commit = str(item["verification_commit"])
        if _SHA.fullmatch(commit) is None:
            raise ReleaseEvidenceError(f"dogfood {feature} has invalid verification_commit")
        if commit != source_commit:
            raise ReleaseEvidenceError(
                f"dogfood {feature} is not verified at release_source_commit"
            )
        bundle = _bound_path(
            repo,
            item["bundle"],
            kind=f"dogfood {feature} bundle",
            require_tracked=execute_commands,
        )
        if not bundle.is_dir():
            raise ReleaseEvidenceError(f"dogfood bundle missing: {bundle}")
        pr_ready = _bound_path(
            repo,
            item["pr_ready"],
            kind=f"dogfood {feature} PR_READY",
            require_tracked=execute_commands,
        )
        if not pr_ready.is_file():
            raise ReleaseEvidenceError(f"dogfood PR_READY missing: {pr_ready}")
        required = {
            f"DEFINE_{feature}.md",
            f"DESIGN_{feature}.md",
            f"BUILD_REPORT_{feature}.md",
        }
        present = {candidate.name for candidate in bundle.iterdir() if candidate.is_file()}
        if not required <= present or not any(name.startswith("SHIPPED_") for name in present):
            raise ReleaseEvidenceError(f"dogfood {feature} bundle is incomplete")
        linter = Path(__file__).parent / "spec-linter" / "spec-lint"
        result = subprocess.run(
            [
                str(linter),
                "--feature-bundle",
                str(bundle),
                "--pr-ready",
                str(pr_ready),
                "--bundle-mode",
                "release",
            ],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise ReleaseEvidenceError(
                f"dogfood {feature} release bundle failed: "
                f"{result.stdout.strip()} {result.stderr.strip()}".strip()
            )
        pr_data = _load_pr_ready(pr_ready)
        if pr_data.get("ship_head_sha") != source_commit:
            raise ReleaseEvidenceError(f"dogfood {feature} PR_READY is stale")
        target = pr_data.get("target_branch")
        pr_target_tip = pr_data.get("target_tip_sha")
        if not isinstance(target, str) or not isinstance(pr_target_tip, str):
            raise ReleaseEvidenceError(f"dogfood {feature} target evidence is incomplete")
        if target != authorized_target:
            raise ReleaseEvidenceError(
                f"dogfood {feature} target {target!r} is not authorized target "
                f"{authorized_target!r}"
            )
        origin = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if origin.returncode == 0:
            fetched = subprocess.run(
                ["git", "fetch", "--quiet", "origin", target],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            if fetched.returncode != 0:
                raise ReleaseEvidenceError(f"could not refresh origin/{target}")
            live_tip = _git(repo, "rev-parse", f"origin/{target}")
        else:
            live_tip = _git(repo, "rev-parse", target)
        if pr_target_tip != target_tip:
            raise ReleaseEvidenceError(
                f"dogfood {feature} target tip does not match production evidence"
            )
        try:
            _verify_live_target(
                repo,
                frozen_tip=pr_target_tip,
                live_tip=live_tip,
                source_commit=source_commit,
            )
        except ReleaseEvidenceError as exc:
            raise ReleaseEvidenceError(
                f"dogfood {feature} target tip changed"
            ) from exc

    if execute_commands:
        _run_release_commands(repo)
        if _git(repo, "status", "--porcelain", "--untracked-files=all"):
            raise ReleaseEvidenceError("release verification left a dirty worktree")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    try:
        validate_release_evidence(
            args.report,
            args.repo.resolve(),
            execute_commands=True,
            authorized_target=args.target,
        )
    except (OSError, ReleaseEvidenceError, yaml.YAMLError) as exc:
        print(f"RELEASE BLOCKED: {exc}", file=sys.stderr)
        return 1
    print("RELEASE EVIDENCE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
