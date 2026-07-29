# BRAINSTORM: Autopilot Ignition Gate

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTOPILOT_IGNITION_GATE |
| **Date** | 2026-07-28 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** (translated from Portuguese) "Autopilot (`/auto`) may only start its autonomous loop when the clarity matrix is 15/15 — when every question has been answered and 100% of the required information has been provided. WHY: if the autopilot flow starts without all gaps filled, the workflow fills those gaps automatically, and the result is often not what I want or expect. The brainstorm questions and the define clarifications must therefore be executed and asked mandatorily, so the clarity matrix reaches 15/15 — only then can `/auto` implement what I actually want."

**Context Gathered:**

- `sdd-autopilot/SKILL.md` currently enforces a non-blocking invariant ("a run NEVER waits for a human"; `AskUserQuestion` forbidden for the entire run) with Gate 0 at clarity ≥ 12/15 — scores of 12–14 proceed with machine-filled gaps marked `[ASSUMED]`, which is exactly the failure mode the user wants to eliminate.
- Under autopilot, Brainstorm self-answers every discovery question from KB + codebase evidence; Define aborts below 12 but never asks.
- The interactive conduct of `sdd-brainstorm` (one-question-at-a-time discovery, user-selected approach, validated YAGNI) and `sdd-define` (targeted gap questions until the gate passes) already implements the exact interview the user is asking for — autopilot's conduct overrides are what suppress it.
- Two entrypoints share the policy: `/auto` (interactive terminal) and `plugin-extras/scripts/autopilot.sh` (headless CI/cron, physically unable to ask).

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `.claude/skills/sdd-autopilot/SKILL.md`, `.claude/commands/workflow/auto.md`, `plugin-extras/scripts/autopilot.sh`, `.claude/sdd/templates/AUTOPILOT_RUN_TEMPLATE.md`, `docs/getting-started/autopilot.md`, `tests/` | Policy change lives in the skill (single source); entrypoints change sequencing/input contract only |
| Relevant KB Domains | `shared` (component-model), `testing` | Layer decisions follow the component model; new `autopilot.sh` contract needs pytest coverage |
| IaC Patterns | N/A | Documentation/skill/script change; no infrastructure |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Does the 15/15 gate apply to autopilot only, or also to supervised `/define` (currently 12/15)? | **Autopilot only** — supervised `/define` keeps 12/15 | 15/15 is autopilot *policy*, not a sensor change; `sdd-define` stays untouched |
| 2 | What does the headless runner (CI/cron, cannot ask) do below 15/15? | **Require a pre-validated DEFINE** — raw intent as input becomes a usage error, not a gate | `autopilot.sh` input contract changes from intent string to DEFINE artifact path |
| 3 | How deep is the mandatory pre-ignition interview in interactive `/auto`? | **Full interactive Brainstorm + Define gap questions** — zero `[ASSUMED]` before ignition | Phase 0/1 run with their native interactive conduct; autopilot's Brainstorm/Define overrides become dead code |
| 4 | After ignition (15/15 reached), does autonomy stay total? | **No — Design decisions with confidence < 0.80 come back to the user** (interactive mode) | The non-blocking invariant gains one explicit, ledger-recorded exception post-ignition |
| 5 | What does headless Design do at confidence < 0.80, since it cannot ask? | **Abort with the pending decision described in the report**; user resumes interactively | Resume protocol extended: an interactive resume re-asks the pending decision and continues |

**Minimum Questions:** 3 (asked 5)

---

## Sample Data Inventory

> Samples improve LLM accuracy through in-context learning and few-shot prompting.

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | N/A | 0 | No past RUN REPORTs with wrong auto-filled gaps identified |
| Output examples | N/A | 0 | No ideal-interview transcript provided |
| Ground truth | N/A | 0 | — |
| Related code | `.claude/skills/sdd-autopilot/SKILL.md`, `.claude/skills/sdd-define/SKILL.md`, `.claude/skills/sdd-brainstorm/SKILL.md` | 3 | Existing contracts (clarity score matrix, gap report shape, gate ledger) anchor the design |

