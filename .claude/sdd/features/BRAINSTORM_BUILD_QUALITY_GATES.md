# BRAINSTORM: Build Quality Gates

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | BUILD_QUALITY_GATES |
| **Date** | 2026-07-28 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** Transform the actionable conclusion of the Superpowers-vs-AgentSpec benchmark (2026-07-28) into an SDD feature: (1) mandatory adversarial whole-branch review before a feature ships, and (2) a TDD-as-law option in sdd-build. Evidence: the benchmark's AgentSpec build shipped a UTC date bug (`new Date().toISOString()` in the frontend) that 37/37 passing tests could not catch, while the Superpowers run's mandatory final review caught and fixed the identical bug class before PR.

**Context Gathered:**
- `sdd-ship` verification order today checks artifacts + build report + tests only — no code review is in the mandatory path; `/review` and `/judge` exist but are optional commands outside the Build→Ship flow
- `sdd-build` ends at full-run verification with per-file retry (max 3); TDD is not part of its execution loop
- `sdd-autopilot` owns the gate policy table (Gates I, D, P) with retry budgets and abort-with-gap-report semantics — the natural home for a new gate's autonomous conduct
- CLAUDE.md lists "Flag System (progressive enhancement)" as Planned — a `--tdd` flag fits that vocabulary
- The `code-reviewer` agent already exists (severity-ranked review is its output format)
- Benchmark artifacts preserved in `~/Documents/ai-bootcamp/work/{agentspec,superpowers}`

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `.claude/skills/sdd-build/` (primary), `.claude/skills/sdd-ship/` (verdict check), `.claude/skills/sdd-autopilot/` (Gate R), `.claude/commands/workflow/build.md` (flag surface), `.claude/sdd/templates/BUILD_REPORT_TEMPLATE.md` (Review Verdict section), `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` (contract registration) | Skill-layer policy change per component model — commands stay entrypoints |
| Relevant KB Domains | testing, python, shared/component-model | Review lens + TDD patterns; layer-decision grounding |
| IaC Patterns | N/A | Framework/methodology feature, no infrastructure |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Scope: one feature with internal MoSCoW, two features, or review gate only? | One feature, MoSCoW internal | Single SDD cycle: review gate = MUST, `--tdd` flag = SHOULD |
| 2 | In `/auto`, what happens on Critical/Important findings at the gate? | Retry with budget, then abort | New Gate R row in sdd-autopilot policy: fix-loop budget 2, persistent findings → abort with gap report listing findings |
| 3 | Primary acceptance criterion? | Re-run the full Spendly benchmark with the gate active | Success = gate reports the UTC-class bug before handoff and blocks until fixed; cost (~200k tokens/run) and non-determinism accepted, mitigated by seeded-fault fallback (validation 2) |
| 4 | Which samples/ground truth to inventory? | Superpowers `REVIEW.md` + UTC bug exemplar | Review output format reference + verified seeded-fault target for acceptance |

**Minimum Questions:** 3 (asked 4) ✅

---

## Sample Data Inventory

> Samples improve LLM accuracy through in-context learning and few-shot prompting.

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Output examples | `~/Documents/ai-bootcamp/work/superpowers/REVIEW.md` | 1 | Real whole-branch review that caught 2 Important bugs — severity taxonomy (Critical/Important/Minor), finding format, resolution notes |
| Ground truth | `~/Documents/ai-bootcamp/work/agentspec/app/static/index.html:79` | 1 | Verified undetected bug: `new Date().toISOString().slice(0, 10)` — tomorrow's date in UTC-negative timezones; the seeded-fault exemplar |
| Related code | `.claude/skills/sdd-ship/SKILL.md` (readiness matrix), `.claude/agents/*/code-reviewer.md` | 2 | Readiness matrix rows to extend; existing reviewer agent to reuse |

**How samples will be used:**

- REVIEW.md as the reference shape for the gate's review output (severity-ranked findings, per-finding resolution)
- UTC bug as the seeded fault planted during the acceptance benchmark if no equivalent bug emerges naturally
- Readiness matrix as the extension point for the ship-side verdict check

---

## Approaches Explored

### Approach A: Contract-grade gate in sdd-ship + `--tdd` in sdd-build ⭐ Recommended

**Description:** Ship gains a step 0 in its verification order — dispatch `code-reviewer` on the full branch diff (merge-base→HEAD) before any archival; Critical/Important → Cannot ship, route back to `/build`; Minor → Ship with notes. Registered in WORKFLOW_CONTRACTS.yaml; new Gate R in sdd-autopilot.

