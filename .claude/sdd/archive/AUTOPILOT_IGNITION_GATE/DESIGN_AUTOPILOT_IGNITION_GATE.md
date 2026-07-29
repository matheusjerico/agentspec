# DESIGN: Autopilot Ignition Gate

> Technical design for implementing the Autopilot Ignition Gate — mandatory human-answered pre-ignition interview, 15/15 re-scored ignition, and the low-confidence decision fork.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTOPILOT_IGNITION_GATE |
| **Date** | 2026-07-28 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_AUTOPILOT_IGNITION_GATE.md](./DEFINE_AUTOPILOT_IGNITION_GATE.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                        AUTOPILOT IGNITION GATE                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  INTERACTIVE                              HEADLESS (CI/cron)             │
│  /auto "<intent>"                         autopilot.sh <DEFINE-path>     │
│      │                                        │                          │
│      ▼                                        │  raw intent? ──► exit 2  │
│  ┌────────────────────────────┐               │  (usage error)           │
│  │ PRE-IGNITION (human-answered) │            │                          │
│  │ sdd-brainstorm (native      │              │                          │
│  │   interactive conduct)      │              │                          │
│  │ sdd-define (gap questions   │              │                          │
│  │   until 15/15)              │              │                          │
│  │ abandoned? → Needs          │              │                          │
│  │   Clarification, NO run     │              │                          │
│  └──────────┬─────────────────┘               │                          │
│             ▼                                 ▼                          │
│  ┌──────────────────────────────────────────────────────────┐            │
│  │ 🔥 GATE I — IGNITION (sdd-autopilot policy)              │            │
│  │ re-read DEFINE from disk → RE-SCORE per sdd-define       │            │
│  │ rubric → 15/15? open run (REPORT+branch) : ABORT (I)     │            │
│  │ with gap report — recorded score is NEVER trusted        │            │
│  └──────────┬───────────────────────────────────────────────┘            │
│             ▼                                                            │
│  ┌──────────────────────────────────────────────────────────┐            │
│  │ AUTONOMOUS LOOP (unchanged shape)                        │            │
│  │ DESIGN → Gates L/J → BUILD → Gate B → SHIP → Gate S → PR │            │
│  │                                                          │            │
│  │ Design decision confidence < 0.80 — GATE D fork:         │            │
│  │   interactive → AskUserQuestion (un-capped, ledger row)  │            │
│  │   headless    → ABORT (D) + Pending Decision block       │            │
│  │                 resume re-asks 1:1 and continues         │            │
│  └──────────────────────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| Gate I (Ignition) | Replaces Gate 0: re-reads the DEFINE from disk and re-scores it against the sdd-define rubric at ignition time; 15/15 opens the run, anything less aborts with a gap report | `sdd-autopilot/SKILL.md` policy (markdown) |
| Pre-ignition sequencer | Runs `sdd-brainstorm` then `sdd-define` with their **native interactive conduct** before engaging autopilot policy; nothing autonomous exists until Gate I passes | `commands/workflow/auto.md` (thin entrypoint) |
| Headless input contract | `autopilot.sh` accepts only an existing `DEFINE_{FEATURE}.md` path; any other argument is a preflight usage error (exit 2) | Bash (`plugin-extras/scripts/autopilot.sh`) |
| Gate D (Decision) fork | Design decision at confidence < 0.80: interactive asks the user (unlimited, one ledger row per pause); headless aborts with a Pending Decision block | `sdd-autopilot/SKILL.md` conduct override |
| Pending Decision block | Structured ADR-like block in the RUN REPORT: ID, exact question, options with per-option confidence, evidence, affected phase/file — the resume re-asks it 1:1 | `AUTOPILOT_RUN_TEMPLATE.md` section |
| Resume extension | `❌ Aborted (D)` runs resume interactively: rebuild the `AskUserQuestion` from the block, apply the answer, continue without regenerating approved artifacts | `sdd-autopilot/SKILL.md` resume protocol |

---

## Key Decisions

### Decision 1: Gate I re-scores the DEFINE — the recorded score is never trusted

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted (user-confirmed in Define session) |
| **Date** | 2026-07-28 |

**Context:** The headless entrypoint receives a DEFINE that may be days old or hand-edited; the interactive path could carry a stale breakdown after manual tweaks. A gate that reads the recorded total can be satisfied by editing one table cell.

**Choice:** At ignition, the loop re-reads `DEFINE_{FEATURE}.md` from disk and recomputes the clarity score against the rubric owned by `sdd-define` (5 elements × 0–3). Only a recomputed 15/15 ignites. The recorded breakdown is display metadata, never a sensor.

**Rationale:** Consistent with the existing resume principle "artifact existence alone is NOT approval". The sensor stays owned by `sdd-define`; autopilot consumes it — no rubric duplication.

**Alternatives Rejected:**
1. Trust the recorded total — one hand-edit defeats the entire guarantee (AT-005 exists to prevent exactly this).
2. Trust + structural validation only — catches malformed tables, not inflated scores.

**Consequences:**
- Model-computed re-scoring may vary marginally on a borderline document (risk A-002); the gap report prints the recomputed breakdown so the user can amend and retry.
- Headless ignition costs one extra document read + scoring pass — negligible against a full run.

---

### Decision 2: Pre-ignition interview lives in the command layer; ignition policy in the skill

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** The mandatory interview must run before anything autonomous exists. Something has to sequence it, and the component model assigns sequencing of existing pieces to commands, policy to skills.

**Choice:** `auto.md` (entrypoint) sequences: load `sdd-brainstorm` → run interactively → load `sdd-define` → iterate gap questions until 15/15 → invoke `sdd-autopilot` starting at Gate I. The skill's run lifecycle begins at Gate I; Brainstorm/Define conduct-override rows are deleted from the skill (dead policy — no entrypoint runs those phases autonomously).

**Rationale:** Reuses the phase skills' native interactive conduct untouched (DEFINE assumption A-001, validated by reading both skills — no auto-aware changes needed). Single-source policy preserved: the command adds sequencing, zero gate rules.

**Alternatives Rejected:**
1. Interview inside the run (skill gains an interactive/headless axis in every phase) — two policies per gate, wholesale invariant rewrite, larger change surface for identical observable behavior (rejected in Brainstorm as Approach B).
2. Abort-only Gate 0 at 15/15 — returns homework instead of conducting the mandatory interview (rejected as Approach C).

**Consequences:**
- The interview's Q&A audit trail lives in BRAINSTORM/DEFINE documents (Discovery table, clarity breakdown), not the RUN REPORT — accepted trade-off from Brainstorm.
- RUN REPORT and branch are created only at ignition; `{FEATURE}` derivation moves from intent parsing to the DEFINE filename.

---

### Decision 3: `/auto` argument surface — intent, DEFINE path, or feature name

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** Headless must pass a DEFINE path through to the policy loop, and interactive users who already hold a 15/15 DEFINE should not be forced through a redundant interview.

**Choice:** `/auto` accepts exactly three argument forms:

| Argument | Path |
|----------|------|
| `"<intent>"` (quoted prose) | Pre-ignition interview → Gate I |
| `<path to DEFINE_*.md>` | Straight to Gate I (re-score decides) |
| `FEATURE_NAME` (bare) | Resume protocol (unchanged) |

`autopilot.sh` forwards **only** the DEFINE-path form; `{FEATURE}` is derived from the DEFINE filename suffix at ignition and frozen as today.

**Rationale:** One policy loop, three doors. The DEFINE-path form is what headless forwards, and it doubles as the interactive shortcut — Gate I re-scores in every case, so no door weakens the guarantee.

**Alternatives Rejected:**
1. Headless-only DEFINE-path form — forces interactive users with a ready DEFINE through a no-op interview.
2. A separate `/auto-headless` command — second entrypoint to keep in policy parity for zero behavioral gain.

**Consequences:**
- `--no-brainstorm` becomes meaningful only for the intent form (skip Phase 0, straight to interactive Define); documented as a no-op for the other two forms.
- Argument classification rule (in the command): existing file whose basename matches `DEFINE_*.md` → path form; SCREAMING_SNAKE bare word → resume; anything else → intent.

---

### Decision 4: Gate D — the low-confidence fork is a gate, not a WARN

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted (user-confirmed in Brainstorm/Define sessions) |
| **Date** | 2026-07-28 |

**Context:** Today a Design decision below 0.80 confidence adds a WARN row and proceeds on an `[ASSUMED]` default — the user explicitly rejected machine assumptions at that threshold. The threshold and per-decision confidence values already exist in Design conduct (DEFINE assumption A-003, validated).

**Choice:** Formalize the fork as **Gate D** in the gate policy table: sensor = Design's own per-decision confidence; < 0.80 → interactive mode fires `AskUserQuestion` (un-capped — the human is the budget; one ledger row per pause; answer recorded, no `[ASSUMED]`); headless mode → ABORT with terminal status `❌ Aborted (D)` and a Pending Decision block. Decisions ≥ 0.80 keep today's conduct (inline ADR + `[ASSUMED]`, ledger-visible).

**Rationale:** A ledger-visible gate keeps every pause auditable and gives the abort a first-class terminal state the runner already maps to exit 1. Un-capped is deliberate: capping human answers contradicts the feature's premise, and `--max-iterations` continues to bound only Gate L/J regenerations.

**Alternatives Rejected:**
1. Keep WARN-and-proceed — the exact failure mode this feature exists to remove.
2. Cap interactive pauses per run — aborts a legitimate run with a willing human present, on an arbitrary number.

**Consequences:**
- The non-blocking invariant is rewritten: *"Post-ignition, a headless run never waits for a human; an interactive run pauses only at Gate D."* Terminal Summary's `Human Interactions` row changes from `0 (invariant)` to a count with Gate D references.
- Every run still terminates: headless maps the pause to ABORT; interactive pauses resolve by answer.

---

### Decision 5: Pending Decision block — structured, resume re-asks 1:1

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted (user-confirmed in Define session) |
| **Date** | 2026-07-28 |

**Context:** A headless Gate D abort is only actionable if the resume can reconstruct the exact question without reinterpretation.

**Choice:** The RUN REPORT gains a `Pending Decision (on Gate D abort — otherwise "N/A")` section holding one structured block per aborted decision (shape in Code Patterns, Pattern 2): ID, exact question, options with per-option confidence and evidence, affected phase/file. Interactive resume detects `❌ Aborted (D)`, builds the `AskUserQuestion` 1:1 from the block (options verbatim), records the answer as a ledger row, marks the block resolved, and continues from Design without regenerating approved artifacts.

**Rationale:** Deterministic and auditable — the question asked at resume is provably the question the run aborted on.

**Alternatives Rejected:**
1. Free-text description — resume must reinterpret prose; non-deterministic reconstruction.

**Consequences:**
- Exactly one pending decision per abort (the run stops at the first < 0.80 decision); the section holds at most one unresolved block at a time.
- Resume ordering: Gate D resolution precedes any further Design work on resume.

---

### Decision 6: Headless usage error is preflight, not a gate

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** A raw intent handed to `autopilot.sh` must fail before any Claude invocation — burning a headless session to discover a wrong argument type wastes a CI slot.

**Choice:** Argument validation happens in the script's existing preflight (exit 2 family): the argument must be an existing file, basename matching `^DEFINE_[A-Z0-9_]+\.md$`, resolved against the repository root. Failure prints a usage error naming the contract and pointing to interactive `/auto`. No new exit codes: 0/1/2/3 semantics unchanged (`❌ Aborted (I)` and `❌ Aborted (D)` both map to the existing exit 1).

**Rationale:** The script stays policy-free — it validates argument *shape*, never content; scoring stays in the skill. Existing exit-code consumers (CI configs) keep working.

**Alternatives Rejected:**
1. Forward anything and let Gate I sort it out — spends a full headless invocation to report a usage mistake.
2. New exit code for usage errors — breaks the documented 0/1/2/3 contract for no consumer benefit.

**Consequences:**
- `autopilot.sh --help`, header comment, and usage examples rewritten for the DEFINE-path contract; `--no-brainstorm` removed from headless help (meaningless without an intent form).

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `.claude/skills/sdd-autopilot/SKILL.md` | Modify | Gate I policy (re-score), Gate D fork + gate table rows, invariant rewrite, lifecycle (run starts at ignition), delete Brainstorm/Define conduct rows, resume extension (Pending Decision), flag semantics | (general) — `create-skill` + `sdd-autopilot` loaded | None |
| 2 | `.claude/commands/workflow/auto.md` | Modify | Pre-ignition sequencing (interactive Phase 0+1), three-form argument surface, rewritten usage/examples/invariants | (general) — `component-model` loaded (thin-entrypoint boundary) | 1 |
| 3 | `plugin-extras/scripts/autopilot.sh` | Modify | DEFINE-path input contract in preflight, usage/help rewrite, prompt forwarding `/auto "<path>"` | @shell-script-specialist | 1 |
| 4 | `.claude/sdd/templates/AUTOPILOT_RUN_TEMPLATE.md` | Modify | Gate legend I/D, Pending Decision section, Human Interactions row (count + Gate D refs), gap report retitled for Gate I | (general) — `component-model` loaded (template shape ownership) | 1 |
| 5 | `tests/test_autopilot_runner.py` | Modify | Contract cases: raw intent → exit 2 + pointer message; missing file → exit 2; non-DEFINE basename → exit 2; valid path → prompt forwards `/auto "<path>"`; Aborted report → exit 1 (existing pattern) | @test-generator | 3 |
| 6 | `docs/getting-started/autopilot.md` | Modify | Two-entrypoint contract, ignition model, Gate D behavior, resume of pending decisions | @code-documenter | 1, 2, 3 |
| 7 | `CLAUDE.md` | Modify | Active Development Tasks row + command table line for `/auto` reflecting the ignition model | @code-documenter | 6 |

**Total Files:** 7

---

## Agent Assignment Rationale

> Agents discovered from `.claude/agents/` — Build phase invokes matched specialists. Citations resolved against `.claude/skills/agent-router/routing.json` per specialist-autoprovision; no gaps found, no provisioning events.

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @shell-script-specialist | 3 | Citation: routing one-liner "Elite shell scripting specialist for building production-grade Bash scripts with best practices, error handling" — `autopilot.sh` is exactly that surface |
| @test-generator | 5 | Citation: routing one-liner "Test automation expert for Python. Generates pytest unit tests, integration tests, and fixtures"; `kb_domains: [testing]` hit — extends the existing stub-based integration suite |
| @code-documenter | 6, 7 | Citation: routing one-liner "Documentation specialist for creating comprehensive, production-ready documentation" — user-guide and project-doc updates |
| (general) | 1, 2, 4 | Skill citations (not gaps): file 1 → `create-skill` (repo skill-authoring conventions); files 2, 4 → `component-model` (thin-entrypoint boundary; template-shape ownership). Policy/markdown edits the main loop handles with those skills loaded |

**Agent Discovery:**
- Scanned: `.claude/skills/agent-router/routing.json` (generated oracle; ad-hoc greps are never the sensor)
- Matched by: routing one-liners, `kb_domains` signals, file type

---

## Code Patterns

### Pattern 1: Headless argument validation (autopilot.sh preflight)

```bash
# Preflight: the single positional argument must be an existing DEFINE artifact.
# Shape-only validation — scoring belongs to Gate I in the skill.
validate_define_argument() {
    local arg="$1"
    if [[ ! -f "$arg" ]]; then
        fail_preflight "argument is not an existing file: ${arg}
Headless autopilot requires a pre-validated DEFINE document.
Produce one interactively first:  /auto \"<intent>\"
Then relaunch:                    $(basename "$0") .claude/sdd/features/DEFINE_{FEATURE}.md"
    fi
    local base
    base="$(basename "$arg")"
    if [[ ! "$base" =~ ^DEFINE_[A-Z0-9_]+\.md$ ]]; then
        fail_preflight "argument must be a DEFINE_{FEATURE}.md artifact, got: ${base}"
    fi
    DEFINE_PATH="$arg"
}

build_prompt() {
    local escaped_path
    escaped_path="$(escape_for_double_quotes "$DEFINE_PATH")"
    PROMPT="/auto \"${escaped_path}\""
    if [[ ${#PASSTHROUGH_ARGS[@]} -gt 0 ]]; then
        PROMPT+=" ${PASSTHROUGH_ARGS[*]}"
    fi
}
```

### Pattern 2: Pending Decision block (RUN REPORT template section)

```markdown
## Pending Decision (on Gate D abort — otherwise "N/A")

> One structured block per Gate D abort. The interactive resume rebuilds its
> AskUserQuestion 1:1 from this block — options verbatim, nothing reinterpreted.

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

**To resume:** `/auto {FEATURE}` in an interactive session — the pending
question is re-asked first; the run continues from Design on answer.
```

### Pattern 3: Gate I procedure (skill policy — replaces the Gate 0 row)

```markdown
### Gate I procedure (ignition)

1. Resolve the DEFINE path (from the interview handoff, the path argument, or
   resume) and re-read it from disk.
2. RE-SCORE the document against the sdd-define rubric (5 elements × 0–3).
   The recorded Clarity Score Breakdown is display metadata — never the sensor.
3. Recomputed 15/15 → open the run: create AUTOPILOT_RUN_{FEATURE}.md, create
   or reuse the feat/auto-{feature-kebab} branch, append ledger row
   `I | ignition | 1 | re-score 15/15 | PASS`.
4. Anything below 15/15 → ABORT before anything autonomous exists: write the
   RUN REPORT with Status ❌ Aborted (I) and the Gap Report — one row per
   element scoring < 3, with the recomputed breakdown. No branch, no phases.
5. {FEATURE} is derived from the DEFINE filename suffix and frozen (identity
   invariant unchanged).
```

### Pattern 4: Runner contract test (extends existing stub pattern)

```python
def test_raw_intent_argument_is_a_usage_error(tmp_path: Path) -> None:
    """A prose intent must fail preflight (exit 2) before any claude call."""
    repo, bin_dir, argv_file = _make_repo_with_stub(tmp_path, status_row=None)
    result = _run(repo, ["Add a --dry-run flag to the rollout script"],
                  path_dirs=f"{bin_dir}:{BASE_PATH}")
    assert result.returncode == 2
    assert "DEFINE" in result.stderr        # names the contract
    assert "/auto" in result.stderr         # points to the interactive path
    assert not argv_file.exists()           # claude was never invoked
```

---

## Data Flow

```text
1. User states an intent: /auto "make ingestion resilient"
   │
   ▼
2. Interactive Phase 0 (sdd-brainstorm, native conduct): discovery questions
   one at a time, user selects approach, YAGNI validated → BRAINSTORM doc
   │
   ▼
3. Interactive Phase 1 (sdd-define): entity extraction → clarity score →
   targeted gap questions until re-scored 15/15 → DEFINE doc
   │   (user abandons → DEFINE saved "Needs Clarification"; flow ENDS — no run)
   ▼
4. Gate I: DEFINE re-read from disk, re-scored → 15/15 → RUN REPORT + branch
   created; {FEATURE} frozen from filename          (< 15/15 → ❌ Aborted (I))
   │
   ▼
5. Autonomous loop: DESIGN (Gates L/J) → BUILD (Gate B) → SHIP (Gate S) → PR
   │
   ├─ 5a. Design decision ≥ 0.80 → inline ADR [ASSUMED], ledger-visible (as today)
   └─ 5b. Design decision < 0.80 → GATE D:
          interactive: AskUserQuestion → answer → ledger row → continue
          headless:    ❌ Aborted (D) + Pending Decision block
                        → /auto FEATURE (interactive) re-asks 1:1 → continue
   │
   ▼
6. Terminal: ✅ Success (PR) / ⚠ Partial / ❌ Aborted (I|D|L|J|P|B|S)
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| `claude` CLI (headless invocation) | `claude -p "/auto \"<define-path>\"" --permission-mode acceptEdits` | User's existing Claude Code session |
| `tools/spec-linter` / `tools/spec-judge` | CLI sensors for Gates L/J (unchanged) | None (spec-judge: `OPENROUTER_API_KEY`, unchanged) |
| `AUTOPILOT_WEBHOOK_URL` webhook | Best-effort POST after terminal status (unchanged) | None; URL never printed |
| GitHub via `/create-pr` | PR stage (unchanged) | `gh` CLI |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Integration (runner contract) | AT-003 + argument-shape matrix: raw intent / missing file / bad basename → exit 2, no claude call; valid DEFINE path → prompt `/auto "<path>"`; Aborted status → exit 1 | `tests/test_autopilot_runner.py` | pytest + claude stub (existing suite pattern) | Every new preflight branch |
| Structural (documents) | Edited SKILL/command/template lint-clean; this DESIGN + DEFINE pass their phase contracts | phase artifacts | `tools/spec-linter/spec-lint` | Exit 0 on all bound artifacts |
| E2E scenario walkthroughs (manual, scripted in BUILD_REPORT) | AT-001 (interview → ignition), AT-002 (abandonment → no run), AT-004/005 (headless re-score aborts incl. inflated recorded score), AT-006 (interactive Gate D pause), AT-007/008 (headless Gate D abort → resume re-ask, 0 regenerations) | scenario checklist | live `/auto` session | All 8 acceptance tests exercised |

Conduct rules (interview mandatoriness, Gate D fork) live in markdown policy executed by the model — they are verified by the E2E walkthroughs and the ledger/report artifacts they must produce, not by pytest.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Raw intent / bad path to `autopilot.sh` | Preflight usage error, exit 2, claude never invoked; message names the DEFINE contract and points to interactive `/auto` | No — user fixes invocation |
| DEFINE re-scores < 15/15 at Gate I | `❌ Aborted (I)`; gap report with recomputed per-element breakdown; no branch, no autonomous artifacts | No budget — user amends the DEFINE (interactively) and relaunches |
| Recorded 15/15 but re-score lower (AT-005) | Same as above; gap report notes the discrepancy explicitly | No |
| User abandons the interview | No run, no report; DEFINE saved `Needs Clarification` (sdd-define's own status rules) | Re-run `/auto` anytime — resume of the *interview* is just re-running `/define` |
| Design decision < 0.80, interactive | Gate D pause: AskUserQuestion, answer recorded as ledger row, continue | N/A — human answer resolves it; un-capped |
| Design decision < 0.80, headless | `❌ Aborted (D)` + Pending Decision block; exit 1 via existing status mapping | Resume interactively: `/auto FEATURE` re-asks 1:1 |
| Claude invocation timeout / crash (headless) | Unchanged: runner defers to RUN REPORT status; missing report → exit 2 | Resume protocol (unchanged) |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `AUTOPILOT_TIMEOUT_MIN` | int | `60` | Unchanged — minutes before the headless claude invocation is killed |
| `AUTOPILOT_WEBHOOK_URL` | string | unset | Unchanged — best-effort terminal notification |
| `AUTOPILOT_LOG` | string | unset | Unchanged — transcript append path |
| `--max-iterations N` | flag | per-gate budgets | Unchanged scope — bounds Gate L/J regenerations only; explicitly does NOT bound Gate D pauses |
| `--no-brainstorm` | flag | off | Re-scoped: intent form only — skip interactive Phase 0, go straight to interactive Define; no-op (documented) for path/resume forms; removed from headless help |

No new configuration keys are introduced.

---

## Security Considerations

- The DEFINE path is shell-quoted through the existing `escape_for_double_quotes` helper before prompt embedding; basename regex rejects surprise argument shapes at preflight.
- No secrets or environment values in the RUN REPORT (existing rule, unchanged); the Pending Decision block records evidence and options — never credentials or private context (public-repo hygiene gate applies).
- Webhook URL never logged or printed (unchanged).
- Gate I re-scoring reads only repo-local artifacts; no new network surface anywhere in the change.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Gate Ledger rows for every Gate I evaluation and every Gate D pause/abort (gate id, sensor result, outcome, timestamp) — appended live, as today |
| Metrics | Terminal Summary `Human Interactions` row: count of Gate D pauses with PD references (replaces the hardcoded `0 (invariant)`); gap report carries the recomputed breakdown |
| Tracing | Pending Decision blocks (PD-n) link abort → resume → resolution across sessions; Phase Artifacts table unchanged |

---

## Pipeline Architecture (if applicable)

Not applicable — this feature changes workflow policy, one shell contract, and documentation; no data pipelines, ETL, or analytics are involved.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-28 | design-agent | Initial version from DEFINE_AUTOPILOT_IGNITION_GATE.md; assumptions A-001/A-003/A-004 validated during design (A-002 mitigated via gap-report breakdown) |
| 1.1 | 2026-07-28 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_AUTOPILOT_IGNITION_GATE.md`