**How samples will be used:**

- Existing gate ledger / gap report / clarity-breakdown formats serve as the schema reference for the new Ignition Gate rows and the "Pending Decision" report section.
- Synthetic test cases (raw intent in headless, DEFINE at 14/15, DEFINE at 15/15) will serve as pytest fixtures.

---

## Approaches Explored

### Approach A: Ignition by artifact ⭐ Recommended

**Description:** Autopilot policy begins at a 15/15 DEFINE for both entrypoints. Interactive `/auto` with a raw intent sequences the normal supervised phases (`sdd-brainstorm` interactive → `sdd-define` with gap questions until 15/15) and only then reaches **ignition**: the autonomous run opens (RUN REPORT, branch) and proceeds Design → Build → Ship → PR. Headless receives the finished DEFINE artifact as input. Autopilot's Brainstorm/Define conduct overrides are deleted as dead code.

**Pros:**

- Reuses the phase skills' native interactive conduct intact — zero new questioning machinery
- Perfect entrypoint symmetry: "a 15/15 DEFINE goes in, a PR comes out"
- The non-blocking invariant survives nearly intact — it holds from ignition onward
- Sequencing existing pieces is command-layer responsibility, exactly where the component model places it

**Cons:**

- The interview happens *outside* the run — Q&A is recorded in BRAINSTORM/DEFINE (Discovery table, clarity breakdown), not in the RUN REPORT
- `/auto` stops being "one intent in" in the strict sense

**Why Recommended:** Confidence ~0.90 — KB pattern + codebase match: the component model (`.claude/kb/shared/component-model.md`) assigns sequencing of existing pieces to commands, and `sdd-brainstorm`/`sdd-define` already implement 100% of the requested interview.

---

### Approach B: Interview inside the run

**Description:** `sdd-autopilot` gains an interactive/headless mode axis across **all** phases: the run opens first (RUN REPORT, branch), and Brainstorm/Define execute *inside* it with interactive conduct; the conduct-override table becomes two columns.

**Pros:**

- Unified auditability — the full interview Q&A lands in the RUN REPORT
- Branch and checkpoint commits also cover the intake phase

**Cons:**

- The skill becomes two policies in one file (every gate must define conduct ×2)
- The non-blocking invariant must be rewritten wholesale
- Much larger change surface for the same observable outcome

---

### Approach C: Harden the gate only (Optional)

**Description:** Gate 0 rises to 15/15 and aborts; no interview inside `/auto` — the gap report tells the user to run `/brainstorm` + `/define` manually and come back.

**Pros:**

- Minimal change

**Cons:**

- Does not deliver the mandatory in-flow questioning the user explicitly asked for (rejected in discovery question 3)

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-07-28 (interactive session) |
| **Reasoning** | Reuses existing interactive phase conduct with zero new questioning machinery; keeps single-source policy; clean pre-/post-ignition boundary matching the user's mental model |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | 15/15 threshold applies to autopilot ignition only | With a human supervising phase-by-phase, minor gaps are tolerable; supervised `/define` keeps 12/15 | Raising the supervised gate to 15/15 |
| 2 | Headless contract: DEFINE artifact in, raw intent = usage error | CI/cron cannot ask; forcing pre-validated input preserves the guarantee without pretending headless can interview | Fail-fast on raw intent below 15/15; dual-input |
| 3 | Full interactive Brainstorm + Define gap-filling before ignition | Zero `[ASSUMED]` pre-ignition — the machine never picks the approach or fills requirement gaps on the user's behalf | Targeted gap questions only, machine-selected approach |
| 4 | Post-ignition: Design decisions with confidence < 0.80 ask the user (interactive) | The user prefers a pause over a low-confidence assumption even mid-run | Preserving total autonomy with WARN rows |
| 5 | Headless < 0.80 → ABORT with pending decision in report, resumable interactively | Keeps headless terminating and honest; the decision is made by the user at resume, never assumed | `[ASSUMED]`+WARN (current behavior); paused-state + push notification |
| 6 | Brainstorm/Define conduct overrides deleted from `sdd-autopilot` | Neither entrypoint ever runs those phases autonomously again — dead policy is deleted, not kept "just in case" | Keeping the overrides behind a flag |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| `--min-clarity N` flag (accept < 15/15 consciously) | User chose a hard 15/15 gate; an escape hatch reintroduces the failure mode | Yes |
| "Paused (decision pending)" state + push notification for headless | Rejected in discovery Q5 — plain abort + interactive resume is simpler and always terminates | Yes |
| Formal DEFINE "certification" artifact (stamp/hash) | Ignition simply re-reads the Clarity Score Breakdown from the DEFINE on disk | Yes |
| Dual-input headless (raw intent OR DEFINE) | Rejected in discovery Q2 — one input surface to maintain | Yes |
| Raising supervised `/define` gate to 15/15 | Out of scope per discovery Q1 | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Lifecycle (pre-ignition interview, ignition gate, post-ignition flow, headless contract) | ✅ | "Sim, está correto" | No |
| Component change map (skill/command/runner/template/docs/tests + explicit non-changes) | ✅ | "Sim, pode escrever" | No |

