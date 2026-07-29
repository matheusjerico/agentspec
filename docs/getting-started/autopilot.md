# Autopilot — User Guide

> State one intent, answer the interview until it's launch-ready, then get back an open PR or an actionable gap report. Every gap is filled by you, before ignition — never auto-filled.

---

## What Autopilot Is

`/auto "<intent>"` runs the full SDD workflow — Brainstorm → Define → Design → Build → Ship → open PR — from a single stated intent. The run has an **ignition boundary**: everything before it is a supervised, human-answered interview; everything after it is autonomous, decided by quality gates rather than by you.

**The guarantee:** nothing autonomous exists before ignition — no RUN REPORT, no branch, no commit. The pre-ignition interview (interactive Brainstorm, then interactive Define gap questions) runs until the clarity score is **15/15**, and every gap it finds is answered by you, never assumed. Once ignition fires, the run is lights-out with exactly one sanctioned exception: a Design decision below 0.80 confidence (**Gate D**) is asked, not assumed, in an interactive session. Every other gate resolves to proceed, retry-within-budget, or abort-with-report, so every run still terminates.

```bash
/auto "<intent>" [--no-brainstorm] [--no-judge] [--no-ship] [--no-pr] [--max-iterations N]
/auto <path/to/DEFINE_FEATURE.md> [flags]   # DEFINE already validated — straight to ignition
/auto FEATURE_NAME                          # resume shorthand: continue an existing run
```

| Terminal state | What you get |
|-----------------|---------------|
| `✅ Success (PR: <url>)` | Open PR with code, phase docs, and archive |
| `⚠ Partial Success` | Everything ran, but the PR step itself failed — the branch is the deliverable, with the exact manual command in the report |
| `❌ Aborted (I)` | Ignition re-score fell below 15/15 — gap report names each element; amend the DEFINE and re-run |
| `❌ Aborted (D)` | A headless run hit a Design decision below 0.80 confidence — a Pending Decision block is recorded; resume interactively to answer it |
| `❌ Aborted (<other gate>)` | A gate reached its terminal failure — report carries the violations |

Good fits: features you'd normally walk through all 5 phases for — hand it a rough intent and answer the interview, or hand it an already-validated DEFINE to skip straight to ignition.
Skip it for: exploratory work where you want to steer each phase — use `/brainstorm`, `/define`, `/design`, `/build`, `/ship` directly instead.

---

## Writing a Launch-Ready Intent

### The interview, not a gate

A vague intent no longer aborts the run — it triggers a longer interview. `/auto "<intent>"` always walks the same two supervised phases (interactive Brainstorm, unless `--no-brainstorm`, then interactive Define) and keeps asking gap questions until the DEFINE scores **15/15** against the same 5 elements — Problem, Users, Goals, Success, Scope — each 0–3. A sparse intent just means more questions before ignition, not a failure.

### Good: fewer questions

```text
Add a --dry-run flag to scripts/rollout-agentspec.sh: print the file plan without
copying, exit 0; covered by pytest cases for empty and populated targets
```

This scores high because it names the problem (missing dry-run flag), a concrete target (the script and its users), a measurable success criterion (prints the plan, exits 0), and bounds scope with a test requirement — the interview has little left to ask.

### Vague: a longer interview, not a fail

```text
make the rollout script better
```

No named problem, no measurable outcome, no scope boundary. `/auto` on this intent still ignites — Define just asks about all three before the DEFINE can reach 15/15.

### The fast path: hand it an already-validated DEFINE

If you already hold a `DEFINE_{FEATURE}.md` scored at 15/15 (produced by a prior `/define` run, or a prior `/auto` interview), skip the interview entirely:

```bash
/auto .claude/sdd/features/DEFINE_ROLLOUT_DRY_RUN.md
```

Gate I re-scores it from disk — it never trusts the recorded score — and ignites at 15/15 or aborts with a gap report. This is the fast path for prepared users, and it is also the **only** form the headless runner accepts.

### Example gap report (Gate I abort)

