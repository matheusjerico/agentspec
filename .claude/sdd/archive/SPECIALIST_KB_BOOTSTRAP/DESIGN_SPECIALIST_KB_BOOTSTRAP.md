# DESIGN: Specialist KB Bootstrap

> Technical design for implementing SPECIALIST_KB_BOOTSTRAP — generated agents born with a light, source-validated KB, promoted to `--validated` on reuse.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SPECIALIST_KB_BOOTSTRAP |
| **Date** | 2026-07-28 |
| **Author** | design-agent (interactive session; validation coverage rule user-confirmed) |
| **DEFINE** | [DEFINE_SPECIALIST_KB_BOOTSTRAP.md](./DEFINE_SPECIALIST_KB_BOOTSTRAP.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│              SPECIALIST KB BOOTSTRAP — SYSTEM DIAGRAM                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DESIGN phase (unchanged surface — Step 4.5 already runs the sub-flow)      │
│  ┌───────────────────────────────────────────────────────────┐              │
│  │ specialist-autoprovision sub-flow, step 2 (agent branch)  │              │
│  │                                                           │              │
│  │  domain in _index.yaml? ── YES ──► kb_domains: [domain]   │              │
│  │        │                           (cite existing KB)     │              │
│  │        NO                                                 │              │
│  │        ▼                                                  │              │
│  │  ★ KB BOOTSTRAP (new): kb_domains: [domain] anyway        │              │
│  │    manifest += task "create KB {domain}" @kb-architect    │              │
│  │    ordered BEFORE every task of the new specialist        │              │
│  └───────────────────────────────────────────────────────────┘              │
│                              │                                              │
│                              ▼                                              │
│  BUILD phase (existing Gate B machinery governs everything below)           │
│  ┌───────────────────────────────────────────────────────────┐              │
│  │ KB task: @kb-architect (frontmatter model: sonnet)        │              │
│  │  • light single-pass, genai shape, _templates binding     │              │
│  │  • structural claims cite official docs (ADR-1)           │              │
│  │  • provenance header on every file (ADR-2)                │              │
│  │  • blocking hygiene grep → additive _index.yaml           │              │
│  │  ├─ ✅ verified ──► specialist tasks run WITH grounding   │              │
│  │  └─ ❌ 3 retries ──► REVERT: kb_domains: [] + router      │              │
│  │        regen + WARN; specialist tasks run anyway          │              │
│  └───────────────────────────────────────────────────────────┘              │
│                                                                             │
│  ★ REUSE HOOK (new, sdd-build): delegation to an agent whose KB's           │
│    index.md carries "Provenance: auto-generated" →                          │
│    manifest += FINAL best-effort task "upgrade KB → --validated"            │
│    (kb-build; max 1 upgrade per run — ADR-3; failure → WARN)                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `specialist-autoprovision` skill (MODIFY) | Owns all new methodology: the KB bootstrap branch in sub-flow step 2, the KB-task prompt contract (shape, validation rule, header), the revert procedure, the upgrade rule + per-run cap, and the extended provenance row shapes | Markdown skill edit — capability owner extended, no new skill |
| `sdd-build` reuse hook (MODIFY) | Thin branch at delegation: unvalidated-KB sensor fires → append the capped upgrade task; points at the skill for all semantics | Markdown edit — hook only |
| `sdd-design` | **No change** — Step 4.5 already invokes the sub-flow; the bootstrap lives inside it | — |
| Gate machinery | **No change** — the KB task and upgrade task are ordinary manifest tasks under Gate B; Gate P untouched | — |
| Reused verbatim | `kb-architect` (T2, `model: sonnet`, WebSearch/WebFetch), `/create-kb` light mode, `kb-build` (`--validated`), `_templates/`, `_index.yaml`, `genai` (few-shot shape) | Existing |

---

## Key Decisions

### Decision 1: Validation coverage — structural claims must cite official docs

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted (user-confirmed 2026-07-28) |
| **Date** | 2026-07-28 |

**Context:** The DEFINE delegated the light-mode cost/assurance dial: which claims in a generated KB must carry source citations?

**Choice:** **Structural claims** — versions, API signatures, configuration keys and defaults, syntax, and code examples MUST cite an official-docs source fetched during the pass (WebSearch/WebFetch). Conceptual prose (trade-off explanations, when-to-use guidance) may come from model knowledge, covered by the confidence declared in the provenance header.

**Rationale:** Hallucination damage concentrates in falsifiable specifics — a wrong config default or invented API signature grounds the specialist into concrete failure; imprecise prose does not. Structural-only validation costs roughly half a dozen fetches per KB, keeping the single-pass profile the timing decision (Build task) depends on.

**Alternatives Rejected:**
1. Every claim cited — a single pass with dozens of fetches becomes a disguised `--validated`; the cost that motivated the original YAGNI cut returns through the back door.
2. Agent's own judgment (today's light behavior) — explicitly rejected by the user at the brainstorm quality gate; makes the header's confidence claim unauditable.

