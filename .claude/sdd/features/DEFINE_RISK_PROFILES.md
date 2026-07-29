# DEFINE: Risk Profiles

> Add a machine-readable `risk_profile` to every new DEFINE — deterministic level derivation, auditable overrides, propagation to Design — rolled out in Observe/Warn mode (nothing new blocks; CRITICAL halt stays fail-closed).

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | RISK_PROFILES |
| **Date** | 2026-07-29 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 15/15 |

**Source:** `docs/superpowers/plans/2026-07-29-agentspec-incremental-improvements.md` — Increment 2 (§8), rollout policy §17.2, PR 2 scope §18 ("delivers Increment 2 in Observe/Warn mode; does NOT yet activate the full rigor matrix"). Phase 0 exploration is carried by the plan itself (approaches compared in §2–§4 against benchmark evidence; YAGNI in §21) — ratified by the maintainer via the program goal.

---

## Problem Statement

AgentSpec applies the same process rigor to every change: a typo-level doc fix and an authentication rewrite walk through identical gates, because no machine-readable risk classification exists — there is a risk register and a CRITICAL halt (plan §5), but no profile that downstream phases and future policies (risk-driven TDD, Task Review — Increments 4–5) can read deterministically.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| AgentSpec maintainer (Matheus) | Develops the framework; sequences Increments 4–5 which consume the profile | Cannot make rigor proportional to risk (plan §4.1) without a machine-readable level; uniform process makes small changes slow and risky changes under-guarded |
| Autopilot runs (`/auto`, `autopilot.sh`) | Autonomous execution where gates read policy inputs, never judgment | No deterministic risk input exists for future gate policy; today the only risk signal is the CRITICAL halt |
| Plugin consumers (vendored installs, user projects) | Run the distributed plugin on real features | Their low-risk changes pay full-process cost; their high-risk changes get no extra scrutiny |

---

## Goals

What success looks like (prioritized):

| Priority | Goal |
|----------|------|
| **MUST** | `DEFINE_TEMPLATE.md` gains a `Risk Profile` section carrying the §8.1 model: `level`, `reasons`, 5 `dimensions` (data_loss, security, reversibility, blast_radius, migration), `override` (applied, author, rationale) |
| **MUST** | `sdd-define` SKILL gains a risk-profile step: score the 5 dimensions, derive `level = max(applicable dimensions)`, apply the deterministic elevation rules, record reasons |
| **MUST** | Deterministic elevation rules land as DATA in `WORKFLOW_CONTRACTS.yaml` (new `risk_profiles` block): auth/authz change → ≥ high; destructive migration → critical; production write without rollback → critical; new endpoint without sensitive data → ≥ medium; pure documentation → normally low; levels enumerated `low/medium/high/critical` |
| **MUST** | Overrides are auditable: `author`, `rationale`, and effect recorded; an override NEVER removes the existing CRITICAL halt (fail-closed, plan §8.2/§17.2) |
| **MUST** | Propagation to Design: `DESIGN_TEMPLATE.md` + `sdd-design` SKILL echo the level and reasons from the DEFINE (level never silently recomputed or dropped) |
| **MUST** | Observe/Warn rollout: spec-linter emits WARN-level findings for define-phase profile gaps (absent section, invalid level, override without rationale) — exit 0, never blocking; `define.required_sections` is NOT extended (that would be Enforce) |
| **MUST** | Legacy DEFINEs (no profile): treated as effective `medium` with a visible WARN — never a silent `low` (plan §8.5) |
| **MUST** | Bump `WORKFLOW_CONTRACTS.yaml` version + history entry (plan §17.1) |
| **SHOULD** | `BUILD_REPORT_TEMPLATE.md` metadata gains an optional `Risk Level` row (additive; absent on legacy reports is not a finding in this increment) |
| **SHOULD** | Contract/documental tests: block shape in YAML, template markers, skill anchors, plugin parity |
| **COULD** | Autopilot RUN REPORT records the feature's risk level as display metadata |
| **COULD** | Keyword hint table (e.g., "auth", "migration", "PII") in the sdd-define step to prompt dimension scoring |

