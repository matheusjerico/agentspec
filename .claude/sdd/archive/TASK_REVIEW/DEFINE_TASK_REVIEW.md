# DEFINE: Task Review

> Find defects before they pile up at the final review: per-task independent review keyed on manifest risk/reviewer, blind-first context, task verdicts with a separate fix budget, dependents blocked while dirty — high/critical enforced, medium in Warn.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TASK_REVIEW |
| **Date** | 2026-07-29 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 15/15 |

**Source:** plan §11 (flow §11.2, blind-first §11.3, cost control §11.4, acceptance §11.6), §18 PR 5 scope ("initially high/critical; medium enters in Warn"). Phase 0 carried by the ratified plan (benchmark: Superpowers' incremental reviews caught defects the final pass then didn't have to). Consumes Increment 2's risk level, Increment 3's manifest `reviewer`/`risk`, Increment 4's per-risk policy precedent.

---

## Problem Statement

All review pressure lands on the whole-branch final pass (§5 "Revisão por tarefa | Ausente"): defects accumulate across tasks before anyone independent looks, dependents build on unreviewed work, and the final reviewer faces an integrated diff where task-local mistakes are hardest to attribute and cheapest to have caught earlier (§11.1).

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| AgentSpec maintainer (Matheus) | Owns the §8.3 Task Review matrix row | No per-task review exists; the matrix row is plan prose |
| Autopilot runs | Build delegates tasks and must decide review depth without a human | No policy maps task risk → review obligation; no verdict vocabulary for tasks |
| Plugin consumers | Ship multi-task features | A dirty early task silently contaminates every dependent before the branch review sees it |

---

## Goals

What success looks like (prioritized):

| Priority | Goal |
|----------|------|
| **MUST** | `task_review` contract block in `WORKFLOW_CONTRACTS.yaml`: verdict vocabulary (`clean`, `clean-with-minors`, `dirty`, `skipped-by-policy`), per-risk policy (low → executor_checklist; medium → selective_independent, Warn rollout; high → independent_required; critical → independent_plus_specialist), blind-first rule (§11.3 — reviewer forms the initial assessment WITHOUT the implementer's justification), per-task fix budget (1 round, separate from the final review's 2), dependents-blocked-while-dirty rule, enforcement map |
| **MUST** | `sdd-build` SKILL: per-task review step in the execution loop — after a task's verification, dispatch its manifest `reviewer` with blind-first context (requirements, acceptance, task diff, tests, dependent interfaces, risks — NOT the implementer's rationale); record verdict; blocking findings → 1 fix round; still dirty → dependents do NOT start, task recorded dirty; reviewer==implementer only where policy allows |
| **MUST** | BUILD_REPORT template: new `## Task Reviews` section — one row per reviewed task: Task ID, risk, reviewer, verdict, blocking/minor counts, fix rounds |
| **MUST** | `BuildReportContract` rules: on v2 reports WITH a Risk Level row — `BR.task_review_missing` (report risk high/critical and no Task Reviews section, or a manifest-tasked row without a review row → FAIL; medium → WARN; low/no-row → silent) and `BR.task_review_dirty` (any task verdict `dirty` → FAIL — dependents built on dirty work must not ship); invalid verdict token → FAIL |
| **MUST** | Branch-level final review (Step 5.5 / Gate R) stays mandatory and byte-identical — task reviews never replace it (§11.6) |
| **MUST** | Version bump + history |
| **SHOULD** | Report records local-vs-final finding counts (raw material for Increment 9 metrics) |
| **COULD** | `skipped-by-policy` verdicts carry the policy citation (e.g. "low → executor_checklist") |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] `BR.task_review_missing`: high/critical without reviews → FAIL (≥2 tests: absent section, unreviewed task); medium → WARN (≥1); low/no-Risk-row → silent (≥2)
- [ ] `BR.task_review_dirty`: any dirty verdict → FAIL (≥1); invalid verdict token → FAIL (≥1); all-clean → 0 findings (≥1)
- [ ] Policy, vocabulary, budgets, and blind-first rule exist as contract data — ≥3 documental tests; skill flow anchors ≥3
- [ ] Final-review contract untouched: existing Gate R / Step 5.5 tests stay green unchanged
- [ ] 0 regressions: both suites green; build + Step 5e parity exit 0

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | High risk without task reviews | v2 report, Risk Level high, no Task Reviews section | `spec-lint --phase build` | Exit 1, `BR.task_review_missing` |
| AT-002 | Task without a review row | high report, Task Reviews present, one Task ID unreviewed | Linter | Exit 1, same rule naming the task |
| AT-003 | Medium warns | medium report, no Task Reviews | Linter | Exit 0, WARN |
| AT-004 | Low silent | low report, no section | Linter | 0 task-review findings |
| AT-005 | Dirty verdict blocks | any risk, a review row `dirty` | Linter | Exit 1, `BR.task_review_dirty` |
| AT-006 | Invalid verdict token | review row `verdict: sketchy` | Linter | Exit 1 |
| AT-007 | All-clean passes | high report, every task reviewed clean/clean-with-minors | Linter | 0 task-review findings |
| AT-008 | Legacy silent | report without Risk Level row | Linter | Neither rule fires |
| AT-009 | Conduct anchors | sdd-build + contracts | Documental tests | blind-first, budget separation, dependents-blocked, verdict vocabulary asserted |
| AT-010 | Parity + suites | build + suites | Run | Exit 0, all green |

