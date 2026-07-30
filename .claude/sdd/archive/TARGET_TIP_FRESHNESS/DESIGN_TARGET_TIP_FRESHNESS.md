# DESIGN: TARGET_TIP_FRESHNESS

| Attribute | Value |
|---|---|
| **Feature** | TARGET_TIP_FRESHNESS |

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-VALIDATE-001
      description: Validate the production contract for TARGET_TIP_FRESHNESS
      agent: code-reviewer
      risk: high
      files:
        modify: []
        create: []
        delete: []
      depends_on: []
      parallel_group: release-validation
      knowledge:
        required: []
        domain: release
      verification:
        type: test
        command: "uv run --project tools/spec-linter pytest -q tools/spec-linter/tests/test_pr_readiness_git_hardening.py"
        success_criteria: "focused regression suite passes"
      execution:
        commit: "test(release): validate target_tip_freshness"
```

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type |
|---|---|---|---|---|---|
| 1 | REQ-001 | MUST | TASK-VALIDATE-001 | tools/spec-linter/tests/test_pr_readiness_git_hardening.py | test |
