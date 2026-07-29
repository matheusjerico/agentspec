# DESIGN: Build Quality Gates

> Technical design for implementing Build Quality Gates

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | BUILD_QUALITY_GATES |
| **Date** | 2026-07-29 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_BUILD_QUALITY_GATES.md](./DEFINE_BUILD_QUALITY_GATES.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│              BUILD QUALITY GATES — MODIFIED PHASE 3→4 FLOW               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  /build DESIGN ──→ tasks ──→ per-file verify ──→ full validation         │
│      │                                              │                    │
│      │ [--tdd] per code task: RED (observed) →      ▼                    │
│      │         GREEN → evidence row          ┌──────────────────┐        │
│      │                                       │ STEP 5.5 (NEW)   │        │
│      │                                       │ WHOLE-BRANCH     │        │
│      │                                       │ REVIEW           │        │
│      │                                       │ @code-reviewer   │        │
│      │                                       │ merge-base→HEAD  │        │
│      │                                       │ DEFINE ATs=lens  │        │
│      │                                       └────────┬─────────┘        │
│      │                              Critical/Important│    Minor         │
│      │                              ┌─────────────────┤      │           │
│      │                              ▼                 │      ▼           │
│      │                        FIX LOOP (≤2 rounds,    │  recorded        │
│      │                        scoped re-review)       │      │           │
│      │                              └────────┬────────┴──────┘           │
│      ▼                                       ▼                           │
│  BUILD_REPORT ◄── ## Review Verdict (clean / clean-with-minors /         │
│      │                dirty / missing) + ## TDD Evidence (--tdd)         │
│      ▼                                                                   │
│  /ship — Build Report Validation [NEW item: verdict present & clean?]    │
│      │        missing/dirty → Cannot ship → route back to /build         │
│      ▼                                                                   │
│  /auto — Gate R consumes the same verdict: fix loop budget 2 → abort     │
│           with gap report (pre_ship_checklist now 5 items)               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| sdd-build Step 5.5 | Whole-branch adversarial review + fix loop + verdict recording; `--tdd` per-task conduct | Skill markdown (`.claude/skills/sdd-build/SKILL.md`) |
| BUILD_REPORT template sections | `## Review Verdict` (findings + resolutions) and `## TDD Evidence` shapes | Template markdown |
| sdd-ship verdict check | Build Report Validation + readiness matrix + quality gate refuse missing/dirty verdicts | Skill markdown |
| sdd-autopilot Gate R | Autonomous policy row: review findings → retry 2 → abort with gap report; Gate S checklist 4→5 items | Skill markdown |
| Contract registration | `build.execution.final_review` block + `ship.pre_ship_checklist` item `review_verdict_clean` | `WORKFLOW_CONTRACTS.yaml` |
| `/build --tdd` surface | Flag parsing row in the command entrypoint (thin — semantics live in the skill) | Command markdown |
| Doc-contract test suite | pytest assertions that every surface above exists and is consistent | `tests/test_build_quality_gates.py` |

---

## Key Decisions

### Decision 1: Review executor, scope, and lens

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted (pre-decided by DEFINE constraints) |
| **Date** | 2026-07-29 |

**Context:** The gate needs a reviewer, a diff scope, and review criteria.

**Choice:** Dispatch the existing `code-reviewer` agent via the Task tool on the `git merge-base <default-branch> HEAD`→`HEAD` diff, with the feature's DEFINE acceptance criteria passed as the review lens, severity taxonomy Critical/Important/Minor.

**Rationale:** DEFINE constraints mandate reusing `code-reviewer` (citable in routing.json) and skill-layer policy. The merge-base scope reviews exactly what the branch adds — the benchmark's UTC bug lived in exactly such a diff.

**Alternatives Rejected:**
1. New dedicated reviewer agent — rejected: DEFINE out-of-scope; `code-reviewer` exists.
2. Per-file review during task execution — rejected: whole-branch context is what caught the benchmark bugs; per-file review misses cross-file behavior.

**Consequences:**
- Review quality is bounded by a same-model single reviewer (risk A-002; Judge V1+ is the escalation path).
- The dispatch is one Task call at build end — cost is bounded and predictable.

### Decision 2: Verdict taxonomy `[ASSUMED]`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted `[ASSUMED]` (confidence 0.90) |
| **Date** | 2026-07-29 |

**Context:** Ship must mechanically distinguish shippable from non-shippable reports.

