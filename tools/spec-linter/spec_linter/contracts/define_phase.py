"""Define-phase contract (loaded as data).

Built from `define.required_sections` (FAIL semantics, unchanged) and the
top-level `risk_profiles` block of WORKFLOW_CONTRACTS.yaml, validates a
DEFINE_{FEATURE}.md against structural section presence plus semantic `RP.*`
risk-profile rules. WHAT is checked — the section list, the level/dimension
vocabulary, the override's required fields, the legacy effective level — is
data handed in by the caller; severity is this contract's own choice.

Rollout is `observe_warn` (`risk_profiles.rollout`): every `RP.*` rule below
is `Level.WARN`, unconditionally — a missing, invalid, or unjustified risk
profile never fails a lint run. Raising any `RP.*` rule to FAIL (Enforce) is a
future, versioned contract change, not a side effect of this module.
`L2.required_section` keeps its existing FAIL semantics, exactly mirroring
`SddPhaseContract` — this preserves current exit-1 behavior for missing
required sections; `risk_profile` itself is deliberately NOT one of them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from ..verdict import Finding, Level

# Two deliberately different heading vocabularies:
# - Section PRESENCE uses any ATX level (#{1,6}) — mirroring SddPhaseContract
#   exactly, so routing define to this contract changes NO FAIL behavior
#   (observe/warn invariant: this module introduces zero new blocking paths).
# - The Risk Profile SCAN is ##-only: a demoted "### Risk Profile" is simply
#   not found, RP.profile_missing fires — WARN-only stakes, fail-open by design.
_HEADING = re.compile(r"^#{1,6}\s+(.*\S)\s*$", re.MULTILINE)
_H2 = re.compile(r"^##\s+(.*\S)\s*$", re.MULTILINE)
_YAML_FENCE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _section_after(artifact: str, slug_prefix: str) -> str | None:
    """Text between the first `##` heading whose slug starts with
    `slug_prefix` and the next `##` heading (or end of document); `None` if
    no such heading exists."""
    matches = list(_H2.finditer(artifact))
    for i, m in enumerate(matches):
        if _slug(m.group(1)).startswith(slug_prefix):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(artifact)
            return artifact[start:end]
    return None


def _parse_profile(artifact: str) -> dict | None:
    """The `risk_profile` mapping from the first fenced ```yaml block of the
    `## Risk Profile...` section. Anything short of that — missing section,
    missing fence, malformed YAML, a non-mapping document, a `risk_profile`
    value that isn't itself a mapping — resolves to `None`; this parser never
    raises (observe/warn rollout: an unparseable profile is a WARN finding,
    never a linter crash)."""
    section = _section_after(artifact, "risk_profile")
    if section is None:
        return None
    fence = _YAML_FENCE.search(section)
    if fence is None:
        return None
    try:
        document = yaml.safe_load(fence.group(1))
    except yaml.YAMLError:
        return None
    if not isinstance(document, dict):
        return None
    profile = document.get("risk_profile")
    return profile if isinstance(profile, dict) else None


@dataclass(frozen=True, slots=True)
class _ParsedDefinePhase:
    headings: set[str]
    profile: dict | None


class DefinePhaseContract:
    def __init__(
        self,
        required_sections: list[str],
        levels: list[str],
        dimensions: list[str],
        dimension_values: list[str],
        override_required: list[str],
        legacy_level: str,
    ) -> None:
        self.name = "sdd-phase:define"
        self._required = required_sections
        self._levels = levels
        self._dimensions = dimensions
        self._dimension_values = dimension_values
        self._override_required = override_required
        self._legacy_level = legacy_level

    def parse(self, artifact: str) -> _ParsedDefinePhase:
        headings = {_slug(m.group(1)) for m in _HEADING.finditer(artifact)}
        return _ParsedDefinePhase(headings=headings, profile=_parse_profile(artifact))

    def check(self, parsed: _ParsedDefinePhase) -> list[Finding]:
        findings = self._check_required_sections(parsed)
        findings.extend(self._check_profile(parsed.profile))
        return findings

    def _check_required_sections(self, parsed: _ParsedDefinePhase) -> list[Finding]:
        findings: list[Finding] = []
        for section in self._required:
            if _slug(section) not in parsed.headings:
                findings.append(
                    Finding(
                        level=Level.FAIL,
                        rule="L2.required_section",
                        field=section,
                        message=f"required section '{section}' is missing",
                        expected="section present as a heading",
                        found="absent",
                    )
                )
        return findings

    def _check_profile(self, profile: dict | None) -> list[Finding]:
        if profile is None:
            return [self._profile_missing_finding()]

        findings: list[Finding] = []
        level = profile.get("level")
        level_valid = level in self._levels
        if not level_valid:
            findings.append(self._level_invalid_finding(level))

        findings.extend(self._check_override(profile))

        valid_dimension_values, dimension_findings = self._check_dimensions(profile)
        findings.extend(dimension_findings)

        if level_valid and valid_dimension_values:
            findings.extend(self._check_level_below_dimensions(level, valid_dimension_values))

        return findings

    def _profile_missing_finding(self) -> Finding:
        return Finding(
            level=Level.WARN,
            rule="RP.profile_missing",
            field="Risk Profile",
            message=(
                "no parseable Risk Profile — effective level "
                f"'{self._legacy_level}' is assumed (observe/warn rollout); add a "
                "Risk Profile section with a ```yaml risk_profile block per "
                "DEFINE_TEMPLATE.md's Risk Profile section"
            ),
            expected="## Risk Profile section with a risk_profile YAML block",
            found="absent",
        )

    def _level_invalid_finding(self, level: object) -> Finding:
        found = str(level) if level is not None else "absent"
        message = (
            f"Risk Profile level '{level}' is not one of the contract's allowed values"
            if level is not None
            else "Risk Profile carries no 'level' field"
        )
        return Finding(
            level=Level.WARN,
            rule="RP.level_invalid",
            field="level",
            message=message,
            expected=" | ".join(self._levels),
            found=found,
        )

    def _check_dimensions(self, profile: dict) -> tuple[list[str], list[Finding]]:
        dimensions = profile.get("dimensions")
        if not isinstance(dimensions, dict):
            return [], [
                Finding(
                    level=Level.WARN,
                    rule="RP.dimension_invalid",
                    field="dimensions",
                    message="Risk Profile carries no 'dimensions' mapping",
                    expected=", ".join(self._dimensions),
                    found="absent",
                )
            ]

        findings: list[Finding] = []
        valid_values: list[str] = []
        for key, value in dimensions.items():
            if key not in self._dimensions:
                findings.append(
                    Finding(
                        level=Level.WARN,
                        rule="RP.dimension_invalid",
                        field=f"dimensions.{key}",
                        message=f"unknown risk dimension '{key}'",
                        expected=", ".join(self._dimensions),
                        found=str(key),
                    )
                )
                continue
            if value not in self._dimension_values:
                findings.append(
                    Finding(
                        level=Level.WARN,
                        rule="RP.dimension_invalid",
                        field=f"dimensions.{key}",
                        message=(
                            f"dimension '{key}' value '{value}' is not one of the "
                            "contract's allowed values"
                        ),
                        expected=", ".join(self._dimension_values),
                        found=str(value),
                    )
                )
                continue
            valid_values.append(value)
        return valid_values, findings

    def _check_override(self, profile: dict) -> list[Finding]:
        override = profile.get("override")
        if not isinstance(override, dict):
            return []
        applied = override.get("applied")
        # Strict: only a real boolean True or the literal string "true" counts —
        # a quoted "false" is a non-empty (truthy) string, not an applied override.
        if applied is not True and not (
            isinstance(applied, str) and applied.strip().lower() == "true"
        ):
            return []
        missing = [field for field in self._override_required if not override.get(field)]
        if not missing:
            return []
        verb = "is" if len(missing) == 1 else "are"
        return [
            Finding(
                level=Level.WARN,
                rule="RP.override_unjustified",
                field="override",
                message=(
                    f"override.applied is true but {', '.join(missing)} {verb} "
                    "absent/empty — an override must be auditable"
                ),
                expected=", ".join(self._override_required),
                found=", ".join(missing),
            )
        ]

    def _check_level_below_dimensions(
        self, level: str, valid_values: list[str]
    ) -> list[Finding]:
        if level not in self._dimension_values:
            return []
        level_rank = self._dimension_values.index(level)
        max_value = max(valid_values, key=self._dimension_values.index)
        max_rank = self._dimension_values.index(max_value)
        if level_rank >= max_rank:
            return []
        return [
            Finding(
                level=Level.WARN,
                rule="RP.level_below_dimensions",
                field="level",
                message=(
                    f"declared level '{level}' is below the declared dimensions — "
                    f"a dimension value of '{max_value}' implies at least that level"
                ),
                expected=f">= {max_value}",
                found=level,
            )
        ]
