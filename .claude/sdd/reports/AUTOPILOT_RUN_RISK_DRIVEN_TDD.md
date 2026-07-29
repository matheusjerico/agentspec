# AUTOPILOT RUN: Risk Driven TDD

> Autonomous run record for RISK_DRIVEN_TDD — the run's single source of state (resume replays the Gate Ledger) and its authoritative report. Created at OPEN, before Gate I can possibly fail; rows appended the moment each gate resolves.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | RISK_DRIVEN_TDD |
| **Artifact Suffix** | RISK_DRIVEN_TDD — immutable, derived from the DEFINE filename; DESIGN, BUILD_REPORT, and AUTOPILOT_RUN must all use this exact suffix |
| **Started** | 2026-07-29 17:47Z |
| **Entrypoint** | /auto (interactive) |
| **DEFINE (input)** | .claude/sdd/features/DEFINE_RISK_DRIVEN_TDD.md |
| **Flags** | none |
| **Branch** | feat/auto-risk-driven-tdd |
| **Status** | 🔄 In Progress |

---

## Gate Ledger

> One row per gate evaluation — every retry, every visible skip (exit code or reason named), every Gate D pause or abort, every skipped-by-flag stage. Appended live, never batched. Tokens/Cost are optional (COULD-scope); leave `-` when not measured.

| Gate | Phase | Attempt | Sensor result | Outcome | Timestamp | Tokens | Cost |
|------|-------|---------|---------------|---------|-----------|--------|------|
| I | ignition | 1 | re-score 15/15 (P3/U3/G3/S3/Sc3); spec-lint --phase define exit 0 (RP.* clean) | PASS | 2026-07-29T17:47Z | - | - |
| L | design | 1 | spec-lint --phase design exit 0 — v2 task manifest validated by live TM.* rules | PASS | 2026-07-29T17:52Z | - | - |
| J | design | 1 | spec-judge exit 3 (daily budget) | SKIP:exit3 | 2026-07-29T17:52Z | - | - |

**Outcome legend:** PASS · FAIL (recoverable, retry follows) · REFINE (judge WARN fed one regeneration) · ANSWERED (Gate D interactive pause resolved by the human) · SKIP:{reason} (visible skip — sensor could not run; never an assumed PASS) · SKIPPED (flag) · ABORT (terminal)

---

## Phase Artifacts

> The interview artifacts (BRAINSTORM/DEFINE) are produced pre-ignition under supervised conduct; the ignition checkpoint commit brings them onto the run branch.

| Phase | Artifact | Checkpoint Commit | Gate Summary |
|-------|----------|-------------------|--------------|
| Ignition | .claude/sdd/features/DEFINE_RISK_DRIVEN_TDD.md | ae02600 — ignition | I: re-score 15/15 |
| Design | .claude/sdd/features/DESIGN_RISK_DRIVEN_TDD.md | pending | L: PASS (TM live) · J: SKIP:exit3 · D: 0 pauses (4 [ASSUMED] ≥ 0.85) |
| Build | pending | - | - |
| Ship | pending | - | - |
| PR | pending | - | - |

---

## Autonomous Decisions

> Every self-answered question, every `[ASSUMED]` marker, every decision fork resolved without a human. Gate D answers are NOT rows here — they are human decisions, recorded as ANSWERED ledger rows and (on headless aborts) Pending Decision blocks. This table plus those records is why the run is reviewable after the fact.

| # | Phase | Decision Point | Chose | Confidence | Rationale |
|---|-------|----------------|-------|------------|-----------|
| 1 | interview | Phase 0 conduct for a plan-sourced intent | Ratified plan §10 as the Phase 0 artifact | 0.95 | Same maintainer-ratified basis as prior runs |

---

## Retry & Budget Accounting

| Budget | Limit | Spent | Notes |
|--------|-------|-------|-------|
| Gate L regenerations | 1 per document | 0 | - |
| Gate J refinements | 1 per document | 0 | - |
| Gate D pauses | un-capped (interactive) | 0 | - |
| Build per-file retries | 3 per file | 0 | - |
| `--max-iterations` cap | default | 0 | L+J only — never Gate D |

---

## Gap Report (on Gate I abort — otherwise "N/A")

N/A

---

## Pending Decision (on Gate D abort — otherwise "N/A")

N/A

---

## Notification Attempts

| Tier | Target | Result |
|------|--------|--------|
| Terminal summary | stdout | pending |
| OS notification | n/a (interactive entrypoint) | - |
| Webhook | not configured | - |

---

## Terminal Summary

| Metric | Value |
|--------|-------|
| **Terminal Status** | 🔄 In Progress |
| **Phases Completed** | 0/5 (ignition · design · build · ship · PR) |
| **Gates Evaluated** | 1 (1 PASS) |
| **Total Regenerations** | 0 |
| **Human Interactions** | 0 |
| **PR** | - |
| **Manual Follow-up** | - |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | autopilot | Run opened |