**Priority Guide:**
- **MUST** = MVP fails without this
- **SHOULD** = Important, but workaround exists
- **COULD** = Nice-to-have, cut first if needed

---

## Success Criteria

Measurable outcomes (must include numbers):

- [ ] A new DEFINE with a valid Risk Profile lints with 0 risk findings; one missing/invalid profile element yields exactly WARN-level findings (exit 0, never exit 1) — proven by ≥1 PASS-path and ≥1 WARN-path test per rule
- [ ] The elevation rules exist as data: `risk_profiles` block enumerates 4 levels + 5 dimensions + ≥5 elevation rules, each anchored by ≥1 contract test
- [ ] Level derivation is deterministic: same declared dimensions → same level (max rule), asserted by ≥3 table-driven tests including 1 elevation override case
- [ ] Legacy DEFINE (no profile) produces a WARN naming effective level `medium` — ≥1 test; 0 paths produce a silent `low`
- [ ] Propagation: DESIGN template carries the level echo; ≥1 documental test asserts template + skill anchors on both sides
- [ ] 0 regressions: root suite and spec-linter suite stay green; `./build-plugin.sh` (incl. Step 5e parity) exits 0

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Valid profile passes clean | A DEFINE with level `medium`, 5 dimensions, no override | `spec-lint --phase define` runs | Exit 0, no risk findings |
| AT-002 | Missing profile warns (Observe/Warn) | A new DEFINE without the Risk Profile section | Linter runs | Exit 0, WARN finding with migration guidance |
| AT-003 | Invalid level warns | Profile with `level: banana` | Linter runs | Exit 0, WARN naming allowed levels |
| AT-004 | Override without rationale warns | Profile with `override.applied: true`, empty rationale | Linter runs | Exit 0, WARN naming the missing rationale |
| AT-005 | Legacy default is medium, never silent low | A pre-profile DEFINE | Linter runs | WARN stating effective level `medium` |
| AT-006 | Elevation rules are data | `WORKFLOW_CONTRACTS.yaml` | Contract tests run | 4 levels, 5 dimensions, ≥5 elevation rules asserted verbatim |
| AT-007 | Max-dimension derivation | Dimensions {security: high, others: low} | Derivation test evaluates the rule table | Level ≥ high |
| AT-008 | CRITICAL halt survives override | Profile `level: critical` with `override.applied: true` | Documental tests run | Skill + contract text states the halt is never removed by override; anchor test passes |
| AT-009 | Design echoes the profile | A DEFINE with a profile | DESIGN template/skill inspected | Echo section present; documental test green |
| AT-010 | Plugin parity | `./build-plugin.sh` runs | Step 5e parity test | Exit 0, canonical == packaged |

---

## Out of Scope

Explicitly NOT included in this feature (plan §18 PR 2, §21):

- Activating the §8.3 rigor matrix (TDD-by-risk → Increment 4; Task Review by risk → Increment 5; E2E/security/rollback policies → later increments)
- Enforce mode: no FAIL-level findings, no `define.required_sections` extension, no gate that blocks on profile absence
- Automatic risk recalibration from metrics (§21: never from a single run)
- Changing the existing CRITICAL halt semantics (it stays exactly as-is; this feature only guarantees an override cannot remove it)
- Risk profiles for BRAINSTORM or retrofit of archived DEFINEs (legacy adapter is the WARN default, not a migration)
- Increments 3–9 of the program

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `.claude/` canonical, `plugin/` generated; parity proven post-package (Step 5e, Increment 1) | All edits land canonically; `./build-plugin.sh` must stay green |
| Technical | spec-linter stays deterministic; WARN findings must keep exit 0 (existing `Level.WARN` semantics) | Risk rules are parse-and-compare only; severity ceiling WARN in this increment |
| Compatibility | Observe → Warn → Enforce (plan §17.2); only the pre-existing CRITICAL halt is fail-closed | No new blocking behavior anywhere in this increment |
| Compatibility | Legacy artifacts stay readable (plan §4.6); effective `medium` default, visible | No silent defaults |
| Process | Dogfooding (§16.4): this feature runs under `/auto`; its own DEFINE carries a prospective profile (below) | The autonomous run exercises the paths it ships |

