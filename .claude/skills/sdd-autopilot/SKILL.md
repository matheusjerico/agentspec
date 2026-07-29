---
name: sdd-autopilot
description: |
  Single-source gate policy for Autopilot: a DEFINE re-scored at 15/15 ignites an autonomous SDD run (Design → Build → Ship → PR) with quality gates — not per-phase human approval — deciding proceed, retry, or abort. The mandatory pre-ignition interview (interactive Brainstorm + Define, human-answered until 15/15) happens before any run exists: the /auto command sequences it, and the headless runner requires the finished DEFINE artifact as its input. Owns the complete autonomous-run methodology — Gate I (ignition re-scoring, never trusting the recorded score), the gate policy table and retry budgets, Gate D (the low-confidence decision fork: ask the human in interactive mode, abort headless with a structured Pending Decision block), the per-phase auto-mode conduct overrides, the run lifecycle (ignition-first, checkpoint commits), the resume protocol including pending-decision re-asks, the RUN REPORT ledger obligations, abort semantics with gap reports, and the best-effort notification step. Consumed by both entrypoints: the /auto command (interactive) and plugin scripts/autopilot.sh (headless); neither restates a policy rule.
  Use when executing an autonomous SDD run — "/auto", "run the full workflow autonomously", "lights-out", "resume the autopilot run" — or when either entrypoint needs a gate's proceed/retry/abort rule.
  Do not use for a single supervised phase (use that phase's sdd-* skill), and do not use to change gate sensors — clarity scoring, lint contracts, and judge tiers are owned by their phases and by WORKFLOW_CONTRACTS.yaml; autopilot consumes them as-is.
---

# SDD Autopilot — autonomous execution from a validated DEFINE

A DEFINE re-scored at 15/15 in; an open PR or an actionable gap report out. This skill is the **only** place autopilot policy lives: the `/auto` command (interactive) and `scripts/autopilot.sh` (headless) both execute this file and add no rules of their own. Autopilot adds **policy, not sensors** — every gate below consumes an existing sensor whose contract is owned elsewhere (`WORKFLOW_CONTRACTS.yaml`, `tools/spec-linter/USAGE.md`, `tools/spec-judge/USAGE.md`, the sdd-define clarity rubric) and never reinterprets a verdict.

## The ignition boundary

**Nothing autonomous exists before Gate I passes, and a headless run NEVER waits for a human.**

- **Pre-ignition** is supervised territory: the interview that produces the DEFINE runs under `sdd-brainstorm` and `sdd-define` with their native interactive conduct — every discovery question and every clarity gap is answered by the human, zero `[ASSUMED]` markers. This skill does not govern the interview; it begins at Gate I.
- **Post-ignition**, every gate resolves to exactly one of: proceed, retry-within-budget, or abort-with-report. `AskUserQuestion` is forbidden for the rest of the run with exactly one sanctioned exception: **Gate D in interactive mode** (a Design decision below 0.80 confidence goes back to the human instead of becoming an assumption).
- Headless runs have no exceptions: Gate D maps to abort, every budget is finite, every run terminates.

## Entry forms (policy meaning — the command owns parsing)

| Argument form | Policy |
|---------------|--------|
| `"<intent>"` (quoted prose) | Interactive only: the command sequences supervised Phase 0 (`sdd-brainstorm`) and Phase 1 (`sdd-define`, gap questions until 15/15), then enters this skill at Gate I with the resulting DEFINE path |
| `<path to DEFINE_*.md>` | Straight to Gate I — the re-score decides; this is the only form the headless runner forwards |
| `FEATURE_NAME` (bare SCREAMING_SNAKE) | Resume protocol |

The headless runner rejects anything that is not an existing `DEFINE_{FEATURE}.md` path at preflight (usage error, exit 2) — a raw intent in CI is an invocation mistake, not a gate evaluation.

## Run lifecycle

```text
1. INTAKE     Resolve the DEFINE path (from the interview handoff, the path
              argument, or resume). Derive {FEATURE} from the DEFINE filename
              suffix; freeze it for the entire run. Parse flags. Check for an
              existing run (Resume).
2. OPEN       Create .claude/sdd/reports/AUTOPILOT_RUN_{FEATURE}.md from
              .claude/sdd/templates/AUTOPILOT_RUN_TEMPLATE.md — Status: In
              Progress, DEFINE path recorded, flags. The report exists before
              Gate I can possibly fail: 100%-of-runs reporting is structural.
3. GATE I     Ignition (procedure below). PASS → if on the default branch,
              create and switch to feat/auto-{feature-kebab}, otherwise reuse
              the current branch; checkpoint commit "auto({FEATURE}): ignition"
              including the pre-ignition interview artifacts. FAIL → gap
              report, Status ❌ Aborted (I), CLOSE. No branch, no phases.
4. DESIGN     Load sdd-design → apply the conduct override below (Gate D may
              fire here) → write the artifact → Gate L → Gate J → ledger rows →
              checkpoint commit "auto({FEATURE}): design complete".
5. BUILD      Load sdd-build; execute under its own decide-never-ask policy
              (delegation, per-file retry_limit 3, Step 5.5 whole-branch
              review). Per-task commits (Step 4.9, commit_parallel) compose
              with this phase's checkpoint commit — task commits land during
              the build, the checkpoint closes the phase; parallel dispatch
              of validated parallel_group tasks respects the run's agent
              budget. Gate L on the BUILD_REPORT (--phase build
              --legacy-mode fail). Then Gate R (review verdict), then Gate B.
              Checkpoint commit.
6. SHIP       Load sdd-ship. Gate S (pre-ship checklist). Archive. Final commit.
7. PR         /create-pr. URL into the report. (Skipped stages per flags.)
8. CLOSE      Terminal status into the report; delete .autopilot/ scratch;
              notification step (best-effort).
```

**Artifact identity invariant:** `{FEATURE}` is derived exactly once at INTAKE —
from the DEFINE filename suffix — and never re-derived by a later phase. DESIGN,
BUILD_REPORT, and AUTOPILOT_RUN must therefore share the identical suffix:

```text
.claude/sdd/features/DEFINE_{FEATURE}.md      (pre-ignition input)
.claude/sdd/features/DESIGN_{FEATURE}.md
.claude/sdd/reports/BUILD_REPORT_{FEATURE}.md
.claude/sdd/reports/AUTOPILOT_RUN_{FEATURE}.md
```

Before each phase writes its artifact, reject any proposed filename whose suffix
differs from the frozen `{FEATURE}`. A mismatch is an orchestration error: record
it and abort rather than creating a second feature identity.

**Context discipline (protocol obligation):** the loop carries forward only artifact paths and gate results. Each phase re-reads its input document from disk; never paste a prior phase's document body into the running context beyond what that phase's skill itself reads.

## Gate policy

| Gate | Sensor | PASS | Recoverable failure | Budget | Terminal failure | Sensor unavailable |
|------|--------|------|--------------------|--------|------------------|--------------------|
| **I — Ignition** | clarity **re-score** of the DEFINE read from disk (sdd-define rubric: 5 elements × 0–3; the recorded Clarity Score Breakdown is display metadata, never the sensor) | recomputed 15/15 → proceed | none — fail-fast | 0 | < 15/15 → ABORT with gap report (recomputed breakdown; discrepancy with the recorded score noted explicitly) | n/a (model-computed) |
| **L — Lint** | `tools/spec-linter/spec-lint <artifact> --phase <phase>` exit code; for the BUILD_REPORT the invocation is `--phase build --legacy-mode fail` — legacy reports fail closed under /auto (both severities are contract-declared in `build.report_contract.legacy`; the flag names the context, never reinterprets a verdict) | 0 → proceed | exit 1 → regenerate the document once with the violations in context, re-lint | 1 per document | second exit 1 → ABORT, violations in report | exit 2, or CLI not executable → VISIBLE SKIP row, proceed — never assume PASS |
| **J — Judge** | `tools/spec-judge/spec-judge <artifact> --spec <ephemeral spec> --tier standard` exit code | 0 with PASS → proceed | 0 with WARN → one refinement incorporating every finding verbatim, re-judge, then proceed regardless (standard tier is WARN-capped by construction) | 1 per document | none reachable at standard tier | exit 2 (config) / 3 (budget) / 4 (network), or CLI not executable → VISIBLE SKIP row with the code named, proceed |
| **D — Decision** | Design's own per-decision confidence (sdd-design confidence matrix) | ≥ 0.80 → inline ADR with `[ASSUMED]`, ledger-visible (unchanged conduct) | < 0.80 interactive → `AskUserQuestion`, answer recorded as a ledger row, proceed — **un-capped**: the human is the budget | none | < 0.80 headless → ABORT, Status `❌ Aborted (D)`, structured Pending Decision block in the report (resume re-asks it 1:1) | n/a (model-computed) |
| **P — Provision** | specialist-autoprovision citation check after `scripts/generate-agent-router.py` regeneration (sub-flow owned by that skill; sensor contract: the `create-agent` parser contract) | new component citable in the oracle, core checklist items pass → proceed | authoring/validation failure → regenerate the component once with the violations in context | 1 per gap | budget exhausted → ABORT, gap report names the domain, attempts, failing checks | script not executable / oracle unreadable → VISIBLE SKIP row, fall back to `(general)` + WARN — never assume PASS |
| **B — Build** | sdd-build per-file verification + BUILD_REPORT completeness | report shows 100% tasks complete, tests passing | per-file fix-and-retry (sdd-build owns it) | 3 per file | incomplete report after retries → ABORT, failed tasks listed | n/a |
| **R — Review** | BUILD_REPORT Review Verdict (`build.execution.final_review` — whole-branch `code-reviewer` dispatch, sdd-build Step 5.5) | verdict `clean` / `clean-with-minors` → proceed | Critical/Important findings → fix-loop round (fix + scoped re-review; sdd-build owns it) | 2 rounds per build | open findings after budget → ABORT, gap report lists open findings + fix history | reviewer dispatch failed after retry → verdict `missing` → ABORT (fails closed — never an assumed clean) |
| **S — Ship** | pre-ship checklist (`WORKFLOW_CONTRACTS.yaml` → `ship.pre_ship_checklist`; its contract-gate item re-runs `spec-lint --phase build --legacy-mode fail`) | all 6 items pass | none | 0 | any unmet item → ABORT, item named | n/a |
| **PR** | `/create-pr` outcome | PR URL returned | none | 0 | failure → terminal status **⚠ Partial Success**, exact manual command in report | n/a |

Gate ordering within the Design document phase is fixed: **Gate L, then Gate J** — the judge runs only after a lint PASS (ADR-003 `runs_after`; never on a structural FAIL, and not after a Gate L visible skip — a skipped lint is not a PASS, so Gate J records `SKIPPED (no lint PASS)` and the run proceeds). Design is the only phase inside the loop that takes the full L→J pair — Gate L alone also validates the BUILD_REPORT (`--phase build --legacy-mode fail`, after sdd-build Step 6.5 writes and self-checks it), and Gate J never runs on reports; the pre-ignition BRAINSTORM/DEFINE are validated by their own supervised phase gates before this skill ever runs.

`--max-iterations N` caps the **run-wide sum** of Gate L + Gate J regenerations (default: the per-gate budgets, i.e. up to 2 per document). It explicitly does **not** bound Gate D pauses. When the cap is hit, the next recoverable failure becomes terminal: ABORT with budget accounting.

### Gate I procedure (ignition)

1. Re-read `DEFINE_{FEATURE}.md` from disk (the path resolved at INTAKE).
2. **Re-score** the document against the sdd-define rubric (5 elements × 0–3).
   The recorded Clarity Score Breakdown is never consulted as the sensor.
3. Recomputed 15/15 → ledger row `I | ignition | 1 | re-score 15/15 | PASS`,
   create/reuse the branch, checkpoint commit, proceed to DESIGN.
4. Below 15/15 → append the Gap Report (one row per element scoring < 3, with
   the recomputed per-element breakdown; if the document's recorded total
   disagrees with the re-score, note the discrepancy in the report), set
   Status `❌ Aborted (I)`, CLOSE. Nothing autonomous has been created.

### Gate D procedure (low-confidence decision fork)

Fires the moment Design conduct produces a decision whose confidence is below
0.80 — before any default is applied:

- **Interactive:** fire `AskUserQuestion` with the decision's options and
  evidence; record the pause and the answer as a ledger row
  (`D | design | n | confidence 0.NN | ANSWERED`); apply the answer — the
  decision carries no `[ASSUMED]` marker. Un-capped: repeat for every such
  decision.
- **Headless:** write one Pending Decision block (shape owned by
  `AUTOPILOT_RUN_TEMPLATE.md`: ID, the exact question, options with per-option
  confidence and evidence, affected phase/file), ledger row
  (`D | design | 1 | confidence 0.NN | ABORT`), Status `❌ Aborted (D)`, CLOSE.
  The run stops at the first sub-threshold decision — at most one unresolved
  block exists at a time.

### Gate J procedure (ephemeral conformance spec)

The judge needs a spec; phase documents carry no frontmatter, so the loop materializes one per artifact:

```bash
SPEC_DIR=".claude/sdd/reports/.autopilot/${FEATURE}"
mkdir -p "$SPEC_DIR"
cat > "${SPEC_DIR}/spec_${PHASE}.yaml" <<EOF
name: autopilot-${PHASE}-conformance
intent: |
  ${INTENT}                                # the DEFINE's problem statement line
  Phase purpose: ${PHASE_PURPOSE}          # the phase's purpose line from WORKFLOW_CONTRACTS.yaml
output_contract:
  required_fields: [${PHASE_REQUIRED_SECTIONS}]   # that phase's required_sections list
EOF

tools/spec-judge/spec-judge "$ARTIFACT" --spec "${SPEC_DIR}/spec_${PHASE}.yaml" --tier standard
```

Standard tier only. Selecting a FAIL-eligible tier is a policy change, not a consumer option — see the boundary in the frontmatter. WARN findings feed exactly one refinement; the refined document is re-linted (a refinement can break structure) before the single re-judge. Re-lint after refinement draws from the same Gate L budget; if it is spent, a lint FAIL here is terminal.

The `.autopilot/` scratch directory is ephemeral: deleted at CLOSE, never committed, never archived.

## Auto-mode conduct overrides

Phase skills assume an interactive user. Under autopilot, these overrides apply — they change **conduct** (how the phase gets its answers), never the phase's output contract or quality gate. Brainstorm and Define have no rows here: those phases run only pre-ignition, supervised, with their native conduct.

| Phase | Interactive conduct | Autopilot override |
|-------|--------------------|--------------------|
| Design | Open questions may go back to the user | Confidence ≥ 0.80: the question becomes an inline ADR with the chosen default and an `[ASSUMED]` marker. Confidence < 0.80: **Gate D** — interactive asks the human (answer recorded, no assumption); headless aborts with the Pending Decision block |
| Build | Already decide-never-ask | Unchanged. CRITICAL-risk halt maps to ABORT-with-report (the halt is preserved; only the reporting surface changes) |
| Provisioning (within Design/Build) | The specialist-autoprovision layer fork may ask once at the component-model gate | Assume skill + thin executor, record `[ASSUMED]`; Gate P governs proceed/retry/abort |
| Ship | Minor issues → ask user (0.80 confidence branch) | Checklist is binding and mechanical: all 5 items pass → proceed; any unmet item → ABORT. The 0.80 "ask" branch maps to: record a WARN ledger row and proceed **iff** the checklist itself passes |

Every self-answered question, every `[ASSUMED]` marker, and every Gate D pause is mirrored into the RUN REPORT (Autonomous Decisions table; Gate D rows in the ledger) — the run is reviewable after the fact because everything it decided or asked is on the record.

## Resume protocol

Resume is the default; `--fresh` is not a flag (delete the RUN REPORT to force a fresh run — an explicit human act).

1. **Match:** on `/auto`, look for `AUTOPILOT_RUN_*.md` whose `{FEATURE}` matches the DEFINE filename suffix (path form) or equals the argument (bare feature name form).
2. **Pending decision first:** if the report's Status is `❌ Aborted (D)` with an unresolved Pending Decision block — interactive resume rebuilds the `AskUserQuestion` **1:1 from the block** (options verbatim, nothing reinterpreted), records the answer as a ledger row, marks the block `✅ Resolved`, sets Status back to `🔄 In Progress`, and continues from Design. A headless invocation pointed at such a run cannot ask: it re-aborts idempotently with the same block.
3. **Replay:** read the Gate Ledger; find the last gate row with outcome PASS (or VISIBLE SKIP) per phase.
4. **Verify survivors:** for each phase at or before that point, confirm the artifact exists on disk. Artifact existence alone is NOT approval — the ledger row is; a document present on disk whose gate never passed is regenerated. (Gate I on resume follows the same rule: an approved ignition row is trusted; absent one, the DEFINE is re-scored.)
5. **Continue:** resume at the first phase without an approved gate, on the recorded branch, appending to the same report. Approved artifacts are never regenerated (0 regenerations of approved work).
6. A report whose Status is already terminal (`✅`/`⚠`) — or `❌ Aborted` on a gate other than D with nothing left to answer — plus the same `{FEATURE}` → for `✅`/`⚠`, do nothing except print the report path and state the run is closed; for `❌ Aborted (I)`, the fix is amending the DEFINE (interactively) and re-running, which re-enters at Gate I. Re-opening a shipped run is `/iterate` territory, not autopilot's.

## RUN REPORT obligations

- Created at OPEN, before Gate I can possibly fail — 100%-of-runs reporting is structural, not aspirational.
- Shape: `.claude/sdd/templates/AUTOPILOT_RUN_TEMPLATE.md`. Follow it; do not invent sections.
- **Gate Ledger:** one row per gate evaluation — including every retry, every visible skip (with the exit code or reason), every Gate D pause or abort, every skipped-by-flag stage. Appended the moment the gate resolves, never batched at the end.
- **Autonomous Decisions:** every self-answered question, `[ASSUMED]` marker, and decision fork resolved without a human (Gate D answers are ledger rows, not `[ASSUMED]` entries).
- **Gap report (on Gate I abort):** one row per clarity element scoring < 3 in the **recomputed** breakdown — the element, its recomputed score, and precisely what information is missing to raise it; plus an explicit note when the recorded total disagreed with the re-score.
- **Pending Decision (on Gate D abort):** one structured block per the template's shape; at most one unresolved block at a time; resolved blocks stay in the report as the audit trail.
- **Human Interactions** (Terminal Summary): the count of Gate D pauses answered during the run, with their PD/ledger references — `0` on a fully lights-out run.
- Terminal Status values: `✅ Success (PR: <url>)` · `⚠ Partial Success` · `❌ Aborted (<gate>)`.
- Never echo environment values or secrets; sensors are recorded as present/absent, keys are never printed.

## Flags (semantics — the command owns parsing)

| Flag | Policy meaning |
|------|----------------|
| `--no-brainstorm` | Intent form only: skip supervised Phase 0; the intent feeds the interactive Define directly. No-op (documented) for the path and resume forms; not offered by the headless runner |
| `--no-judge` | Gate J skipped; ledger rows `SKIPPED (flag)` — coverage narrowed visibly |
| `--no-ship` | Stop after BUILD (+ PR unless `--no-pr`); no archive; Gate S not evaluated |
| `--no-pr` | Terminal state after SHIP; report records the branch as the deliverable |
| `--max-iterations N` | Run-wide Gate L + Gate J regeneration cap (see Gate policy); never bounds Gate D |

## Notification step (best-effort by contract)

Fire-and-forget, after the terminal status is written — a notification failure changes nothing about the run outcome and becomes one ledger note:

1. **Terminal summary** — always, both entrypoints: terminal status, report path, PR URL if any.
2. **OS notification** — headless runner only (`osascript` on darwin, `notify-send` on linux, skip silently if absent).
3. **Webhook** — headless runner only, iff `AUTOPILOT_WEBHOOK_URL` is set: POST `{feature, status, pr_url, report_path}`, 10s timeout.

The RUN REPORT is the authoritative record; notifications are conveniences.

## Anti-patterns

| Never do | Why | Instead |
|----------|-----|---------|
| Ask the user anything post-ignition outside Gate D | Breaks the ignition boundary | Decide per the conduct overrides; record the decision |
| Trust the DEFINE's recorded clarity score at Gate I | One hand-edit defeats the entire guarantee | Re-score from the document content; the recorded breakdown is display metadata |
| Apply an `[ASSUMED]` default to a sub-0.80 Design decision | The exact failure mode this gate exists to remove | Gate D: ask (interactive) or abort with the Pending Decision block (headless) |
| Treat lint/judge exit ≥ 2 as PASS | Assumed verdicts poison every downstream phase | VISIBLE SKIP row; proceed with coverage narrowed loudly |
| Re-encode a gate rule in the command or runner | Two policies drift; parity dies | Both entrypoints execute this file |
| Regenerate an approved artifact on resume | Wastes the checkpoint; risks divergence from the approved state | Trust the ledger, verify existence, continue |
| Pad a DEFINE to clear Gate I | Fabricated requirements compound through every phase | Abort with a gap report naming what is missing; fix the DEFINE interactively |
| Run Gate J after a Gate L skip or FAIL | Violates ADR-003 `runs_after` | Judge only on a real lint PASS |
| Commit or archive `.autopilot/` scratch | Ephemeral working files in permanent history | Delete at CLOSE |

## References

- Entrypoints: `.claude/commands/workflow/auto.md` (interactive) · `plugin-extras/scripts/autopilot.sh` (headless; `scripts/autopilot.sh` in the installed plugin)
- Report template: `.claude/sdd/templates/AUTOPILOT_RUN_TEMPLATE.md`
- Sensor contracts: `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` (`contract_enforcement`, `behavioral_enforcement`, `build.execution`, `ship.pre_ship_checklist`) · `tools/spec-linter/USAGE.md` · `tools/spec-judge/USAGE.md` · clarity rubric: `.claude/skills/sdd-define/SKILL.md`
- Phase methodologies: `.claude/skills/sdd-brainstorm|define|design|build|ship/SKILL.md` (Brainstorm/Define: pre-ignition, supervised)
- Provisioning methodology (Gate P's sub-flow): `.claude/skills/specialist-autoprovision/SKILL.md`
- Design rationale: `.claude/sdd/features/DESIGN_AUTOPILOT.md` (Decisions 1–6) · `.claude/sdd/features/DESIGN_AUTOPILOT_IGNITION_GATE.md` (ignition model, Gates I/D)
