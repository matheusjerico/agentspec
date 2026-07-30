# Codex Adapters for AgentSpec

**Status:** Approved design  
**Date:** 2026-07-29

## Goal

Make AgentSpec skills and workflows discoverable and executable by Codex while
keeping `.claude/` as the only editable source of truth.

The integration is repository-local. It must not install or modify skills under
the user's global Codex directories.

## Architecture

Add a generated compatibility layer under `.agents/skills/`.

Each generated Codex skill is a small adapter containing Codex-compatible
frontmatter and an instruction to read and follow one canonical file under
`.claude/`. The adapter must not copy the canonical workflow or methodology
body.

Two source collections feed the generator:

1. `.claude/skills/*/SKILL.md`
2. `.claude/commands/**/*.md`, excluding catalog files such as `README.md`

The generated output is committed so a fresh clone is immediately discoverable
by Codex without running a setup command. A deterministic check prevents the
committed output from drifting from `.claude/`.

## Naming

Canonical Claude skills retain their declared names when exposed to Codex.

Claude commands are exposed as Codex skills with the `agentspec-` prefix. For
example:

| Canonical command | Codex skill |
|---|---|
| `.claude/commands/workflow/brainstorm.md` | `agentspec-brainstorm` |
| `.claude/commands/workflow/define.md` | `agentspec-define` |
| `.claude/commands/data-engineering/schema.md` | `agentspec-schema` |

Command names must be globally unique after prefixing. A collision is a
generation error rather than an implicit overwrite.

## Adapter Contract

Every generated adapter:

- lives at `.agents/skills/<name>/SKILL.md`;
- has only `name` and `description` in YAML frontmatter;
- states that it is generated and must not be edited;
- identifies the exact canonical `.claude/` source path;
- requires Codex to read the canonical file completely before acting;
- treats the canonical file as authoritative if adapter metadata conflicts;
- translates Claude-specific invocation syntax only at the boundary;
- uses Codex-native tools when a canonical instruction names an equivalent
  Claude tool;
- reports a genuine unavailable capability instead of silently skipping a
  required step.

The adapter does not rewrite paths such as `.claude/sdd/`, because those paths
are workspace artifacts shared by both clients.

## Generator

Add `scripts/generate-codex-adapters.py` with two modes:

- default: regenerate `.agents/skills/` deterministically;
- `--check`: build the expected representation in memory and fail with a useful
  diff or file list when the committed adapters are missing, stale, or extra.

Generation must be fail-closed for:

- invalid or missing YAML frontmatter;
- missing `name` or `description`;
- invalid Codex skill names;
- duplicate output names;
- source paths outside the two approved `.claude/` collections;
- an empty source inventory.

The generator owns the complete `.agents/skills/` directory. Files elsewhere
under `.agents/`, if introduced later, are outside its ownership.

## Discovery and Execution Flow

1. Codex opens the repository.
2. Codex discovers the committed adapters in `.agents/skills/`.
3. A user request triggers a named or semantically matching adapter.
4. The adapter directs Codex to read the corresponding canonical `.claude/`
   file completely.
5. Codex follows the canonical workflow using available native tools and writes
   normal AgentSpec artifacts under `.claude/sdd/`.

No runtime synchronization or global installation is required.

## Validation

Automated tests must verify:

- every canonical skill has exactly one adapter;
- every non-catalog command has exactly one prefixed adapter;
- no adapter points outside `.claude/`;
- every adapter points to an existing file;
- generated frontmatter contains only `name` and `description`;
- generation is deterministic;
- `--check` succeeds on the committed tree and fails after representative
  source or output drift;
- stale and unexpected generated adapters are removed in write mode.

Run the existing test suite after the focused generator tests to catch packaging
or parity regressions.

## Documentation and Build Integration

Document the Codex entrypoints in the main README without implying that Claude
slash commands work unchanged in Codex.

Wire `scripts/generate-codex-adapters.py --check` into the repository's existing
quality checks. The Claude plugin build remains sourced from `.claude/` and does
not package `.agents/`.

## Error Handling

Generation errors identify the source file and violated invariant. Write mode
must construct and validate the expected output before replacing generated
files, so a malformed source cannot leave a partially updated adapter tree.

Codex execution adapters cannot promise parity for a required Claude-only
capability. When no native equivalent exists, Codex must name the unavailable
capability and stop at that boundary.

## Non-Goals

- Installing AgentSpec globally in Codex.
- Moving or renaming canonical `.claude/` content.
- Making `.agents/` an independently editable source.
- Converting Claude agents into Codex subagents.
- Changing the Claude plugin package or its marketplace behavior.

## Acceptance Criteria

1. A fresh clone contains a discoverable repo-local Codex skill for every
   canonical AgentSpec skill and command.
2. Editing only a generated adapter is detected as drift.
3. Editing a canonical name or description requires regeneration and is
   detected by `--check`.
4. Invoking an adapter causes Codex to load its canonical `.claude/` file.
5. No user-global Codex state is modified.
