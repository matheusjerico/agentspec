# AUTOPILOT RUN: {Feature Name}

> Autonomous run record for {FEATURE} — the run's single source of state (resume replays the Gate Ledger) and its authoritative report. Created at OPEN, before Gate I can possibly fail; rows appended the moment each gate resolves.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | {FEATURE_NAME} |
| **Artifact Suffix** | {FEATURE_NAME} — immutable, derived from the DEFINE filename; DESIGN, BUILD_REPORT, and AUTOPILOT_RUN must all use this exact suffix |
| **Started** | {YYYY-MM-DD HH:MMZ} |
| **Entrypoint** | /auto (interactive) / autopilot.sh (headless) |
| **DEFINE (input)** | {path to DEFINE_{FEATURE}.md — the run's input artifact} |
| **Flags** | {flags passed, or "none"} |
| **Branch** | {feat/auto-{feature-kebab} — created only after Gate I passes} |
| **Status** | 🔄 In Progress / ✅ Success (PR: {url}) / ⚠ Partial Success / ❌ Aborted ({gate}) |

---

## Gate Ledger

> One row per gate evaluation — every retry, every visible skip (exit code or reason named), every Gate D pause or abort, every skipped-by-flag stage. Appended live, never batched. Tokens/Cost are optional (COULD-scope); leave `-` when not measured.

| Gate | Phase | Attempt | Sensor result | Outcome | Timestamp | Tokens | Cost |
|------|-------|---------|---------------|---------|-----------|--------|------|
| {I/L/J/D/P/B/S/PR} | {phase} | {n} | {e.g., re-score 15/15 · spec-lint exit 0 · confidence 0.72 · spec-judge WARN (B1 ×1) · exit 3 budget} | {PASS / FAIL / REFINE (budget x/y) / ANSWERED / SKIP:exit2 / SKIP:unavailable / SKIPPED (flag) / ABORT} | {ISO-8601} | - | - |

**Outcome legend:** PASS · FAIL (recoverable, retry follows) · REFINE (judge WARN fed one regeneration) · ANSWERED (Gate D interactive pause resolved by the human) · SKIP:{reason} (visible skip — sensor could not run; never an assumed PASS) · SKIPPED (flag) · ABORT (terminal)

---

## Phase Artifacts

> The interview artifacts (BRAINSTORM/DEFINE) are produced pre-ignition under supervised conduct; the ignition checkpoint commit brings them onto the run branch.

| Phase | Artifact | Checkpoint Commit | Gate Summary |
|-------|----------|-------------------|--------------|
| Ignition | {DEFINE path (input)} | {short SHA — "auto({FEATURE}): ignition"} | {I: re-score 15/15 · or ABORT (I)} |
| Design | {path} | {short SHA} | {e.g., L:PASS · J:REFINE→PASS · D: {n} ANSWERED} |
| Build | {BUILD_REPORT path} | {short SHA} | {B: 100% complete} |
| Ship | {archive folder} | {short SHA} | {S: 4/4 checklist} |
| PR | {URL or "skipped (flag)" or "failed — see Partial Success"} | - | {…} |

---

## Autonomous Decisions

> Every self-answered question, every `[ASSUMED]` marker, every decision fork resolved without a human. Gate D answers are NOT rows here — they are human decisions, recorded as ANSWERED ledger rows and (on headless aborts) Pending Decision blocks. This table plus those records is why the run is reviewable after the fact.

| # | Phase | Decision Point | Chose | Confidence | Rationale |
|---|-------|----------------|-------|------------|-----------|
| 1 | {phase} | {what was open} | {choice} | {0.80–1.00} | {why this is the safest documented default} |

---

## Retry & Budget Accounting

| Budget | Limit | Spent | Notes |
|--------|-------|-------|-------|
| Gate L regenerations | 1 per document | {n} | {which documents} |
| Gate J refinements | 1 per document | {n} | {which documents} |
| Gate D pauses | un-capped (interactive) / 0 (headless — aborts) | {n} | {ledger refs; the human is the budget} |
| Build per-file retries | 3 per file | {n} | {which files} |
| `--max-iterations` cap | {N or "default"} | {n} | {L+J only — never Gate D; hit? → terminal} |

---

## Gap Report (on Gate I abort — otherwise "N/A")

> One row per clarity element scoring < 3 in the breakdown **recomputed at ignition** — the recorded score in the DEFINE is display metadata and was not consulted. This is the actionable output of an aborted ignition.

| Element | Recomputed Score | What is missing |
|---------|------------------|-----------------|
| {Problem / Users / Goals / Success / Scope} | {0–2} | {precisely what information would raise this to 3} |

**Recorded-score discrepancy:** {none / "DEFINE records {X}/15 but re-score computed {Y}/15 — the re-score wins"}

**To relaunch:** amend the DEFINE interactively (`/define` gap questions, or `/auto "<intent>"` to re-enter the interview), then re-run `/auto {DEFINE path}`.

---

## Pending Decision (on Gate D abort — otherwise "N/A")

> One structured block per Gate D abort. The interactive resume rebuilds its AskUserQuestion **1:1 from this block** — options verbatim, nothing reinterpreted. At most one unresolved block exists at a time; resolved blocks remain as the audit trail.

### PD-{n}: {one-line decision title}

| Attribute | Value |
|-----------|-------|
| **Phase / File** | Design — {artifact or manifest row affected} |
| **Question** | {the exact question, as it would have been asked} |
| **Status** | ⏳ Pending / ✅ Resolved ({answer}, {ISO-8601}) |

| Option | Confidence | Evidence |
|--------|------------|----------|
| {option A} | {0.00–1.00} | {KB/codebase evidence found} |
| {option B} | {0.00–1.00} | {evidence} |

**To resume:** `/auto {FEATURE}` in an interactive session — the pending question is re-asked first; the run continues from Design on answer.

---

## Notification Attempts

| Tier | Target | Result |
|------|--------|--------|
| Terminal summary | stdout | {shown} |
| OS notification | {osascript / notify-send / n/a} | {sent / tool absent / failed — run outcome unchanged} |
| Webhook | {set? (URL never printed)} | {2xx / failed — run outcome unchanged / not configured} |

---

## Terminal Summary

| Metric | Value |
|--------|-------|
| **Terminal Status** | {✅ / ⚠ / ❌ as in Metadata} |
| **Phases Completed** | {n}/5 (ignition · design · build · ship · PR) |
| **Gates Evaluated** | {n} ({p} PASS · {f} FAIL · {a} ANSWERED · {s} skips) |
| **Total Regenerations** | {n} |
| **Human Interactions** | {n} Gate D pauses answered ({ledger/PD refs, or 0 — fully lights-out}) |
| **PR** | {URL or "-"} |
| **Manual Follow-up** | {none / exact command, on Partial Success} |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {YYYY-MM-DD} | autopilot | Run opened |
