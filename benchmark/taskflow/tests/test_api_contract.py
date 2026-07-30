from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from benchmark.taskflow.acceptance.api_contract import (
    discover_api,
    results_as_json,
    run_api_contract,
)


OPENAPI = {
    "openapi": "3.1.0",
    "paths": {
        "/health": {"get": {"responses": {"200": {"description": "ready"}}}},
        "/api/tasks": {
            "get": {
                "parameters": [
                    {"name": "status", "in": "query"},
                    {"name": "search", "in": "query"},
                ],
                "responses": {"200": {"description": "tasks"}},
            },
            "post": {"responses": {"201": {"description": "created"}}},
        },
        "/api/tasks/{task_id}": {
            "get": {"responses": {"200": {"description": "task"}}},
            "patch": {"responses": {"200": {"description": "updated"}}},
            "delete": {"responses": {"204": {"description": "deleted"}}},
        },
    },
}


class FakeTaskFlow:
    def __init__(self) -> None:
        self.tasks: dict[str, dict] = {}
        self.restart_count = 0

    def restart(self) -> None:
        self.restart_count += 1

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/openapi.json":
            return httpx.Response(200, json=OPENAPI)
        if path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if path == "/api/tasks" and request.method == "POST":
            payload = __import__("json").loads(request.content)
            title = payload.get("title", "")
            description = payload.get("description")
            status = payload.get("status", "todo")
            if (
                not isinstance(title, str)
                or not title.strip()
                or len(title) > 120
                or (description is not None and len(description) > 500)
                or status not in {"todo", "doing", "done"}
            ):
                return httpx.Response(422, json={"detail": "invalid"})
            now = datetime.now(UTC).isoformat()
            task_id = uuid4().hex
            task = {
                "id": task_id,
                "title": title.strip(),
                "description": description,
                "status": status,
                "created_at": now,
                "updated_at": now,
            }
            self.tasks[task_id] = task
            return httpx.Response(201, json=task)
        if path == "/api/tasks" and request.method == "GET":
            tasks = list(self.tasks.values())
            status = request.url.params.get("status")
            search = request.url.params.get("search")
            if status:
                tasks = [task for task in tasks if task["status"] == status]
            if search:
                needle = search.casefold()
                tasks = [
                    task
                    for task in tasks
                    if needle in task["title"].casefold()
                    or needle in (task["description"] or "").casefold()
                ]
            return httpx.Response(200, json=tasks)
        if path.startswith("/api/tasks/"):
            task_id = path.rsplit("/", 1)[-1]
            task = self.tasks.get(task_id)
            if task is None:
                return httpx.Response(404, json={"detail": "not found"})
            if request.method == "GET":
                return httpx.Response(200, json=task)
            if request.method == "PATCH":
                payload = __import__("json").loads(request.content)
                task.update(payload)
                task["updated_at"] = datetime.now(UTC).isoformat()
                return httpx.Response(200, json=task)
            if request.method == "DELETE":
                del self.tasks[task_id]
                return httpx.Response(204)
        return httpx.Response(405)


def test_contract_passes_against_complete_black_box_api():
    fake = FakeTaskFlow()

    results = run_api_contract(
        "http://taskflow.test",
        fake.restart,
        transport=httpx.MockTransport(fake),
    )

    assert len(results) == 15
    assert all(result.passed for result in results), results
    assert fake.restart_count == 1


def test_contract_reports_ambiguous_discovery_without_exercising_api():
    ambiguous = deepcopy(OPENAPI)
    ambiguous["paths"]["/other/tasks"] = deepcopy(OPENAPI["paths"]["/api/tasks"])
    ambiguous["paths"]["/other/tasks/{task_id}"] = deepcopy(
        OPENAPI["paths"]["/api/tasks/{task_id}"]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/openapi.json":
            return httpx.Response(200, json=ambiguous)
        raise AssertionError("evaluator must stop after ambiguous discovery")

    results = run_api_contract(
        "http://taskflow.test",
        lambda: None,
        transport=httpx.MockTransport(handler),
    )

    assert results[0].name == "api-discovery"
    assert results[0].passed is False
    assert "found 2" in results[0].detail


def test_discovery_rejects_collection_without_filter_and_search_parameters():
    incomplete = deepcopy(OPENAPI)
    incomplete["paths"]["/api/tasks"]["get"]["parameters"] = []

    try:
        discover_api(incomplete)
    except ValueError as exc:
        assert "found 0" in str(exc)
    else:
        raise AssertionError("incomplete API shape should not be accepted")


def test_results_json_is_serializable_and_timestamped():
    fake = FakeTaskFlow()
    results = run_api_contract(
        "http://taskflow.test",
        fake.restart,
        transport=httpx.MockTransport(fake),
    )

    output = results_as_json(results[:1])

    assert output[0]["name"] == "api-discovery"
    assert output[0]["passed"] is True
    assert datetime.fromisoformat(output[0]["recorded_at"]).tzinfo is not None