---

## Technical Context

> Essential context for Design phase - prevents misplaced files and missed infrastructure needs.

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `.claude/sdd/templates/{DEFINE,DESIGN,BUILD_REPORT}_TEMPLATE.md`, `.claude/skills/{sdd-define,sdd-design}/SKILL.md`, `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`, `tools/spec-linter/` (define-phase warn rules), `tests/`, `tools/spec-linter/tests/` | Framework/tooling feature — no application code |
| **KB Domains** | `python`, `testing` | Linter rules in Python; pytest patterns for table-driven rule tests |
| **IaC Impact** | None | Local tooling and documents only |

**Why This Matters:**

- **Location** → Design phase uses correct project structure, prevents misplaced files
- **KB Domains** → Design phase pulls correct patterns from `.claude/kb/`
- **IaC Impact** → Triggers infrastructure planning, avoids "works locally" failures

---

## Data Contract (if applicable)

Not applicable — framework feature; no data pipelines, ETL, or analytics surface.

---

## Risk Profile (prospective — dogfood of the model this feature ships)

```yaml
risk_profile:
  level: medium
  reasons:
    - "new logic (linter warn rules) with limited blast radius"
    - "workflow-policy surface touched, but nothing blocking is introduced"
  dimensions:
    data_loss: low
    security: low
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
| A-001 | WARN-level findings on the define phase can coexist with the existing FAIL-only `SddPhaseContract` (via a define-specific contract or a warn-rule extension) without changing exit-code semantics | Needs a small contract-composition refactor in the linter first; Design must scope it | [ ] |
| A-002 | The 5-dimension model + max rule from plan §8.1–8.2 is sufficient for Increments 4–5 to key policies on `level` alone | Increment 4/5 would need profile schema v2 — additive, migration-safe by design | [ ] |
| A-003 | A YAML block inside a fenced code block in the DEFINE Markdown is parseable deterministically by the linter (fence extraction + `yaml.safe_load`) | Profile would need a table representation instead; template change only | [ ] |
| A-004 | The existing CRITICAL halt lives in build-agent/skill text and needs only a documented non-override guarantee, not new enforcement code | If a mechanical link is required, a documental anchor test is the Observe-phase stand-in | [ ] |
| A-005 | Increment 1's parity + documental test infrastructure absorbs this increment's additions without structural change | Test scaffolding rework would inflate scope | [ ] |

**Note:** Validate critical assumptions before DESIGN phase. Unvalidated assumptions become risks.

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Specific and evidenced: uniform rigor, no machine-readable profile (plan §5 gap table + §4.1 principle) |
| Users | 3 | Three personas named with concrete pain points, ratified by the maintainer in the program goal and Increment 1's merged archive |
| Goals | 3 | §8.1 model, §8.2 rules, §17.2 rollout and §18 scope split translate 1:1 into the MoSCoW table |
| Success | 3 | Every criterion carries a number (test counts, exit codes, 0 regressions) |
| Scope | 3 | Explicit deferrals: rigor matrix, Enforce mode, recalibration, halt changes — each mapped to its future increment |
| **Total** | **15/15** | |

**Scoring Guide:**
- 0 = Missing entirely
- 1 = Vague or incomplete
- 2 = Clear but missing details
- 3 = Crystal clear, actionable

**Minimum to proceed: 12/15**

---

## Open Questions

None blocking — ready for Design. One decision is explicitly deferred to Design (chooses *how*, not *whether*): whether the define-phase WARN rules live in a new `DefinePhaseContract` or as an optional warn-layer on `SddPhaseContract` (A-001). Design decides from the current engine structure, mirroring Increment 1's Decision 1.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-29 | define-agent | Initial version — extracted from the incremental-improvements plan §8/§17.2/§18 (PR 2 scope) under the /auto pre-ignition interview |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_RISK_PROFILES.md`
