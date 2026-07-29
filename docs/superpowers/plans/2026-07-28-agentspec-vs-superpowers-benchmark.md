# AgentSpec vs. Superpowers Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce two independently developed TaskFlow applications and an evidence-backed comparison of AgentSpec and Superpowers from brainstorming through PR readiness.

**Architecture:** A controller repository stores the frozen brief, session launcher, evidence schema, black-box evaluator, and final report. Two native Claude Code sessions run independently in `/work2/agentspec` and `/work2/superpowers`, each with exactly one target plugin loaded. Evaluation treats both repositories as opaque systems and records raw results before scoring.

**Tech Stack:** Claude Code 2.1.220, AgentSpec 3.2.0, Superpowers 6.2.0, Bash, Python 3.13, pytest, Playwright, Git, FastAPI, SQLite, React, TypeScript.

## Global Constraints

- Use the frozen requirements in `docs/superpowers/specs/2026-07-28-agentspec-vs-superpowers-benchmark-design.md`.
- Use `/work2/agentspec` and `/work2/superpowers`; never copy application code or generated planning artifacts between them.
- Use the same Claude Code version, model alias, effort, permission mode, budget, and initial prompt for both native sessions.
- Load only `plugin/` for the AgentSpec run and only the pinned Superpowers 6.2.0 plugin directory for the Superpowers run.
- Keep secrets out of logs and reports.
- Do not publish GitHub repositories or PRs without separate explicit authorization.
- Record unavailable telemetry as `unavailable`; never estimate it.
- Run order must be randomized once, recorded, and not changed.

---

## File Structure

### Controller repository

- `benchmark/taskflow/brief.md` — exact prompt delivered to both native sessions.
- `benchmark/taskflow/evidence.schema.json` — machine-readable evidence contract.
- `benchmark/taskflow/session_driver.py` — launches and resumes native Claude Code sessions while preserving JSONL events.
- `benchmark/taskflow/acceptance/api_contract.py` — API discovery and black-box behavioral checks.
- `benchmark/taskflow/acceptance/ui_contract.spec.ts` — browser acceptance flow.
- `benchmark/taskflow/acceptance/package.json` — isolated browser-evaluator dependencies.
- `benchmark/taskflow/collect.py` — runs repository-native checks and writes normalized evidence.
- `benchmark/taskflow/score.py` — validates evidence and computes the approved weighted score.
- `benchmark/taskflow/tests/` — controller, collector, and scorer tests.
- `benchmark/taskflow/runs/` — sanitized prompts, JSONL logs, timing, and evidence for each run.
- `benchmark/taskflow/report.md` — final comparison and recommendation.

### Implementation repositories

- `/work2/agentspec/` — AgentSpec-native artifacts and TaskFlow implementation.
- `/work2/superpowers/` — Superpowers-native artifacts and TaskFlow implementation.

The controller knows only documented start/check commands and observable HTTP/browser behavior. It does not import implementation modules from either repository.

---

### Task 1: Freeze the common brief and evidence contract

**Files:**

- Create: `benchmark/taskflow/brief.md`
- Create: `benchmark/taskflow/evidence.schema.json`
- Create: `benchmark/taskflow/tests/test_evidence_schema.py`

**Interfaces:**

- Consumes: approved benchmark design.
- Produces: `brief.md`; JSON objects with top-level keys `framework`, `versions`, `run`, `phases`, `verification`, `repository`, `pr`, and `limitations`.

- [ ] **Step 1: Write the failing schema test**