**Consequences:**
- Trade-off accepted: conceptual prose can still be subtly off — flagged as such by the header, and correctable at promotion time (`--validated` re-researches everything).
- Benefit gained: the KB-task verification is checkable — structural claims without a source URL fail the task (Gate B retry), not a vibe check.

---

### Decision 2: Provenance header on every file; sensor = one line in the domain's `index.md`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** The header format and the machine-readable "unvalidated" sensor were delegated to Design (DEFINE A-004). The sensor must be cheap (checked at every delegation) and must not change schemas other components parse.

**Choice:** Every generated file opens with the provenance block (Pattern 2). The **sensor is the single line `> **Provenance**: auto-generated` in the domain's `index.md`** — one file read per delegated domain, no `_index.yaml` schema change. Promotion flips that line to `> **Provenance**: validated ({date})` in `index.md` and all sibling files.

**Rationale:** Extends the existing house style (`genai` files already carry `MCP Validated` + `Confidence` stamps) instead of inventing metadata. `_index.yaml` is parsed by registration flows and the KB discovery step of every phase — an additive-but-new field there would ripple through consumers for no gain over a header line.

**Alternatives Rejected:**
1. `validation:` field in `_index.yaml` — schema change with multiple consumers; documented as the A-004 fallback if header sensing proves unreliable.
2. Scanning all domain files at delegation — N reads where one suffices; `index.md` is the domain's declared front door.

**Consequences:**
- Trade-off accepted: the sensor trusts `index.md` to be present and headed correctly — guaranteed by the KB task's own verification (a KB without a conformant `index.md` fails the task).
- Benefit gained: zero schema migrations; the sensor doubles as human-facing warning text.

---

### Decision 3: Promotion budget — max 1 upgrade per run (drip promotion)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-07-28 |

**Context:** A run may delegate to several agents with unvalidated KBs. The `--validated` build is the expensive 6-stage flow; appending several as tail tasks could dwarf the run's own work — best-effort tail work must be bounded.

**Choice:** At most **one** upgrade task per run — the first-used unvalidated KB. Every other unvalidated KB touched by the run gets a provenance row (`upgrade deferred — promotion budget spent`) recommending `/create-kb <domain> --validated`.

**Rationale:** Reuse keeps firing on future runs, so deferred KBs are promoted one run at a time — the fleet converges to validated without any single run paying a spike. Bounded tail cost preserves the "run's critical path is never hostage" property the timing decision (Q5) was chosen for.

**Alternatives Rejected:**
1. Upgrade every unvalidated KB used — unbounded tail cost; a run touching three bootstrapped domains triples its budget after its real work is done.
2. No automatic upgrade beyond a recommendation — collapses into the "post-run advisory" option the user rejected; light KBs would linger indefinitely.

**Consequences:**
- Trade-off accepted: convergence takes as many runs as there are unvalidated KBs in heavy rotation — acceptable drip.
- Benefit gained: predictable worst-case run cost: real work + at most one light KB creation + at most one validated upgrade.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `.claude/skills/specialist-autoprovision/SKILL.md` | Modify | KB bootstrap branch in sub-flow step 2; new "KB bootstrap" section (task prompt contract, header format, revert procedure, upgrade rule + cap, provenance rows) | (general) | None |
| 2 | `.claude/skills/sdd-build/SKILL.md` | Modify | Reuse-detection branch at delegation (sensor check + capped upgrade-task append; semantics pointer to the skill) | (general) | 1 |
| 3 | `CHANGELOG.md` | Modify | `[Unreleased]` entry | (general) | 1–2 |
| 4 | `CLAUDE.md` | Modify | Key Files row for `specialist-autoprovision` gains the KB bootstrap mention | (general) | 1 |
| 5 | `docs/reference/README.md` | Modify | Skill catalog row updated (KB bootstrap + promotion) | (general) | 1 |
| 6 | `plugin/` tree | Regenerate | `./build-plugin.sh` — mirrors the two edited skills; never hand-edited | (general) | 1–5 |

**Total Files:** 6 manifest rows (5 authored + 1 regenerated tree). No skill-count changes — no new components.

---

## Agent Assignment Rationale

