"""Implementation-independent TaskFlow API acceptance contract.

The evaluator intentionally communicates only over HTTP.  It discovers the
task API from OpenAPI instead of importing application code or assuming a
framework-specific module layout.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx


@dataclass(frozen=True)
class CheckResult:
    """One independently reportable black-box assertion."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ApiShape:
    collection_path: str
    item_path: str
    update_method: str
    status_parameter: str
    search_parameter: str


def _result(name: str, assertion: bool, detail: str) -> CheckResult:
    return CheckResult(name=name, passed=assertion, detail=detail)


def _parameters(operation: Mapping[str, Any]) -> set[str]:
    return {
        str(parameter.get("name"))
        for parameter in operation.get("parameters", [])
        if parameter.get("in") == "query" and parameter.get("name")
    }


def discover_api(openapi: Mapping[str, Any]) -> ApiShape:
    """Find one unambiguous CRUD task resource in an OpenAPI document."""

    paths = openapi.get("paths")
    if not isinstance(paths, Mapping):
        raise ValueError("OpenAPI document has no paths object")

    candidates: list[ApiShape] = []
    for collection_path, operations in paths.items():
        if "{" in collection_path or not isinstance(operations, Mapping):
            continue
        if not {"get", "post"}.issubset(operations):
            continue

        collection_params = _parameters(operations["get"])
        status_params = collection_params.intersection({"status", "state"})
        search_params = collection_params.intersection(
            {"search", "q", "query", "text"}
        )
        if len(status_params) != 1 or len(search_params) != 1:
            continue

        prefix = collection_path.rstrip("/") + "/"
        for item_path, item_operations in paths.items():
            if (
                not item_path.startswith(prefix)
                or "{" not in item_path
                or not isinstance(item_operations, Mapping)
                or "delete" not in item_operations
            ):
                continue
            update_methods = {"patch", "put"}.intersection(item_operations)
            if len(update_methods) != 1:
                continue
            candidates.append(
                ApiShape(
                    collection_path=collection_path,
                    item_path=item_path,
                    update_method=next(iter(update_methods)),
                    status_parameter=next(iter(status_params)),
                    search_parameter=next(iter(search_params)),
                )
            )

    if len(candidates) != 1:
        raise ValueError(
            f"expected one discoverable task CRUD resource, found {len(candidates)}"
        )
    return candidates[0]


def _item_url(shape: ApiShape, task_id: Any) -> str:
    start = shape.item_path.index("{")
    end = shape.item_path.index("}", start)
    return f"{shape.item_path[:start]}{task_id}{shape.item_path[end + 1:]}"


def _request_ok(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json: Mapping[str, Any] | None = None,
    params: Mapping[str, Any] | None = None,
) -> httpx.Response:
    response = client.request(method, path, json=json, params=params)
    response.raise_for_status()
    return response