Gate I aborts only reach the DEFINE-path form: the interactive interview never stops short of 15/15 (it either reaches 15/15 or the human abandons it, in which case the DEFINE is saved `Needs Clarification` with no run report at all). Point `/auto` at an under-specified DEFINE, though, and Gate I aborts with the RUN REPORT's Gap Report table naming exactly what to add — one row per element scoring below 3 in the **recomputed** breakdown, never the score recorded in the document:

| Element | Recomputed Score | What is missing |
|---------|-------------------|------------------|
| Problem | 1 | What "better" means — performance, error handling, output format? |
| Success | 0 | No measurable outcome — what does the script produce today that it wouldn't after the change? |
| Scope | 1 | No boundary — which parts of the script change, and what's explicitly out |

**Recorded-score discrepancy:** none — or, e.g., "DEFINE records 13/15 but re-score computed 11/15 — the re-score wins."

Fix the DEFINE (interactively, via `/define` gap questions, or a fresh `/auto "<intent>"` interview) and re-run `/auto <DEFINE path>` — Gate I re-scores from scratch.

---

## Flags

Everything runs by default; every flag opts a stage out.

| Flag | Effect |
|------|--------|
| `--no-brainstorm` | Intent form only: skip the interactive Phase 0 — the intent feeds the interactive Define gap questions directly (no-op for the DEFINE-path and resume forms; not offered by the headless runner) |
| `--no-judge` | Skip Gate J everywhere (recorded as skipped-by-flag) |
| `--no-ship` | Stop after Build (+ PR unless `--no-pr`); no archive; Gate S not evaluated |
| `--no-pr` | Stop after Ship; no PR — the branch is the deliverable |
| `--max-iterations N` | Run-wide cap on Gate L + Gate J regenerations (default: per-gate budgets, up to 2 per document); never bounds Gate D |

---

## Headless Usage (CI/cron)

The headless runner never runs the interview — it requires an already-validated DEFINE as its input:

```bash
scripts/autopilot.sh <path/to/DEFINE_FEATURE.md> [--no-judge] [--no-ship] [--no-pr] [--max-iterations N]
```

In the AgentSpec repo itself the script lives at `plugin-extras/scripts/autopilot.sh` (merged into `plugin/scripts/` at build time, alongside `init-workspace.sh`).

A raw intent string is a **preflight usage error** (exit 2): the runner checks the argument is an existing file whose basename matches `DEFINE_{FEATURE}.md` before it does anything else, and the error message points you back at an interactive `/auto "<intent>"` run if it isn't. `--no-brainstorm` is not offered by the headless runner — there is no interview to skip.

### Producing the DEFINE first

Run the interview interactively, once, in a Claude Code session — either path leaves a validated `DEFINE_{FEATURE}.md` on disk:

```bash
/auto "<intent>"          # interview to 15/15, then ignites and runs to completion/abort
/define <FEATURE_NAME>    # same interactive gap-question loop, no ignition — just the DEFINE
```

Then hand the resulting path to the script:

```bash
scripts/autopilot.sh .claude/sdd/features/DEFINE_ROLLOUT_DRY_RUN.md
```

