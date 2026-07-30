#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# AgentSpec Plugin Builder
# =============================================================================
# Packages .claude/ (source of truth) into plugin/ (distributable plugin).
# Rewrites internal paths from .claude/ to ${CLAUDE_PLUGIN_ROOT}/ while
# preserving workspace paths (.claude/sdd/features, reports, archive, storage).
#
# Usage:
#   ./build-plugin.sh --dev     # Build from a development worktree
#   ./build-plugin.sh --release # Build from a clean release commit
#   ./build-plugin.sh --help    # Show this help
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="${SCRIPT_DIR}/.claude"
FINAL_PLUGIN_DIR="${SCRIPT_DIR}/plugin"
EXTRAS_DIR="${SCRIPT_DIR}/plugin-extras"
BUILD_MODE="dev"
BUILD_ROOT=""
PLUGIN_DIR=""
STAGED_PLUGIN_DIR=""
BACKUP_DIR=""
BUILD_COMMIT=""
BUILD_TREE_STATE="clean"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { printf "${BLUE}[INFO]${NC} %s\n" "$1"; }
ok()    { printf "${GREEN}[OK]${NC} %s\n" "$1"; }
warn()  { printf "${YELLOW}[WARN]${NC} %s\n" "$1"; }
error() { printf "${RED}[ERROR]${NC} %s\n" "$1" >&2; }

# Cleanup trap for interrupted builds
cleanup() {
    if [[ -n "${BACKUP_DIR}" && -d "${BACKUP_DIR}" && ! -d "${FINAL_PLUGIN_DIR}" ]]; then
        mv "${BACKUP_DIR}" "${FINAL_PLUGIN_DIR}" 2>/dev/null || true
    fi
    [[ -n "${BUILD_ROOT}" && -d "${BUILD_ROOT}" ]] && rm -rf "${BUILD_ROOT}"
    [[ -n "${BACKUP_DIR}" && -d "${BACKUP_DIR}" ]] && rm -rf "${BACKUP_DIR}"
    return 0
}
trap cleanup EXIT

# ─── Help ────────────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    cat <<'EOF'
AgentSpec Plugin Builder

Packages .claude/ (source of truth) into plugin/ (distributable plugin).
Rewrites internal paths to ${CLAUDE_PLUGIN_ROOT}/ and merges plugin-extras/.

Usage:
  ./build-plugin.sh --dev     Build from the current development worktree
  ./build-plugin.sh --release Build from a clean Git worktree
  ./build-plugin.sh --help    Show this help

The default is --dev for backwards compatibility. Both modes record the exact
Git commit and a deterministic file hash manifest. Release mode additionally
requires a clean Git worktree.

Output: plugin/ directory ready for `claude --plugin-dir ./plugin`
EOF
    exit 0
fi

case "${1:---dev}" in
    --dev) BUILD_MODE="dev" ;;
    --release) BUILD_MODE="release" ;;
    *)
        error "unknown option: ${1}"
        exit 2
        ;;
esac

# ─── Preflight ───────────────────────────────────────────────────────────────

if [[ ! -d "${SOURCE_DIR}" ]]; then
    error ".claude/ directory not found at ${SOURCE_DIR}"
    exit 1
fi

if [[ ! -f "${FINAL_PLUGIN_DIR}/.claude-plugin/plugin.json" ]]; then
    error "plugin/.claude-plugin/plugin.json not found. Create the manifest first."
    exit 1
fi

if ! BUILD_COMMIT="$(git -C "${SCRIPT_DIR}" rev-parse --verify HEAD 2>/dev/null)"; then
    error "plugin builds require a Git commit (could not resolve HEAD)"
    exit 1
fi

if [[ "${BUILD_MODE}" == "release" ]] && [[ -n "$(git -C "${SCRIPT_DIR}" status --porcelain --untracked-files=all)" ]]; then
    error "release builds require a clean Git worktree"
    exit 1
fi
if [[ -n "$(git -C "${SCRIPT_DIR}" status --porcelain --untracked-files=all)" ]]; then
    BUILD_TREE_STATE="dirty"
