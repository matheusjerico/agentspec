# ============================================================================
# AgentSpec — developer Makefile
# ============================================================================
# Single entry point for everything a contributor needs to do locally.
# Every target is idempotent and safe to re-run.
#
# Quick start:
#   make help          # show all targets
#   make build         # full plugin build (tests + generate + package)
#   make test          # pytest suite only
#   make check         # drift check (tests + --check on generators)
#   make lint          # shellcheck + markdown warnings
# ============================================================================

# Use bash so we get [[ ]], set -u, etc. — not POSIX sh.
SHELL := /usr/bin/env bash

.DEFAULT_GOAL := help
.PHONY: help build build-release test test-all check release-gate lint clean generate plugin install-deps spec-lint spec-judge

# ----------------------------------------------------------------------------
# Help
# ----------------------------------------------------------------------------

help: ## Show this help
	@echo "AgentSpec — developer targets"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "  %-18s %s\n", "TARGET", "DESCRIPTION"; printf "  %-18s %s\n", "------", "-----------"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "Most-used: make build  |  make test  |  make check"

# ----------------------------------------------------------------------------
# Core targets
# ----------------------------------------------------------------------------

build: ## Full plugin build (tests + regenerate agent-router + package)
	@./build-plugin.sh --dev

build-release: ## Reproducible plugin build from a clean committed tree
	@./build-plugin.sh --release

test: test-all ## Run every blocking pytest suite

test-all: ## Run root, spec-linter, and spec-judge suites
	@python3 -m pytest tests/ -q
	@cd tools/spec-linter && python3 -m pytest -q
	@cd tools/spec-judge && python3 -m pytest -q -m "not live"

check: ## Drift check — tests + generators in --check mode (fails on drift)
	@$(MAKE) test-all
	@python3 scripts/generate-agent-router.py --check
	@python3 scripts/generate-codex-adapters.py --check

release-gate: ## Re-run all release checks and validate post-remediation evidence
	@python3 tools/release_gate.py \
		docs/superpowers/reports/2026-07-30-agentspec-remediation-benchmark.md \
		--repo . \
		--target main

generate: ## Regenerate agent-router and repo-local Codex adapters
	@python3 scripts/generate-agent-router.py
	@python3 scripts/generate-codex-adapters.py

plugin: build ## Alias for `make build`

spec-lint: ## Run the spec-linter component test suite (tools/spec-linter)
	@if [ -x tools/spec-linter/.venv/bin/python ]; then \
		( cd tools/spec-linter && .venv/bin/python -m pytest -v ); \
	else \
		( cd tools/spec-linter && python3 -m pytest -v ); \
	fi

spec-judge: ## Run the spec-judge component test suite (tools/spec-judge, offline)
	@if [ -x tools/spec-judge/.venv/bin/python ]; then \
		( cd tools/spec-judge && .venv/bin/python -m pytest -v -m "not live" ); \
	else \
		( cd tools/spec-judge && python3 -m pytest -v -m "not live" ); \
	fi

# ----------------------------------------------------------------------------
# Hygiene
# ----------------------------------------------------------------------------

lint: ## Lint shell scripts via shellcheck (skips gracefully if not installed)
	@if command -v shellcheck >/dev/null 2>&1; then \
		echo "Running shellcheck..."; \
		shellcheck -S warning \
			build-plugin.sh \
			.claude/skills/visual-explainer/scripts/share.sh \
			plugin-extras/scripts/init-workspace.sh \
			plugin-extras/scripts/autopilot.sh; \
	else \
		echo "shellcheck not installed — brew install shellcheck"; \
		exit 0; \
	fi

clean: ## Remove generated plugin/ artifacts (keep .claude-plugin/)
	@find plugin -mindepth 1 -maxdepth 1 \
		! -name '.claude-plugin' \
		! -name 'README.md' \
		-exec rm -rf {} + 2>/dev/null || true
	@echo "Plugin artifacts cleaned. Run 'make build' to rebuild."

install-deps: ## Install optional dev dependencies (pytest, shellcheck)
	@echo "Installing pytest..."
	@python3 -m pip install --user pytest
	@if ! command -v shellcheck >/dev/null 2>&1; then \
		echo ""; \
		echo "shellcheck not installed. On macOS:  brew install shellcheck"; \
		echo "                        On Linux:    apt-get install shellcheck"; \
	fi
