# DEFINE: Build Quality Gates

> Mandatory adversarial whole-branch review at the end of sdd-build (with ship-side verdict enforcement and an autopilot gate) plus an opt-in `--tdd` mode for `/build`.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | BUILD_QUALITY_GATES |
| **Date** | 2026-07-28 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Designed) |
| **Clarity Score** | 15/15 |

---

## Problem Statement

AgentSpec's mandatory Build→Ship path verifies artifacts and tests but never reviews code adversarially, so whole-branch bugs that tests cannot reach ship undetected — proven by the 2026-07-28 Superpowers benchmark, where the AgentSpec build shipped a UTC date bug with 37/37 tests passing while Superpowers' mandatory final review caught the identical bug class before PR.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| AgentSpec user | Runs `/build` + `/ship` on features | Bugs outside test reach (frontend JS, cross-file behavior) ship silently; no per-run way to demand TDD rigor |
| Autopilot operator | Launches `/auto` lights-out runs | The highest-risk path (no human review) has the weakest quality net — no adversarial review before the PR |
| AgentSpec maintainer | Owns framework quality | Benchmark exposed a structural gap vs. Superpowers' review discipline; needs it closed at the methodology layer |

---

## Goals

What success looks like (prioritized):

| Priority | Goal |
|----------|------|
| **MUST** | Whole-branch adversarial review as the final step of sdd-build: dispatch the existing `code-reviewer` on the merge-base→HEAD diff with the feature's DEFINE acceptance criteria as review lens |
| **MUST** | `BUILD_REPORT` gains a **Review Verdict** section: verdict + severity-ranked findings (Critical/Important/Minor) + per-finding resolution |
| **MUST** | Critical/Important findings enter a fix loop inside build (fix → scoped re-review); Minor findings are recorded, never block |
| **MUST** | sdd-ship's Build Report Validation refuses to ship when the Review Verdict is missing or has unresolved Critical/Important findings (existing Cannot-ship row) |
| **MUST** | Gate R in sdd-autopilot: in `/auto`, fix-loop budget of 2 rounds; findings persisting after round 2 → abort with a gap report listing open findings |
| **SHOULD** | `--tdd` opt-in flag on `/build`: each manifest task follows RED-GREEN with the failing-test run observed and recorded as evidence in the BUILD_REPORT; default `/build` behavior unchanged |
| **COULD** | Fix-loop re-reviews scoped to the fix diff only (not the whole branch), per the Superpowers scoped re-review pattern |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists (the review gate itself is the safety net for non-TDD builds)
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] Benchmark re-run (Spendly brief, gate active): the review reports ≥1 Critical/Important finding on the UTC-class bug — naturally occurring, or the seeded ground-truth exemplar planted as fallback — and blocks handoff until resolved (100% detection of the seeded exemplar)
- [ ] 100% of `/build` runs produce a BUILD_REPORT containing a Review Verdict section
- [ ] `/ship` refuses (Cannot ship) in 100% of cases where the verdict is missing or has unresolved Critical/Important findings
- [ ] In `/auto`, the fix loop runs at most 2 rounds; a 3rd evaluation with open findings aborts the run with a gap report — 0 runs proceed past Gate R with open Critical/Important findings
- [ ] With `--tdd`: red-run evidence recorded for 100% of manifest tasks before their implementation; without the flag: 0 behavioral change vs. current `/build`

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Clean build ships | A completed build whose final review finds no Critical/Important issues | sdd-build finishes its review step | BUILD_REPORT Review Verdict = clean; handoff to `/ship` proceeds |
| AT-002 | Gate catches the benchmark bug | Benchmark re-run with gate active and a UTC-class bug present (natural or seeded `toISOString` exemplar) | The whole-branch review runs | Bug reported as Critical/Important; handoff blocked until the fix loop resolves it |
| AT-003 | Ship refuses dirty/missing verdict | A BUILD_REPORT with no Review Verdict section (or unresolved Critical/Important findings) | `/ship` runs Build Report Validation | Ship refuses via the existing Cannot-ship row, routing back to `/build` |
| AT-004 | Gate R aborts on persistent findings | An `/auto` run where a Critical finding survives 2 fix rounds | Gate R evaluates after round 2 | Run aborts; gap report lists the open findings and fix history |
| AT-005 | TDD mode records red runs | `/build --tdd` on a design with a file manifest | Each manifest task executes | A failing-test run is recorded before implementation and a green run after, per task, in the BUILD_REPORT |
| AT-006 | Default build unchanged | `/build` without `--tdd` | The build executes | Task execution identical to current behavior (no TDD enforcement); the review step still runs |