**Pros:**
- True last line before the artifact leaves — cannot be bypassed by invoking `/ship` directly
- Matches the benchmark evidence placement (Superpowers' final whole-branch review)
- Reuses ship's existing route-back-to-build semantics

**Cons:**
- Ship phase grows beyond pure archival, straining its "not for implementation work" boundary
- Fix loop would span two phases (findings at ship, fixes in build)

**Why Recommended:** sdd-ship already owns verification order + readiness matrix + route-back (codebase match, confidence 0.85); the benchmark bug shipped precisely because ship trusted the build report without a review.

---

### Approach B: Whole-branch review as the final step of sdd-build (SELECTED)

**Description:** The review becomes the final step of sdd-build's execution loop, after full-run verification: dispatch `code-reviewer` on the merge-base→HEAD diff with the DEFINE acceptance criteria as review lens. Critical/Important → fix loop inside build with scoped re-review; Minor → recorded. BUILD_REPORT gains a **Review Verdict** section (verdict + findings by severity + resolution). Bypass mitigation: sdd-ship's existing Build Report Validation checklist gains one line — "Review verdict present and clean?" — missing/dirty verdict falls into the existing Cannot-ship row. Ship stays archival-only (reads a field, never dispatches reviews).

**Pros:**
- Fixes happen in the phase where code changes belong; phase boundaries stay clean
- Single-phase fix loop (find and fix in build), matching Superpowers' structure
- Ship remains pure archival per its own skill contract

**Cons:**
- Without the verdict check, invoking `/ship` directly on an old build would skip the review (mitigated by the checklist line)
- Review runs even when a build will be iterated further before shipping

---

### Approach C: `/ship` command chains `/review`

**Description:** Thin change — the `/ship` command runs the existing `/review` (dual-AI) first; no skill or contract changes.

**Pros:**
- Minimal diff

**Cons:**
- Policy would live in the command layer — violates the component model (commands are entrypoints, not policy owners)
- Headless runner bypasses it; not contract-registered → not truly mandatory

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach B |
| **User Confirmation** | 2026-07-28 (approach question + validation checkpoint 1) |
| **Reasoning** | Review belongs at the end of the phase that owns code changes; ship stays pure archival. The bypass con is mitigated by the ship-side verdict check on the existing Build Report Validation checklist (confirmed in validation 1). |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Review gate = final step of sdd-build, whole-branch diff, DEFINE acceptance criteria as lens | Fixes live where code changes belong; single-phase fix loop | Gate at ship entry (Approach A); command chaining (Approach C) |
| 2 | BUILD_REPORT gains a Review Verdict section (verdict, findings by severity, resolutions) | Persistent, auditable record the ship phase can validate | Verdict only in chat/run log |
| 3 | sdd-ship Build Report Validation checks "Review verdict present and clean?" → missing/dirty = Cannot ship | Closes the direct-`/ship` bypass without making ship dispatch reviews | Unprotected build-end review; full gate in ship |
| 4 | Gate R in sdd-autopilot: Critical/Important → fix loop, budget 2 rounds, then abort with gap report | Benchmark evidence: real findings fixed in 1 round; consistent with existing gate budgets; caps runaway cost | Abort immediately; unlimited retries; Superpowers' 5-round breaker |
| 5 | `--tdd` flag on `/build`, opt-in, SHOULD priority | Review gate is the safety net (workaround exists → not MUST); default-on would raise every build's cost; DE contexts (DAGs/notebooks/SQL) sometimes impractical; fits planned Flag System | TDD default-on with opt-out; TDD as documentation only |
| 6 | Acceptance = benchmark re-run with seeded-fault fallback: if no UTC-class bug emerges naturally, plant the ground-truth exemplar before the review runs | Preserves the user-chosen real-world criterion while making detection provable (a detector that finds nothing is indistinguishable from a broken one when the sample has no target) | Re-run without fallback (proves mechanics only when no bug emerges); dedicated fixture repo |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Dedicated new reviewer agent | `code-reviewer` already exists with the right output shape | Yes |
| Cross-model judge (`/judge`) inside the gate | Judge V1+ is a separate planned track; single-reviewer gate is the MVP | Yes |
| TDD default-on with opt-out | Cost/latency on every build; DE contexts sometimes impractical | Yes |
| Browser/JS test tooling (catch frontend bugs via tests) | The review gate is the chosen catch mechanism; new toolchain out of scope | Yes |
| Multi-model ensemble review | Single reviewer is the MVP; ensemble is Judge V1+ territory | Yes |
| Dedicated planted-bug fixture repo | Superseded — seeded fault lives inside the benchmark re-run as fallback | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Architecture concept (build-end review + Review Verdict + ship verdict check) | ✅ | "Sim, correto" | No |
| Gate R policy + `--tdd` semantics + acceptance criterion | ✅ | Approved after detailed explanation; seeded-fault fallback added to acceptance | Yes |

**Minimum Validations:** 2 (completed 2) ✅

---

## Suggested Requirements for /define

### Problem Statement (Draft)
AgentSpec's mandatory Build→Ship path verifies artifacts and tests but never reviews the code adversarially, so whole-branch bugs that tests cannot reach (proven by the benchmark's shipped UTC date bug) ship undetected — and the build loop offers no enforced test-first discipline.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| AgentSpec users running `/build` + `/ship` | Bugs outside test reach ship silently; no way to demand TDD rigor per run |
| Autopilot (`/auto`) runs | Lights-out runs have no adversarial review before the PR — the highest-risk path has the weakest net |
| AgentSpec maintainers | Benchmark exposed a structural quality gap vs. Superpowers' review discipline |

### Success Criteria (Draft)
- [ ] Benchmark re-run with gate active: review reports the UTC-class bug (naturally occurring or seeded fallback) before handoff and blocks until fixed
- [ ] BUILD_REPORT contains a Review Verdict section with severity-ranked findings and resolutions
- [ ] `/ship` refuses (Cannot ship) when the verdict is missing or has unresolved Critical/Important findings
- [ ] In `/auto`, Gate R retries the fix loop at most 2 rounds, then aborts with a gap report listing open findings
- [ ] `/build --tdd` produces per-task red-run evidence in the BUILD_REPORT; default `/build` behavior unchanged

### Constraints Identified
- Policy lives in the skill layer (sdd-build/sdd-ship/sdd-autopilot); commands remain thin entrypoints (component model)
- Reuse the existing `code-reviewer` agent; no new agents
- Contract changes registered in WORKFLOW_CONTRACTS.yaml
- Ship phase stays archival-only — it validates the recorded verdict, never dispatches reviews

### Out of Scope (Confirmed)
- Cross-model judge/ensemble in the gate (Judge V1+ track)
- Browser/JS test tooling
- TDD default-on
- Changes to supervised-mode human authority (human still decides on findings outside `/auto`)

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 6 |
| Validations Completed | 2 |
| Duration | ~25 min (interactive) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_BUILD_QUALITY_GATES.md`
