# DESIGN: SEMANTIC_RELEASE_EVIDENCE_GATE

| Attribute | Value |
|---|---|
| **Feature** | SEMANTIC_RELEASE_EVIDENCE_GATE |

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-VALIDATE-001
      description: Validate the production contract for SEMANTIC_RELEASE_EVIDENCE_GATE
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
        command: "uv run --project tools/spec-linter pytest -q tests/test_release_gate.py"
        success_criteria: "focused regression suite passes"
      execution:
        commit: "test(release): validate semantic_release_evidence_gate"
```

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type |
|---|---|---|---|---|---|
| 1 | REQ-001 | MUST | TASK-VALIDATE-001 | tests/test_release_gate.py | test |
