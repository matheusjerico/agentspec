---
name: specialist-autoprovision
description: |
  Detects and fills specialist gaps before implementation is delegated: resolves every task domain in the agent-matched file manifest against the generated router inventory using a mandatory-citation rule, and on a gap runs the JIT provisioning sub-flow — component-model layer gate, create-agent/create-skill SOP authoring, public-repo hygiene gate, mandatory router regeneration, and core ship-checklist validation — so execution is delegated only after the new specialist is citable in the oracle.
  Owns the citation match semantics, the sub-flow steps and their ordering, the supervised/autonomous conduct fork (at most one question, only at the layer decision), the provenance row shape, and the degradation rule when the sensor itself is unavailable. Also owns the KB bootstrap: a generated agent whose domain has no KB is born with a light, source-validated KB — created by kb-architect (its own frontmatter model) as a dependency-ordered build task before the specialist's first delegation — and light KBs are promoted to --validated when reuse is detected, at most one upgrade per run. Consumed as thin hooks by sdd-design (Step 4.5, the primary sensor) and sdd-build (delegation safety net); the proceed/retry/abort policy for autonomous runs is Gate P, owned by sdd-autopilot.
  Use when a manifest row has no citable specialist, when delegation hits an unresolvable @agent, or when asked to check specialist coverage or provision a missing specialist.
  Do not use to author a component when the layer is already decided and no coverage question exists — that is create-skill or create-agent directly — and do not use to change gate budgets or abort semantics, which are owned by sdd-autopilot.
---

# Specialist Autoprovision — gap detection and JIT provisioning

Resolve every task domain against the specialist inventory before delegation; when nothing covers a domain, create the specialist through the existing authoring SOPs — never a bespoke path — and delegate only after the regenerated router resolves it.

This skill owns the methodology. `sdd-design` (Step 4.5) and `sdd-build` (delegation safety net) load it as thin hooks; `sdd-autopilot` owns the autonomous gate policy (Gate P). None of them restate a rule that lives here, and this skill states no gate budget — that is Gate P's.

## The citation rule (match semantics)

A task domain **resolves** if and only if a **citation** can be recorded — a specific inventory entry plus the covering signal:

| Citation type | Form | Resolution |
|---|---|---|
| Agent | `{agent-name, signal}` where the signal is a `kb_domains` hit or explicit coverage in the routing one-liner (`description` first line) in `.claude/skills/agent-router/routing.json` | Manifest row gets `@agent-name`; citation recorded in the Agent Assignment Rationale |
| Skill | An existing skill (`.claude/skills/<name>/SKILL.md`) whose description covers the capability | Manifest row stays `(general)` with that skill loaded — **not a gap** |

**No citable entry → gap → run the provisioning sub-flow.** Never resolve a domain from memory of the inventory: cite the oracle artifact. Never assign a numeric confidence to a match — the citation is the evidence, and it is checkable mechanically after the run.

The oracle is `.claude/skills/agent-router/routing.json` (plus generated `SKILL.md`), regenerated from agent frontmatter by `scripts/generate-agent-router.py` — it cannot drift from the real inventory, which is why ad-hoc greps of agent files are never the sensor.

## The provisioning sub-flow

Run the steps in order. Steps 1–5 are the synchronous core; step 6 schedules the rest.

### 1. Layer gate

Load the `component-model` skill and decide the layer for the missing capability: skill, agent (thin executor), or extend-existing. The four-condition anti-sprawl gate in `.claude/agents/README.md` binds the agent option — no existing agent covers >60%, unique KB/tool combination, ≥3 distinct triggers, no >80% overlap. This fork is the only point the conduct table below may ask a human.

### 2. Author via the SOP

- Layer = skill → author per `create-skill` (naming, placement, frontmatter pitfalls).
- Layer = agent → author per `create-agent` (frontmatter contract as the router reads it: clean first description line, inline `kb_domains`, real escalation targets). Scaffold from `.claude/agents/_template.md`; tool scope least-privilege for the role — no `Bash` or network tools unless the role requires them.
- Layer = extend-existing → apply the extension and stop; no new component, no further sub-flow steps beyond re-verifying the citation.

When the layer is AGENT, check the domain against `.claude/kb/_index.yaml`:

- **Domain registered** → `kb_domains: [domain]` cites the existing KB. Done.
- **Domain absent** → declare `kb_domains: [domain]` anyway and append the KB bootstrap task to the file manifest (see **KB bootstrap** below), dependency-ordered before every task of the new specialist — no delegation ever runs un-KB'd except through the declared revert path.

Generated SKILLS never trigger KB creation — they are methodology, not consumers of domain grounding.