```python
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parents[1]


def test_evidence_schema_accepts_minimal_complete_record():
    schema = json.loads((ROOT / "evidence.schema.json").read_text())
    record = {
        "framework": "agentspec",
        "versions": {"claude": "2.1.220", "framework": "3.2.0"},
        "run": {"order": 1, "started_at": "2026-07-28T12:00:00Z",
                "ended_at": "2026-07-28T13:00:00Z", "tokens": "unavailable"},
        "phases": [],
        "verification": [],
        "repository": {"path": "/work2/agentspec", "commit": "abc123"},
        "pr": {"title": "feat: add TaskFlow", "body_path": "PR.md"},
        "limitations": [],
    }
    Draft202012Validator(schema).validate(record)
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `uv run --with pytest --with jsonschema pytest benchmark/taskflow/tests/test_evidence_schema.py -v`  
Expected: FAIL because `evidence.schema.json` does not exist.

- [ ] **Step 3: Write the frozen brief and strict JSON Schema**

Copy sections 4, 5, 6, and 8 of the approved design into `brief.md`, preserving every limit and exclusion. Add instructions to use the loaded framework's complete native workflow and finish with a clean feature branch plus `PR.md`.

Define all produced fields in `evidence.schema.json`, set `additionalProperties: false` at the root, require every top-level key listed under Interfaces, and restrict `framework` to `agentspec` or `superpowers`.

- [ ] **Step 4: Run the schema test**

Run: `uv run --with pytest --with jsonschema pytest benchmark/taskflow/tests/test_evidence_schema.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add benchmark/taskflow/brief.md benchmark/taskflow/evidence.schema.json benchmark/taskflow/tests/test_evidence_schema.py
git commit -m "test(benchmark): freeze TaskFlow evidence contract"
```

### Task 2: Build the native session driver

**Files:**

- Create: `benchmark/taskflow/session_driver.py`
- Create: `benchmark/taskflow/tests/test_session_driver.py`

**Interfaces:**

- Consumes: framework name, work directory, plugin directory, prompt file, model, effort, and budget.
- Produces: `runs/<framework>/events.jsonl`, `metadata.json`, `stdout.log`, `stderr.log`, and a resumable Claude session ID.
- Produces function: `build_command(config: RunConfig) -> list[str]`.

- [ ] **Step 1: Write failing command-construction tests**

```python
from pathlib import Path

from benchmark.taskflow.session_driver import RunConfig, build_command


def test_build_command_loads_only_selected_plugin(tmp_path: Path):
    config = RunConfig(
        framework="agentspec",
        workdir=tmp_path,
        plugin=Path("/plugins/agentspec"),
        prompt=Path("/brief.md"),
        model="sonnet",
        effort="high",
        budget_usd=30.0,
    )
    command = build_command(config)
    assert command.count("--plugin-dir") == 1
    assert command[command.index("--plugin-dir") + 1] == "/plugins/agentspec"
    assert ["--output-format", "stream-json"] == command[
        command.index("--output-format"):command.index("--output-format") + 2
    ]
    assert "--dangerously-skip-permissions" not in command
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `uv run --with pytest pytest benchmark/taskflow/tests/test_session_driver.py -v`  
Expected: FAIL because `session_driver` does not exist.

- [ ] **Step 3: Implement the driver**

Use a frozen dataclass:

```python
@dataclass(frozen=True)
class RunConfig:
    framework: Literal["agentspec", "superpowers"]
    workdir: Path
    plugin: Path
    prompt: Path
    model: str
    effort: str
    budget_usd: float
```

`build_command` must use `claude -p`, `--input-format stream-json`, `--output-format stream-json`, `--verbose`, `--include-hook-events`, `--permission-mode acceptEdits`, the configured model/effort/budget, and exactly one `--plugin-dir`. Stream input and output without echoing environment values. Parse the result event for session ID, cost, usage, and terminal status; retain raw JSONL.

- [ ] **Step 4: Test failure handling**

Add tests proving a non-zero child exit is recorded, malformed JSONL is retained and flagged, and a resume command uses `--resume <session-id>` with the same plugin and work directory.

Run: `uv run --with pytest pytest benchmark/taskflow/tests/test_session_driver.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add benchmark/taskflow/session_driver.py benchmark/taskflow/tests/test_session_driver.py
git commit -m "feat(benchmark): add native Claude session driver"
```