fi

# Keep staging on the same filesystem as plugin/ so the final rename is atomic.
BUILD_ROOT="$(mktemp -d "${SCRIPT_DIR}/.plugin-build.XXXXXX")"
STAGED_PLUGIN_DIR="${BUILD_ROOT}/plugin"
PLUGIN_DIR="${STAGED_PLUGIN_DIR}"
mkdir -p "${PLUGIN_DIR}"
cp -R "${FINAL_PLUGIN_DIR}/.claude-plugin" "${PLUGIN_DIR}/.claude-plugin"
[[ -f "${FINAL_PLUGIN_DIR}/README.md" ]] && cp "${FINAL_PLUGIN_DIR}/README.md" "${PLUGIN_DIR}/README.md"

info "Building AgentSpec plugin from commit ${BUILD_COMMIT} (${BUILD_MODE} mode) ..."

# ─── Step 0: Run Python tests ────────────────────────────────────────────────
# Fail fast if scripts/judge.py or scripts/generate-agent-router.py regress.
# Release builds fail closed when pytest is unavailable: packaging an untested
# linter or judge would make the distributable less trustworthy than source.

if [[ -d "${SCRIPT_DIR}/tests" ]]; then
    if ! python3 -c "import pytest" 2>/dev/null; then
        error "pytest is required for plugin builds — install it before packaging"
        exit 1
    fi
    info "Running every blocking Python suite..."
    # Root parity compares against the previous package, so it remains a
    # post-package check (Step 5e).
    if ! (cd "${SCRIPT_DIR}" && python3 -m pytest tests/ -q --ignore=tests/test_plugin_parity.py >/dev/null); then
        error "Root tests failed"
        exit 1
    fi
    if ! (cd "${SCRIPT_DIR}/tools/spec-linter" && python3 -m pytest -q >/dev/null); then
        error "Spec Linter tests failed"
        exit 1
    fi
    if ! (cd "${SCRIPT_DIR}/tools/spec-judge" && python3 -m pytest -q -m "not live" >/dev/null); then
        error "Spec Judge tests failed"
        exit 1
    fi
    ok "All Python suites passed"
fi

# ─── Step 0b: Regenerate agent-router from agent frontmatter ─────────────────
# Ensures .claude/skills/agent-router/SKILL.md and routing.json reflect the
# current agent set before we copy them into the plugin.

if [[ -f "${SCRIPT_DIR}/scripts/generate-agent-router.py" ]]; then
    if [[ "${BUILD_MODE}" == "release" ]]; then
        info "Checking generated agent-router sources..."
        if python3 "${SCRIPT_DIR}/scripts/generate-agent-router.py" --check >/dev/null; then
            ok "agent-router sources are current"
        else
            error "release build refuses stale generated agent-router sources"
            exit 1
        fi
    elif python3 "${SCRIPT_DIR}/scripts/generate-agent-router.py" >/dev/null; then
        ok "agent-router regenerated"
    else
        error "agent-router generation failed"
        exit 1
    fi
else
    warn "scripts/generate-agent-router.py not found — skipping regeneration"
fi

# ─── Step 1: Prepare isolated staging tree ───────────────────────────────────

ok "Staging tree prepared"

# ─── Step 2: Copy components ─────────────────────────────────────────────────

info "Copying agents..."
cp -r "${SOURCE_DIR}/agents" "${PLUGIN_DIR}/agents"

info "Copying commands..."
cp -r "${SOURCE_DIR}/commands" "${PLUGIN_DIR}/commands"

if [[ -d "${SOURCE_DIR}/skills" ]]; then
    info "Copying skills..."
    cp -r "${SOURCE_DIR}/skills" "${PLUGIN_DIR}/skills"
else
    warn ".claude/skills/ not found — creating empty skills dir"
    mkdir -p "${PLUGIN_DIR}/skills"
fi

info "Copying KB domains..."
cp -r "${SOURCE_DIR}/kb" "${PLUGIN_DIR}/kb"

