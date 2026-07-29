# AUTOPILOT RUN: Workflow Metrics

> Autonomous run record for WORKFLOW_METRICS — the run's single source of state (resume replays the Gate Ledger) and its authoritative report. Created at OPEN, before Gate I can possibly fail; rows appended the moment each gate resolves.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | WORKFLOW_METRICS |
| **Artifact Suffix** | WORKFLOW_METRICS — immutable, derived from the DEFINE filename; DESIGN, BUILD_REPORT, and AUTOPILOT_RUN must all use this exact suffix |
| **Started** | 2026-07-29 23:15Z |
| **Entrypoint** | /auto (interactive) |
| **DEFINE (input)** | .claude/sdd/features/DEFINE_WORKFLOW_METRICS.md |
| **Flags** | none |
| **Branch** | feat/auto-workflow-metrics |
| **Status** | 🔄 In Progress |

---

## Gate Ledger

> One row per gate evaluation — every retry, every visible skip (exit code or reason named), every Gate D pause or abort, every skipped-by-flag stage. Appended live, never batched. Tokens/Cost are optional (COULD-scope); leave `-` when not measured.

| Gate | Phase | Attempt | Sensor result | Outcome | Timestamp | Tokens | Cost |
|------|-------|---------|---------------|---------|-----------|--------|------|
| I | ignition | 1 | re-score 15/15 (P3/U3/G3/S3/Sc3); spec-lint --phase define exit 0 | PASS | 2026-07-29T23:15Z | - | - |

**Outcome legend:** PASS · FAIL (recoverable, retry follows) · REFINE (judge WARN fed one regeneration) · ANSWERED (Gate D interactive pause resolved by the human) · SKIP:{reason} (visible skip — sensor could not run; never an assumed PASS) · SKIPPED (flag) · ABORT (terminal)

---

## Phase Artifacts

> The interview artifacts (BRAINSTORM/DEFINE) are produced pre-ignition under supervised conduct; the ignition checkpoint commit brings them onto the run branch.

| Phase | Artifact | Checkpoint Commit | Gate Summary |
|-------|----------|-------------------|--------------|
| Ignition | .claude/sdd/features/DEFINE_WORKFLOW_METRICS.md | pending (this commit) | I: re-score 15/15 |
| Design | pending | - | - |
| Build | pending | - | - |
| Ship | pending | - | - |
| PR | pending | - | - |

---

## Autonomous Decisions

> Every self-answered question, every `[ASSUMED]` marker, every decision fork resolved without a human. Gate D answers are NOT rows here — they are human decisions, recorded as ANSWERED ledger rows and (on headless aborts) Pending Decision blocks. This table plus those records is why the run is reviewable after the fact.

| # | Phase | Decision Point | Chose | Confidence | Rationale |
|---|-------|----------------|-------|------------|-----------|
| 1 | interview | Phase 0 conduct | Ratified plan §15 as the Phase 0 artifact | 0.95 | Same basis as prior runs |

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

> One row per clarity element scoring < 3 in the breakdown **recomputed at ignition** — the recorded score in the DEFINE is display metadata and was not consulted. This is the actionable output of an aborted ignition.

| Element | Recomputed Score | What is missing |
|---------|------------------|-----------------|
N/A



---

## Pending Decision (on Gate D abort — otherwise "N/A")

> One structured block per Gate D abort. The interactive resume rebuilds its AskUserQuestion **1:1 from this block** — options verbatim, nothing reinterpreted. At most one unresolved block exists at a time; resolved blocks remain as the audit trail.

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
