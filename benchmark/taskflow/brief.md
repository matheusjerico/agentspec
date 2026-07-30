# TaskFlow — common implementation brief

Build a production-quality, locally runnable full-stack task manager using the
complete native workflow supplied by the single plugin loaded in this session.
Proceed from brainstorming through requirements, design, planning,
implementation, testing, review, correction, Git history, and PR readiness.

## Required behavior

A user can create, list, edit, delete, search, and filter tasks, and move a task
between `todo`, `doing`, and `done`.

Each task has:

- a stable unique identifier;
- a title required after trimming, 1–120 characters;
- an optional description of at most 500 characters;
- a status restricted to `todo`, `doing`, or `done`, defaulting to `todo`;
- creation and update timestamps.

Data must survive an application restart. Search must match title and
description case-insensitively. Filtering must return only the requested
status.

The frontend must work at desktop and mobile widths, perform operations without
page reloads, label interactive controls accessibly, distinguish all statuses,
and expose loading, empty, validation, and request-failure states.

## Technical constraints

- Backend: Python, FastAPI, and SQLite.
- Frontend: React and TypeScript.
- API: JSON over HTTP.
- Document supported runtime versions and exact clean install, run, test, lint,
  type-check, and build commands.
- Include backend unit/integration tests, frontend component tests, and one
  browser end-to-end flow.
- Include a CI workflow that runs the documented checks.
- Do not add authentication, multi-user behavior, deployment, or an external
  database.

## Invalid inputs

Reject whitespace-only titles, titles longer than 120 characters, descriptions
longer than 500 characters, and unknown statuses. A missing task must produce a
not-found response.

## Delivery evidence

Keep all native brainstorm, requirements, architecture, plan, build, test, and
review artifacts. Work on a feature branch with coherent commits. Finish with a
clean working tree and a root-level `PR.md` containing the proposed PR title,
summary, test evidence, risks, and known limitations.

Do not create or publish a GitHub repository or pull request. Do not inspect
the other benchmark implementation. Do not copy application code or generated
planning artifacts from outside this repository.

