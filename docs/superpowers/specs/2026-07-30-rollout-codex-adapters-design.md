# Codex Adapters in the Vendored Rollout

**Status:** Approved design
**Date:** 2026-07-30

## Goal

Extend `scripts/rollout-agentspec.sh` so vendored installs receive a working
`.agents/skills/` adapter tree, making AgentSpec discoverable by Codex in the
consuming repositories — not just in this one.

Today the rollout syncs `.claude/` only. The Codex layer designed in
`2026-07-29-codex-adapters-design.md` stops at this repository's boundary, so
vendored installs either lack `.agents/` entirely or carry hand-made symlink
trees that drift.

## Why generation, not copying

This repository's committed `.agents/skills/` cannot be copied to a target.
It contains adapters for repo-local skills that `build-plugin.sh` deliberately
excludes from the payload. Copying them would produce adapters whose canonical
`.claude/` path does not exist in the target — broken on arrival.

Symlinking `.agents/skills` to `.claude/skills` is equally wrong: it bypasses
the adapter layer whose entire purpose is translating Claude-specific tool
names at the Codex boundary, and it cannot expose commands, which do not live
under `.claude/skills/`.

Adapters are therefore generated against the target's own post-sync `.claude/`
tree. This covers payload components and target-local skills alike, and every
adapter points at a canonical file that provably exists in that target.

## Source scope

Two collections feed generation, and the second is narrower than in the
repo-local generator:

1. `<target>/.claude/skills/*/SKILL.md` — every skill the target has, payload
   or target-owned.
2. `<target>/.claude/commands/<set>/**/*.md` for each AgentSpec command set
   only, excluding `README.md`.

Restricting commands to AgentSpec-owned sets is load-bearing. Target-local
command directories are authored for Claude's slash-command surface, where the
`name` field is a human-readable title rather than a skill slug. Feeding those
to a generator that requires slug names aborts generation for the whole target.
Excluding them also avoids labelling third-party commands with the
`agentspec-` prefix, which would misattribute them.

Loose command files directly under `.claude/commands/` are target-owned and
out of scope for the same reason.

## Codex-native skills

A target may host genuine Codex skills under `.agents/skills/` and expose them
to Claude by symlinking `.claude/skills/<name>` into that directory. Those
skills are Codex-native already.

A skill whose resolved path lies inside `.agents/` is skipped as a source. The
generator must never emit an adapter that would overwrite the skill it was
derived from, which would both destroy content and orphan the inbound symlink.

## Ownership contract

`.agents/skills/` in a target follows the contract already used for
`.claude/skills/`: generated adapters are replaced by scoped delete-then-write,
and every entry the generator did not produce is preserved and reported.

`.agents/skills/` is not wholly AgentSpec-owned in a target, even though it is
wholly generator-owned in this repository. Codex-native skills live there.

When `.agents/skills` is an existing symlink rather than a directory, it is
replaced by a real directory. A whole-directory symlink cannot host adapters
alongside preserved entries, and it exposes no commands.

A target without `.agents/` receives one. The directory is derived from that
target's `.claude/`, so its absence is a gap to fill rather than a signal that
the target opted out. A target without `.claude/` is skipped exactly as today,
and no `.agents/` is created for it.

## Failure semantics

Generation validates every adapter in memory before writing anything, so a
malformed source cannot leave a partial tree.

When validation fails for a target — missing `name` or `description`, an
invalid skill name, a duplicate output name — that target's `.agents/` is left
untouched, its `.claude/` sync stands, and the run reports the offending source
and the violated invariant. Remaining targets still process. The run exits 1,
matching the existing partial-failure code.

A malformed target-local component must not block that target's AgentSpec
upgrade, and it must not pass silently.

## Backups and rollback

`backup_target` copies `.agents` alongside `.claude` into the stamp directory.
`rollback_target` restores both, restoring whichever paths the stamp contains
so that stamps predating this change remain usable.

## Generator changes

`scripts/generate-codex-adapters.py` gains:

- `--root PATH` to generate against an arbitrary repository root, defaulting to
  the current repo-local behaviour;
- a command-set restriction applied when generating for a target;
- source skipping for skills resolving inside `.agents/`;
- preservation of unrecognised entries under the output root, replacing the
  current unconditional tree replacement when operating on a target.

Repo-local behaviour, including `--check` in the quality gates, is unchanged.

## Reporting

The dry-run plan gains a per-target line stating how many adapters would be
generated, which entries would be preserved, and any validation error that
would mark the target partial. The plan must let a reader predict the applied
result without running it.

## Validation

Automated tests must verify:

- adapters are generated for payload and target-local skills, and for AgentSpec
  command sets only;
- target-local command directories and loose command files produce no adapters;
- a skill resolving inside `.agents/` produces no adapter and survives the run;
- unrecognised entries under `.agents/skills/` survive the run;
- an existing `.agents/skills` symlink is replaced by a real directory;
- a malformed source leaves the target's `.agents/` byte-identical and reports
  the source path and invariant;
- backup captures `.agents`, and rollback restores it;
- rollback from a stamp containing only `.claude` still succeeds;
- every generated adapter points at a file that exists in that target.

## Non-Goals

- Packaging `.agents/` into the Claude plugin.
- Making `.agents/` editable in a target.
- Generating adapters for target-local command directories.
- Modifying user-global Codex state.

## Acceptance Criteria

1. After a rollout, each target contains an adapter for every payload skill,
   every target-local skill, and every AgentSpec command.
2. Every adapter in a target points at a canonical `.claude/` file present in
   that target.
3. Codex-native skills under `.agents/skills/` and their inbound symlinks
   survive a rollout unchanged.
4. A malformed target-local component marks only that target partial and leaves
   its `.agents/` unchanged.
5. A rollout can be rolled back to its pre-run `.claude/` and `.agents/` state
   from a single stamp.