def run_api_contract(
    base_url: str,
    restart: Callable[[], None],
    *,
    transport: httpx.BaseTransport | None = None,
    timeout: float = 10.0,
) -> list[CheckResult]:
    """Execute TaskFlow criteria 1–9 and return non-throwing check results.

    ``restart`` must restart the backend while retaining its configured SQLite
    database.  A transport override exists solely for deterministic evaluator
    self-tests; benchmark runs use a real HTTP connection.
    """

    results: list[CheckResult] = []
    with httpx.Client(
        base_url=base_url.rstrip("/"),
        transport=transport,
        timeout=timeout,
    ) as client:
        try:
            openapi_response = _request_ok(client, "GET", "/openapi.json")
            openapi = openapi_response.json()
            shape = discover_api(openapi)
        except Exception as exc:
            return [_result("api-discovery", False, str(exc))]

        results.append(
            _result(
                "api-discovery",
                True,
                f"collection={shape.collection_path}, item={shape.item_path}",
            )
        )

        paths = openapi.get("paths", {})
        health_paths = [
            path
            for path, operations in paths.items()
            if "health" in path.casefold()
            and isinstance(operations, Mapping)
            and "get" in operations
        ]
        try:
            if health_paths:
                response = _request_ok(client, "GET", health_paths[0])
                detail = f"{health_paths[0]} returned {response.status_code}"
            else:
                detail = "OpenAPI readiness endpoint returned successfully"
            results.append(_result("readiness", True, detail))
        except Exception as exc:
            results.append(_result("readiness", False, str(exc)))

        marker = uuid4().hex
        title = f"TaskFlow contract {marker}"
        description = f"Persistence marker {marker}"
        task: dict[str, Any] | None = None
        try:
            response = _request_ok(
                client,
                "POST",
                shape.collection_path,
                json={
                    "title": title,
                    "description": description,
                    "status": "todo",
                },
            )
            task = response.json()
            required = {
                "id",
                "title",
                "description",
                "status",
                "created_at",
                "updated_at",
            }
            valid = (
                isinstance(task, dict)
                and required.issubset(task)
                and task["title"] == title
                and task["description"] == description
                and task["status"] == "todo"
            )
            results.append(
                _result(
                    "create-valid-task",
                    valid,
                    "created task contains all required fields"
                    if valid
                    else f"invalid response fields: {task!r}",
                )
            )
        except Exception as exc:
            results.append(_result("create-valid-task", False, str(exc)))

        invalid_payloads = {
            "reject-whitespace-title": {"title": "   "},
            "reject-long-title": {"title": "x" * 121},
            "reject-long-description": {
                "title": "valid",
                "description": "x" * 501,
            },
            "reject-unknown-status": {"title": "valid", "status": "blocked"},
        }
        for name, payload in invalid_payloads.items():
            try:
                response = client.post(shape.collection_path, json=payload)
                results.append(
                    _result(
                        name,
                        response.status_code in {400, 422},
                        f"returned HTTP {response.status_code}",
                    )
                )
            except Exception as exc:
                results.append(_result(name, False, str(exc)))

        if task is None or "id" not in task:
            results.extend(
                _result(name, False, "valid task was not created")
                for name in (
                    "list-task",
                    "persistence-after-restart",
                    "update-task",
                    "missing-task-not-found",
                    "filter-by-status",
                    "case-insensitive-search-title",
                    "case-insensitive-search-description",
                    "delete-task",
                )
            )
            return results

        task_id = task["id"]
        item_path = _item_url(shape, task_id)
        try:
            listed = _request_ok(client, "GET", shape.collection_path).json()
            passed = isinstance(listed, list) and any(
                row.get("id") == task_id for row in listed if isinstance(row, dict)
            )
            results.append(_result("list-task", passed, "created task is listed"))
        except Exception as exc:
            results.append(_result("list-task", False, str(exc)))

        try:
            restart()
            listed = _request_ok(client, "GET", shape.collection_path).json()
            passed = isinstance(listed, list) and any(
                row.get("id") == task_id for row in listed if isinstance(row, dict)
            )
            results.append(
                _result(
                    "persistence-after-restart",
                    passed,
                    "task remained in SQLite-backed collection after restart",
                )
            )
        except Exception as exc:
            results.append(_result("persistence-after-restart", False, str(exc)))

        updated_title = f"Updated {marker}"
        updated_description = f"Changed description {marker}"
        update_payload = {
            "title": updated_title,
            "description": updated_description,
            "status": "doing",
        }
        try:
            updated = _request_ok(
                client,
                shape.update_method.upper(),
                item_path,
                json=update_payload,
            ).json()
            passed = all(updated.get(key) == value for key, value in update_payload.items())
            results.append(
                _result(
                    "update-task",
                    passed,
                    "title, description, and status were updated",
                )
            )
        except Exception as exc:
            results.append(_result("update-task", False, str(exc)))

        try:
            missing = client.request(
                shape.update_method.upper(),
                _item_url(shape, f"missing-{marker}"),
                json=update_payload,
            )
            results.append(
                _result(
                    "missing-task-not-found",
                    missing.status_code == 404,
                    f"returned HTTP {missing.status_code}",
                )
            )
        except Exception as exc:
            results.append(_result("missing-task-not-found", False, str(exc)))

        try:
            filtered = _request_ok(
                client,
                "GET",
                shape.collection_path,
                params={shape.status_parameter: "doing"},
            ).json()
            passed = (
                isinstance(filtered, list)
                and any(row.get("id") == task_id for row in filtered)
                and all(row.get("status") == "doing" for row in filtered)
            )
            results.append(
                _result("filter-by-status", passed, "all filtered tasks are doing")
            )
        except Exception as exc:
            results.append(_result("filter-by-status", False, str(exc)))

        for name, query in (
            ("case-insensitive-search-title", updated_title.swapcase()),
            ("case-insensitive-search-description", updated_description.swapcase()),
        ):
            try:
                matches = _request_ok(
                    client,
                    "GET",
                    shape.collection_path,
                    params={shape.search_parameter: query},
                ).json()
                passed = isinstance(matches, list) and any(
                    row.get("id") == task_id for row in matches
                )
                results.append(_result(name, passed, "case-insensitive match found"))
            except Exception as exc:
                results.append(_result(name, False, str(exc)))

        try:
            response = client.delete(item_path)
            response.raise_for_status()
            remaining = _request_ok(client, "GET", shape.collection_path).json()
            passed = isinstance(remaining, list) and all(
                row.get("id") != task_id for row in remaining
            )
            results.append(
                _result("delete-task", passed, "deleted task is absent from collection")
            )
        except Exception as exc:
            results.append(_result("delete-task", False, str(exc)))

    return results


def results_as_json(results: list[CheckResult]) -> list[dict[str, Any]]:
    """Return a stable JSON-serializable representation for evidence files."""

    recorded_at = datetime.now(UTC).isoformat()
    return [
        {
            "name": result.name,
            "passed": result.passed,
            "detail": result.detail,
            "recorded_at": recorded_at,
        }
        for result in results
    ]
