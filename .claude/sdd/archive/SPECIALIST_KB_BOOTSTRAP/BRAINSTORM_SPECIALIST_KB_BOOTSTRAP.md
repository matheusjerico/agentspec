# BRAINSTORM: Specialist KB Bootstrap

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SPECIALIST_KB_BOOTSTRAP |
| **Date** | 2026-07-28 |
| **Author** | brainstorm-agent (interactive session — every decision user-confirmed) |
| **Status** | ✅ Shipped |

---

## Initial Idea

**Raw Input (user, translated):**

> A newly created agent should be born with a KB. There is a KB-generation agent, correct? So provisioning should launch a subagent for KB creation — and that subagent can use a model that is NOT Fable (the main-loop model).

**Context Gathered:**

- This revisits YAGNI cut #1 of SPECIALIST_AUTOPROVISION (shipped and archived 2026-07-28): "Auto-creation of KB domains during provisioning" was deferred with "Can Add Later? Yes". The SHIPPED document's recommendations already pointed here: "If A-003 proves wrong (specialists with `kb_domains: []` underperform), revisit the deferred KB auto-creation with `/create-kb` single-pass mode."
- The KB-generation agent exists: `kb-architect` (T2, **`model: sonnet`**, tools include `WebSearch`/`WebFetch`). Key fact: subagents launched via the Task tool run on the model declared in **their** frontmatter, not the main-loop model — the "non-Fable" requirement is native delegation behavior, requiring zero new configuration.
- `/create-kb` has two modes: **light** (single-pass via kb-architect, cheap, default) and **`--validated`** (the `kb-build` skill: 6 stages with adversarial refutation and an independent fact-check gate — expensive, opt-in). The light mode has no mandatory external-validation gate today; quality rides on the agent's own confidence model.
- Existing KB house style already carries validation stamps: `genai` files have `MCP Validated: <date>` and `Confidence: 0.95` headers — provenance marking is established practice, not an invention.
- The shipped provisioning flow (specialist-autoprovision) creates agents with `kb_domains: []` when no KB covers the domain, records the gap in provenance, and the file manifest already supports dependency-ordered tasks (ADR-2 precedent: deferred checklist items as manifest build tasks).

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | Extension of `.claude/skills/specialist-autoprovision/SKILL.md` (sub-flow step) + a reuse-detection hook in `sdd-build` | Extend the capability's owner — no new skill (component model) |
| Relevant KB Domains | `genai` (multi-agent-systems, agentic-workflow, guardrails), `prompt-engineering`, `shared/component-model.md` | Same domains as the parent feature |
| IaC Patterns | N/A — framework tooling feature | No infrastructure |

---

## Discovery Questions & Answers

> Interactive session — every answer selected explicitly by the user.

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | When is the KB created relative to the first delegation? | **Dependency-ordered Build task**: the agent is born with `kb_domains: [domain]`, and the manifest gains a "create KB" task (`@kb-architect`) ordered **before** the specialist's tasks. Design stays lean; delegation never runs un-KB'd | The ordering machinery in `sdd-build` is the guarantee — no new orchestration |
| 2 | Quality bar for the auto-generated KB? | **Light + mandatory source validation**: single-pass, but claims must be validated against official docs via WebSearch/WebFetch, and every file carries a provenance header (auto-generated, date, sources, confidence, "review before promoting to ground truth") | Mitigates the hallucinated-grounding risk that motivated the original cut; makes mandatory what light mode leaves to agent judgment |
| 3 | Which generated components, which modes? | **Agents only, both modes** (supervised `/design` and `/auto`). Generated skills stay out: they are methodology (the HOW), not consumers of domain grounding | KB cost lands only on the rarer agent-shaped gap; behavior identical across modes |
| 4 | Gold-standard sample for the generator to imitate? | **`genai`** — already practices validation/confidence headers, lean 5–9 file structure, executable code patterns | Few-shot form target; prevents imitating volume instead of shape |
| 5 | When does the `--validated` upgrade run for a reused-but-unvalidated KB? | **Final task of the reusing run, best-effort** (failure → WARN, never a blocker): the run's real work is not held hostage by the 6-stage build; the next runs get the validated KB | Creates the two-tier lifecycle: born light → promoted on first reuse |

**Minimum Questions:** 3 ✅ (5 asked, all user-answered)

---

## Sample Data Inventory

