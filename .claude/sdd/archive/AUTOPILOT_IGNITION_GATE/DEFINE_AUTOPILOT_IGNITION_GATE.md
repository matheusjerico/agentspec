# DEFINE: Autopilot Ignition Gate

> Autopilot may only start its autonomous loop from a DEFINE re-scored at 15/15 — the pre-ignition interview is mandatory and human-answered, and no requirement gap is ever machine-filled on the user's behalf.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTOPILOT_IGNITION_GATE |
| **Date** | 2026-07-28 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 15/15 |

---

## Problem Statement

Autopilot currently ignites autonomous runs at clarity scores as low as 12/15 and silently machine-fills the remaining requirement gaps with `[ASSUMED]` markers, frequently implementing something different from what the user intended — and the divergence is only discovered after a full run has burned through Design, Build, and Ship.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| AgentSpec maintainer | Runs `/auto` interactively | Autonomous runs implement the wrong thing when the intent had unanswered gaps; discovering the divergence costs a full run |
| CI/cron operator | Invokes `scripts/autopilot.sh` headlessly | Headless runs proceed on under-specified intents with no opportunity to intervene |

---

## Goals

What success looks like (prioritized):

| Priority | Goal |
|----------|------|
| **MUST** | Ignition Gate: the autonomous loop starts only from a DEFINE that **re-scores** 15/15 at ignition time (the gate recomputes the clarity score from the document content; it never trusts the recorded breakdown) |
| **MUST** | Interactive `/auto` sequences full interactive Phase 0 + Phase 1 (`sdd-brainstorm` and `sdd-define` native conduct) before ignition — zero `[ASSUMED]` markers pre-ignition; the human answers every discovery and gap question |
| **MUST** | Headless contract: `autopilot.sh` accepts only a `DEFINE_{FEATURE}.md` path; a raw intent argument is a usage error (exit ≠ 0), not a gate evaluation |
| **MUST** | Post-ignition exception: a Design decision with confidence < 0.80 asks the user in interactive mode (unlimited, each pause ledger-recorded) and ABORTs in headless mode with a structured Pending Decision block |
| **MUST** | Resume after a pending-decision abort re-asks exactly that decision — an `AskUserQuestion` built 1:1 from the Pending Decision block — then continues without regenerating any approved artifact |
| **MUST** | The Brainstorm and Define conduct-override rows are deleted from `sdd-autopilot` (dead policy — neither entrypoint runs those phases autonomously anymore) |
| **SHOULD** | `AUTOPILOT_RUN_TEMPLATE.md` gains an Ignition Gate ledger row shape and the Pending Decision section |
| **SHOULD** | `docs/getting-started/autopilot.md` and `CLAUDE.md` document the new two-entrypoint contract |
| **SHOULD** | pytest coverage for the new `autopilot.sh` input contract (raw intent → error; DEFINE < 15/15 → gap report; DEFINE 15/15 → ignition) |
| **COULD** | Ledger analytics note: count of interactive < 0.80 pauses per run surfaced in the RUN REPORT summary |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] 0 autonomous artifacts (RUN REPORT, `feat/auto-*` branch, checkpoint commits) created before a DEFINE re-scores 15/15 in interactive `/auto`
- [ ] 0 `[ASSUMED]` markers in BRAINSTORM/DEFINE documents produced through interactive `/auto`
- [ ] 100% of raw-intent invocations of `autopilot.sh` exit non-zero with a usage error pointing to interactive `/auto`
- [ ] 100% of headless ignitions on a DEFINE re-scoring < 15/15 abort with a gap report naming every element scoring < 3
- [ ] 100% of Design decisions with confidence < 0.80 produce either a ledger-recorded user answer (interactive) or a Pending Decision block + abort (headless) — 0 `[ASSUMED]` fallbacks at that threshold
- [ ] Resume after a pending-decision abort asks exactly 1 question (the pending decision) and regenerates 0 approved artifacts
- [ ] Supervised `/define` gate unchanged: 12/15 threshold appears intact in `sdd-define` after the change

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Interactive happy path | A raw intent with gaps | `/auto "<intent>"` runs | Interactive Brainstorm + Define interview executes; after 15/15 re-score, ignition opens RUN REPORT + branch and the run proceeds autonomously |
| AT-002 | User abandons interview | Define iteration ends below 15/15 (user stops answering) | The interview cannot reach 15/15 | No RUN REPORT, no branch, nothing autonomous; DEFINE saved as `Needs Clarification` |
| AT-003 | Headless raw intent | `autopilot.sh "add a flag to X"` | The runner parses its argument | Exit ≠ 0 with usage error naming the DEFINE-path contract and pointing to interactive `/auto` |
| AT-004 | Headless under-specified DEFINE | A DEFINE whose content re-scores 14/15 | `autopilot.sh <path>` runs the Ignition Gate | ABORT with gap report: one row per element < 3, score, and what is missing |
| AT-005 | Stale recorded score | A DEFINE whose breakdown table claims 15/15 but whose content re-scores 13/15 | The Ignition Gate re-scores | ABORT with gap report — the re-score verdict wins over the recorded value |
| AT-006 | Interactive low-confidence design decision | Post-ignition Design hits a decision at confidence < 0.80 | The decision is evaluated | `AskUserQuestion` fires; the answer and pause are ledger-recorded; the run continues; no `[ASSUMED]` marker |
| AT-007 | Headless low-confidence design decision | Same decision in a headless run | The decision is evaluated | ABORT; RUN REPORT contains a structured Pending Decision block (ID, exact question, options with confidence each, evidence, affected phase/file) |
| AT-008 | Resume after pending decision | An aborted run from AT-007 | `/auto FEATURE_NAME` runs interactively | The pending decision is re-asked 1:1 from the block; on answer, the run continues from Design without regenerating approved artifacts |