**Minimum Validations:** 2 (completed 2)

---

## Suggested Requirements for /define

Based on this brainstorm session, the following should be captured in the DEFINE phase:

### Problem Statement (Draft)

Autopilot starts autonomous runs with clarity scores as low as 12/15 and silently fills the remaining requirement gaps with machine assumptions (`[ASSUMED]`), frequently implementing something different from what the user intended.

### Target Users (Draft)

| User | Pain Point |
|------|------------|
| AgentSpec maintainer running `/auto` interactively | Autonomous runs implement the wrong thing when the intent had unanswered gaps; discovering the divergence costs a full run |
| CI/cron operator using `autopilot.sh` | Headless runs proceed on under-specified intents with no opportunity to intervene |

### Success Criteria (Draft)

- [ ] Interactive `/auto` with a raw intent never opens a RUN REPORT or branch before a DEFINE at 15/15 exists (0 autonomous artifacts pre-ignition)
- [ ] BRAINSTORM/DEFINE documents produced via `/auto` contain 0 `[ASSUMED]` markers — every discovery question answered by the human
- [ ] `autopilot.sh` with a raw intent argument exits non-zero with a usage error pointing to interactive `/auto`
- [ ] `autopilot.sh` with a DEFINE below 15/15 aborts with a gap report naming every element scoring < 3
- [ ] Design decision with confidence < 0.80: interactive run asks the user (ledger row recorded); headless run aborts with a "Pending Decision" section in the report
- [ ] Resuming after a pending-decision abort re-asks exactly that decision and continues without regenerating any approved artifact

### Constraints Identified

- Single-source policy preserved: both entrypoints execute `sdd-autopilot`; no gate rule re-encoded in the command or runner
- Sensor ownership unchanged: clarity scoring (5 elements × 0–3) stays in `sdd-define`; the supervised 12/15 gate is untouched
- Every run must still terminate: the interactive < 0.80 pause exists only where a human is present; headless always resolves to a terminal state
- Public repository hygiene (no private references in any artifact)

### Out of Scope (Confirmed)

- `--min-clarity` escape-hatch flag
- Paused-state + push-notification infrastructure for headless
- Formal DEFINE certification artifact (stamp/hash)
- Dual-input headless runner
- Any change to the supervised `/define` 12/15 gate or the clarity sensor itself
- Judge V1+ features (multi-model ensemble, PostToolUse hook)

### Open Questions (for /define)

1. Does the Ignition Gate trust the Clarity Score Breakdown recorded in the DEFINE, or re-score from scratch?
2. Does the interactive < 0.80 question consume any budget/cap (e.g., interaction with `--max-iterations`)?
3. Exact shape of the "Pending Decision" section in `AUTOPILOT_RUN_TEMPLATE.md` (what the resume re-asks).

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 5 |
| Validations Completed | 2 |
| Duration | ~30 minutes |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_AUTOPILOT_IGNITION_GATE.md`
