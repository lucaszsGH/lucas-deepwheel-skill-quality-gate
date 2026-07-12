#!/usr/bin/env python3
"""Validate Quality Gate-specific product rules."""
from __future__ import annotations

from pathlib import Path
import re
import stat
import sys


REQUIRED_REFERENCES = (
    "github-publishability-checklist.md",
    "high-risk-domain-policy.md",
    "interaction-and-onboarding-policy.md",
    "new-user-capability-preflight.md",
    "quality-gate-framework.md",
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