The runner is a policy-free wrapper: preflight checks (the `claude` CLI is on `PATH`, the working directory is a git repo, the argument resolves to an existing `DEFINE_{FEATURE}.md`), a single `claude -p '/auto <DEFINE path> <flags>'` invocation, then exit-code mapping read from the RUN REPORT's terminal status.

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTOPILOT_TIMEOUT_MIN` | `60` | Minutes before the `claude -p` invocation is killed by `timeout` |
| `AUTOPILOT_WEBHOOK_URL` | unset | Optional webhook — POSTs `{feature, status, pr_url, report_path}` on completion, 10s timeout, best-effort |
| `AUTOPILOT_LOG` | unset | Optional transcript tee — path to write the headless session output |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Terminal status was Success |
| `1` | Terminal status was Aborted — including the two ignition-boundary abort labels, `❌ Aborted (I)` (ignition re-score below 15/15) and `❌ Aborted (D)` (a Design decision is pending and needs an interactive resume) |
| `2` | Preflight or operational failure — `claude` CLI missing, not a git repo, the argument isn't an existing `DEFINE_{FEATURE}.md` path, or the terminal status could not be determined |
| `3` | Terminal status was Partial Success — the workflow completed, but a non-gate step such as PR creation failed |

Schedule `scripts/autopilot.sh <path/to/DEFINE_FEATURE.md>` from cron or a CI job and branch on the exit code; the RUN REPORT and the PR (if any) are the artifacts to inspect afterward. A `❌ Aborted (D)` result needs a human: resume with `/auto FEATURE_NAME` in an interactive session to answer the pending question.

---

## Reading the RUN REPORT

Every run — success or abort — writes `.claude/sdd/reports/AUTOPILOT_RUN_{FEATURE}.md` from `AUTOPILOT_RUN_TEMPLATE.md`. It's created at OPEN, before Gate I can possibly fail, and it is the run's only state: resume replays it, an abort explains itself through it.

| Section | What it tells you |
|---------|-------------------|
| **Metadata** | DEFINE input path, flags, branch, current status |
| **Gate Ledger** | One row per gate evaluation — every retry, every visible skip (with the reason), every Gate D pause or abort, every skip-by-flag, appended live as each gate resolves |
| **Phase Artifacts** | Document path, checkpoint commit, and gate summary per phase |
| **Autonomous Decisions** | Every self-answered question and `[ASSUMED]` marker, with confidence and rationale — Gate D answers are ledger rows, not entries here |
| **Retry & Budget Accounting** | Spend against the Gate L / Gate J / Build budgets, Gate D pauses (un-capped in interactive mode), and `--max-iterations` |
| **Gap Report** | Present only on a Gate I abort — the recomputed per-element breakdown, plus any discrepancy with the recorded score |
| **Pending Decision** | Present only on a Gate D abort — the exact question, options with per-option confidence and evidence; an interactive resume rebuilds and re-asks it 1:1 |
| **Terminal Summary** | Phases completed, gates evaluated, PR URL or exact manual follow-up, and **Human Interactions** — the count of Gate D pauses answered (`0` on a fully lights-out run) |

Start with the Gate Ledger if you're auditing what the run decided on your behalf; read Autonomous Decisions if you want to know *why*.

---

## Resuming a Run

Resume is the default — there is no `--fresh` flag.

```bash
/auto FEATURE_NAME                  # resume by feature name
/auto <path/to/DEFINE_FEATURE.md>   # resume by DEFINE path (same {FEATURE} suffix)
```

If the matched report's Status is `❌ Aborted (D)`, resume answers the pending question **first**: the `AskUserQuestion` is rebuilt 1:1 from the Pending Decision block (options verbatim, nothing reinterpreted), your answer is recorded as a ledger row, the block is marked resolved, and the run continues from Design. A headless invocation pointed at such a run cannot ask — it re-aborts idempotently with the same block; only an interactive `/auto FEATURE_NAME` can resolve it.

If the matched report's Status is `❌ Aborted (I)`, there is nothing to resume yet — the fix is amending the DEFINE (interactively, via `/define` gap questions or a fresh `/auto "<intent>"` interview) and re-running `/auto <DEFINE path>`, which re-enters at Gate I.

For any other in-progress run, `/auto` replays the Gate Ledger to the last **approved** gate (a passed or visibly-skipped gate, not just a file that happens to exist on disk) and continues from the first phase without one — on the recorded branch, appending to the same report. Nothing already approved is regenerated.

If the matched report is already terminal (`✅`/`⚠`), `/auto` does nothing but print the report path and state the run is closed — reopening a shipped run is `/iterate` territory, not autopilot's. To force a genuinely fresh run, delete the RUN REPORT first — an explicit human act, not a flag.

---

## Requirements and Degradation

Autopilot works best with:

- `tools/spec-linter/spec-lint` present (Gate L)
- `tools/spec-judge/spec-judge` present, and `OPENROUTER_API_KEY` set (Gate J)

Neither is required to run. When a sensor is missing or errors operationally, the run does **not** assume a pass — it proceeds with a **visible skip**, recorded in the Gate Ledger with the exit code or reason named. Coverage narrows loudly, never silently.

**Branch safety:** every run works on `feat/auto-{feature-kebab}`, created only after Gate I passes (or reused on resume). `main` is never touched by an autopilot run — a killed session leaves `main` clean and the branch holding every checkpoint commit made so far.

---

## Gate Reference

| Gate | Checks | Retry budget | Abort condition |
|------|--------|---------------|------------------|
| **I — Ignition** | Clarity **re-score** of the DEFINE read from disk (sdd-define rubric, 5 elements × 0–3) — the recorded score is display metadata, never the sensor | none — fail-fast | recomputed < 15/15 → abort with a gap report (recomputed breakdown; any discrepancy with the recorded score noted) |
| **L — Lint** | `spec-lint` exit code | 1 regeneration per document | second lint FAIL → abort with violations listed |
| **J — Judge** | `spec-judge` exit code, standard tier (runs only after a Gate L PASS) | 1 refinement per document (WARN only) | none reachable — standard tier is WARN-capped by design |
| **D — Decision** | Design's own per-decision confidence (sdd-design confidence matrix) | un-capped in interactive mode (the human is the budget); 0 in headless | headless only: confidence < 0.80 → abort with a structured Pending Decision block, resumed 1:1 by an interactive `/auto FEATURE_NAME` |
| **B — Build** | Per-file verification + BUILD_REPORT completeness | 3 retries per file | incomplete report after retries → abort with failed tasks listed |
| **S — Ship** | Pre-ship checklist (4 items) | none | any unmet item → abort with the item named |
| **PR** | `/create-pr` outcome | none | failure → **Partial Success** (not an abort) with the manual command in the report |

Interactive mode never aborts at Gate D — a sub-0.80 decision is asked instead. Sensor unavailable (lint/judge CLI absent, or an operational exit code) is always a visible skip in the ledger, never a silent pass — see Requirements and Degradation above.

---

## E2E Validation

For releases touching autopilot, run the canonical pair, then the induced-failure checklist. The fixtures in `tests/fixtures/autopilot/` (`intent_complete.txt`, `intent_vague.txt`) drive the pre-ignition interview, which needs a human in the loop and isn't scriptable as a single command — the canonical pair below targets Gate I directly with a DEFINE document instead, since that's the boundary this feature changed.

### Canonical pair

```bash
# (a) Expect: full run, open PR, RUN REPORT shows Gate I at recomputed 15/15
# and every subsequent gate PASS. Use any DEFINE that already scores 15/15
# (e.g. one produced by a prior interactive /auto or /define run).
/auto .claude/sdd/features/DEFINE_<FEATURE>.md

