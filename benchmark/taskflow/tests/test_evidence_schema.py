import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parents[1]


def test_evidence_schema_accepts_minimal_complete_record():
    schema = json.loads((ROOT / "evidence.schema.json").read_text())
    record = {
        "framework": "agentspec",
        "versions": {"claude": "2.1.220", "framework": "3.2.0"},
        "run": {
            "order": 1,
            "started_at": "2026-07-28T12:00:00Z",
            "ended_at": "2026-07-28T13:00:00Z",
            "tokens": "unavailable",
        },
        "phases": [],
        "verification": [],
        "repository": {"path": "/work2/agentspec", "commit": "abc123"},
        "pr": {"title": "feat: add TaskFlow", "body_path": "PR.md"},
        "limitations": [],
    }
    Draft202012Validator(schema).validate(record)
