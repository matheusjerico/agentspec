# DESIGN: Pr Readiness

> Technical design: `pr_readiness` contract block with per-item evidence mapping, a PR_READY template (checklist + §14.3 description skeleton), Ship-side generation after Gate S, /create-pr consumption with mutable-state revalidation, and the Build/Autopilot boundary lines. Zero linter changes.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | PR_READINESS |
| **Date** | 2026-07-29 |
| **Author** | design-agent (autopilot conduct) |
| **DEFINE** | [DEFINE_PR_READINESS.md](./DEFINE_PR_READINESS.md) |
| **Risk Level** | medium (echo from DEFINE — publication path + three skills; explicit-intent guard preserved) |
| **Status** | ✅ Complete (Built) |
| **Design Confidence** | 0.90 — conduct/data/template increment; A-003 validated against the real 405-line command |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│              UNIFIED PR READINESS — SYSTEM DIAGRAM                    │
├──────────────────────────────────────────────────────────────────────┤
│  ONE definition (pr_readiness block, evidence-mapped):                │
│    branch: tree clean · base resolved      ← git state               │
│    quality: lint/types/tests/build         ← report Verification     │
│    traceability: MUSTs covered             ← filled matrix           │
│    review: verdict clean* · 0 blocking     ← Review Verdict section  │
│    delivery: migration/rollback/residuals  ← report + SHIPPED        │
│                                                                      │
│  Build  → produces evidence, NEVER opens PRs                         │
│  Ship   → after Gate S: validate the contract from archived evidence │
│           → PR_READY_{F}.md (reports/) or a gap report naming exact  │
│             actions — non-destructive, ship still completes          │
│  /create-pr → PR_READY present: revalidate the MUTABLE subset        │
│           immediately before publication (tree clean, tests green,   │
│           verdict unchanged) + description from the skeleton         │
│           (matrix PASTED, never reconstructed);                      │
│           PR_READY absent: legacy conduct byte-compatible;           │
│           publication ONLY on explicit user intent (autopilot's PR   │
│           stage = flag-sanctioned intent)                            │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `pr_readiness` block | 5 dimensions, 13 items, each with `evidence:` mapping (v3.15.0) | YAML |
| `PR_READY_TEMPLATE.md` | Checklist-with-evidence + §14.3 description skeleton (10 sections) | Markdown template (new) |
| Ship generation step | Post-Gate-S validation + artifact write or gap report | sdd-ship SKILL |
| /create-pr consumption | Revalidation of the mutable subset + description reuse + intent guard | Command markdown |
| Boundary lines | sdd-build evidence-only; sdd-autopilot PR stage consumes PR_READY | Skill markdown |

---

## Key Decisions

### Decision 1: PR_READY generation is post-Gate-S and additive — never a new ship blocker `[ASSUMED 0.90]`
Gate S's 6-item checklist stays untouched (DEFINE Out of Scope). A failed readiness dimension yields a gap report inside the PR_READY artifact itself (status: `⚠ gaps`), naming exact actions (§14.5) — ship completes, the PR stage/user decides.

### Decision 2: Mutable vs frozen subset split `[ASSUMED 0.90]`
Frozen at ship (matrix coverage, review verdict recorded, delivery notes) — re-reading the archive suffices. Mutable (working tree clean, tests green, verdict unchanged vs new commits) — /create-pr revalidates immediately before publication; any drift → refuse with the §14.5 action list, never republish stale readiness.

### Decision 3: Legacy conduct preserved byte-compatible `[ASSUMED 0.92]`
/create-pr without a PR_READY artifact behaves exactly as today (standalone users, non-SDD repos). The consumption branch is an additive section keyed on artifact existence.