# (b) Expect: abort at Gate I with a gap report; no DESIGN/BUILD artifacts
# created. Take a 15/15 DEFINE and flatten one element back to something
# vague (e.g. replace the Success section with "TBD") before pointing
# /auto at it — the on-disk re-score decides, not the recorded total.
/auto .claude/sdd/features/DEFINE_<UNDERSPECIFIED>.md
```

### Induced-failure checklist

| Condition | How | Expect |
|-----------|-----|--------|
| Judge budget exhausted | `JUDGE_BUDGET=0 /auto <DEFINE path>` | Gate J records a visible skip; run proceeds |
| Linter unavailable | temporarily rename `tools/spec-linter/spec-lint` | Gate L records a visible skip; run proceeds |
| Killed mid-Build | kill the session during Build, then re-run `/auto` for the same feature | Resume continues from Build without regenerating already-approved artifacts — Ignition and Design, the only pre-Build gates in this run's ledger; Brainstorm/Define are pre-ignition interview phases, not run artifacts |

---

## References

- Policy (single source): `.claude/skills/sdd-autopilot/SKILL.md`
- Command: `.claude/commands/workflow/auto.md`
- Run report shape: `.claude/sdd/templates/AUTOPILOT_RUN_TEMPLATE.md`
- Headless runner: `plugin-extras/scripts/autopilot.sh` (repo) / `scripts/autopilot.sh` (installed plugin)
- Judge setup (for Gate J): `docs/getting-started/judge-setup.md`
