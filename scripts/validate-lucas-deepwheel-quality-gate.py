#!/usr/bin/env python3
"""Validate Quality Gate-specific product rules."""
from __future__ import annotations

from pathlib import Path
import json
import re
import stat
import sys


REQUIRED_REFERENCES = (
    "github-publishability-checklist.md",
    "high-risk-domain-policy.md",
    "interaction-and-onboarding-policy.md",
    "new-user-capability-preflight.md",
    "quality-gate-framework.md",
    "public-surface-consistency.md",
    "release-state-reconciliation.md",
    "reviewer-role-matrix.md",
    "security-and-privacy-gate.md",
    "token-and-budget-policy.md",
    "validation-report-template.md",
)

REQUIRED_TERMS = (
    "已支持",
    "需要工具",
    "暂不承诺",
    "CLEAN",
    "CONCERNS",
    "BLOCK",
    "退出码",
    "关联 Skill",
    "独立产品入口",
    "7 角色",
    "敏感值",
    "相对文件名",
    "行为安全合同",
    "GitHub main",
    "VISUAL ASSET STALE",
    "生产契约",
    "消费者视角",
)

REQUIRED_SCANNER_TERMS = (
    "LOCAL_PATH_PATTERNS",
    "PII_PATTERNS",
    "SENSITIVE_PATTERNS",
    "check_publication",
    "check_risk_profile",
    "has_numeric_safety_signal",
    "numeric_safety_contract_required",
    "behavioral_safety_contract_required",
    "REQUIRED_HIGH_RISK_BEHAVIOR_CASES",
    "check_public_surface_review",
    "PUBLIC-SURFACE-REVIEW.json",
    "PUBLIC_SURFACE_PRODUCTION_FIELDS",
    "VISUAL ASSET STALE",
    "high-risk behavior regression test file is missing",
    "high-risk behavior regression tests lack declared cases",
    "INTRO_ASSET_SUFFIXES",
    "publication checklist has incomplete items",
    "high-risk professional sign-off is incomplete",
    "professional sign-off target does not match current Skill",
    "tree_sha256",
    "print-skill-sha256",
    "deduplicate",
    "raise SystemExit(main())",
    'return 2',
    'return 1',
)

FORBIDDEN_SCANNER_TERMS = (
    "Users/zhangshuai",
    "if p.name == 'skill_quality_gate.py'",
    'if p.name == "skill_quality_gate.py"',
)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


if len(sys.argv) not in (2, 3):
    fail(
        "usage: validate-lucas-deepwheel-quality-gate.py "
        "<skill_dir> [publication_dir]"
    )

skill = Path(sys.argv[1]).expanduser().resolve()
publication = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) == 3 else None

if not skill.is_dir():
    fail("Skill directory is missing")
if skill.name != "lucas-deepwheel-skill-quality-gate":
    fail("unexpected Skill directory name")

skill_md = skill / "SKILL.md"
if not skill_md.is_file():
    fail("SKILL.md is missing")
text = skill_md.read_text(encoding="utf-8")
frontmatter = re.match(r"^---\n(.*?)\n---\n", text, re.S)
if frontmatter is None:
    fail("SKILL.md frontmatter is missing")
keys = [
    line.split(":", 1)[0].strip()
    for line in frontmatter.group(1).splitlines()
    if ":" in line
]
if keys != ["name", "description"]:
    fail("frontmatter must contain only name and description")
for term in REQUIRED_TERMS:
    if term not in text:
        fail(f"SKILL.md missing required term: {term}")

references = skill / "references"
for name in REQUIRED_REFERENCES:
    if not (references / name).is_file():
        fail(f"missing reference: {name}")

if not (skill / "agents" / "openai.yaml").is_file():
    fail("agents/openai.yaml is missing")

scanner = skill / "scripts" / "skill_quality_gate.py"
if not scanner.is_file():
    fail("skill_quality_gate.py is missing")
if not scanner.read_bytes().startswith(b"#!/usr/bin/env python3\n"):
    fail("skill_quality_gate.py must start with the Python shebang")
if not (scanner.stat().st_mode & stat.S_IXUSR):
    fail("skill_quality_gate.py is not executable")
scanner_text = scanner.read_text(encoding="utf-8")
for term in REQUIRED_SCANNER_TERMS:
    if term not in scanner_text:
        fail(f"scanner missing required behavior marker: {term}")
for term in FORBIDDEN_SCANNER_TERMS:
    if term in scanner_text:
        fail(f"scanner contains forbidden behavior: {term}")

reconciler = skill / "scripts" / "reconcile_release_state.py"
if not reconciler.is_file():
    fail("reconcile_release_state.py is missing")
if not reconciler.read_bytes().startswith(b"#!/usr/bin/env python3\n"):
    fail("reconcile_release_state.py must start with the Python shebang")
if not (reconciler.stat().st_mode & stat.S_IXUSR):
    fail("reconcile_release_state.py is not executable")
reconciler_text = reconciler.read_text(encoding="utf-8")
for term in (
    "MATCH",
    "DRIFT",
    "NOT PUSHED",
    "PR OPEN",
    "ACTIONS PENDING",
    "ACTIONS FAILED",
    "INSTALL OUTDATED",
    ".installed-version",
    "UNRELEASED",
    "gh_json",
    "safe_tree",
):
    if term not in reconciler_text:
        fail(f"release-state reconciler misses marker: {term}")