### Task 3: Create and validate isolated repositories

**Files:**

- Create: `/work2/agentspec/.git/`
- Create: `/work2/superpowers/.git/`
- Create: `benchmark/taskflow/runs/run-order.json`
- Create: `benchmark/taskflow/runs/environment.json`

**Interfaces:**

- Consumes: local AgentSpec plugin at `plugin/`; Superpowers plugin at `/Users/matheusjericopalhares/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0`.
- Produces: two empty Git repositories on branch `main`, each with only an initial `README.md` commit, plus immutable run-order and version records.

- [ ] **Step 1: Verify all prerequisites before writing**

Run:

```bash
claude --version
python3 --version
node --version
npm --version
git --version
test -f plugin/.claude-plugin/plugin.json
test -f /Users/matheusjericopalhares/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/.claude-plugin/plugin.json
```

Expected: every command exits 0; versions are captured in `environment.json`.

- [ ] **Step 2: Create exact isolated targets**

Create `/work2` if absent, then create only the two approved child directories. Abort if either target exists with non-benchmark content. Initialize each with `git init -b main`, a one-line repository-specific README, configured local benchmark author identity, and an initial commit.

- [ ] **Step 3: Randomize and freeze run order**

Use `secrets.randbelow(2)` once. Write:

```json
{"seed_source": "python.secrets", "order": ["agentspec", "superpowers"]}
```

or the reversed order. Never regenerate this file during the benchmark.

- [ ] **Step 4: Verify isolation**

Run `git -C <target> status --short`, `git -C <target> log --oneline`, and compare inode-resolved roots.  
Expected: both trees clean, one initial commit each, distinct real paths, no remotes.

- [ ] **Step 5: Commit controller records**

```bash
git add benchmark/taskflow/runs/run-order.json benchmark/taskflow/runs/environment.json
git commit -m "chore(benchmark): freeze environment and run order"
```

### Task 4: Conduct the AgentSpec native workflow

**Files:**

- Modify: `/work2/agentspec/**`
- Create: `benchmark/taskflow/runs/agentspec/**`

**Interfaces:**

- Consumes: `brief.md`, AgentSpec plugin, supervised answers drawn only from the approved design.
- Produces: native AgentSpec workflow artifacts, runnable TaskFlow, tests, feature branch, commits, `PR.md`, and raw session evidence.

- [ ] **Step 1: Launch the AgentSpec session when selected by run order**

Start from `/work2/agentspec` with the driver, identical shared model settings, and only the local `plugin/` directory. The first prompt must include `brief.md` verbatim and request the supervised AgentSpec workflow from brainstorm through PR readiness.

- [ ] **Step 2: Apply approval discipline**

Answer product questions only from the frozen design. Record every user response. Require native phase artifacts before approving the next phase. Do not inject Superpowers terminology or implementation suggestions.

- [ ] **Step 3: Let the native workflow implement and review**

Permit AgentSpec to select specialists, build, run tests, review, and correct findings. Do not manually edit application files. When the workflow requests PR publication, instruct it to create `PR.md` and stop before network publication.

- [ ] **Step 4: Verify terminal repository state**

Run:

```bash
git -C /work2/agentspec status --short
git -C /work2/agentspec log --oneline --decorate
test -s /work2/agentspec/PR.md
```

Expected: clean feature branch, non-empty commit history beyond bootstrap, non-empty `PR.md`.

- [ ] **Step 5: Preserve evidence**

Sanitize only secret values, never failed commands or unfavorable results. Hash every raw log and write hashes into the AgentSpec metadata record.

### Task 5: Conduct the Superpowers native workflow

**Files:**

- Modify: `/work2/superpowers/**`
- Create: `benchmark/taskflow/runs/superpowers/**`

**Interfaces:**