> Samples improve LLM accuracy through in-context learning and few-shot prompting.

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Gold-standard KB (few-shot shape) | `.claude/kb/genai/` | 1 domain (11 files) | User-selected exemplar: header stamps, lean structure, code patterns |
| KB structure templates | `.claude/kb/_templates/` | 7 | The binding artifact shapes |
| Domain registry | `.claude/kb/_index.yaml` | 1 | Existence sensor + additive registration target |
| Generator agent | `.claude/agents/architect/kb-architect.md` | 1 | T2, `model: sonnet`, WebSearch/WebFetch in scope |
| Related flows | `/create-kb` command, `kb-build` skill, `specialist-autoprovision` skill (sub-flow + provenance shape) | 3 | The pipeline to reuse verbatim |
| Provenance header examples | `genai` file headers (`MCP Validated`, `Confidence`) | n | Existing house style to extend, not invent |

**How samples will be used:**

- `genai` as the few-shot form target in the KB-creation task prompt
- `_templates/` + `_index.yaml` as binding structure and registration contracts
- Existing headers as the base for the auto-generated provenance header format

---

## Approaches Explored

### Approach A: Sub-flow extension + ordinary Build task ⭐ Selected

**Description:** Extend the `specialist-autoprovision` sub-flow: when the layer gate lands on AGENT and the domain is absent from `_index.yaml`, the agent is created already declaring `kb_domains: [domain]`, and the manifest gains a "create KB {domain} (light + source-validated, `@kb-architect`)" task dependency-ordered before the specialist's tasks. The KB task is an ordinary Build task — the existing Gate B (3 retries, verification) governs it; **no new gate**. Reuse detection (an unvalidated KB consumed by a delegated agent) appends the `--validated` upgrade as the run's final best-effort task.

**Pros:**
- Zero new machinery: manifest ordering, Gate B, kb-architect, `/create-kb` modes, and provenance rows all exist
- Same pattern as the shipped ADR-2 (deferred items as manifest tasks) — the repo's own precedent
- "Non-Fable" requirement satisfied natively by kb-architect's frontmatter (`model: sonnet`)
- Failure degrades to the exact shipped behavior (`kb_domains: []` + WARN) — never worse than status quo, never silent

**Cons:**
- Build runs get longer when a KB task is present (bounded: light mode, one domain per gap)
- The reusing run still executes on the light KB (upgrade lands for the *next* runs) — accepted trade-off from Q5

**Why Selected:** Confidence **0.95** — KB pattern (genai model-tiering: frontier plans, cheaper models execute; guardrails: pre-execution validation gates) + direct codebase match (ADR-2 deferred-task precedent, dependency ordering, Gate B, kb-architect all compose without modification).

---

### Approach B: Standalone `specialist-kb-bootstrap` skill

**Description:** A new sibling skill hooked into design/build separately from specialist-autoprovision.

**Why not:** The capability is one step of an existing flow; the component model says extend the owner, not create a neighbor. A second skill would restate the sub-flow's context (gap detection, provenance, degradation) — skill sprawl.

---

### Approach C: Synchronous KB creation inside the Design-phase sub-flow

**Description:** The provisioning sub-flow pauses to build the KB before finalizing the manifest.

**Why not:** Rejected by the user at Q1 — lengthens Design, holds the manifest hostage to KB research time, worst case in autopilot (phase budgets, Gate P retries). Creation-time grounding is not needed: delegation happens in Build, and ordering guarantees the KB exists by then.

---

## Data Engineering Context (if applicable)

N/A — framework tooling feature (AgentSpec developing AgentSpec); no data pipelines, sources, or SLAs involved.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | ✅ Explicit — flow diagram confirmed verbatim ("está do jeito que imaginei") 2026-07-28; all five decision forks user-selected |
| **Reasoning** | Earliest guarantee that matters (KB before first delegation, via ordering), full reuse of existing machinery, native model tiering, degradation bounded at the shipped status quo |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | KB task governed by the existing Gate B — no new autopilot gate | It is an ordinary manifest task; Gate B's retry-3 + verification already fits | A dedicated "Gate K" (new policy surface for no new sensor) |
| 2 | Model policy = kb-architect's frontmatter (`model: sonnet`) — no new config | Task-tool delegation already runs subagents on their declared model; single source | A model-override parameter surface for KB tasks |
| 3 | Agent born declaring `kb_domains: [domain]`; KB-task failure reverts to `[]` + router regeneration + WARN | Never-worse-than-status-quo invariant (inherited from the parent feature); no broken KB references survive | Aborting the run on KB failure (KB-less specialist is the functional status quo) |
| 4 | Mandatory provenance header on every generated KB file (auto-generated, date, sources, confidence, review note) | Extends the existing house style (genai stamps); doubles as the "unvalidated" sensor for the upgrade trigger | Unmarked generated KBs (hallucinated grounding with an authority seal) |
| 5 | Two-tier lifecycle: born light → `--validated` upgrade queued as the reusing run's **final best-effort task** (failure → WARN) | Reuse is the evidence the domain matters; the run's critical path is never hostage to the 6-stage build | Blocking upgrade before the reusing delegation; post-run advisory only |
| 6 | `_index.yaml` registration strictly additive; same domain twice in one run cites the just-created KB | Inherited invariants (kb-build additivity; never-provision-twice) | Overwrite/regenerate on repeat encounter |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Backfilling KBs for the 58 existing agents' uncovered territories | Only newly generated agents trigger; backfill is a deliberate act | Yes |
| Judge/eval pass over generated KBs | Judge V1+ territory (same cut as both parent features) | Yes |
| Refreshing stale existing KBs during provisioning | Different problem, different flow | Yes |
| Rollout of generated KBs to vendored consumer repos | `rollout-agentspec` owns distribution | Yes |
| New model-override config for the KB task | kb-architect frontmatter is the single source; "non-Fable" is native | Yes |