---

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-CONTRACT-001
      title: pr_readiness block + v3.15.0 history
      requirements: [REQ-001, REQ-006]
      depends_on: []
      files: { create: [], modify: [.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: contract, commit: "feat(sdd): pr_readiness contract data" }
      acceptance: ["yaml.safe_load exposes pr_readiness with evidence mapping"]
      verification:
        green: "python3 -c 'import yaml; yaml.safe_load(open(\".claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml\"))[\"pr_readiness\"]'"
    - id: TASK-TMPL-001
      title: PR_READY_TEMPLATE.md
      requirements: [REQ-002]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [.claude/sdd/templates/PR_READY_TEMPLATE.md], modify: [], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tmpl, commit: "docs(sdd): PR_READY template" }
      acceptance: ["checklist with evidence pointers + 10 description sections"]
      verification:
        green: "grep -q 'Residual risks' .claude/sdd/templates/PR_READY_TEMPLATE.md"
    - id: TASK-SKILL-001
      title: sdd-ship generation step (post-Gate-S)
      requirements: [REQ-003]
      depends_on: [TASK-TMPL-001]
      files: { create: [], modify: [.claude/skills/sdd-ship/SKILL.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: docs, commit: "docs(sdd): ship generates PR_READY" }
      acceptance: ["validation from archived evidence; gap report on failure; non-blocking"]
      verification:
        green: "grep -q 'PR_READY' .claude/skills/sdd-ship/SKILL.md"
    - id: TASK-CMD-001
      title: /create-pr consumption + revalidation + intent guard
      requirements: [REQ-004]
      depends_on: [TASK-TMPL-001]
      files: { create: [], modify: [.claude/commands/workflow/create-pr.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: medium
      execution: { tdd: "off", parallel_group: docs2, commit: "docs(sdd): create-pr consumes PR_READY" }
      acceptance: ["mutable-subset revalidation; matrix pasted; legacy branch; explicit intent"]
      verification:
        green: "grep -q 'PR_READY' .claude/commands/workflow/create-pr.md"
    - id: TASK-SKILL-002
      title: sdd-build boundary + sdd-autopilot PR stage
      requirements: [REQ-005]
      depends_on: [TASK-CONTRACT-001]
      files: { create: [], modify: [.claude/skills/sdd-build/SKILL.md, .claude/skills/sdd-autopilot/SKILL.md], tests: [] }
      owner: "(general)"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: docs3, commit: "docs(sdd): PR boundaries" }
      acceptance: ["build evidence-only; autopilot PR stage consumes PR_READY"]
      verification:
        green: "grep -q 'never opens' .claude/skills/sdd-build/SKILL.md"
    - id: TASK-TEST-001
      title: Documental anchors
      requirements: [REQ-007]
      depends_on: [TASK-CONTRACT-001, TASK-TMPL-001, TASK-SKILL-001, TASK-CMD-001, TASK-SKILL-002]
      files: { create: [tests/test_pr_readiness.py], modify: [], tests: [tests/test_pr_readiness.py] }
      owner: "@test-generator"
      reviewer: "@code-reviewer"
      risk: low
      execution: { tdd: "off", parallel_group: tests, commit: "test(sdd): pr readiness anchors" }
      acceptance: ["block+evidence, template, three consumers, intent guard, history"]
      verification:
        green: "rtk proxy python3 -m pytest tests/test_pr_readiness.py -q"
```

---

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type |
|---|-----|----------|-------|-------|-------------------|
| 1 | REQ-001 | MUST | TASK-CONTRACT-001 | tests/test_pr_readiness.py | contract |
| 2 | REQ-002 | MUST | TASK-TMPL-001 | tests/test_pr_readiness.py | deterministic_inspection |
| 3 | REQ-003 | MUST | TASK-SKILL-001 | tests/test_pr_readiness.py | deterministic_inspection |
| 4 | REQ-004 | MUST | TASK-CMD-001 | tests/test_pr_readiness.py | deterministic_inspection |
| 5 | REQ-005 | MUST | TASK-SKILL-002 | tests/test_pr_readiness.py | deterministic_inspection |
| 6 | REQ-006 | MUST | TASK-CONTRACT-001 | tests/test_pr_readiness.py | contract |
| 7 | REQ-007 | SHOULD | TASK-TEST-001 | tests/test_pr_readiness.py | deterministic_inspection |

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `WORKFLOW_CONTRACTS.yaml` | Modify | `pr_readiness` block + v3.15.0 | (general) | None |
| 2 | `.claude/sdd/templates/PR_READY_TEMPLATE.md` | Create | Checklist + description skeleton | (general) | 1 |
| 3 | `.claude/skills/sdd-ship/SKILL.md` | Modify | Generation step | (general) | 2 |
| 4 | `.claude/commands/workflow/create-pr.md` | Modify | Consumption section | (general) | 2 |
| 5 | `.claude/skills/sdd-build/SKILL.md` + `sdd-autopilot/SKILL.md` | Modify | Boundaries | (general) | 1 |
| 6 | `tests/test_pr_readiness.py` | Create | Documental anchors | @test-generator | 1–5 |

**Total Files:** 7 across 6 tasks

**`pr_readiness` block (file 1, exact shape):**

```yaml
pr_readiness:
  shared_by: [build, ship, create-pr]   # one definition, three consumers (§14.5)
  branch:
    working_tree_clean: { required: true, evidence: "git status --short empty", mutable: true }
    base_resolved: { required: true, evidence: "merge-base with the target branch resolves", mutable: true }
  quality:
    lint: { required: pass, evidence: "BUILD_REPORT Verification Results — Lint Check", mutable: false }
    types: { required: pass_or_not_configured, evidence: "BUILD_REPORT Verification Results — Type Check", mutable: false }
    tests: { required: pass, evidence: "BUILD_REPORT Verification Results — Tests; re-run at publication", mutable: true }
    build: { required: pass_or_not_configured, evidence: "project build command when configured", mutable: true }
  traceability:
    must_requirements_covered: { required: true, evidence: "filled Traceability Matrix — every MUST row Result pass or exception-recorded", mutable: false }
  review:
    branch_verdict: { required: [clean, clean-with-minors], evidence: "BUILD_REPORT Review Verdict", mutable: false }
    blocking_findings_open: { required: 0, evidence: "Review Verdict findings table — no OPEN Critical/Important", mutable: false }
    verdict_unchanged: { required: true, evidence: "no commits after ship without re-review", mutable: true }
  delivery:
    migration_plan: { required: present_or_not_applicable, evidence: "BUILD_REPORT/SHIPPED delivery notes", mutable: false }
    rollback_plan: { required: present_or_not_applicable, evidence: "BUILD_REPORT/SHIPPED delivery notes", mutable: false }
    residual_risks: { required: documented, evidence: "Review Verdict recorded minors + SHIPPED residuals", mutable: false }
  behavior:
    build: "produces evidence, never opens PRs"
    ship: "validates this contract after Gate S; writes PR_READY_{FEATURE}.md or a gap report — non-destructive"
    create_pr: "consumes PR_READY when present; revalidates every mutable item immediately before publication; explicit user intent required (autopilot PR stage = flag-sanctioned intent); no PR_READY → legacy conduct"
```

---

## Agent Assignment Rationale

| Agent | Files | Citation (routing.json) |
|-------|-------|-------------------------|
| @test-generator | 6 | "Test automation expert for Python … pytest" |
| (general) | 1–5 | Skill citation: `component-model` |

---

## Code Patterns

### PR_READY template skeleton (file 2 core sections)

```markdown
# PR READY: {Feature}
## Readiness Checklist  (one row per contract item: status + evidence pointer + mutable?)
## PR Description (generated — paste, don't rebuild)
### Problem & solution / ### Scope & out of scope / ### Requirements delivered
### Test strategy / ### Traceability Matrix (summarized) / ### Residual risks
### Migration & rollback / ### Review findings / ### Validation instructions
### Screenshots (when applicable)
## Gaps (when any item failed — exact actions; otherwise "None")
```

---

## Data Flow

```text
Build (evidence) → Ship Gate S → validate pr_readiness → PR_READY artifact
→ /create-pr: revalidate mutable subset → publish on explicit intent
→ description pasted from the skeleton → PR_READY cleaned after URL exists
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| GitHub via gh CLI | existing /create-pr path | unchanged |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Contract (documental) | Block (5 dims, 13 items, evidence per item), template sections, 3 consumers, intent guard, history | file 6 | pytest | AT-001…AT-009; ≥10 tests |
| Regression + parity | Prior suites + Step 5e | existing | pytest | AT-009/010 |
| E2E (dogfood) | This run's ship generates the first PR_READY; its PR consumes it | live | - | full loop |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Readiness dimension fails at ship | PR_READY written with `⚠ gaps` + exact actions; ship completes | No |
| Mutable revalidation fails at create-pr | Refuse publication; list the drift; never destroy | No |
| PR_READY absent | Legacy conduct | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `pr_readiness.<dim>.<item>` | map | §14.1 | required + evidence + mutable flag |
| `pr_readiness.behavior` | map | 3 consumers | The shared conduct contract |

---

## Security Considerations

- Publication keeps the explicit-intent guard; nothing widens external actions.
- Revalidation-before-publication closes the stale-readiness window (§20 risk table).

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Readiness | PR_READY checklist rows carry evidence pointers — auditable without re-derivation |
| Drift | Revalidation failures name the exact mutable item that moved |

---

## Pipeline Architecture (if applicable)

Not applicable.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | design-agent (autopilot) | Initial — 3 [ASSUMED] decisions (≥ 0.90), 6-task v2 manifest, matrix |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_PR_READINESS.md`