**Choice:** Four verdict values: `clean` (no findings or all resolved) · `clean-with-minors` (only Minor findings recorded) · `dirty` (unresolved Critical/Important) · `missing` (no Review Verdict section). Ship proceeds on `clean`/`clean-with-minors`, refuses on `dirty`/`missing`.

**Rationale:** Mirrors the existing Ship Readiness Matrix rows (Ship immediately / Ship with notes / Cannot ship); `missing` fails safe — an absent verdict is never treated as clean.

**Alternatives Rejected:**
1. Boolean clean/dirty — rejected: loses the "ship with notes" middle row the matrix already has.
2. Numeric score — rejected: severities are the reviewer's native output; a score invents precision.

**Consequences:**
- `missing` blocking ship makes the gate effectively mandatory for all builds after this feature ships.

### Decision 3: Supervised-mode fix-loop budget `[ASSUMED]`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted `[ASSUMED]` (confidence 0.85) |
| **Date** | 2026-07-29 |

**Context:** DEFINE fixes the `/auto` budget (Gate R: 2 rounds → abort) but not the supervised `/build` loop bound.

**Choice:** Same 2-round budget in supervised mode; on exhaustion, record the open findings as a Blocker in the BUILD_REPORT (existing blocker mechanics) with verdict `dirty` and recommend `/iterate`.

**Rationale:** One budget, one behavior — the supervised/autonomous fork differs only in the terminal surface (Blocker row vs. run abort), matching how sdd-build already handles blockers.

**Alternatives Rejected:**
1. Unbounded supervised loop — rejected: violates "all budgets bounded" invariant.
2. Superpowers' 5-round breaker — rejected in DEFINE discovery (Q2): 2 chosen, benchmark evidence shows 1 round sufficed.

**Consequences:**
- A stubborn finding stops the build in both modes; the human resolves via `/iterate` or manual fix.

### Decision 4: `--tdd` composition with per-file verification `[ASSUMED]`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted `[ASSUMED]` (confidence 0.85) |
| **Date** | 2026-07-29 |

**Context:** sdd-build already verifies per file with retry ≤3; RED-GREEN must compose with it, and not every manifest row is code.

**Choice:** With `--tdd`, each code-bearing task becomes: write failing test → run and observe the expected failure (evidence captured) → implement minimal code → run to green → existing per-file verification. Non-code tasks (markdown, YAML, templates) record `TDD: n/a (non-code artifact)` in the TDD Evidence table.

**Rationale:** Wrapping (not replacing) the existing loop keeps default behavior untouched (AT-006) and makes the flag purely additive.

**Alternatives Rejected:**
1. TDD for all tasks including docs — rejected: no meaningful failing test exists for prose; would force theater.
2. Replace per-file verification with TDD — rejected: loses lint/type checks.

**Consequences:**
- Test files precede implementation files in dependency order when the flag is set.

### Decision 5: Contract registration shape `[ASSUMED]`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted `[ASSUMED]` (confidence 0.90) |
| **Date** | 2026-07-29 |

**Context:** The gate must be contract-grade, not just skill prose.

**Choice:** Add `final_review` block under `build.execution` (reviewer, scope, severity taxonomy, verdict values, fix-loop budget 2) and append `review_verdict_clean` to `ship.pre_ship_checklist` (4→5 items). Update sdd-autopilot Gate S text from "all 4 items" to "all 5 items".

**Rationale:** `build.execution` already carries execution policy (`retry_limit: 3`); the checklist is Gate S's sensor — extending both makes the verdict enforceable by the existing machinery with zero new sensors.

**Alternatives Rejected:**
1. New top-level contract section — rejected: the gate is build-phase policy, not a new phase.
2. Skill-prose only — rejected: DEFINE constraint requires contract registration.

**Consequences:**
- Every consumer of `pre_ship_checklist` sees 5 items; the doc-contract tests pin this.

### Decision 6: AT-002 execution mode — human-decided at Gate D

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted (Gate D ANSWERED — no `[ASSUMED]` marker) |
| **Date** | 2026-07-29 |

**Context:** The interview fixed "full benchmark re-run" as the acceptance criterion; a cheaper deterministic alternative existed. Deviating from an explicit interview choice is sub-0.80 confidence → Gate D fired (interactive: ask).

