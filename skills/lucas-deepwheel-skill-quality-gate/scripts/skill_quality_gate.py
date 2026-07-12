#!/usr/bin/env python3
"""Audit an Agent Skill and optional publication package without exposing matched values."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Iterable


TEXT_EXTENSIONS = {
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SKIP_PARTS = {".git", "__pycache__"}
SKIP_NAMES = {".DS_Store"}
MAX_TEXT_BYTES = 2_000_000

RAW_RESIDUE_NAMES = {
    "audio.mp3",
    "audio.wav",
    "curl.err",
    "debug.log",
    "headers.txt",
    "page.html",
    "parsed.json",
    "raw.html",
    "response.dump",
    "source.html",
    "transcript.tmp",
}

SENSITIVE_PATTERNS = {
    "private key": re.compile(
        rb"-----BEGIN " + rb"[A-Z0-9 ]*" + rb"PRIVATE KEY-----"
    ),
    "provider credential": re.compile(
        rb"\b(?:"
        + rb"sk-"
        + rb"[A-Za-z0-9_-]{20,}|"
        + rb"gh[pousr]_[A-Za-z0-9]{20,}|"
        + rb"github_pat_[A-Za-z0-9_]{20,}|"
        + rb"(?:AKIA|ASIA)[A-Z0-9]{16}|"
        + rb"xox[baprs]-[A-Za-z0-9-]{10,})\b"
    ),
    "jwt": re.compile(
        rb"\b"
        + rb"eyJ"
        + rb"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
    ),
    "bearer credential": re.compile(
        rb"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._~+/-]{12,}"
    ),
    "credential assignment": re.compile(
        rb"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
        rb"session[_-]?key|password|passwd|cookie)\s*[:=]\s*"
        rb"[\"']?[A-Za-z0-9._~+/-]{12,}"
    ),
    "embedded URL credential": re.compile(rb"https?://[^\s/:@]+:[^\s/@]+@"),
}

LOCAL_PATH_PATTERNS = {
    "macOS home path": re.compile(rb"/" + rb"Users/" + rb"[^/\s\"']+"),
    "Linux home path": re.compile(rb"/" + rb"home/" + rb"[^/\s\"']+"),
    "Windows home path": re.compile(
        rb"[A-Za-z]:\\" + rb"Users\\" + rb"[^\\\s\"']+"
    ),
    "macOS volume path": re.compile(rb"/" + rb"Volumes/" + rb"[^\s\"']+"),
}

PII_PATTERNS = {
    "email address": re.compile(
        rb"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
    ),
    "mainland China phone number": re.compile(rb"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "mainland China ID number": re.compile(
        rb"(?<!\d)\d{17}[0-9Xx](?!\d)"
    ),
}

# Lucas-DeepWheel family publication baseline. Product-specific CLI docs,
# release templates, validators, and test filenames must not be required
# for every Skill in the family. Third-party packages may need a tailored baseline.
REQUIRED_PUBLICATION_FILES = (
    ".gitattributes",
    "assets/intro/README.md",
    ".gitignore",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/validate.yml",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "README.zh-CN.md",
    "SECURITY.md",
    "VERSION",
    "docs/INSTALLATION.md",
    "docs/PUBLICATION-CHECKLIST.md",
    "docs/REVIEW-RECORD.md",
    "docs/ROADMAP.md",
    "docs/TEST-RUNS.md",
    "docs/VERSIONING.md",
    "examples/example-prompts.md",
    "scripts/install-local.py",
    "scripts/validate-lucas-deepwheel-skill.py",
    "scripts/validate-version.py",
    "scripts/verify-installed-copy.py",
)

INTRO_ASSET_SUFFIXES = (
    "hero-en.svg",
    "hero-en.png",
    "hero-zh-CN.svg",
    "hero-zh-CN.png",
    "workflow-en.svg",
    "workflow-en.png",
    "workflow-zh-CN.svg",
    "workflow-zh-CN.png",
)

CORE_GROUPS = (
    ("什么时候使用", "使用本 Skill", "使用边界"),
    ("什么时候不要使用", "不使用本 Skill", "不使用"),
    ("标准流程",),
    ("安全边界",),
    ("完成前验收",),
)

POLICY_GROUPS = {
    "new user capability preflight": ("能力体检", "OCR", "PDF", "视频", "音频", "安装"),
    "token budget policy": ("token", "低消耗", "分段", "确认"),
    "independent product entry": ("独立", "入口", "文件夹"),
    "companion Skill routing": ("关联 Skill", "安装", "降级"),
    "interaction and onboarding": ("首次", "下一步", "恢复", "渐进", "用户"),
    "capability claims": ("已支持", "需要工具", "暂不承诺"),
}

HIGH_RISK_ENGLISH_TERMS = (
    "medical", "genetic", "nutrition", "clinical", "diagnosis", "treatment",
    "supplement", "dose", "prescription", "legal", "financial", "investment", "tax",
)
NUMERIC_RISK_ENGLISH_TERMS = (
    "dose", "dosing", "supplement amount", "intake amount", "upper intake level",
)
NUMERIC_RISK_CJK_TERMS = (
    "剂量", "补充量", "摄入量", "耐受最高摄入量",
)

HIGH_RISK_CJK_TERMS = (
    "医疗", "基因", "营养", "临床", "诊断", "治疗", "膳食", "补充剂", "剂量",
    "疾病", "药物", "法律", "法务", "财务", "投资", "税务", "健康数据", "健康报告", "健康建议",
)

RISK_LEVELS = {"low", "medium", "high"}
HIGH_RISK_BOOL_KEYS = (
    "consent_required",
    "human_review_required",
    "source_provenance_required",
    "refusal_rules_required",
)
REQUIRED_HIGH_RISK_BEHAVIOR_CASES = (
    "consent_missing",
    "data_subject_unconfirmed",
    "minimum_input_missing",
    "safety_preflight_incomplete",
    "stop_condition",
    "blocked_output_suppression",
    "source_provenance_invalid",
)


def finding(severity: str, title: str, detail: str) -> dict[str, str]:
    return {"severity": severity, "title": title, "detail": detail}


def safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return "<outside-target>"


def safe_declared_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    return relative


def iter_paths(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        if path.name in SKIP_NAMES:
            continue
        yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def tree_sha256(root: Path) -> str:
    digest = sha256()
    for path in iter_paths(root):
        if path.is_file() and not path.is_symlink():
            digest.update(safe_relative(path, root).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def scan_tree(root: Path) -> tuple[list[dict[str, str]], str]:
    findings: list[dict[str, str]] = []
    text_parts: list[str] = []
    for path in iter_paths(root):
        label = safe_relative(path, root)
        if path.is_symlink():
            findings.append(
                finding("critical", "symbolic link is not allowed", label)
            )
            continue
        if not path.is_file():
            continue
        if path.name.lower() in RAW_RESIDUE_NAMES:
            findings.append(
                finding("critical", "raw capture or debug residue found", label)
            )
        if path.stat().st_size > MAX_TEXT_BYTES:
            findings.append(
                finding("warning", "large file was not content-scanned", label)
            )
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        data = path.read_bytes()
        text_parts.append(data.decode("utf-8", errors="ignore"))
        for category, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(data):
                findings.append(
                    finding("critical", f"{category} shaped value found", label)
                )
        for category, pattern in LOCAL_PATH_PATTERNS.items():
            if pattern.search(data):
                findings.append(
                    finding("warning", f"{category} found", label)
                )
        for category, pattern in PII_PATTERNS.items():
            if pattern.search(data):
                findings.append(
                    finding("warning", f"{category} found", label)
                )
    return findings, "\n".join(text_parts)


def _extract_scalar(frontmatter: str, key: str) -> str:
    """取 YAML 标量值，兼容 双引号 / 单引号 / 折叠(>) / 字面(|) / 无引号 五种写法。"""
    inline = re.search(rf"^{key}:[ \t]*(.*)$", frontmatter, re.M)
    if not inline:
        return ""
    raw = inline.group(1).strip()
    if raw in (">", "|", ">-", "|-", ">+", "|+"):
        # 块标量：收集紧随其后的缩进续行
        lines = frontmatter.splitlines()
        start = next(
            (i for i, ln in enumerate(lines) if re.match(rf"^{key}:", ln)), None
        )
        if start is None:
            return ""
        block: list[str] = []
        for ln in lines[start + 1:]:
            if ln.strip() == "":
                block.append("")
            elif ln[:1].isspace():
                block.append(ln.strip())
            else:
                break
        return " ".join(x for x in block if x).strip()  # 折叠：空格连接
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
        return raw[1:-1].strip()
    return raw


def parse_frontmatter(text: str) -> tuple[str, str] | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    frontmatter = match.group(1)
    # 只数顶层键(行首无缩进)，避免把折叠/字面块的缩进续行误当成键
    keys = [
        line.split(":", 1)[0].strip()
        for line in frontmatter.splitlines()
        if ":" in line and not line[:1].isspace()
    ]
    if keys != ["name", "description"]:
        return "", ""
    name = _extract_scalar(frontmatter, "name")
    description = _extract_scalar(frontmatter, "description")
    return name, description


def has_high_risk_signal(text: str) -> bool:
    lower = text.lower()
    for term in HIGH_RISK_ENGLISH_TERMS:
        if re.search(r"\b" + re.escape(term) + r"\b", lower):
            return True
    return any(term in text for term in HIGH_RISK_CJK_TERMS)


def has_numeric_safety_signal(text: str) -> bool:
    lower = text.lower()
    for term in NUMERIC_RISK_ENGLISH_TERMS:
        if re.search(r"\b" + re.escape(term) + r"\b", lower):
            return True
    return any(term in text for term in NUMERIC_RISK_CJK_TERMS)


def check_risk_profile(
    skill: Path,
    skill_text: str,
    all_text: str,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    high_risk_detected = has_high_risk_signal(all_text)
    profile_path = skill / "agents" / "risk-profile.json"

    if not profile_path.is_file():
        severity = "critical" if high_risk_detected else "note"
        findings.append(
            finding(
                severity,
                "machine-readable risk profile is missing",
                "add agents/risk-profile.json before public release",
            )
        )
        return findings

    try:
        profile = json.loads(read_text(profile_path))
    except (json.JSONDecodeError, OSError):
        findings.append(
            finding("critical", "risk profile is invalid", "agents/risk-profile.json")
        )
        return findings

    if profile.get("schema_version") != 1:
        findings.append(
            finding("critical", "risk profile schema is unsupported", "schema_version must be 1")
        )
    level = profile.get("risk_level")
    if level not in RISK_LEVELS:
        findings.append(
            finding("critical", "risk level is invalid", "use low, medium, or high")
        )
    meta_audit = profile.get("risk_context") == "meta_audit"
    meta_entry = any(term in skill_text.lower() for term in ("audit", "evaluate", "check")) or "审计" in skill_text or "检查" in skill_text
    if high_risk_detected and level != "high" and not (meta_audit and meta_entry):
        findings.append(
            finding("critical", "high-risk domain is under-classified", "risk_level must be high")
        )

    if level == "high":
        domains = profile.get("domains")
        if not isinstance(domains, list) or not domains:
            findings.append(
                finding("critical", "high-risk domains are missing", "declare one or more domains")
            )
        sensitive_data = profile.get("sensitive_data")
        if not isinstance(sensitive_data, list) or not sensitive_data:
            findings.append(
                finding("critical", "high-risk sensitive data classes are missing", "declare sensitive_data")
            )
        for key in HIGH_RISK_BOOL_KEYS:
            if profile.get(key) is not True:
                findings.append(
                    finding("critical", "high-risk control is disabled", key)
                )
        numeric_enabled = profile.get("personalized_numeric_guidance_enabled")
        if numeric_enabled is not None and not isinstance(numeric_enabled, bool):
            findings.append(
                finding(
                    "critical",
                    "numeric guidance enablement flag is invalid",
                    "personalized_numeric_guidance_enabled must be true or false",
                )
            )
        if numeric_enabled is False and not str(profile.get("unreviewed_output_policy", "")).strip():
            findings.append(
                finding(
                    "critical",
                    "disabled numeric guidance lacks an unreviewed output policy",
                    "declare unreviewed_output_policy",
                )
            )
        if profile.get("behavioral_safety_contract_required") is not True:
            findings.append(
                finding(
                    "critical",
                    "high-risk behavioral safety contract is not required",
                    "enable behavioral_safety_contract_required",
                )
            )
        behavior_contract = safe_declared_path(profile.get("behavioral_safety_contract_path"))
        if behavior_contract is None:
            findings.append(
                finding(
                    "critical",
                    "behavioral safety contract path is invalid",
                    "use a safe relative path",
                )
            )
        elif not (skill / behavior_contract).is_file() or (skill / behavior_contract).is_symlink():
            findings.append(
                finding(
                    "critical",
                    "behavioral safety contract file is missing",
                    str(behavior_contract),
                )
            )
        elif not ((skill / behavior_contract).stat().st_mode & 0o100):
            findings.append(
                finding(
                    "critical",
                    "behavioral safety contract is not executable",
                    str(behavior_contract),
                )
            )
        behavior_test = safe_declared_path(profile.get("behavioral_test_path"))
        if behavior_test is None:
            findings.append(
                finding(
                    "critical",
                    "high-risk behavioral test path is invalid",
                    "declare a safe publication-relative test path",
                )
            )
        case_ids = profile.get("behavioral_case_ids")
        if not isinstance(case_ids, list) or any(not isinstance(item, str) for item in case_ids):
            findings.append(
                finding(
                    "critical",
                    "high-risk behavioral case identifiers are invalid",
                    "declare behavioral_case_ids as a string list",
                )
            )
        else:
            missing_cases = [item for item in REQUIRED_HIGH_RISK_BEHAVIOR_CASES if item not in case_ids]
            if missing_cases:
                findings.append(
                    finding(
                        "critical",
                        "high-risk behavior regression coverage is incomplete",
                        ", ".join(missing_cases),
                    )
                )
        if has_numeric_safety_signal(all_text):
            if profile.get("numeric_safety_contract_required") is not True:
                findings.append(
                    finding(
                        "critical",
                        "numeric high-risk guidance lacks a machine safety contract",
                        "enable numeric_safety_contract_required",
                    )
                )
            relative = safe_declared_path(profile.get("numeric_contract_path"))
            if relative is None:
                findings.append(
                    finding("critical", "numeric safety contract path is invalid", "use a safe relative path")
                )
            elif not (skill / relative).is_file() or (skill / relative).is_symlink():
                findings.append(
                    finding("critical", "numeric safety contract file is missing", str(relative))
                )
            elif not ((skill / relative).stat().st_mode & 0o100):
                findings.append(
                    finding("critical", "numeric safety contract is not executable", str(relative))
                )
        for term in ("安全边界", "同意", "来源", "停止", "复核"):
            if term not in skill_text:
                findings.append(
                    finding("critical", "high-risk boundary control is missing", term)
                )
    return findings


def check_skill(skill: Path) -> tuple[list[dict[str, str]], str | None]:
    findings: list[dict[str, str]] = []
    skill_text = ""
    if not skill.is_dir():
        return [
            finding(
                "critical",
                "Skill directory is missing",
                "requested Skill directory does not exist",
            )
        ], None

    scan_findings, all_text = scan_tree(skill)
    findings.extend(scan_findings)

    skill_md = skill / "SKILL.md"
    skill_name: str | None = None
    if not skill_md.is_file():
        findings.append(
            finding("critical", "SKILL.md is missing", "required entrypoint")
        )
    else:
        text = read_text(skill_md)
        skill_text = text
        parsed = parse_frontmatter(text)
        if parsed is None:
            findings.append(
                finding(
                    "critical",
                    "SKILL.md frontmatter is missing",
                    "YAML frontmatter is required",
                )
            )
        elif parsed == ("", ""):
            findings.append(
                finding(
                    "critical",
                    "SKILL.md frontmatter is invalid",
                    "frontmatter must contain only name and description",
                )
            )
        else:
            skill_name, description = parsed
            if skill_name != skill.name:
                findings.append(
                    finding(
                        "critical",
                        "Skill name does not match directory",
                        "frontmatter name must equal the Skill folder name",
                    )
                )
            if not (1 <= len(description) <= 1024):
                findings.append(
                    finding(
                        "critical",
                        "Skill description length is invalid",
                        "description must be 1 to 1024 characters",
                    )
                )
            if "Use when" not in description:
                findings.append(
                    finding(
                        "warning",
                        "description lacks use boundary",
                        "add an explicit Use when clause",
                    )
                )
            if "Do not" not in description and "不要" not in description:
                findings.append(
                    finding(
                        "warning",
                        "description lacks do-not-use boundary",
                        "add an adjacent-task exclusion",
                    )
                )
        for group in CORE_GROUPS:
            if not any(term in text for term in group):
                findings.append(
                    finding(
                        "warning",
                        "SKILL.md may miss a core section",
                        " / ".join(group),
                    )
                )

    references = skill / "references"
    risk_text = skill_text
    if references.is_dir():
        risk_text += "\n" + "\n".join(
            read_text(path)
            for path in sorted(references.rglob("*"))
            if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS
        )
    if not references.is_dir():
        findings.append(
            finding(
                "warning",
                "references folder is missing",
                "complex Skills should use references",
            )
        )
    elif any(path.is_dir() for path in references.rglob("*")):
        findings.append(
            finding(
                "warning",
                "references are nested",
                "keep references one level deep",
            )
        )

    if not (skill / "agents" / "openai.yaml").is_file():
        findings.append(
            finding(
                "warning",
                "agents/openai.yaml is missing",
                "add agent metadata",
            )
        )

    lower_text = all_text.lower()
    for label, terms in POLICY_GROUPS.items():
        missing = [term for term in terms if term.lower() not in lower_text]
        if missing:
            findings.append(
                finding(
                    "warning",
                    f"missing or weak {label}",
                    ", ".join(missing),
                )
            )

    findings.extend(check_risk_profile(skill, skill_text, risk_text))
    return findings, skill_name


def check_publication(
    publication: Path,
    skill: Path,
    skill_name: str | None,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not publication.is_dir():
        return [
            finding(
                "critical",
                "publication directory is missing",
                "requested publication directory does not exist",
            )
        ]

    scan_findings, publication_text = scan_tree(publication)
    findings.extend(scan_findings)

    for relative in REQUIRED_PUBLICATION_FILES:
        if not (publication / relative).is_file():
            findings.append(
                finding("warning", "publication file is missing", relative)
            )

    publication_checklist = publication / "docs" / "PUBLICATION-CHECKLIST.md"
    if publication_checklist.is_file():
        checklist_text = read_text(publication_checklist)
        incomplete_items = re.findall(r"(?m)^\s*-\s*\[\s\]\s+", checklist_text)
        if incomplete_items:
            findings.append(
                finding(
                    "warning",
                    "publication checklist has incomplete items",
                    f"docs/PUBLICATION-CHECKLIST.md: {len(incomplete_items)} incomplete",
                )
            )

    profile_path = skill / "agents" / "risk-profile.json"
    try:
        publication_profile = (
            json.loads(read_text(profile_path)) if profile_path.is_file() else {}
        )
    except (json.JSONDecodeError, OSError):
        publication_profile = {}
    if publication_profile.get("risk_level") == "high":
        behavior_test = safe_declared_path(publication_profile.get("behavioral_test_path"))
        if behavior_test is None:
            findings.append(
                finding(
                    "critical",
                    "high-risk publication behavioral test path is invalid",
                    "declare behavioral_test_path in agents/risk-profile.json",
                )
            )
        elif not (publication / behavior_test).is_file() or (publication / behavior_test).is_symlink():
            findings.append(
                finding(
                    "critical",
                    "high-risk behavior regression test file is missing",
                    str(behavior_test),
                )
            )
        else:
            test_text = read_text(publication / behavior_test)
            declared_cases = publication_profile.get("behavioral_case_ids")
            expected_cases = (
                [item for item in declared_cases if isinstance(item, str)]
                if isinstance(declared_cases, list)
                else list(REQUIRED_HIGH_RISK_BEHAVIOR_CASES)
            )
            missing_markers = [item for item in expected_cases if item not in test_text]
            if missing_markers:
                findings.append(
                    finding(
                        "critical",
                        "high-risk behavior regression tests lack declared cases",
                        ", ".join(missing_markers),
                    )
                )
        _, skill_publication_text = scan_tree(skill)
        numeric_publication = (
            has_numeric_safety_signal(skill_publication_text)
            and publication_profile.get("personalized_numeric_guidance_enabled") is not False
        )
        signoff_severity = "critical" if numeric_publication else "warning"
        signoff = publication / "docs" / "PROFESSIONAL-SIGNOFF.md"
        if not signoff.is_file():
            findings.append(
                finding(
                    signoff_severity,
                    "high-risk professional sign-off is missing",
                    "numeric high-risk publication is blocked without approval"
                    if numeric_publication
                    else "docs/PROFESSIONAL-SIGNOFF.md",
                )
            )
        else:
            signoff_text = read_text(signoff)
            if not re.search(r"(?im)^Status:\s*APPROVED\s*$", signoff_text):
                findings.append(
                    finding(
                        signoff_severity,
                        "high-risk professional sign-off is incomplete",
                        "numeric high-risk publication is blocked until docs/PROFESSIONAL-SIGNOFF.md records Status: APPROVED"
                        if numeric_publication
                        else "docs/PROFESSIONAL-SIGNOFF.md must record Status: APPROVED",
                    )
                )
            else:
                target_match = re.search(
                    r"(?im)^Target Skill SHA256:\s*([0-9a-f]{64})\s*$",
                    signoff_text,
                )
                if target_match is None or target_match.group(1) != tree_sha256(skill):
                    findings.append(
                        finding(
                            signoff_severity,
                            "professional sign-off target does not match current Skill",
                            "numeric high-risk publication is blocked until the approved fingerprint matches"
                            if numeric_publication
                            else "record the current --print-skill-sha256 value",
                        )
                    )

    intro_dir = publication / "assets" / "intro"
    intro_names = (
        [path.name for path in intro_dir.iterdir() if path.is_file()]
        if intro_dir.is_dir()
        else []
    )
    for suffix in INTRO_ASSET_SUFFIXES:
        if not any(name.endswith(suffix) for name in intro_names):
            findings.append(
                finding(
                    "warning",
                    "bilingual GitHub introduction asset is missing",
                    suffix,
                )
            )

    issue_dir = publication / ".github" / "ISSUE_TEMPLATE"
    if not issue_dir.is_dir() or not any(path.is_file() for path in issue_dir.iterdir()):
        findings.append(
            finding(
                "warning",
                "issue template is missing",
                ".github/ISSUE_TEMPLATE",
            )
        )

    for readme_name in ("README.md", "README.zh-CN.md"):
        path = publication / readme_name
        if path.is_file():
            text = read_text(path)
            if "scripts/install-local.py" not in text:
                findings.append(
                    finding(
                        "warning",
                        "README does not expose safe installer",
                        readme_name,
                    )
                )
            if "docs/INSTALLATION.md" not in text:
                findings.append(
                    finding(
                        "warning",
                        "README does not link installation guide",
                        readme_name,
                    )
                )
            language_suffixes = (
                ("hero-en.png", "workflow-en.png")
                if readme_name == "README.md"
                else ("hero-zh-CN.png", "workflow-zh-CN.png")
            )
            for suffix in language_suffixes:
                if "assets/intro/" not in text or suffix not in text:
                    findings.append(
                        finding(
                            "warning",
                            "README does not route to its language-specific introduction asset",
                            readme_name + ": " + suffix,
                        )
                    )

    for term in ("Quick Start", "Installation", "Security", "Contributing", "License"):
        if term.lower() not in publication_text.lower():
            findings.append(
                finding(
                    "note",
                    "publication may miss a GitHub usability term",
                    term,
                )
            )

    if skill_name:
        packaged = publication / "skills" / skill_name
        if not packaged.is_dir():
            findings.append(
                finding(
                    "warning",
                    "packaged Skill is missing",
                    f"skills/{skill_name}",
                )
            )
        elif packaged.resolve() != skill.resolve():
            left = {
                safe_relative(path, skill): path.read_bytes()
                for path in iter_paths(skill)
                if path.is_file() and not path.is_symlink()
            }
            right = {
                safe_relative(path, packaged): path.read_bytes()
                for path in iter_paths(packaged)
                if path.is_file() and not path.is_symlink()
            }
            if left != right:
                findings.append(
                    finding(
                        "warning",
                        "provided and packaged Skill contents differ",
                        f"skills/{skill_name}",
                    )
                )

    return findings


def deduplicate(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, str]] = []
    for item in findings:
        key = (item["severity"], item["title"], item["detail"])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def summarize(findings: list[dict[str, str]]) -> dict[str, int | str]:
    critical = sum(item["severity"] == "critical" for item in findings)
    warning = sum(item["severity"] == "warning" for item in findings)
    note = sum(item["severity"] == "note" for item in findings)
    if critical:
        verdict = "BLOCK"
    elif warning:
        verdict = "CONCERNS"
    else:
        verdict = "CLEAN"
    return {
        "verdict": verdict,
        "critical": critical,
        "warning": warning,
        "note": note,
    }


def exit_code(summary: dict[str, int | str]) -> int:
    if summary["verdict"] == "BLOCK":
        return 2
    if summary["verdict"] == "CONCERNS":
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit an Agent Skill and optional publication package."
    )
    parser.add_argument("skill_dir")
    parser.add_argument("--publication-dir")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--print-skill-sha256", action="store_true")
    args = parser.parse_args()

    skill = Path(args.skill_dir).expanduser().resolve()
    if args.print_skill_sha256:
        if not skill.is_dir():
            print("BLOCK: Skill directory is missing")
            return 2
        print(tree_sha256(skill))
        return 0
    findings, skill_name = check_skill(skill)
    if args.publication_dir is not None:
        publication = Path(args.publication_dir).expanduser().resolve()
        findings.extend(check_publication(publication, skill, skill_name))

    findings = deduplicate(findings)
    summary = summarize(findings)
    payload = {"summary": summary, "findings": findings}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Skill Quality Gate: {summary['verdict']}")
        print(
            f"critical={summary['critical']} "
            f"warning={summary['warning']} note={summary['note']}"
        )
        icons = {"critical": "🔴", "warning": "🟡", "note": "🔵"}
        for item in findings:
            print(
                f"{icons[item['severity']]} {item['severity'].upper()}: "
                f"{item['title']} — {item['detail']}"
            )

    return exit_code(summary)


if __name__ == "__main__":
    raise SystemExit(main())
