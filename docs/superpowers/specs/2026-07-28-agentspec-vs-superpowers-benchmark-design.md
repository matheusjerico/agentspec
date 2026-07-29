# AgentSpec vs. Superpowers: Benchmark Design

**Date:** 2026-07-28  
**Status:** Awaiting written-spec approval

## 1. Objective

Compare AgentSpec and Superpowers across a complete software-delivery workflow:
brainstorming, requirements definition, implementation planning, task segregation,
implementation, testing, code review, and pull-request preparation.

The benchmark must produce both qualitative evidence about the workflow and
quantitative evidence from two runnable implementations of the same feature.

## 2. Experimental Method

Use two independent, supervised Claude Code sessions:

- AgentSpec session loaded with the local AgentSpec plugin.
- Superpowers session loaded with the current official Superpowers plugin.

Both sessions receive the same initial feature brief, answers to semantically
equivalent clarification questions, acceptance criteria, runtime constraints, and
opportunities to correct defects. Each tool remains free to apply its native
workflow, create its own artifacts, choose internal boundaries, and delegate work
according to its own methodology.

Supervision is used instead of comparing AgentSpec Autopilot with an interactive
Superpowers run. This avoids granting one solution additional human context or
penalizing the other for mandatory approval gates.

## 3. Isolation

The implementations use separate directories:

- `/work2/agentspec`
- `/work2/superpowers`

Each directory is an independent Git repository with its own branch, commits,
workflow artifacts, application code, tests, and PR description. No application
code or generated planning artifact may be copied between implementations.

A shared benchmark harness may live outside both implementation repositories. It
may supply the common brief, record timing and usage data, start applications, and
run black-box acceptance tests. It may not modify either implementation.

## 4. Common Feature: TaskFlow

TaskFlow is a small full-stack task manager.

### 4.1 User capabilities

A user can:

1. Create a task.
2. View all tasks.
3. Edit a task.
4. Delete a task.
5. Move a task between `todo`, `doing`, and `done`.
6. Search tasks by title or description.
7. Filter tasks by status.

### 4.2 Task data

Each task has:

- a stable unique identifier;
- a required title between 1 and 120 characters after trimming;
- an optional description of at most 500 characters;
- a status of `todo`, `doing`, or `done`;
- creation and update timestamps.

The default status is `todo`. Data must survive an application restart.

### 4.3 User experience

The frontend must:

- work at desktop and mobile widths;
- expose loading, empty, validation, and request-failure states;
- allow all required operations without a page reload;
- provide accessible labels for interactive controls;
- visibly distinguish the three statuses.

Visual polish is evaluated only after functional and accessibility requirements.

### 4.4 Technical constraints

- Backend: Python, FastAPI, and SQLite.
- Frontend: React and TypeScript.
- API: JSON over HTTP.
- The repository must document supported runtime versions.
- The application must run locally using documented commands.
- No authentication, multi-user support, deployment, or external database.

Implementations may choose libraries, file structure, state management, API
shape, migrations, and styling approach independently.

## 5. Minimum Acceptance Criteria

The external evaluator will verify:

1. Health or equivalent readiness can be determined.
2. A valid task can be created and returned with all required fields.
3. Whitespace-only titles, titles over 120 characters, descriptions over 500
   characters, and unknown statuses are rejected.
4. Tasks are listed and persist after backend restart.
5. Title, description, and status can be updated.
6. A missing task returns a not-found response.
7. A task can be deleted and is absent afterward.
8. Status filtering returns only matching tasks.
9. Text search matches title and description case-insensitively.
10. The browser flow can create, edit, filter, search, and delete a task.
11. Loading, empty, validation, and server-error states are represented.
12. Documented automated tests, lint, and type checks pass.

The evaluator may adapt endpoint discovery to a documented API shape, but it may
not weaken behavior requirements.

## 6. Required Delivery Artifacts

Each implementation must contain evidence for:

- brainstorm or discovery;
- requirements/specification;
- architecture/design;
- implementation plan or task breakdown;
- build/implementation record;
- test results;
- code-review findings and dispositions;
- Git history;
- PR title and description;
- setup and run instructions.

Native artifact names and formats are preserved. Missing artifact types are
recorded rather than manufactured after the run.