**Choice:** **Both, B then A** — (B) run the new review procedure against the preserved benchmark repo (`~/Documents/ai-bootcamp/work/agentspec`, branch `feat/expense-tracker`, verified UTC bug at `app/static/index.html:79`) as the deterministic detection proof; then (A) full benchmark re-run via subagent with the modified methodology, planting the UTC exemplar if no equivalent bug emerges naturally.

**Rationale:** Fail-fast ordering — the cheap deterministic test filters before the expensive integration test; the re-run preserves fidelity to the human's interview choice.

**Alternatives Rejected:**
1. Only A — costlier feedback loop if the gate design is broken.
2. Only B — does not exercise the integrated flow; deviates from the interview choice.

**Consequences:**
- Build phase includes two acceptance-verification tasks beyond the file manifest, both recorded in the BUILD_REPORT's Acceptance Test Verification table.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | Modify | `final_review` block under `build.execution`; `review_verdict_clean` appended to `pre_ship_checklist` | (general) | None |
| 2 | `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md` | Modify | Add `## Review Verdict` and `## TDD Evidence` sections | (general) | None |
| 3 | `.claude/skills/sdd-build/SKILL.md` | Modify | Insert Step 5.5 (whole-branch review + fix loop + verdict), `--tdd` conduct, quality-gate rows | (general) | 1, 2 |
| 4 | `.claude/skills/sdd-ship/SKILL.md` | Modify | Build Report Validation + readiness matrix + quality gate verdict checks | (general) | 1 |
| 5 | `.claude/skills/sdd-autopilot/SKILL.md` | Modify | Gate R row in gate policy + budget table row + Gate S "all 5 items" | (general) | 1 |
| 6 | `.claude/commands/workflow/build.md` | Modify | `--tdd` flag in usage/flag table (thin surface, points to skill) | (general) | 3 |
| 7 | `tests/test_build_quality_gates.py` | Create | Doc-contract pytest suite pinning every surface above | @test-generator | 1–6 |

**Total Files:** 7

---

## Agent Assignment Rationale

> Agents discovered from `.claude/agents/` - Build phase invokes matched specialists.

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| (general) | 1–6 | Methodology/contract authoring — no skill-authoring specialist exists in the oracle; covered by the repo-local `create-skill` + `component-model` skills (citation rule: covering skill → resolved as general) |
| @test-generator | 7 | routing.json citation: `test-generator`, kb_domains `['data-quality','dbt','testing']` — pytest suite authoring is its specialization |
| @code-reviewer | runtime executor of Step 5.5 (not a build-time author) | routing.json citation: `code-reviewer`, category `python` — the gate dispatches it at every future build |

**Agent Discovery:**
- Scanned: `.claude/skills/agent-router/routing.json` (58 agents)
- Step 4.5 citation check: all rows resolved (no gaps → no provisioning; Gate P not fired)

---

## Code Patterns

### Pattern 1: WORKFLOW_CONTRACTS.yaml — contract registration (file 1)

```yaml
# Under build.execution (after retry_limit: 3):
  execution:
    task_generation: "on-the-fly from file manifest"
    order: "by dependencies"
    verification: "after each file"
    retry_limit: 3
    final_review:
      reviewer: "code-reviewer"
      scope: "merge-base(default-branch, HEAD)..HEAD diff"
      lens: "DEFINE acceptance tests + severity taxonomy"
      severities: [critical, important, minor]
      verdicts: [clean, clean-with-minors, dirty, missing]
      blocking: "critical|important unresolved -> dirty"
      fix_loop_budget: 2
      tdd_flag: "--tdd — opt-in RED-GREEN per code task, evidence in BUILD_REPORT"

# In ship block:
  pre_ship_checklist:
    - build_report_complete
    - all_tests_passing
    - no_blocking_issues
    - acceptance_tests_verified
    - review_verdict_clean
```

### Pattern 2: BUILD_REPORT_TEMPLATE.md — new sections (file 2, inserted after "## Verification Results")