> Note: "Auto-upgrade light → `--validated`" was initially cut, then **pulled back into scope by the user** with a reuse trigger and best-effort timing (Decision 5) — recorded here so the scope change is auditable.

---

## Incremental Validations

| Section | Presented | User Validation | Adjusted? |
|---------|-----------|-----------------|-----------|
| End-to-end flow (Design hook → ordered KB task → Build execution → degradation path) | ✅ full ASCII diagram | "está do jeito que imaginei, pode seguir" | No |
| Failure semantics + YAGNI cuts | ✅ | User adjusted: auto-upgrade pulled back into scope with reuse trigger | **Yes** — became Decision 5 + Q5 |
| Upgrade timing (final best-effort task) | ✅ with cost trade-offs | Confirmed (Recommended option) | No |

**Minimum Validations:** 2 ✅ (3 completed, one producing a scope revision — the checkpoint mechanism working as intended)

---

## Suggested Requirements for /define

### Problem Statement (Draft)

A specialist agent generated by the provisioning flow operates ungrounded (`kb_domains: []`) whenever its domain has no KB — the A-003 risk was shipped as accepted — and nothing ever promotes an auto-generated light KB to validated status, so bootstrap-quality grounding becomes permanent by default.

### Target Users (Draft)

| User | Pain Point |
|------|------------|
| Autopilot operator running `/auto` | Generated specialists execute with zero domain grounding; KB quality never improves without manual intervention |
| Supervised `/design` + `/build` users | Manual `/create-kb` detour to ground a just-generated specialist |

### Success Criteria (Draft)

- [ ] 100% of generated **agents** whose domain lacks a KB get a light + source-validated KB created by `@kb-architect` (its own frontmatter model — never the main-loop model) as a manifest task ordered before the specialist's first task
- [ ] 100% of generated KB files carry the provenance header (auto-generated, date, cited sources, confidence, review note)
- [ ] KB-task failure (after Gate B retries) reverts the agent to `kb_domains: []`, regenerates the router, and records a WARN — 0 runs aborted because of a KB task
- [ ] A run that delegates to an agent whose KB is marked unvalidated appends the `--validated` upgrade as its final best-effort task (failure → WARN)
- [ ] `_index.yaml` registration is strictly additive; 0 duplicate KB creations for the same domain within a run
- [ ] Every KB creation and upgrade event has a provenance row (RUN REPORT / BUILD_REPORT)

### Constraints Identified

- No new gates: Gate B governs the KB task; Gate P remains untouched (provisioning policy unchanged)
- Single-source reuse: `/create-kb` light mode, `kb-build` (`--validated`), `kb-architect`, and the `specialist-autoprovision` sub-flow are extended, never restated
- Model policy lives only in kb-architect's frontmatter
- Public-repo hygiene applies to generated KB content (same blocking grep as generated components)
- `genai` is the few-shot shape target; `_templates/` remain the binding structure

### Out of Scope (Confirmed)

- Backfill for existing agents' uncovered territories
- Judge/eval of generated KBs (Judge V1+)
- Refresh of stale existing KBs
- Rollout of generated KBs to vendored repos
- Model-override configuration surface

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 (all user-answered — fully interactive session) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 5 (+1 pulled back into scope by the user) |
| Validations Completed | 3 (one produced a scope revision) |
| Duration | Single interactive session (2026-07-28) |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_SPECIALIST_KB_BOOTSTRAP.md`