---

## Out of Scope

- Replacing or weakening the whole-branch final review (§11.6 — it stays mandatory, contract untouched)
- Cross-model second opinion for critical tasks (Judge-layer work; the `independent_plus_specialist` policy names a second SPECIALIST agent, not a second model)
- Metrics schema/aggregation (Increment 9 — this increment only records counts in the report)
- Commit-per-task enforcement (Increment 7); traceability matrix (Increment 6)
- Retrofitting archived reports; Increments 6–9

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` canonical; Step 5e parity | Repackage before ship |
| Technical | Deterministic linter — validates recorded verdicts/rows, never dispatches reviews | Review dispatch is Build conduct |
| Compatibility | Rules fire only on v2 reports WITH a Risk Level row (same opt-in markers as Increment 4) | Pre-Inc2 reports untouched |
| Compatibility | high/critical FAIL from day one (opt-in markers); medium Warn (§18 PR 5); low silent | §17.2 respected |
| Process | Dogfooding under `/auto`: this run's own report (medium) will carry Task Reviews voluntarily — exercising the section shape without being forced | Live shape validation |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `tools/spec-linter/` (build_report.py + cli + tests), `WORKFLOW_CONTRACTS.yaml`, `.claude/skills/sdd-build/SKILL.md`, `BUILD_REPORT_TEMPLATE.md`, `tests/` | Framework/tooling |
| **KB Domains** | `python`, `testing` | Established pattern |
| **IaC Impact** | None | Local only |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Data Contract (if applicable)

Not applicable — framework feature.

---

## Risk Profile

> Derived per sdd-define Step 5.5: level = max(dimension values), raised to any
> applicable elevation floor (`WORKFLOW_CONTRACTS.yaml` → `risk_profiles`).

```yaml
risk_profile:
  level: medium
  reasons:
    - "blast_radius medium: build execution loop conduct + report contract"
    - "no elevation floor applies; new FAILs scoped to opt-in high/critical reports"
  dimensions:
    data_loss: none
    security: none
    reversibility: low
    blast_radius: medium
    migration: none
  override:
    applied: false
    author: null
    rationale: null
```

---

## Assumptions

Assumptions that if wrong could invalidate the design:

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | A `## Task Reviews` markdown table is deterministically parseable with the existing numbered-row machinery | Needs a dedicated parser tweak — small | [ ] |
| A-002 | Matching review rows to task rows by Task ID string equality suffices (v2 manifests give stable ids; v1 builds use `-` and are exempt) | Would need fuzzy matching — reject; v1 exemption covers it | [ ] |
| A-003 | The report's own Risk Level row is the right enforcement key (task-level risk refines WHO reviews, report-level risk decides WHETHER rules fire) | Per-task risk enforcement could follow later — additive | [ ] |
| A-004 | Blind-first is enforceable as conduct + documental anchor only (no deterministic sensor for what a reviewer saw) | Accepted — same boundary as RED validity in Increment 4 | [ ] |
| A-005 | One fix round per task (separate from final review's 2) is the right §11.6 budget split | Contract data — tunable without code change | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | §11.1 + §5 gap row verbatim; cost asymmetry named |
| Users | 3 | Three personas; pains tied to matrix row, delegation policy, dependent contamination |
| Goals | 3 | §11.2–11.4 flow/policy/cost tables map 1:1 to MUSTs |
| Success | 3 | Per-rule numbered test floors; final-review invariance pinned |
| Scope | 3 | Every §11.6 obligation either delivered or explicitly deferred to its owning increment |
| **Total** | **15/15** | |

**Scoring Guide:**
- 0 = Missing entirely
- 1 = Vague or incomplete
- 2 = Clear but missing details
- 3 = Crystal clear, actionable

**Minimum to proceed: 12/15**

---

## Open Questions

None blocking — ready for Design. Deferred *how*: exact Task Reviews table columns and the review-row ↔ task-row matching rule (A-001/A-002) — Design fixes the shapes.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | define-agent | Initial version — plan §11/§18 (PR 5 scope) under the /auto pre-ignition interview |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_TASK_REVIEW.md`