> Step 4.5 citation rule applied (the parent feature's own sensor, dogfooded):

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| (general) | 1–6 | No `routing.json` agent covers skill/framework authoring; the capability is covered by citable skills — `create-skill` (skill conventions) and `component-model` (extend-the-owner decision) — so per the skill-citation clause this is `(general)` with those skills loaded, **not a gap**. Note: `@kb-architect` is cited by the *designed flow* (it executes the KB tasks this feature creates at run time) but is correctly absent from this manifest — this feature only edits markdown. |

**Agent Discovery:**
- Scanned: `routing.json` (58 agents) via the citation rule
- Result: 0 gaps — no provisioning sub-flow triggered for this feature's own build

---

## Code Patterns

### Pattern 1: KB bootstrap branch (inserted into the sub-flow's step 2, agent branch)

```markdown
When the layer is AGENT, check the domain against `.claude/kb/_index.yaml`:

- **Domain registered** → declare `kb_domains: [domain]` citing the existing KB. Done.
- **Domain absent** → declare `kb_domains: [domain]` anyway, and append to the file manifest:

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| N | `.claude/kb/{domain}/` | Create | Bootstrap KB (light + structural-claim validation, genai shape) | @kb-architect | None |
| … | (every task of the new specialist) | … | … | @{new-specialist} | N, … |

The dependency column is the guarantee: no delegation to the new specialist
before the KB task verifies.
```

### Pattern 2: Provenance header (top of every generated KB file; the `index.md` copy is the sensor)

```markdown
> **Provenance**: auto-generated (specialist-kb-bootstrap)
> **Date**: {YYYY-MM-DD}
> **Sources**: {official-docs URLs fetched during the pass}
> **Confidence**: 0.80 — structural claims source-cited; conceptual prose model-derived
> **Note**: review before promoting to ground truth; promote via `/create-kb {domain} --validated`
```

### Pattern 3: KB task delegation prompt (the contract the sub-flow hands @kb-architect)

```markdown
Create the KB domain `{domain}` in light single-pass mode:
- Shape: imitate `.claude/kb/genai/` (index.md, quick-reference.md, 3-4 concepts/, 3-4 patterns/)
- Structure: binding templates in `.claude/kb/_templates/`
- Validation rule (binding): every STRUCTURAL claim — versions, API signatures,
  config keys/defaults, syntax, code examples — must cite an official-docs URL
  you fetched this pass. Conceptual prose may be model-derived.
- Header: Pattern 2 block at the top of EVERY file, sources filled in.
- Register the domain ADDITIVELY in `.claude/kb/_index.yaml` — never modify other entries.
- Do not include any run-private context (client names, credentials, feature details).

Verification (task fails without all four): index.md carries the header; every
structural claim has a source; _index.yaml gained exactly one entry; hygiene grep clean.
```

### Pattern 4: Reuse-detection branch (inserted into `sdd-build` Delegation)

```markdown
### KB promotion on reuse (specialist-kb-bootstrap)

Before delegating to an agent, check each of its `kb_domains`: if the domain's
`index.md` opens with `> **Provenance**: auto-generated` and this run's promotion
budget is unspent (max 1 upgrade per run), append as the run's FINAL task:

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| Z | `.claude/kb/{domain}/` | Upgrade | Promote to --validated (kb-build); BEST-EFFORT: failure → WARN, never a blocker | (general — kb-build skill) | all prior tasks |

Budget spent or additional unvalidated KBs → provenance row
"upgrade deferred — promotion budget spent" recommending `/create-kb {domain} --validated`.
Semantics owner: `.claude/skills/specialist-autoprovision/SKILL.md` (KB bootstrap section).
```

### Pattern 5: Revert procedure (owned by the skill; executed when the KB task exhausts Gate B retries)

```bash
# 1. Agent frontmatter: kb_domains: [{domain}] → kb_domains: []
# 2. Remove any partial KB directory and its _index.yaml entry (leave no broken reference)
# 3. Regenerate the oracle:
python3 scripts/generate-agent-router.py
# 4. Provenance row: "KB bootstrap failed — reverted to kb_domains: []" + WARN
# 5. Specialist tasks proceed (status-quo grounding)
```

---

## Data Flow

```text
1. Design: sub-flow step 2 (agent branch) → domain absent from _index.yaml
   │        → agent declares kb_domains: [domain] + KB task enters manifest (Pattern 1)
   ▼
2. Build: KB task runs first (dependency order) — @kb-architect on its own model
   │        Pattern 3 contract: genai shape, structural claims cited, header, additive index
   ├─ verified → specialist tasks run WITH grounding
   └─ failed after 3 retries → Pattern 5 revert → specialist tasks run anyway (WARN)
   ▼
3. Any later run: delegation touches an agent whose KB index.md says auto-generated
   │        → Pattern 4: ONE upgrade task appended as the run's final task
   ├─ success → headers flip to validated ({date}) — sensor stops firing
   └─ failure → WARN; light KB remains; next run may try again
   ▼
4. Every event (create / revert / upgrade / defer) → provenance row in
   RUN REPORT (autonomous) or BUILD_REPORT (supervised)
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Official documentation sites | WebSearch/WebFetch from `@kb-architect` (already in its tool scope) | None (public docs) |
| `scripts/generate-agent-router.py` | Local CLI — revert path only | None (local) |
| `_index.yaml` / `_templates/` | File read/write — additive registration, binding shapes | None (local) |
| Task tool | Subagent delegation — `@kb-architect` on its frontmatter model | Session |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Structural | Edited skills remain valid; mirrors in sync; router untouched | Manifest rows 1–2, 6 | `./build-plugin.sh` + `git diff --exit-code plugin/`; `generate-agent-router.py --check` (zero drift — no agent frontmatter edited) | Zero drift |
| Scenario | AT-001/002/003: existing-KB citation, bootstrap task insertion + ordering, KB task execution with header/citation verification | Fixture design session: uncovered domain (e.g. `elixir`) forcing an agent gap in an un-KB'd domain | Supervised `/design` + `/build` dry run on a scratch branch | AT-001–003 |
| Scenario | AT-004: revert path | KB task forced to fail (fixture: unreachable sources) | Supervised dry run; inspect frontmatter revert + WARN row | AT-004 |
| Scenario | AT-005/006: reuse promotion + cap; no duplicate creation | Second dry run delegating to the bootstrapped agent; a run touching 2 unvalidated KBs | Inspect final task list (exactly 1 upgrade) + deferral row | AT-005–006 |
| Scenario | AT-007/008: skill-gap boundary; provenance rows | Fixture skill-shaped gap; report inspection | Dry run | AT-007–008 |
| Hygiene | Generated KB content clean of private context | KB task output | Blocking grep against the maintainer's private-context sanitization list (kept outside the repo) | 100% of generated files |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| KB task verification fails (missing header, uncited structural claim, index conflict, hygiene hit) | Gate B fix-and-retry with the failing check named | Yes (3, Gate B) |
| KB task exhausts retries | Pattern 5 revert: `kb_domains: []`, partial KB removed, router regenerated, WARN — specialist tasks proceed | No — degrade, never abort |
| Upgrade task fails (kb-build error, budget, network) | WARN row; light KB remains; sensor fires again next run | No — best-effort by contract |
| Multiple unvalidated KBs in one run | First-used gets the upgrade; others get "upgrade deferred" rows (ADR-3) | n/a |
| Domain gap repeats within a run | Cite the KB created earlier in the run; zero duplicate creations | n/a |
| `index.md` unreadable at sensor check | Treat as NOT unvalidated (no upgrade appended) + WARN row — a broken sensor never triggers expensive work | No |

---

## Configuration

No new config files. Policy constants and single-source owners:

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| Promotion budget | policy constant | 1 upgrade per run | Owned by the KB bootstrap section of `specialist-autoprovision` (ADR-3) |
| Unvalidated sensor | policy constant | `> **Provenance**: auto-generated` line in domain `index.md` | Same owner (ADR-2) |
| Validation rule | policy constant | Structural claims cite official docs | Same owner (ADR-1) |
| KB task model | frontmatter | `kb-architect` → `model: sonnet` | Owned by the agent's frontmatter — no override surface |

---

## Security Considerations

- Generated KB content passes the blocking private-context hygiene grep before landing — same gate as generated components; never land-then-clean.
- Sources are public official-docs URLs only; no credentials or internal endpoints ever appear in `Sources:` lines.
- Provenance rows record events and sensor states — never environment values or keys.
- No new executable surface: the flow adds markdown tasks executed by existing agents and scripts.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Provenance rows per event: `KB created` / `KB bootstrap failed — reverted` / `KB upgraded` / `upgrade deferred (budget)` — in RUN REPORT (autonomous) or BUILD_REPORT (supervised) |
| Metrics | The rows carry domain, mode (light/validated), trigger, outcome — countable post-hoc for promotion-convergence tracking |
| Tracing | Header `Sources:` lines give per-claim audit trails; WARN rows mark every degradation |

---

## Pipeline Architecture (if applicable)

N/A — framework tooling feature (AgentSpec developing AgentSpec); no data pipelines, partitions, or quality gates involved.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-28 | design-agent | Initial version — Decisions 1–3; validation coverage (Decision 1) user-confirmed in session |
| 1.1 | 2026-07-28 | ship-agent | Shipped and archived |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_SPECIALIST_KB_BOOTSTRAP.md`