```markdown
## Review Verdict

> Whole-branch adversarial review — mandatory final step of the build
> (`WORKFLOW_CONTRACTS.yaml` → `build.execution.final_review`). Ship refuses
> `dirty` and `missing` verdicts.

| Attribute | Value |
|-----------|-------|
| **Verdict** | {clean / clean-with-minors / dirty / missing} |
| **Reviewer** | @code-reviewer |
| **Diff scope** | {merge-base sha}..{HEAD sha} |
| **Fix rounds used** | {0-2}/2 |

| # | Severity | Finding | Location | Resolution |
|---|----------|---------|----------|------------|
| 1 | {Critical / Important / Minor} | {finding} | {file:line} | {fixed in <sha> / recorded (minor) / OPEN} |

## TDD Evidence (--tdd runs only)

> One row per code-bearing manifest task. Non-code tasks record `n/a`.

| Task | Test file | RED observed (failure excerpt) | GREEN run | Commit |
|------|-----------|-------------------------------|-----------|--------|
| {task} | {tests/...} | {expected failure line} | {X passed} | {sha} |
```

### Pattern 3: sdd-build SKILL.md — Step 5.5 (file 3, inserted between Step 5 and Step 6)

```markdown
### Step 5.5: Whole-Branch Adversarial Review (mandatory)

Contract: `WORKFLOW_CONTRACTS.yaml` → `build.execution.final_review`.

After full validation passes, dispatch the review — never skip it, never
self-review instead:

1. Compute the branch scope: `BASE=$(git merge-base <default-branch> HEAD)`.
2. Dispatch `code-reviewer` via the Task tool with: the `BASE..HEAD` diff,
   the DEFINE's acceptance tests as the review lens, and the severity
   taxonomy Critical / Important / Minor.
3. Record the outcome in the BUILD_REPORT `## Review Verdict` section.

| Findings | Action |
|----------|--------|
| None | Verdict `clean` → Step 6 |
| Minor only | Record each; verdict `clean-with-minors` → Step 6 |
| Critical/Important | Fix loop (below) |

**Fix loop (budget 2 rounds, supervised and autonomous alike):** one round =
fix the findings → re-run the tests covering the amended code → scoped
re-review of the fix diff only. All findings resolved → verdict `clean` (or
`clean-with-minors`). Budget exhausted with open findings → verdict `dirty`,
open findings recorded as Blockers, recommend `/iterate`; under `/auto`,
Gate R (sdd-autopilot) maps this to abort-with-gap-report.

**Reviewer dispatch failure:** retry once; still failing → verdict `missing`
with a visible WARN — never an assumed `clean`. A `missing` verdict blocks
ship exactly like `dirty`.

### `--tdd` mode (opt-in flag on /build)

When invoked with `--tdd`, each code-bearing task follows RED-GREEN before
the standard per-file verification: write the failing test → run it and
observe the expected failure → write minimal code → run to green. Capture
the observed RED excerpt per task in `## TDD Evidence`. Non-code tasks
(markdown, YAML, templates) record `n/a (non-code artifact)`. Without the
flag, task execution is unchanged.
```

### Pattern 4: tests/test_build_quality_gates.py — doc-contract suite (file 7)

```python
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / ".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml"
BUILD_SKILL = ROOT / ".claude/skills/sdd-build/SKILL.md"
SHIP_SKILL = ROOT / ".claude/skills/sdd-ship/SKILL.md"
AUTOPILOT_SKILL = ROOT / ".claude/skills/sdd-autopilot/SKILL.md"
REPORT_TEMPLATE = ROOT / ".claude/sdd/templates/BUILD_REPORT_TEMPLATE.md"
BUILD_COMMAND = ROOT / ".claude/commands/workflow/build.md"


def contracts() -> dict:
    return yaml.safe_load(CONTRACTS.read_text())


def test_final_review_block_registered():
    review = contracts()["build"]["execution"]["final_review"]
    assert review["reviewer"] == "code-reviewer"
    assert review["fix_loop_budget"] == 2
    assert review["verdicts"] == ["clean", "clean-with-minors", "dirty", "missing"]


def test_pre_ship_checklist_has_five_items_ending_in_review_verdict():
    checklist = contracts()["ship"]["pre_ship_checklist"]
    assert len(checklist) == 5
    assert checklist[-1] == "review_verdict_clean"


def test_build_report_template_carries_review_verdict_section():
    text = REPORT_TEMPLATE.read_text()
    assert "## Review Verdict" in text
    assert "## TDD Evidence" in text


def test_build_skill_defines_step_5_5_and_tdd_mode():
    text = BUILD_SKILL.read_text()
    assert "Step 5.5: Whole-Branch Adversarial Review" in text
    assert "--tdd" in text


def test_ship_skill_checks_review_verdict():
    assert "review_verdict" in SHIP_SKILL.read_text().lower().replace(" ", "_")