### 3. Hygiene gate (blocking)

Before the component counts as authored, grep it against the public-repo private-context list (client names, credentials, run-private data). A hit **blocks** the component: regenerate without the offending context. Never land-then-clean.

### 4. Regenerate the router and verify the citation

```bash
python3 scripts/generate-agent-router.py

# Agents: the regenerated oracle must resolve the new specialist by name
grep -q "\"name\": \"${NEW_AGENT_NAME}\"" .claude/skills/agent-router/routing.json

# Skills: on-disk presence with parseable frontmatter is the citation
test -f ".claude/skills/${NEW_SKILL_NAME}/SKILL.md"
```

The component **exists** only when this verification passes — a written file whose citation does not verify is a failed provisioning attempt, not a specialist.

### 5. Finalize the manifest row

Record the citation for the new component exactly as for a pre-existing one. Within the same run, a later gap for the same domain cites the just-created component — never provision twice for one domain.

### 6. Schedule the deferred checklist items

Append the authoring SOP's remaining ship-checklist items — plugin mirror rebuild, catalog/README updates, count references, CHANGELOG entry — to the file manifest as ordinary build tasks. They stay binding (Gate B completeness and the pre-ship checklist verify them); they are scheduled, never relaxed. Same contracts, same checklist as hand-authored components — there is no "generated" tier.

## KB bootstrap

Applies only to generated **agents** whose domain is absent from `_index.yaml`. Both modes.

### The KB task

The sub-flow appends one manifest row, ordered before the specialist's tasks:

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| N | `.claude/kb/{domain}/` | Create | Bootstrap KB (light + structural-claim validation, genai shape) | @kb-architect | None |

`@kb-architect` runs on its own frontmatter model (`model: sonnet`) — never the main-loop model. The existing Gate B (3 retries, per-task verification) governs the task; no new gate exists.

**Delegation prompt contract (binding):**

```markdown
Create the KB domain `{domain}` in light single-pass mode:
- Shape: imitate `.claude/kb/genai/` (index.md, quick-reference.md, 3-4 concepts/, 3-4 patterns/)
- Structure: binding templates in `.claude/kb/_templates/`
- Validation rule (binding): every STRUCTURAL claim — versions, API signatures,
  config keys/defaults, syntax, code examples — must cite an official-docs URL
  you fetched this pass. Conceptual prose may be model-derived.
- Header: the provenance block below at the top of EVERY file, sources filled in.
- Register the domain ADDITIVELY in `.claude/kb/_index.yaml` — never modify other entries.
- Do not include any run-private context (client names, credentials, feature details).

Verification (task fails without all four): index.md carries the header; every
structural claim has a source; _index.yaml gained exactly one entry; hygiene grep clean.
```

**Provenance header (every generated file; the `index.md` copy is the machine sensor):**

```markdown
> **Provenance**: auto-generated (specialist-kb-bootstrap)
> **Date**: {YYYY-MM-DD}
> **Sources**: {official-docs URLs fetched during the pass}
> **Confidence**: 0.80 — structural claims source-cited; conceptual prose model-derived
> **Note**: review before promoting to ground truth; promote via `/create-kb {domain} --validated`
```

### Revert path (KB task exhausts Gate B retries)

1. Agent frontmatter: `kb_domains: [{domain}]` → `kb_domains: []`
2. Remove any partial KB directory and its `_index.yaml` entry — no broken references survive
3. Regenerate the oracle: `python3 scripts/generate-agent-router.py`
4. Provenance row `KB bootstrap failed — reverted to kb_domains: []` + WARN
5. The specialist's tasks proceed (status-quo grounding) — the run never aborts because of a KB task

### Promotion on reuse

Sensor: the domain's `index.md` opens with `> **Provenance**: auto-generated`. When a run delegates to an agent whose `kb_domains` include such a domain, the run appends the `--validated` upgrade (`kb-build` via `/create-kb {domain} --validated`) as its **final, best-effort** task — failure records WARN and the light KB remains; success flips every file's header to `> **Provenance**: validated ({date})`, silencing the sensor.

**Promotion budget: at most 1 upgrade per run** — the first-used unvalidated domain wins; every other one gets a provenance row `upgrade deferred — promotion budget spent` recommending the manual command. Reuse keeps firing on later runs, so the fleet converges one promotion at a time (drip promotion) with a bounded worst-case run cost. An unreadable `index.md` at sensor time is treated as NOT unvalidated (+ WARN) — a broken sensor never triggers expensive work.

### KB provenance rows