- Consumes: `brief.md`, pinned Superpowers plugin, supervised answers drawn only from the approved design.
- Produces: native Superpowers specs/plans/reviews, runnable TaskFlow, tests, feature branch, commits, `PR.md`, and raw session evidence.

- [ ] **Step 1: Launch the Superpowers session when selected by run order**

Start from `/work2/superpowers` with the same driver and shared model settings, loading only Superpowers 6.2.0. Deliver the exact same first prompt.

- [ ] **Step 2: Apply approval discipline**

Answer product questions only from the frozen design. Review and approve the written design and plan at native gates. Do not inject AgentSpec terminology, artifact formats, or specialist suggestions.

- [ ] **Step 3: Let the native workflow implement and review**

Allow Superpowers to use its native TDD, task execution, review loops, and branch-finishing workflow. Do not manually edit application files. Require `PR.md` instead of publishing.

- [ ] **Step 4: Verify terminal repository state**

Run:

```bash
git -C /work2/superpowers status --short
git -C /work2/superpowers log --oneline --decorate
test -s /work2/superpowers/PR.md
```

Expected: clean feature branch, non-empty commit history beyond bootstrap, non-empty `PR.md`.

- [ ] **Step 5: Preserve evidence**

Apply the same sanitization and hashing procedure as AgentSpec.

### Task 6: Implement black-box API and browser acceptance

**Files:**

- Create: `benchmark/taskflow/acceptance/api_contract.py`
- Create: `benchmark/taskflow/acceptance/ui_contract.spec.ts`
- Create: `benchmark/taskflow/acceptance/package.json`
- Create: `benchmark/taskflow/tests/test_api_contract.py`

**Interfaces:**

- Consumes: documented backend/frontend start commands and base URLs.
- Produces: JUnit/JSON results for acceptance criteria 1–11 without importing implementation code.
- Produces function: `run_api_contract(base_url: str, restart: Callable[[], None]) -> list[CheckResult]`.

- [ ] **Step 1: Write failing evaluator self-tests**

Create a deterministic fake HTTP server fixture and assert checks for valid create, invalid limits, update, missing ID, delete, filtering, case-insensitive search, and persistence across the supplied restart callback.

Run: `uv run --with pytest --with httpx pytest benchmark/taskflow/tests/test_api_contract.py -v`  
Expected: FAIL because the evaluator does not exist.

- [ ] **Step 2: Implement API discovery and checks**

Read the documented base URL and OpenAPI document. Locate the task collection/item operations by method and response schema. If discovery is ambiguous, record a failed `api-discovery` check instead of hard-coding a favorable route.

- [ ] **Step 3: Add the browser contract**

The Playwright test must create a unique task, edit its description and status, filter to that status, search with different letter case, delete it, and verify its absence. Add separate assertions for accessible form labels plus empty, validation, and request-failure states.

- [ ] **Step 4: Run evaluator self-tests**

Run:

```bash
uv run --with pytest --with httpx pytest benchmark/taskflow/tests/test_api_contract.py -v
npm --prefix benchmark/taskflow/acceptance install
npx --prefix benchmark/taskflow/acceptance playwright install chromium
```

Expected: Python tests pass and Chromium installs successfully.

- [ ] **Step 5: Commit**

```bash
git add benchmark/taskflow/acceptance benchmark/taskflow/tests/test_api_contract.py
git commit -m "test(benchmark): add TaskFlow black-box acceptance"
```

### Task 7: Collect, normalize, and score evidence

**Files:**

- Create: `benchmark/taskflow/collect.py`
- Create: `benchmark/taskflow/score.py`
- Create: `benchmark/taskflow/tests/test_score.py`
- Create: `benchmark/taskflow/runs/agentspec/evidence.json`
- Create: `benchmark/taskflow/runs/superpowers/evidence.json`

**Interfaces:**

- Consumes: raw session logs, Git repositories, native test commands, acceptance results, reviews, and PR documents.
- Produces: schema-valid evidence records and category scores totaling 100.
- Produces function: `score(record: Evidence) -> Scorecard`.