def test_autopilot_has_gate_r():
    text = AUTOPILOT_SKILL.read_text()
    assert "R — Review" in text
    assert "all 5 items" in text


def test_build_command_documents_tdd_flag():
    assert "--tdd" in BUILD_COMMAND.read_text()
```

---

## Data Flow

```text
1. /build finishes full validation (lint, types, tests)
   │
   ▼
2. Step 5.5 dispatches @code-reviewer on merge-base..HEAD with DEFINE ATs as lens
   │
   ▼
3. Findings triaged: Minor → recorded · Critical/Important → fix loop (≤2 rounds, scoped re-review)
   │
   ▼
4. Verdict written to BUILD_REPORT ## Review Verdict (clean / clean-with-minors / dirty / missing)
   │
   ▼
5. /ship Build Report Validation reads the verdict — dirty/missing → Cannot ship → /build
   │
   ▼
6. /auto Gate R consumes the same verdict — open findings after budget → abort + gap report
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Task tool (code-reviewer dispatch) | Agent invocation | n/a (local) |
| git (merge-base, diff) | CLI | n/a (local repo) |
| pytest | CLI (doc-contract suite) | n/a |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit (doc-contract) | Every modified surface exists and is consistent | `tests/test_build_quality_gates.py` | pytest + yaml | 7/7 manifest files pinned |
| Acceptance — detection (AT-002/B) | New review procedure vs. preserved Spendly repo with verified UTC bug | dispatch per Step 5.5 against `~/Documents/ai-bootcamp/work/agentspec` `feat/expense-tracker` | Task tool (@code-reviewer) | UTC-class bug reported Critical/Important |
| Acceptance — integration (AT-002/A) | Full benchmark re-run with modified methodology, seeded fallback | fresh work dir, subagent | Agent tool | Gate runs in-flow; bug caught before handoff |
| E2E | Existing suite still green | `tests/` | pytest | 0 regressions |

**Acceptance test coverage (DEFINE):**

| AT | Verified by |
|----|-------------|
| AT-001 (clean build ships) | AT-002/A re-run report (clean path after fixes) + doc-contract tests |
| AT-002 (gate catches benchmark bug) | Detection run (B) + integration re-run (A) — Decision 6 |
| AT-003 (ship refuses dirty/missing) | `test_pre_ship_checklist_*` + `test_ship_skill_checks_review_verdict` (mechanics); semantics prose pinned in sdd-ship |
| AT-004 (Gate R aborts on persistent findings) | `test_autopilot_has_gate_r` + Gate R policy row content |
| AT-005 (--tdd records red runs) | `test_build_skill_defines_step_5_5_and_tdd_mode` + TDD Evidence template section |
| AT-006 (default build unchanged) | `--tdd` sections are additive-only; existing suite green (0 regressions) |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Reviewer dispatch fails | Retry once; then verdict `missing` + visible WARN (fails safe: blocks ship) | Yes (1) |
| Fix loop exhausts budget | Verdict `dirty`, Blockers recorded, `/iterate` recommended; `/auto` → Gate R abort | No |
| Benchmark re-run (A) infrastructure failure | Record in BUILD_REPORT; AT-002 evidence stands on detection run (B); flag partial | No |
| merge-base not computable (no default branch) | Fall back to reviewing all manifest files in full (risk A-003) | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `--tdd` | flag (bool) | off | Opt-in RED-GREEN conduct per code task |
| `final_review.fix_loop_budget` | int (contract) | 2 | Fix rounds before dirty/abort |
| `final_review.verdicts` | enum (contract) | 4 values | Ship-consumable verdict taxonomy |

---

## Security Considerations

- No secrets involved; review runs locally on the repo diff.
- The reviewer dispatch must never include environment values in its prompt (existing RUN REPORT rule extended to review dispatches).
- Verdict `missing` fails closed — absence of review evidence can never ship.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Review Verdict + fix-round count in BUILD_REPORT; Gate R rows in AUTOPILOT_RUN ledger |
| Metrics | Fix rounds used /2, findings by severity, TDD evidence rows |
| Tracing | Diff scope (BASE..HEAD shas) recorded in the verdict table |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | design-agent | Initial version — autopilot run, Gate D decision 6 human-answered |
| 1.1 | 2026-07-29 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_BUILD_QUALITY_GATES.md`