Every KB event writes one row (RUN REPORT / BUILD_REPORT): `KB created` · `KB bootstrap failed — reverted` · `KB upgraded` · `upgrade deferred (budget)` — with domain, mode (light/validated), trigger, and outcome.

## Conduct fork

| Mode | Layer-gate fork (step 1) | Everything else |
|---|---|---|
| Supervised (`/design`, `/build`) | May ask the user **once** (AskUserQuestion) when the four-condition gate does not decide cleanly | Mechanical — contracts decide; no questions |
| Autonomous (`/auto`) | Assume **skill + thin executor** (the conservative default: a skill can later gain an executor; an unnecessary agent pressures the anti-sprawl gate), record `[ASSUMED]` | Gate P policy (sdd-autopilot): proceed / retry within budget / abort with gap report — never ask |

## Provenance (mandatory per event)

Every provisioning event writes one row — RUN REPORT (autonomous) or BUILD_REPORT (supervised):

```markdown
| Component | Layer | Trigger Domain | Phase | Fork Resolution | Validation |
|-----------|-------|----------------|-------|-----------------|------------|
| terraform-modules (skill) | skill + thin executor | terraform | design (Gate P) | [ASSUMED] conservative default | core checklist PASS; docs items → manifest rows 10–12 |
```

Rows record decisions and sensor presence/absence — never environment values, keys, or run-private data.

## Degradation rules

| Failure | Behavior |
|---|---|
| `scripts/generate-agent-router.py` not executable, or oracle unreadable after one regeneration attempt | **VISIBLE SKIP** + fall back to `(general)` execution with a WARN row — the pre-feature status quo, degraded loudly. Never assume a citation that was not verified |
| Authoring output fails step 4 verification | One regeneration with the violations in context (Gate P budget); supervised mode surfaces the failure to the user instead of aborting |
| Hygiene gate hit | Regenerate without the private context — within the same budget |

The flow may degrade **to** the status quo (`(general)` + WARN), never below it, and never silently.

## Anti-patterns

| Never do | Why | Instead |
|---|---|---|
| Grep agent files as the availability sensor | Reimplements and drifts from the router's parser | Cite `routing.json`; regenerate it when in doubt |
| Score matches numerically | LLM scores are not reproducible run-to-run; a flaky sensor decides component creation | The citation rule — binary, recorded, checkable |
| Create an agent for a capability-shaped gap | Most gaps are methodology, not identity; agent sprawl | Layer gate first; default to skill + thin executor |
| Skip router regeneration after authoring | The component is invisible to every later resolution | Step 4 is binding — no verified citation, no specialist |
| Relax checklist items for generated components | Two quality tiers drift apart | Defer and schedule (step 6); never drop |
| Provision the same domain twice in one run | Duplicate components; anti-sprawl violation | Cite the just-created component |
| Embed run-private context in a generated component | Public repo; hygiene is a blocking gate | Step 3 before anything lands |
| Ship a generated KB without the provenance header | Hallucinated grounding with an authority seal; the promotion sensor goes blind | Header on every file — the KB task's verification fails without it |
| Upgrade more than one KB per run | Unbounded best-effort tail cost | Promotion budget: 1 per run; defer the rest with a provenance row |
| Abort a run because a KB task failed | A KB-less specialist is the functional status quo | Revert path + WARN; the specialist's tasks proceed |

## References

- Oracle: `.claude/skills/agent-router/routing.json` + `scripts/generate-agent-router.py` (parser contract documented in `create-agent`)
- Layer gate: `.claude/skills/component-model/SKILL.md`, grounded in `.claude/kb/shared/component-model.md`; anti-sprawl conditions in `.claude/agents/README.md`
- Authoring SOPs: `.claude/skills/create-skill/SKILL.md` · `.claude/skills/create-agent/SKILL.md` · `.claude/agents/_template.md`
- Consumers: `.claude/skills/sdd-design/SKILL.md` (Step 4.5) · `.claude/skills/sdd-build/SKILL.md` (delegation safety net)
- Autonomous gate policy: `.claude/skills/sdd-autopilot/SKILL.md` (Gate P)
- KB machinery (reused verbatim): `.claude/agents/architect/kb-architect.md` · `/create-kb` (light + `--validated`) · `.claude/skills/kb-build/SKILL.md` · `.claude/kb/_templates/` · `.claude/kb/genai/` (few-shot shape)
- Design rationale: `.claude/sdd/archive/SPECIALIST_AUTOPROVISION/DESIGN_SPECIALIST_AUTOPROVISION.md` (Decisions 1–4) · `.claude/sdd/features/DESIGN_SPECIALIST_KB_BOOTSTRAP.md` (Decisions 1–3, KB bootstrap)
