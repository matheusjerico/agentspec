# AUTOPILOT RUN: Risk Profiles

> Autonomous run record for RISK_PROFILES — the run's single source of state (resume replays the Gate Ledger) and its authoritative report. Created at OPEN, before Gate I can possibly fail; rows appended the moment each gate resolves.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | RISK_PROFILES |
| **Artifact Suffix** | RISK_PROFILES — immutable, derived from the DEFINE filename; DESIGN, BUILD_REPORT, and AUTOPILOT_RUN must all use this exact suffix |
| **Started** | 2026-07-29 16:33Z |
| **Entrypoint** | /auto (interactive) |
| **DEFINE (input)** | .claude/sdd/features/DEFINE_RISK_PROFILES.md |
| **Flags** | none |
| **Branch** | feat/auto-risk-profiles |
| **Status** | 🔄 In Progress |

---

## Gate Ledger

> One row per gate evaluation — every retry, every visible skip (exit code or reason named), every Gate D pause or abort, every skipped-by-flag stage. Appended live, never batched. Tokens/Cost are optional (COULD-scope); leave `-` when not measured.

| Gate | Phase | Attempt | Sensor result | Outcome | Timestamp | Tokens | Cost |
|------|-------|---------|---------------|---------|-----------|--------|------|
| I | ignition | 1 | re-score 15/15 (P3/U3/G3/S3/Sc3); spec-lint --phase define exit 0 | PASS | 2026-07-29T16:33Z | - | - |
| L | design | 1 | spec-lint --phase design exit 0 | PASS | 2026-07-29T16:40Z | - | - |
| J | design | 1 | spec-judge exit 3 (daily evaluation budget exhausted: 12/10 calls) | SKIP:exit3 | 2026-07-29T16:41Z | - | - |

**Outcome legend:** PASS · FAIL (recoverable, retry follows) · REFINE (judge WARN fed one regeneration) · ANSWERED (Gate D interactive pause resolved by the human) · SKIP:{reason} (visible skip — sensor could not run; never an assumed PASS) · SKIPPED (flag) · ABORT (terminal)

---

## Phase Artifacts

> The interview artifacts (BRAINSTORM/DEFINE) are produced pre-ignition under supervised conduct; the ignition checkpoint commit brings them onto the run branch.

| Phase | Artifact | Checkpoint Commit | Gate Summary |
|-------|----------|-------------------|--------------|
| Ignition | .claude/sdd/features/DEFINE_RISK_PROFILES.md | 4f5cdcf — "auto(RISK_PROFILES): ignition" | I: re-score 15/15 |
| Design | .claude/sdd/features/DESIGN_RISK_PROFILES.md | pending | L: PASS · J: SKIP:exit3 (budget) · D: 0 pauses (4 [ASSUMED] ≥ 0.85) |
| Build | pending | - | - |
| Ship | pending | - | - |
| PR | pending | - | - |

---

## Autonomous Decisions

> Every self-answered question, every `[ASSUMED]` marker, every decision fork resolved without a human. Gate D answers are NOT rows here — they are human decisions, recorded as ANSWERED ledger rows and (on headless aborts) Pending Decision blocks. This table plus those records is why the run is reviewable after the fact.

| # | Phase | Decision Point | Chose | Confidence | Rationale |
|---|-------|----------------|-------|------------|-----------|
| 1 | interview | Phase 0 conduct for a plan-sourced intent | Treated the ratified plan (§2–§4 evidence, §21 YAGNI) as the Phase 0 artifact; no separate BRAINSTORM | 0.95 | The plan is the maintainer-validated exploration; re-interviewing already-decided approaches adds noise, not clarity |
| 2 | design | Where define-phase WARN rules live (A-001) | New `DefinePhaseContract`, CLI-routed with fallback | 0.90 | Mirrors Increment 1's BuildReportContract precedent; keeps the generic contract untouched |
| 3 | design | Profile representation in the DEFINE | Fenced YAML block inside `## Risk Profile` | 0.85 | Matches the plan §8.1 model verbatim; deterministic fence+safe_load parse |
| 4 | design | Elevation-rule semantics | `{trigger, floor}` data; skill applies floors, linter checks the max rule | 0.90 | Keeps the deterministic core machine-verified; trigger applicability auditable via reasons |
| 5 | design | Severity ceiling this increment | All `RP.*` findings WARN; required_sections untouched | 0.95 | Plan §17.2/§18: Observe/Warn — only the pre-existing CRITICAL halt stays fail-closed |

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
