---
name: auto
description: Execute the SDD workflow from a validated intent — mandatory human-answered interview to 15/15, then gates decide autonomously (Autopilot)
---

# Auto Command

> One stated intent → **mandatory interactive interview** (Brainstorm + Define, human-answered until the clarity re-score is 15/15) → ignition → autonomous Design → Build → Ship → open PR, with quality gates deciding proceed, retry, or abort. Nothing autonomous exists before ignition; after ignition, the only sanctioned pause is a Design decision below 0.80 confidence (Gate D), which is asked — never assumed.

## Usage

```bash
/auto "<intent>" [--no-brainstorm] [--no-judge] [--no-ship] [--no-pr] [--max-iterations N]
/auto <path/to/DEFINE_FEATURE.md> [flags]   # DEFINE ready → straight to ignition (re-score decides)
/auto FEATURE_NAME                          # resume shorthand: continue an existing run
```

## Examples

```bash
# Intent form: the interview runs first — discovery questions, approach choice,
# clarity gaps — all answered by YOU; the autonomous run ignites only at 15/15
/auto "Add a --dry-run flag to scripts/rollout-agentspec.sh"

# DEFINE form: skip the interview — you already hold a validated DEFINE;
# Gate I re-scores it from disk and ignites (or aborts with a gap report)
/auto .claude/sdd/features/DEFINE_ROLLOUT_DRY_RUN.md

# Skip Phase 0 only (intent is already requirements-grade): interview starts
# at the interactive Define gap questions
/auto "<intent>" --no-brainstorm

# Resume after a kill, an ❌ Aborted (I) DEFINE fix, or an ❌ Aborted (D)
# pending decision — the pending question is re-asked first, 1:1
/auto ROLLOUT_DRY_RUN
```

Headless (CI/cron) entrypoint — same policy, same terminal states, but **only the DEFINE form**: `scripts/autopilot.sh <path/to/DEFINE_FEATURE.md> [flags]` (in this repo: `plugin-extras/scripts/autopilot.sh`). A raw intent given to the headless runner is a preflight usage error (exit 2), not a gate evaluation: produce the DEFINE interactively first.

---

## What happens

This command is a thin entrypoint; **every** proceed/retry/abort rule lives in the skill. If a behavior here ever seems to conflict with the skill, the skill wins.

1. **Classify the argument** (this command's only logic beyond flag parsing):
   - Existing file whose basename matches `DEFINE_*.md` → **DEFINE form**
   - Bare `SCREAMING_SNAKE` word → **resume form**
   - Anything else → **intent form**
2. **Intent form — run the pre-ignition interview (supervised, human-answered):**
   - Load `${CLAUDE_PLUGIN_ROOT}/skills/sdd-brainstorm/SKILL.md` and run Phase 0 with its native interactive conduct — discovery questions one at a time, the user selects the approach, YAGNI validated. (Skipped with `--no-brainstorm`.)
   - Load `${CLAUDE_PLUGIN_ROOT}/skills/sdd-define/SKILL.md` and run Phase 1 interactively — entity extraction, clarity scoring, targeted gap questions **until the score is 15/15**. If the user abandons below 15/15, the DEFINE is saved `Needs Clarification` and the flow ends — no run, no report, nothing autonomous.
   - Zero `[ASSUMED]` markers exist in anything the interview produced.
3. **Load `${CLAUDE_PLUGIN_ROOT}/skills/sdd-autopilot/SKILL.md`** and follow it end to end starting at Gate I: ignition re-score of the DEFINE, RUN REPORT creation, branch setup, the autonomous phase loop with Gates I/L/J/D/P/B/S/PR, checkpoint commits, terminal status, notification.
4. **Parse flags** from the arguments (table below) and pass their policy meaning through — this command adds no interpretation of its own.
5. **Terminate** in exactly one of the skill's terminal states, with `AUTOPILOT_RUN_{FEATURE}.md` written in all of them (the interview itself, ending before ignition, produces phase documents but no run report):

| Terminal state | Meaning |
|----------------|---------|
| `✅ Success (PR: <url>)` | Full flow complete; PR open with code + docs + archive |
| `⚠ Partial Success` | Flow complete but a non-gate step failed (e.g., PR creation); report names the exact manual follow-up |
| `❌ Aborted (I)` | Ignition re-score below 15/15; gap report names each element < 3 — amend the DEFINE and re-run |
| `❌ Aborted (D)` | Headless run hit a Design decision < 0.80 confidence; Pending Decision block recorded — resume interactively to answer it |
| `❌ Aborted (<other gate>)` | A gate reached its terminal failure; report carries the violations |

## Flags

| Flag | Effect (semantics owned by the skill) |
|------|----------------------------------------|
| `--no-brainstorm` | Intent form only: skip Phase 0 — the intent feeds the interactive Define directly (no-op for DEFINE/resume forms) |
| `--no-judge` | Skip Gate J (recorded as skipped-by-flag) |
| `--no-ship` | Stop after Build (+ PR unless `--no-pr`); no archive |
| `--no-pr` | No PR; the branch is the deliverable |
| `--max-iterations N` | Run-wide cap on lint/judge regenerations — never bounds Gate D |

## Invariants (from the skill — restated for visibility, not redefined)

- **Nothing autonomous exists before Gate I passes** — no RUN REPORT, no branch, no checkpoint commits during the interview.
- Gate I **re-scores** the DEFINE from disk; the recorded clarity breakdown is never the sensor.
- Post-ignition, a headless run never waits for a human; an interactive run pauses **only** at Gate D (< 0.80 Design decisions), un-capped, every pause ledger-recorded.
- All retry budgets are bounded; every headless run terminates.
- Sensor unavailability (lint/judge exit ≥ 2 or CLI absent) is a **visible skip**, never an assumed PASS.
- Resume is the default: re-running `/auto` with the DEFINE path or the feature name continues from the last approved gate; a pending decision is re-asked first, 1:1 from its block.
- All run writes happen on a `feat/auto-*` branch; `main` is never touched by a run.

---

## References

- Skill (single-source policy): `${CLAUDE_PLUGIN_ROOT}/skills/sdd-autopilot/SKILL.md`
- Interview methodologies (pre-ignition, supervised): `${CLAUDE_PLUGIN_ROOT}/skills/sdd-brainstorm/SKILL.md` · `${CLAUDE_PLUGIN_ROOT}/skills/sdd-define/SKILL.md`
- Run report template: `${CLAUDE_PLUGIN_ROOT}/sdd/templates/AUTOPILOT_RUN_TEMPLATE.md`
- Headless runner: `plugin-extras/scripts/autopilot.sh` (repo) / `${CLAUDE_PLUGIN_ROOT}/scripts/autopilot.sh` (plugin)
- Sensors: `${CLAUDE_PLUGIN_ROOT}/sdd/architecture/WORKFLOW_CONTRACTS.yaml` · `${CLAUDE_PLUGIN_ROOT}/tools/spec-linter/USAGE.md` · `${CLAUDE_PLUGIN_ROOT}/tools/spec-judge/USAGE.md`
- Phase entrypoints sequenced: `/brainstorm` · `/define` · `/design` · `/build` · `/ship` · `/create-pr`
- User guide: `docs/getting-started/autopilot.md`