surface_manifest = publication / "docs" / "PUBLIC-SURFACE-REVIEW.json" if publication else None
if surface_manifest is not None and not surface_manifest.is_file():
    fail("public-surface review manifest is missing")

if publication is not None:
    if not publication.is_dir():
        fail("publication directory is missing")
    test_file = publication / "tests" / "test_skill_quality_gate.py"
    if not test_file.is_file():
        fail("behavior test file is missing")
    test_text = test_file.read_text(encoding="utf-8")
    for marker in (
        "consent_missing",
        "data_subject_unconfirmed",
        "minimum_input_missing",
        "safety_preflight_incomplete",
        "stop_condition",
        "blocked_output_suppression",
        "source_provenance_invalid",
    ):
        if marker not in test_text:
            fail(f"behavior test file misses high-risk marker: {marker}")
    for marker in (
        "test_release_state_reconciler_reports_offline_match",
        "test_release_state_reconciler_ignores_installed_version_marker",
        "test_release_state_reconciler_detects_not_pushed_and_install_outdated",
        "test_release_state_reconciler_reports_pr_open_and_actions_failed",
        "test_missing_public_surface_manifest_returns_visual_asset_stale",
        "test_changed_skill_without_public_surface_review_returns_visual_asset_stale",
        "test_user_visible_review_requires_bilingual_editable_and_rendered_assets",
    ):
        if marker not in test_text:
            fail(f"behavior test file misses rc.5 regression: {marker}")

    try:
        surface_data = json.loads(surface_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail("public-surface review manifest is invalid JSON")
    for key, expected in (
        ("schema_version", 1),
        ("skill_name", "lucas-deepwheel-skill-quality-gate"),
    ):
        if surface_data.get(key) != expected:
            fail(f"public-surface review manifest has unexpected {key}")
    review_pair = (
        surface_data.get("capability_change"),
        surface_data.get("decision"),
    )
    if review_pair not in {
        ("user_visible", "UPDATED"),
        ("internal_only", "NO_CHANGE_REQUIRED"),
    }:
        fail("public-surface review manifest has an invalid decision pair")

    surface_problems = []
    production = surface_data.get("production_contract")
    if not isinstance(production, dict):
        surface_problems.append("production_contract is missing")
    else:
        for field in ("terminal_user", "use_scenario", "desired_belief", "next_action"):
            value = production.get(field)
            if not isinstance(value, dict):
                surface_problems.append(f"production_contract.{field} is invalid")
                continue
            for language in ("en", "zh-CN"):
                if not isinstance(value.get(language), str) or len(value.get(language, "").strip()) < 12:
                    surface_problems.append(f"production_contract.{field}.{language} is incomplete")
        if production.get("content_languages") != ["en", "zh-CN"]:
            surface_problems.append("production_contract.content_languages must be en + zh-CN")
        if production.get("design_system") != "lucas-deepwheel-brand-apply":
            surface_problems.append("production_contract.design_system must use lucas-deepwheel-brand-apply")
        if production.get("brand_principles") != ["precise", "restrained", "credible", "ordered"]:
            surface_problems.append("production_contract.brand_principles do not match DeepWheel")
        if production.get("editable_source") != "SVG" or production.get("rendered_output") != "PNG":
            surface_problems.append("production_contract asset source/output pair must be SVG + PNG")
        if production.get("consumer_reviewed") is not True:
            surface_problems.append("consumer review is incomplete")
        if production.get("brand_reviewed") is not True:
            surface_problems.append("brand review is incomplete")

    intro = publication / "assets" / "intro"
    required_intro_copy = {
        "quality-gate-hero-en.svg": "Keep every surface in sync.",
        "quality-gate-hero-zh-CN.svg": "让每个公开面都同步。",
        "quality-gate-workflow-en.svg": "Reconcile GitHub, Actions, install",
        "quality-gate-workflow-zh-CN.svg": "对账 GitHub、Actions、安装版",
    }
    for name, marker in required_intro_copy.items():
        asset = intro / name
        if not asset.is_file():
            surface_problems.append(f"missing introduction asset: {name}")
        elif marker not in asset.read_text(encoding="utf-8"):
            surface_problems.append(f"introduction asset misses required copy: {name}")

    for relative in (
        "docs/GITHUB-BILINGUAL-INTRO-SPEC.md",
        "assets/intro/README.md",
        "assets/intro/source/visual-tokens.json",
        "scripts/render-intro-assets.py",
    ):
        if not (publication / relative).is_file():
            surface_problems.append(f"public-surface generation file is missing: {relative}")

    version = (publication / "VERSION").read_text(encoding="utf-8").strip()
    for readme_name in ("README.md", "README.zh-CN.md"):
        readme = publication / readme_name
        if not readme.is_file() or version not in readme.read_text(encoding="utf-8")[:600]:
            surface_problems.append(f"README status does not match VERSION: {readme_name}")

    if surface_problems:
        fail("public-surface validation failed: " + "; ".join(surface_problems))
    workflow = publication / ".github" / "workflows" / "validate.yml"
    if not workflow.is_file():
        fail("validation workflow is missing")
    workflow_text = workflow.read_text(encoding="utf-8")
    for term in (
        "Validate version metadata",
        "Validate skill package",
        "Validate Quality Gate-specific rules and behavior",
        "test_skill_quality_gate.py",
    ):
        if term not in workflow_text:
            fail(f"workflow missing required term: {term}")

print("PASS: quality gate validation ok")