---

## Out of Scope

Explicitly NOT included in this feature:

- `--min-clarity` escape-hatch flag (a conscious-risk bypass reintroduces the failure mode)
- "Paused (decision pending)" run state + push-notification infrastructure for headless (plain abort + interactive resume instead)
- Formal DEFINE certification artifact (stamp/hash) — re-scoring at ignition makes it unnecessary
- Dual-input headless runner (raw intent OR DEFINE) — one input surface only
- Any change to the supervised `/define` 12/15 gate or to the clarity sensor itself (5 elements × 0–3)
- Judge V1+ features (multi-model ensemble, PostToolUse hook, automated escalation)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Single-source policy: both entrypoints execute `sdd-autopilot`; no gate rule re-encoded in the command or runner | The Ignition Gate, < 0.80 conduct fork, and resume extension are written once, in the skill |
| Technical | Sensor ownership unchanged: clarity scoring lives in `sdd-define`; 15/15 is autopilot policy consuming that sensor | `sdd-define` is not edited; the skill's scoring rubric is referenced, never duplicated |
| Technical | Every run must terminate: the < 0.80 pause exists only where a human is present; headless always reaches a terminal state | Headless maps the pause to ABORT — no waiting state exists |
| Technical | Public repository hygiene — no private references in any artifact | All examples and docs use sanitized content |
| Resource | No new external dependencies or infrastructure | Changes are markdown (skill/command/template/docs), one shell script contract, and pytest cases |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `.claude/skills/sdd-autopilot/SKILL.md`, `.claude/commands/workflow/auto.md`, `plugin-extras/scripts/autopilot.sh`, `.claude/sdd/templates/AUTOPILOT_RUN_TEMPLATE.md`, `docs/getting-started/autopilot.md`, `CLAUDE.md`, `tests/` | Policy in the skill; entrypoints change sequencing/input contract only; template + docs + tests support |
| **KB Domains** | `shared` (component-model), `testing` | Layer decisions per the component model; pytest patterns for the runner contract |
| **IaC Impact** | None | Markdown, one shell script, tests |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Assumptions

Assumptions that if wrong could invalidate the design:

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | The native interactive conduct of `sdd-brainstorm`/`sdd-define` needs no modification to serve as the pre-ignition interview | Those skills would need auto-aware changes, growing scope beyond the autopilot layer | [ ] |
| A-002 | Re-scoring an unchanged DEFINE at ignition is stable (model-computed scoring is consistent for the same content) | A genuine 15/15 DEFINE could spuriously fail ignition; mitigation: the gap report shows the breakdown so the user amends and retries | [ ] |
| A-003 | Design conduct already produces per-decision confidence values against the 0.80 threshold (today: `< 0.80 → WARN row`) | The confidence computation itself would need defining first — a prerequisite work item | [ ] |
| A-004 | No in-flight autopilot runs exist in the old format that need resume migration | Resume would need a compatibility shim for pre-change RUN REPORTs | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Specific failure mode with named mechanism (`[ASSUMED]` gap-filling past a 12/15 gate) and quantified impact (a full wasted run) |
| Users | 3 | Two personas with distinct, concrete pain points (interactive maintainer, headless operator) |
| Goals | 3 | Six MUSTs each independently testable; all three brainstorm open questions resolved by the user in this session (re-score at ignition; unlimited un-capped interactive pauses; structured ADR-like Pending Decision block) |
| Success | 3 | Seven measurable criteria with explicit counts (0 artifacts pre-ignition, 0 `[ASSUMED]`, 100% usage-error exits, exactly 1 resume question) |
| Scope | 3 | Six explicit exclusions carried from validated YAGNI; boundaries user-confirmed twice (lifecycle and component map validations) |
| **Total** | **15/15** | |

**Scoring Guide:**
- 0 = Missing entirely
- 1 = Vague or incomplete
- 2 = Clear but missing details
- 3 = Crystal clear, actionable

**Minimum to proceed: 12/15**

---

## Open Questions

None - ready for Design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-28 | define-agent | Initial version from BRAINSTORM_AUTOPILOT_IGNITION_GATE.md; three open questions resolved with the user (ignition re-scoring, un-capped interactive pauses, structured Pending Decision block) |
| 1.1 | 2026-07-28 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_AUTOPILOT_IGNITION_GATE.md`