## 7. Execution Protocol

### 7.1 Preparation

1. Record tool versions and the exact commit of each framework.
2. Create empty isolated repositories.
3. Confirm required runtimes and package managers.
4. Store the common feature brief and evaluator outside both repositories.

### 7.2 Supervised workflow

For each solution:

1. Launch a fresh Claude Code session with only the target plugin enabled.
2. Submit the common feature brief.
3. Answer clarification questions using the approved requirements in this design.
4. Approve a phase only when its artifact is reviewable and consistent with the
   common brief.
5. Allow the native planning, delegation, TDD, review, and finishing workflows to
   operate without substituting the other tool's conventions.
6. Record start/end times, session events, reported token usage, commands, test
   outcomes, commits, and human interventions.
7. Stop only for a genuine blocker, completion, or a framework-required gate.

Responses to framework-specific questions will preserve the same product meaning.
They need not use identical words when the available choices differ.

### 7.3 Verification and review

After each native workflow reports completion:

1. Follow its README from a clean dependency installation.
2. Run its own tests, lint, type checks, and build.
3. Run the shared black-box API and browser acceptance suite.
4. Perform an independent code review against the common requirements.
5. Give the native workflow one correction round for confirmed defects.
6. Re-run all applicable checks.
7. Generate a final PR-ready diff and description.

## 8. Pull-Request Boundary

Because the two benchmark repositories do not currently have dedicated GitHub
remotes, the required output is PR-ready:

- feature branch;
- coherent commits;
- clean working tree;
- PR title;
- PR body with summary, test evidence, risks, and known limitations;
- saved diff and final commit SHA.

No public GitHub repository or pull request will be created unless the user later
provides or explicitly authorizes suitable remotes.

## 9. Metrics

### 9.1 Outcome quality

- external acceptance checks passed;
- native tests passed;
- defects by severity before and after correction;
- requirements implemented, missed, or added without need;
- accessibility and responsive behavior;
- maintainability and security observations.

### 9.2 Process quality

- quality and relevance of discovery questions;
- requirement clarity and traceability;
- plan completeness and task granularity;
- effectiveness of task segregation;
- review depth and defect-removal effectiveness;
- recovery from failures and preservation of context;
- usefulness of workflow artifacts for a human reviewer.

### 9.3 Efficiency

- wall-clock time by phase and total;
- number of user interactions and approvals;
- reported input/output tokens where available;
- number of agent or worker invocations;
- correction loops;
- commits, changed files, and lines of application code;
- dependency-install and test duration.

Token measurements are compared only when the harness reports them on the same
basis. Missing telemetry is labeled unavailable, not estimated.

## 10. Scoring

The report will present raw evidence before any aggregate score.

The aggregate score uses:

- 35% functional correctness and acceptance;
- 20% requirements and planning quality;
- 15% test quality;
- 15% code quality and maintainability;
- 10% review and PR readiness;
- 5% execution efficiency.

Any implementation that cannot start or fails data persistence is capped at 60
points. Any unresolved critical security or data-loss defect is capped at 50
points.

Aggregate scoring supplements, rather than replaces, scenario-specific findings.
The conclusion may recommend different tools for different teams or project types.

## 11. Bias Controls and Limitations

- The same base model and Claude Code version are used for both runs.
- Run order will be randomized and recorded.
- The second implementation cannot inspect the first.
- Framework documentation and native artifacts remain available to their own run.
- External evaluation is based on this frozen design, not on requirements invented
  by either implementation.
- AgentSpec is specialized toward data engineering while TaskFlow is general
  full-stack software; the report must treat domain fit as a limitation.
- A single feature and single pair of runs cannot establish universal superiority.
- Stochastic model behavior remains a confounder; findings describe this benchmark
  and identify claims that would require repeated trials.

## 12. Final Deliverables

1. Runnable AgentSpec implementation in `/work2/agentspec`.
2. Runnable Superpowers implementation in `/work2/superpowers`.
3. Raw session and measurement evidence, with secrets removed.
4. Shared evaluator and its results.
5. Side-by-side comparison from brainstorming through PR readiness.
6. Evidence-backed recommendation and limitations.