---

## Out of Scope

Explicitly NOT included in this feature:

- Cross-model judge/ensemble review inside the gate (Judge V1+ track)
- Browser/JS test tooling (the review gate is the chosen catch mechanism for non-Python surfaces)
- TDD default-on (opt-in flag only)
- Changes to supervised-mode human authority — outside `/auto`, findings are presented and the human decides
- New reviewer agents (reuse `code-reviewer`)
- Dedicated planted-bug fixture repo (seeded fault lives inside the benchmark re-run as fallback)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Policy lives in the skill layer (sdd-build/sdd-ship/sdd-autopilot); commands stay thin entrypoints (component model) | Design touches SKILL.md files + contracts, not command logic |
| Technical | Reuse the existing `code-reviewer` agent — no new agents | Review output taxonomy must be aligned via prompt/context, not a new component |
| Technical | Contract changes registered in `WORKFLOW_CONTRACTS.yaml` | Gate becomes contract-grade, enforceable by spec-lint where wired |
| Technical | Ship stays archival-only: it validates the recorded verdict, never dispatches reviews | The gate's execution cost lives entirely in Phase 3 |
| Resource | No new dependencies or infrastructure | Pure methodology/skill change |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `.claude/skills/sdd-build/`, `.claude/skills/sdd-ship/`, `.claude/skills/sdd-autopilot/`, `.claude/commands/workflow/build.md`, `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md`, `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | Skill-layer policy + template shape + contract registration; command file only exposes the `--tdd` flag surface |
| **KB Domains** | testing, python, shared/component-model | TDD patterns and review lens; layer-decision grounding |
| **IaC Impact** | None | Framework/methodology feature |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Assumptions

Assumptions that if wrong could invalidate the design:

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `code-reviewer` output can be constrained to the Critical/Important/Minor taxonomy via dispatch context | Reviewer prompt/agent frontmatter needs an output-contract update (small design addition) | [ ] |
| A-002 | A single same-model reviewer catches UTC-class bugs reliably (benchmark: Superpowers' single final review did) | Escalate Judge V1+ cross-model integration into the gate earlier than planned | [ ] |
| A-003 | merge-base→HEAD diff is computable in all supported flows (git repo, feature branch) | Fall back to reviewing the manifest files in full | [ ] |
| A-004 | 2 fix rounds suffice for typical findings (benchmark: 1 round sufficed) | Budget becomes configurable per run | [ ] |
| A-005 | RED-GREEN per task composes with sdd-build's existing per-file verification retry (max 3) | sdd-build execution loop needs restructuring, raising design scope | [ ] |
| A-006 | The benchmark environment (work dirs + product-owner brief) stays reproducible for acceptance | Replace with a minimal seeded-fault fixture repo (YAGNI-deferred, revivable) | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Specific, evidence-backed (benchmark UTC bug with 37/37 tests passing), names the structural gap |
| Users | 3 | Three personas with concrete pain points, including the autopilot path as highest-risk |
| Goals | 3 | Five MUSTs + one SHOULD + one COULD, each naming its component and mechanism |
| Success | 3 | Every criterion binary/countable; primary criterion made deterministic by the seeded-fault fallback |
| Scope | 3 | Six explicit exclusions; constraints pin the layer, the reused agent, and contract registration |
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
| 1.0 | 2026-07-28 | define-agent | Initial version, extracted from BRAINSTORM_BUILD_QUALITY_GATES.md (4 discovery Q&A, approach B confirmed, 2 validations) |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_BUILD_QUALITY_GATES.md`