info "Copying SDD templates and architecture..."
mkdir -p "${PLUGIN_DIR}/sdd"
cp -r "${SOURCE_DIR}/sdd/templates" "${PLUGIN_DIR}/sdd/templates"
cp -r "${SOURCE_DIR}/sdd/architecture" "${PLUGIN_DIR}/sdd/architecture"

# Copy SDD index and README if they exist
[[ -f "${SOURCE_DIR}/sdd/_index.md" ]] && cp "${SOURCE_DIR}/sdd/_index.md" "${PLUGIN_DIR}/sdd/"
[[ -f "${SOURCE_DIR}/sdd/README.md" ]] && cp "${SOURCE_DIR}/sdd/README.md" "${PLUGIN_DIR}/sdd/"

ok "All components copied"

# ─── Step 2c: Copy the spec-linter tool ──────────────────────────────────────
# Ships the contract-validation engine so the workflow agents' phase-document
# checks can run inside an installed plugin. Copy-then-prune: copy the whole
# tree, then drop dev-only and generated subpaths (the runtime needs only the
# package, wrapper, docs, schema, examples, and packaging metadata).

if [[ -d "${SCRIPT_DIR}/tools/spec-linter" ]]; then
    info "Copying spec-linter tool..."
    mkdir -p "${PLUGIN_DIR}/tools"
    cp -r "${SCRIPT_DIR}/tools/spec-linter" "${PLUGIN_DIR}/tools/spec-linter"
    rm -rf "${PLUGIN_DIR}/tools/spec-linter/.venv"
    rm -rf "${PLUGIN_DIR}/tools/spec-linter/tests"
    find "${PLUGIN_DIR}/tools/spec-linter" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find "${PLUGIN_DIR}/tools/spec-linter" -name '.pytest_cache' -type d -exec rm -rf {} + 2>/dev/null || true
    find "${PLUGIN_DIR}/tools/spec-linter" -name '.ruff_cache' -type d -exec rm -rf {} + 2>/dev/null || true
    find "${PLUGIN_DIR}/tools/spec-linter" -name '*.egg-info' -type d -exec rm -rf {} + 2>/dev/null || true
    ok "spec-linter copied"
else
    warn "tools/spec-linter not found — skipping linter packaging"
fi

# ─── Step 2d: Copy the spec-judge tool ───────────────────────────────────────
# Ships the behavioral evaluation engine (the Judger) alongside the Linter. Same
# copy-then-prune shape; at runtime it imports the sibling Linter's value objects
# via the wrapper's PYTHONPATH, so both tool dirs must ship side by side.

if [[ -d "${SCRIPT_DIR}/tools/spec-judge" ]]; then
    info "Copying spec-judge tool..."
    mkdir -p "${PLUGIN_DIR}/tools"
    cp -r "${SCRIPT_DIR}/tools/spec-judge" "${PLUGIN_DIR}/tools/spec-judge"
    rm -rf "${PLUGIN_DIR}/tools/spec-judge/.venv"
    rm -rf "${PLUGIN_DIR}/tools/spec-judge/tests"
    find "${PLUGIN_DIR}/tools/spec-judge" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find "${PLUGIN_DIR}/tools/spec-judge" -name '.pytest_cache' -type d -exec rm -rf {} + 2>/dev/null || true
    find "${PLUGIN_DIR}/tools/spec-judge" -name '.ruff_cache' -type d -exec rm -rf {} + 2>/dev/null || true
    find "${PLUGIN_DIR}/tools/spec-judge" -name '*.egg-info' -type d -exec rm -rf {} + 2>/dev/null || true
    ok "spec-judge copied"
else
    warn "tools/spec-judge not found — skipping judge packaging"
fi

# ─── Step 2b: Copy plugin-extras (plugin-only content) ───────────────────────

