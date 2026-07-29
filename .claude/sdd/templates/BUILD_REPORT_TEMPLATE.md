# BUILD REPORT: {Feature Name}

> Implementation report for {Feature Name}

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | {FEATURE_NAME} |
| **Date** | {YYYY-MM-DD} |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_{FEATURE}.md](../features/DEFINE_{FEATURE}.md) |
| **DESIGN** | [DESIGN_{FEATURE}.md](../features/DESIGN_{FEATURE}.md) |
| **Status** | In Progress / Complete / Blocked |
| **Schema Version** | 2 |
| **TDD Mode** | {off / opt-in / required} |
| **Risk Level** | {level echoed from the DEFINE Risk Profile / n/a (legacy DEFINE)} |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | {X}/{Y} |
| **Files Created** | {N} |
| **Lines of Code** | {N} |
| **Build Time** | {Duration} |
| **Tests Passing** | {X}/{Y} |
| **Agents Used** | {N} |

---

## Task Execution with Agent Attribution

| # | Task ID | Task | Agent | Status | Duration | Notes |
|---|---------|------|-------|--------|----------|-------|
| 1 | {TASK-AREA-001 / - (v1)} | {Task description} | @{agent-name} | ✅ Complete | {Xm} | {Any notes} |
| 2 | {TASK-AREA-002 / -} | {Task description} | @{agent-name} | ✅ Complete | {Xm} | {Any notes} |
| 3 | {TASK-AREA-003 / -} | {Task description} | (direct) | 🔄 In Progress | - | {No specialist matched} |
| 4 | {TASK-AREA-004 / -} | {Task description} | @{agent-name} | ⏳ Pending | - | - |

**Manifest:** {v2 — tasks consumed from the DESIGN Task Manifest / v1 — tasks inferred from the file manifest (manifest_version: 1)}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Pending | ❌ Blocked

**Agent Key:**
- `@{agent-name}` = Delegated to specialist agent via Task tool
- `(direct)` = Built directly by build-agent (no specialist matched)

---

## Traceability Matrix

> Filled at Build: the Design matrix with Result and Review completed — Result from
> the verification runs, Review from the task verdicts. MUST rows with empty
> Tests or a non-pass Result FAIL the contract gate unless Tests records
> `exception: <reason — citation>`. A missing matrix WARNs at high/critical.

| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |
|---|-----|----------|-------|-------|-------------------|--------|--------|
| 1 | REQ-001 | MUST | TASK-{AREA}-001 | {tests} | {type} | {Pass / Fail} | {clean / clean-with-minors / dirty / skipped-by-policy} |

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| @{agent-1} | {N} | {What patterns/KB used} |
| @{agent-2} | {N} | {What patterns/KB used} |
| (direct) | {N} | DESIGN patterns only |

---

## Task Reviews

> One row per task (v2 manifests; `WORKFLOW_CONTRACTS.yaml` → `task_review`).
> Blind-first per-task review after verification; `dirty` blocks dependents
> and FAILs the contract gate; missing rows FAIL at high/critical report risk
> (WARN at medium). `skipped-by-policy` records the policy citation.

| # | Task ID | Risk | Reviewer | Verdict | Blocking open / Minor | Fix rounds |
|---|---------|------|----------|---------|----------------------|------------|
| 1 | {TASK-AREA-001} | {low/medium/high/critical} | {@reviewer / (self)} | {clean / clean-with-minors / dirty / skipped-by-policy} | {0 / 1} | {0-1}/1 |

---

## Files Created

| File | Lines | Agent | Verified | Notes |
| ---- | ----- | ----- | -------- | ----- |
| `{path/to/file1.py}` | {N} | @{agent-name} | ✅ | {Any notes} |
| `{path/to/file2.py}` | {N} | @{agent-name} | ✅ | {Any notes} |
| `{path/to/config.yaml}` | {N} | (direct) | ✅ | {Any notes} |

---

## Verification Results

### Lint Check

```text
{Output from linter (e.g., ruff, eslint, rubocop) or "All checks passed"}
```

**Status:** ✅ Pass / ❌ Fail

### Type Check

```text
{Output from type checker (e.g., mypy, tsc) or "All checks passed" or "N/A - not configured"}
```

**Status:** ✅ Pass / ❌ Fail / ⏭️ Skipped

### Tests

```text
{Output from test runner (e.g., pytest, jest, go test) or summary}
```

| Test | Result |
|------|--------|
| `test_function_1` | ✅ Pass |
| `test_function_2` | ✅ Pass |
| `test_integration` | ✅ Pass |