- [ ] **Step 1: Write failing scoring tests**

```python
from benchmark.taskflow.score import weighted_total


def test_weighted_total_uses_approved_weights():
    categories = {
        "correctness": 100,
        "requirements_planning": 80,
        "tests": 60,
        "code_quality": 40,
        "review_pr": 20,
        "efficiency": 0,
    }
    assert weighted_total(categories) == 68.0


def test_persistence_failure_caps_total():
    assert weighted_total({key: 100 for key in (
        "correctness", "requirements_planning", "tests",
        "code_quality", "review_pr", "efficiency"
    )}, persistence_passed=False) == 60.0
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `uv run --with pytest pytest benchmark/taskflow/tests/test_score.py -v`  
Expected: FAIL because `score` does not exist.

- [ ] **Step 3: Implement transparent collection and scoring**

Implement the approved weights `35/20/15/15/10/5`, the 60-point startup/persistence cap, and 50-point critical security/data-loss cap. Store every subscore with its evidence path and rationale. Never score missing telemetry as zero unless the metric itself is a required outcome.

- [ ] **Step 4: Run native and external verification identically**

For each repository, use README-documented clean install/start/check commands, then execute the same acceptance suite. Preserve stdout, stderr, exit status, and duration. Give each native workflow exactly one correction round for confirmed defects and repeat the complete applicable suite.

- [ ] **Step 5: Validate evidence and tests**

Run:

```bash
uv run --with pytest --with jsonschema pytest benchmark/taskflow/tests -v
uv run --with jsonschema python benchmark/taskflow/score.py --validate-only
```

Expected: all tests pass and both evidence files validate.

- [ ] **Step 6: Commit**

```bash
git add benchmark/taskflow/collect.py benchmark/taskflow/score.py benchmark/taskflow/tests benchmark/taskflow/runs
git commit -m "feat(benchmark): collect and score comparative evidence"
```

### Task 8: Produce and review the comparative report

**Files:**

- Create: `benchmark/taskflow/report.md`
- Create: `benchmark/taskflow/review.md`

**Interfaces:**

- Consumes: the approved design, both evidence records, raw scorecards, repositories, artifacts, and cited primary sources.
- Produces: auditable comparison, scenario-specific recommendation, limitations, and independent report review.

- [ ] **Step 1: Generate the evidence-first tables**

For every lifecycle phase, show AgentSpec evidence, Superpowers evidence, result, and caveat. Separate observed facts, evaluator judgments, and inferences. Link local artifacts and official upstream documentation.

- [ ] **Step 2: Explain outcome and process differences**

Cover brainstorming, requirements, planning, segregation, implementation, TDD, review, correction, Git history, and PR readiness. Report raw checks and timings before weighted scores.

- [ ] **Step 3: State limitations and recommendations**

Explicitly address single-run stochasticity, AgentSpec's data-engineering specialization, possible telemetry incomparability, supervision effects, and absence of published PRs. Recommend by team/project scenario and identify whether repeated trials could change the conclusion.

- [ ] **Step 4: Independently review the report**

Check every comparative claim against an evidence path or primary citation. Record unsupported claims, arithmetic errors, missing unfavorable evidence, and conflicts with the frozen design in `review.md`; correct the report and retain dispositions.

- [ ] **Step 5: Run final verification**

Run:

```bash
git diff --check
uv run --with pytest --with jsonschema --with httpx pytest benchmark/taskflow/tests -v
git -C /work2/agentspec status --short
git -C /work2/superpowers status --short
```

Expected: no whitespace errors, all controller tests pass, both implementation repositories are clean.

- [ ] **Step 6: Commit**

```bash
git add benchmark/taskflow/report.md benchmark/taskflow/review.md
git commit -m "docs(benchmark): compare AgentSpec and Superpowers"
```