if [[ -d "${EXTRAS_DIR}" ]]; then
    info "Copying plugin-extras (new skills, hooks, scripts)..."
    if [[ -d "${EXTRAS_DIR}/skills" ]] && ls "${EXTRAS_DIR}/skills/"* >/dev/null 2>&1; then
        cp -r "${EXTRAS_DIR}/skills/"* "${PLUGIN_DIR}/skills/"
    fi
    [[ -d "${EXTRAS_DIR}/hooks" ]] && cp -r "${EXTRAS_DIR}/hooks" "${PLUGIN_DIR}/"
    [[ -d "${EXTRAS_DIR}/scripts" ]] && cp -r "${EXTRAS_DIR}/scripts" "${PLUGIN_DIR}/"
    ok "Plugin-extras copied"
fi

# ─── Step 3: Remove workspace-specific directories ───────────────────────────

info "Removing workspace-specific directories from plugin..."
rm -rf "${PLUGIN_DIR:?}/sdd/features"
rm -rf "${PLUGIN_DIR:?}/sdd/reports"
rm -rf "${PLUGIN_DIR:?}/sdd/archive"

# Drop scaffolding files that exist for contributor use only and would
# confuse Claude Code's agent loader (placeholder frontmatter values).
find "${PLUGIN_DIR:?}/agents" -name '_template.md' -delete 2>/dev/null || true

# Repo-local skills: support contributors working in this repository
# (its own review/communication workflows) and are not part of the
# distributed plugin. They live in .claude/skills/ so they load for
# contributors, and are excluded from plugin/skills/ here.
REPO_LOCAL_SKILLS=(meeting-analysis standup-report create-skill create-agent rollout-agentspec)
for skill in "${REPO_LOCAL_SKILLS[@]}"; do
    rm -rf "${PLUGIN_DIR:?}/skills/${skill}"
done

ok "Workspace directories excluded"

# ─── Step 4: Path rewriting ──────────────────────────────────────────────────
#
# REWRITE (plugin-internal references):
#   .claude/kb/           → ${CLAUDE_PLUGIN_ROOT}/kb/
#   .claude/agents/       → ${CLAUDE_PLUGIN_ROOT}/agents/
#   .claude/commands/     → ${CLAUDE_PLUGIN_ROOT}/commands/
#   .claude/skills/       → ${CLAUDE_PLUGIN_ROOT}/skills/
#   .claude/sdd/templates/     → ${CLAUDE_PLUGIN_ROOT}/sdd/templates/
#   .claude/sdd/architecture/  → ${CLAUDE_PLUGIN_ROOT}/sdd/architecture/
#   .claude/sdd/_index.md      → ${CLAUDE_PLUGIN_ROOT}/sdd/_index.md
#   .claude/sdd/README.md      → ${CLAUDE_PLUGIN_ROOT}/sdd/README.md
#
# PRESERVE (workspace output paths — must NOT be rewritten):
#   .claude/sdd/features/  → stays as-is (user's project)
#   .claude/sdd/reports/   → stays as-is (user's project)
#   .claude/sdd/archive/   → stays as-is (user's project)
#   .claude/storage/       → stays as-is (user's project)
# ─────────────────────────────────────────────────────────────────────────────

info "Rewriting paths in .md, .yaml, and .json files..."

while IFS= read -r -d '' file; do
    tmp="${file}.tmp"
    sed \
        -e 's|\.claude/kb/|${CLAUDE_PLUGIN_ROOT}/kb/|g' \
        -e 's|\.claude/agents/|${CLAUDE_PLUGIN_ROOT}/agents/|g' \
        -e 's|\.claude/commands/|${CLAUDE_PLUGIN_ROOT}/commands/|g' \
        -e 's|\.claude/skills/|${CLAUDE_PLUGIN_ROOT}/skills/|g' \
        -e 's|\.claude/sdd/templates/|${CLAUDE_PLUGIN_ROOT}/sdd/templates/|g' \
        -e 's|\.claude/sdd/architecture/|${CLAUDE_PLUGIN_ROOT}/sdd/architecture/|g' \
        -e 's|\.claude/sdd/_index\.md|${CLAUDE_PLUGIN_ROOT}/sdd/_index.md|g' \
        -e 's|\.claude/sdd/README\.md|${CLAUDE_PLUGIN_ROOT}/sdd/README.md|g' \
        -e 's|tools/spec-linter/|${CLAUDE_PLUGIN_ROOT}/tools/spec-linter/|g' \
        -e 's|tools/spec-judge/|${CLAUDE_PLUGIN_ROOT}/tools/spec-judge/|g' \
        "$file" > "$tmp" && mv "$tmp" "$file" || { rm -f "$tmp"; exit 1; }