**Status:** ✅ {X}/{Y} Pass | ❌ {N} Fail

---

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
| 1 | {Critical / Important / Minor} | {finding} | {file:line} | {fixed in {sha} / recorded (minor) / OPEN} |

---

## TDD Evidence (required when TDD Mode != off)

> One row per code-bearing manifest task. Required whenever the Metadata
> `TDD Mode` is `opt-in` or `required` — the contract gate
> (`spec-lint --phase build`, sdd-build Step 6.5) enforces it. Omit this
> section only when `TDD Mode` is `off`.
> Non-code / untestable tasks use the sanctioned grammar
> `n/a — exception: <category>; verified by: <command>` — categories from
> `WORKFLOW_CONTRACTS.yaml` → `tdd_policy.exception_categories`; unknown
> categories FAIL (`BR.tdd_exception_invalid`). In the GREEN column,
> distinguish new tests, regression runs, and alternative verification.

| Task | Test file | RED observed (failure excerpt) | GREEN run | Commit |
|------|-----------|-------------------------------|-----------|--------|
| {task} | {tests/...} | {expected failure line} | {X passed} | {sha} |

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | {Description of issue} | {How it was resolved} | {+Xm} |
| 2 | {Description of issue} | {How it was resolved} | {+Xm} |

---

## Autonomous Decisions

The build phase runs autonomously — it never pauses to ask the user. Every
decision fork reached during the build was resolved by choosing the safest
documented default. This section is the post-run review log: each row is a
fork the build resolved on its own. An empty table means the build hit zero
ambiguity (DESIGN fully pre-decided everything).

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | {What was ambiguous} | {Option A vs Option B} | {Chosen option} | {Why it is the safest / smallest-correct-change default} |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| {What changed from DESIGN} | {Why it changed} | {Effect on system} |

---

## Blockers (if any)

| Blocker | Required Action | Owner |
|---------|-----------------|-------|
| {Description} | {What needs to happen} | {Who can unblock} |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | {From DEFINE} | ✅ Pass / ❌ Fail | {How verified} |
| AT-002 | {From DEFINE} | ✅ Pass / ❌ Fail | {How verified} |
| AT-003 | {From DEFINE} | ✅ Pass / ❌ Fail | {How verified} |

---

## Performance Notes

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| {Metric 1} | {From DEFINE} | {Measured} | ✅ / ❌ |
| {Metric 2} | {From DEFINE} | {Measured} | ✅ / ❌ |

---

## Data Quality Results (if applicable)

> Include this section when the build involves data pipelines, dbt models, or data infrastructure.

### dbt Build Results

```text
{Output from `dbt build --select {models}` or "N/A"}
```

**Status:** ✅ Pass / ❌ Fail

### SQL Lint Results

```text
{Output from `sqlfluff lint` or "N/A"}
```

**Status:** ✅ Pass ({N} files clean) / ❌ {N} violations

### Data Quality Checks

| Check | Tool | Result | Details |
|-------|------|--------|---------|
| {Null PK check} | {dbt test / GE} | ✅ / ❌ | {0 nulls found} |
| {Unique PK check} | {dbt test / GE} | ✅ / ❌ | {0 duplicates} |
| {Referential integrity} | {dbt test / GE} | ✅ / ❌ | {0 orphans} |
| {Row count sanity} | {dbt test / GE} | ✅ / ❌ | {N rows, within range} |
| {Freshness} | {dbt source freshness} | ✅ / ❌ | {Last update: HH:MM} |

### Pipeline Metrics

| Metric | Value |
|--------|-------|
| Models built | {N} |
| Tests passed | {X}/{Y} |
| SQL lint violations | {N} |
| Avg model build time | {X}s |
| Data freshness | {Within SLA / Exceeded} |

---

## Final Status

### Overall: {✅ COMPLETE / 🔄 IN PROGRESS / ❌ BLOCKED}

**Completion Checklist:**

- [ ] All tasks from manifest completed
- [ ] All verification checks pass
- [ ] All tests pass
- [ ] No blocking issues
- [ ] Review Verdict is clean or clean-with-minors
- [ ] Contract gate passed: `spec-lint --phase build` exit 0 (sdd-build Step 6.5)
- [ ] Acceptance tests verified
- [ ] Ready for /ship

---

## Next Step

**If Complete:** `/ship .claude/sdd/features/DEFINE_{FEATURE_NAME}.md`

**If Blocked:** Resolve blockers, then `/build` to resume

**If Issues Found:** `/iterate DESIGN_{FEATURE}.md "{change needed}"`