done < <(find "${PLUGIN_DIR}" \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" \) \
    -type f ! -path "${PLUGIN_DIR}/.claude-plugin/*" -print0)

ok "Paths rewritten"

# ─── Step 5: Rewrite hardcoded absolute paths ────────────────────────────────
# After Step 4, some paths may look like:
#   /Users/username/GitHub/agentspec/${CLAUDE_PLUGIN_ROOT}/skills/...
# We need to strip the absolute prefix, leaving just ${CLAUDE_PLUGIN_ROOT}/...
# Also catch any remaining /Users/.../agentspec/.claude/ patterns.

info "Rewriting absolute paths..."
while IFS= read -r -d '' file; do
    tmp="${file}.tmp"
    sed \
        -e 's|/[^ ]*\${CLAUDE_PLUGIN_ROOT}/|${CLAUDE_PLUGIN_ROOT}/|g' \
        -e 's|/[^ ]*/\.claude/skills/|${CLAUDE_PLUGIN_ROOT}/skills/|g' \
        -e 's|cd \.claude/skills/|cd ${CLAUDE_PLUGIN_ROOT}/skills/|g' \
        "$file" > "$tmp" && mv "$tmp" "$file" || { rm -f "$tmp"; exit 1; }
done < <(find "${PLUGIN_DIR}" -type f \( -name "*.md" -o -name "*.py" -o -name "*.sh" \) \
    ! -path "${PLUGIN_DIR}/.claude-plugin/*" -print0)

ok "Absolute paths rewritten"

# ─── Step 5b: Restore executable permissions (lost during sed tmp→mv) ────────

chmod +x "${PLUGIN_DIR}/scripts/"*.sh 2>/dev/null || true
chmod +x "${PLUGIN_DIR}/tools/spec-linter/spec-lint" 2>/dev/null || true
chmod +x "${PLUGIN_DIR}/tools/spec-judge/spec-judge" 2>/dev/null || true

# ─── Step 5d: spec-judge cross-package import smoke-check ─────────────────────
# The Judger imports the sibling Linter's value objects at runtime via the
# PYTHONPATH its wrapper sets. Verify that resolves in the BUILT plugin when a
# suitable interpreter is available. Installed dependencies make a failed
# self-check blocking; missing runtime dependencies are also a packaging error.

if [[ -x "${PLUGIN_DIR}/tools/spec-judge/spec-judge" ]]; then
    if ! python3 -c "import pydantic, yaml" >/dev/null 2>&1; then
        error "python3 lacks pydantic/pyyaml required by the packaged Spec Judge"
        exit 1
    fi
    if "${PLUGIN_DIR}/tools/spec-judge/spec-judge" --selfcheck >/dev/null 2>&1; then
        ok "spec-judge import smoke-check passed (spec_linter resolves in the built plugin)"
    else
        error "spec-judge --selfcheck failed in the built plugin"
        exit 1
    fi
fi

# ─── Step 5c: Sync root .claude-plugin/marketplace.json ─────────────────────
# `claude plugin marketplace add <owner>/<repo>` fetches
# .claude-plugin/marketplace.json from the repository root via GitHub's raw
# content API. The canonical manifest lives under plugin/.claude-plugin/, so
# we mirror it to the root after every build with `source` rewritten to
# `./plugin`. Keeps the root copy in sync automatically and prevents drift.

info "Preparing root .claude-plugin/marketplace.json..."
ROOT_MANIFEST="${SCRIPT_DIR}/.claude-plugin/marketplace.json"
PLUGIN_MANIFEST="${PLUGIN_DIR}/.claude-plugin/marketplace.json"
STAGED_ROOT_MANIFEST="${BUILD_ROOT}/marketplace.json"
python3 - <<PY
import json, pathlib
src = pathlib.Path("${PLUGIN_MANIFEST}")
dst = pathlib.Path("${STAGED_ROOT_MANIFEST}")
manifest = json.loads(src.read_text())
for p in manifest.get("plugins", []):
    p["source"] = "./plugin"
dst.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
PY
ok "Root marketplace manifest prepared"

# ─── Step 5d: Write reproducible build provenance ────────────────────────────
# The manifest deliberately excludes itself. Its stable ordering, content
# hashes, commit timestamp, and normalized relative paths make two builds of
# the same commit comparable without embedding wall-clock time or staging paths.

SOURCE_DATE_EPOCH="$(git -C "${SCRIPT_DIR}" show -s --format=%ct "${BUILD_COMMIT}")"
export SOURCE_DATE_EPOCH
python3 - "${PLUGIN_DIR}" "${BUILD_COMMIT}" "${BUILD_MODE}" "${BUILD_TREE_STATE}" <<'PY'
import hashlib
import json
import os
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
commit = sys.argv[2]
mode = sys.argv[3]
tree_state = sys.argv[4]
files = []
for path in sorted(p for p in root.rglob("*") if p.is_file()):
    rel = path.relative_to(root).as_posix()
    if rel == "BUILD-MANIFEST.json":
        continue
    files.append(
        {
            "path": rel,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mode": format(path.stat().st_mode & 0o777, "04o"),
        }
    )
payload = {
    "schema_version": 1,
    "commit": commit,
    "source_date_epoch": int(os.environ["SOURCE_DATE_EPOCH"]),
    "mode": mode,
    "tree_state": tree_state,
    "files": files,
}
(root / "BUILD-MANIFEST.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n"
)
PY
ok "Reproducible BUILD-MANIFEST.json written"

# ─── Step 5e: Run plugin/ parity test (post-package) ─────────────────────────
# Confirms plugin/ is structurally in sync with .claude/ + plugin-extras/
# after packaging. Must run here, not in Step 0: it compares plugin/ against
# canonical sources, and plugin/ only reflects this build once packaging,
# rewriting, and chmod are done.

if [[ -f "${SCRIPT_DIR}/tests/test_plugin_parity.py" ]]; then
    info "Running plugin/ parity test..."
    if (cd "${SCRIPT_DIR}" && AGENTSPEC_PLUGIN_ROOT="${PLUGIN_DIR}" \
        python3 -m pytest tests/test_plugin_parity.py -q >/dev/null 2>&1); then
        ok "Plugin parity test passed"
    else
        error "plugin/ diverged from canonical sources after packaging — inspect parity failures"
        error "run: python3 -m pytest tests/test_plugin_parity.py -v"
        exit 1
    fi
fi

# ─── Step 6: Verify no stale .claude/ paths remain ──────────────────────────

info "Verifying path migration..."

# Collect stale references (grep returns 1 on no match — use || true)
_stale_filter() {
    grep -r '\.claude/' "${PLUGIN_DIR}" \
        --include="*.md" --include="*.yaml" --include="*.yml" \
        | grep -v 'CLAUDE_PLUGIN_ROOT' \
        | grep -v '\.claude/sdd/features' \
        | grep -v '\.claude/sdd/reports' \
        | grep -v '\.claude/sdd/archive' \
        | grep -v '\.claude/sdd/' \
        | grep -v '\.claude/storage' \
        | grep -v '\.claude-plugin' \
        | grep -v '\.claude/settings' \
        | grep -v 'CLAUDE\.md' \
        | grep -v '\.claude/plans' \
        | grep -v '\.claude/memory' \
        | grep -v '^[[:space:]]*#' \
        || true
}

STALE_OUTPUT=$(_stale_filter)
STALE_COUNT=$(printf '%s' "${STALE_OUTPUT}" | grep -c '.' || true)

if [[ "${STALE_COUNT}" -gt 0 ]]; then
    warn "${STALE_COUNT} potentially stale .claude/ references found:"
    printf '%s\n' "${STALE_OUTPUT}" | head -20
    echo ""
    warn "Review the above references — some may be intentional (workspace paths)."
else
    ok "No stale .claude/ paths found"
fi

# ─── Step 6b: Publish staged output transactionally ─────────────────────────
# Nothing above mutates plugin/. Keep a rollback copy across the two renames;
# cleanup restores it if the second rename is interrupted or fails. There is a
# short visibility gap between renames, so this is rollback-safe rather than a
# single atomic directory replacement.

if [[ "${BUILD_MODE}" == "release" ]]; then
    CURRENT_COMMIT="$(git -C "${SCRIPT_DIR}" rev-parse --verify HEAD)"
    if [[ "${CURRENT_COMMIT}" != "${BUILD_COMMIT}" ]] || \
       [[ -n "$(git -C "${SCRIPT_DIR}" status --porcelain --untracked-files=all)" ]]; then
        error "release source changed after preflight; refusing to publish staging"
        exit 1
    fi
fi

BACKUP_DIR="${SCRIPT_DIR}/.plugin-backup.$$"
mv "${FINAL_PLUGIN_DIR}" "${BACKUP_DIR}"
if ! mv "${STAGED_PLUGIN_DIR}" "${FINAL_PLUGIN_DIR}"; then
    mv "${BACKUP_DIR}" "${FINAL_PLUGIN_DIR}"
    BACKUP_DIR=""
    error "atomic plugin publish failed; previous plugin restored"
    exit 1
fi
rm -rf "${BACKUP_DIR}"
BACKUP_DIR=""
PLUGIN_DIR="${FINAL_PLUGIN_DIR}"

# Publish the derived root marketplace file using a same-directory rename.
mkdir -p "${SCRIPT_DIR}/.claude-plugin"
ROOT_MANIFEST_TMP="${ROOT_MANIFEST}.tmp.$$"
cp "${STAGED_ROOT_MANIFEST}" "${ROOT_MANIFEST_TMP}"
mv "${ROOT_MANIFEST_TMP}" "${ROOT_MANIFEST}"
ok "Staged plugin published transactionally with rollback"

# ─── Step 7: Summary ─────────────────────────────────────────────────────────

AGENT_COUNT=$(find "${PLUGIN_DIR}/agents" -name "*.md" -not -name "README.md" -not -name "_template.md" | wc -l | tr -d ' ')
COMMAND_COUNT=$(find "${PLUGIN_DIR}/commands" -name "*.md" -not -name "README.md" | wc -l | tr -d ' ')
SKILL_COUNT=$(find "${PLUGIN_DIR}/skills" -name "SKILL.md" | wc -l | tr -d ' ')
KB_COUNT=$(find "${PLUGIN_DIR}/kb" -maxdepth 1 -type d ! -name "kb" ! -name "_templates" | wc -l | tr -d ' ')
if [[ -x "${PLUGIN_DIR}/tools/spec-linter/spec-lint" ]]; then
    LINTER_STATUS="bundled"
else
    LINTER_STATUS="not bundled"
fi
if [[ -x "${PLUGIN_DIR}/tools/spec-judge/spec-judge" ]]; then
    JUDGE_STATUS="bundled"
else
    JUDGE_STATUS="not bundled"
fi

echo ""
echo "============================================"
printf "${GREEN}AgentSpec Plugin Build Complete${NC}\n"
echo "============================================"
echo "  Agents:   ${AGENT_COUNT}"
echo "  Commands: ${COMMAND_COUNT}"
echo "  Skills:   ${SKILL_COUNT}"
echo "  KB:       ${KB_COUNT} domains"
echo "  Linter:   ${LINTER_STATUS}"
echo "  Judger:   ${JUDGE_STATUS}"
echo ""
echo "  Output:   ${PLUGIN_DIR}/"
echo ""
echo "  Test with:"
echo "    claude --plugin-dir ./plugin"
echo ""
echo "  Validate with:"
echo "    claude plugin validate ./plugin"
echo "============================================"
