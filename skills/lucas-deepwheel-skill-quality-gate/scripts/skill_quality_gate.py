#!/usr/bin/env python3
"""Audit an Agent Skill and optional publication package without exposing matched values."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
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
    ("什么时候使用", "使用本 Skill", "使用边界", "适用边界", "Use when"),
    ("什么时候不要使用", "不使用本 Skill", "不使用", "什么时候不用", "Do not use"),
    ("标准流程", "生成流程", "工作流程", "使用流程", "how it works"),
    ("安全边界", "safety boundary"),
    ("完成前验收", "交付前自检", "自检清单", "交付前", "pre-flight", "pre-delivery"),
)

POLICY_GROUPS = {
    "new user capability preflight": ("能力体检", "OCR", "PDF", "视频", "音频", "安装"),
    "token budget policy": ("token", "低消耗", "分段", "确认"),
    "independent product entry": ("独立", "入口", "文件夹"),
    "companion Skill routing": ("关联 Skill", "安装", "降级"),
    "interaction and onboarding": ("首次", "下一步", "恢复", "渐进", "用户"),
    "capability claims": ("已支持", "需要工具", "暂不承诺"),
}

# O2:工具类 Skill 才需要的策略检查;自包含域 Skill(risk-profile skill_type=domain)对这些 N/A,降为 NOTE
TOOL_ONLY_POLICY = frozenset({
    "new user capability preflight",
    "token budget policy",
    "companion Skill routing",
    "independent product entry",
})

# ③ 命名规则:环境变量配置期望前缀(如 "lucas-deepwheel-")。
# 配了 → 核验目标 Skill 名是否遵此前缀(不遵=WARNING);没配 → 提醒建立统一命名规则(NOTE)。
NAME_PREFIX_ENV = "SKILL_QUALITY_GATE_NAME_PREFIX"

# Token 量级估算 + 介绍/引导硬核验的常量。量级值只是数量级参考,非精确分词。
CJK_RANGES = ((0x4E00,0x9FFF),(0x3400,0x4DBF),(0xF900,0xFAFF),(0x3000,0x303F),(0xFF00,0xFFEF))
TOKEN_ENV = {
    "cjk_coef": ("SKILL_QUALITY_GATE_TOKEN_CJK_COEF", 1.0),
    "other_coef": ("SKILL_QUALITY_GATE_TOKEN_OTHER_COEF", 0.25),
    "entry": ("SKILL_QUALITY_GATE_TOKEN_ENTRY", 8000),
    "full": ("SKILL_QUALITY_GATE_TOKEN_FULL", 40000),
    "heavy_file": ("SKILL_QUALITY_GATE_TOKEN_HEAVYFILE", 30000),
}
QUICKSTART_HEADINGS = ("quick start","getting started","快速上手","快速开始","上手","最小示例","首次使用","试一试")
PROGRESSIVE_WORDING = re.compile(r"按需\s*(读|加载)|需要时.{0,6}读|如需.{0,10}读|先读.{0,20}(速览|索引|框架|导航).{0,10}再|阅读顺序|阅读协议|渐进披露|read\s.{0,20}as\sneeded|load[\s-]?on[\s-]?demand|progressive\sdisclosure|see\sreferences", re.IGNORECASE)
PROGRESSIVE_POINTER = re.compile(r"(references|assets|scripts|examples)/[^\s)\"'`]+\.(md|txt|json|ya?ml|py|sh|toml)", re.IGNORECASE)
PROGRESSIVE_NATURAL = re.compile(r"详见|参见|见\s*(references|assets|附录|章节)|完整规范|完整清单|full\sspec|see\sthe\s.{0,20}(guide|spec|reference)", re.IGNORECASE)
RUNNABLE_FENCE = re.compile(r"```(bash|sh|shell|console)\b", re.IGNORECASE)
RUNNABLE_LINE = re.compile(r"^\s*(python3?|npx|node|bash|sh|pip3?|\./|/?scripts/)\b", re.MULTILINE)

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
PUBLIC_SURFACE_CORE_FILES = {
    "README.md",
    "README.zh-CN.md",
    "CHANGELOG.md",
    "docs/INSTALLATION.md",
    "examples/example-prompts.md",
}

# ── 视角版 A（audience 视角）+ B（--stage）+ C（--report / 修复优先级）───────
# audience 是「视角/尺子」轴，不是松紧轴：只切换「从谁的尺子审、审哪些关注点」，
# 作用面仅限下面 9 个门面 check_id（FACADE_SET）；通用/结构/安全/critical/描述
# 在三视角下逐字一致，audience 一律不碰。
AUDIENCE_VALUES = {"public", "private"}

# 9 个对外门面 check_id（第三方门面/体验维度）。large/heavy/entry 刻意不在此集，
# 它们是作者自用也在意的 token/结构维度，归通用/结构轴，只受 skill_type 软化。
FACADE_SET = frozenset(
    {
        "onboarding.first_success",
        "pub.usability_term",
        "pub.readme_installer",
        "pub.readme_install_guide",
        "pub.readme_intro_route",
        "pub.intro_asset",
        "pub.surface_stale",
        "pub.issue_template",
        "pub.highstar_addon",
    }
)
# 唯一允许 note→warning 的门面集（Lucas 拍板 = 保留 LIFT）。public 视角对这两项
# 解除按 skill_type 的私用软化、还原门面固有 severity=warning。绝不碰 critical。
FACADE_LIFT_SET = frozenset({"onboarding.first_success", "pub.usability_term"})

# 车道（独立于 severity 的第二维标签，绝不塞进 severity 字典）。
LANE_ONBOARDING = "上手"
LANE_PUBLISH = "发布"
LANE_HIGHSTAR = "星标"
LANE_QUALITY = "质量"
_SEVERITY_RANK = {"critical": 0, "warning": 1, "note": 2}
_LANE_RANK = {LANE_ONBOARDING: 0, LANE_PUBLISH: 1, LANE_HIGHSTAR: 2, LANE_QUALITY: 3}

# --stage start 专用字形（3 键、与 main 的 icons 互不干扰，绝不产生第 4 种）。
START_GLYPHS = {"critical": "◆地基", "warning": "▲成型", "note": "·加分"}

# verdict → 一句话建议（体检卡用）。
VERDICT_ADVICE = {
    "CLEAN": "可继续",
    "CONCERNS": "暂缓定稿",
    "BLOCK": "阻断发布",
    "DRAFTING": "引导中（非发布裁决）",
}

# 高星加分门面标题（public-only note，只提示不改判定）。
HIGHSTAR_TERMS = ("Troubleshooting", "Roadmap")

# 诚实/措辞红线：以下字面串一律不得出现在任何输出（横幅/NOTE/report/findings）。
FORBIDDEN_COPY_TERMS = (
    "从严",
    "放宽",
    "更严",
    "更松",
    "放松",
    "模拟",
    "首次上手实测",
    "smoke test",
)

# 单一真源：脚手架全景引用的 check_id 必须 ⊆ 此集（反漂移）。
ALL_CHECK_IDS = frozenset(
    {
        "onboarding.first_success",
        "onboarding.large_no_progressive",
        "onboarding.heavy_file",
        "onboarding.entry_heavy",
        "desc.use_when",
        "desc.do_not",
        "core.section",
        "structure.references",
        "meta.agents",
        "meta.naming",
        "security.scan",
        "risk.high_risk_control",
        "pub.usability_term",
        "pub.readme_installer",
        "pub.readme_install_guide",
        "pub.readme_intro_route",
        "pub.intro_asset",
        "pub.surface_stale",
        "pub.issue_template",
        "pub.highstar_addon",
    }
)

# 「好 Skill 要件全景」目标态清单（派生自 ALL_CHECK_IDS 单一真源）。
# 每个 family = (家族名, (check_id, ...), 是否对外门面家族)。
SCAFFOLD_FAMILIES = (
    ("入口与结构", ("core.section", "structure.references", "meta.agents"), False),
    ("描述与自动触发", ("desc.use_when", "desc.do_not"), False),
    ("上手路径", ("onboarding.first_success",), True),
    (
        "Token 与结构经济",
        ("onboarding.large_no_progressive", "onboarding.heavy_file", "onboarding.entry_heavy"),
        False,
    ),
    ("安全与合规", ("security.scan", "risk.high_risk_control"), False),
    ("命名规则", ("meta.naming",), False),
    (
        "对外发布门面",
        (
            "pub.usability_term",
            "pub.readme_installer",
            "pub.readme_install_guide",
            "pub.readme_intro_route",
            "pub.intro_asset",
            "pub.surface_stale",
            "pub.issue_template",
        ),
        True,
    ),
    ("高星加分", ("pub.highstar_addon",), True),
)

# default（audience 未声明）文本页脚：中性视角措辞（RT2#1）——default 已经审门面，
# 绝不说「不含门面/未审门面」。
DEFAULT_AUDIENCE_FOOTER = (
    "视角未声明；已按通用检查 + 门面（按类型自然严重度）审。"
    "要以对外门面视角审加 --audience public；以自用视角审加 --audience private。"
)


def finding(
    severity: str, title: str, detail: str, check_id: str = ""
) -> dict[str, str]:
    item = {"severity": severity, "title": title, "detail": detail}
    if check_id:
        item["_check_id"] = check_id
    return item


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


def listed_files_sha256(root: Path, relatives: list[str]) -> str | None:
    digest = sha256()
    for value in sorted(relatives):
        relative = safe_declared_path(value)
        if relative is None:
            return None
        path = root / relative
        if not path.is_file() or path.is_symlink():
            return None
        digest.update(str(relative).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def check_public_surface_review(
    publication: Path,
    skill: Path,
    skill_name: str | None,
) -> list[dict[str, str]]:
    path = publication / "docs" / "PUBLIC-SURFACE-REVIEW.json"
    if not path.is_file() or path.is_symlink():
        return [
            finding(
                "warning",
                "VISUAL ASSET STALE",
                "docs/PUBLIC-SURFACE-REVIEW.json is missing",
                check_id="pub.surface_stale",
            )
        ]
    try:
        manifest = json.loads(read_text(path))
    except (json.JSONDecodeError, OSError):
        return [
            finding(
                "warning",
                "VISUAL ASSET STALE",
                "public-surface review manifest is invalid",
                check_id="pub.surface_stale",
            )
        ]

    problems: list[str] = []
    if manifest.get("schema_version") != 1:
        problems.append("schema_version")
    if skill_name and manifest.get("skill_name") != skill_name:
        problems.append("skill_name")
    capability_change = manifest.get("capability_change")
    decision = manifest.get("decision")
    if capability_change not in {"user_visible", "internal_only"}:
        problems.append("capability_change")
    if decision not in {"UPDATED", "NO_CHANGE_REQUIRED"}:
        problems.append("decision")
    if capability_change == "user_visible" and decision != "UPDATED":
        problems.append("user_visible change must update public surfaces")
    if not isinstance(manifest.get("reason"), str) or len(manifest.get("reason", "").strip()) < 20:
        problems.append("reason")
    if manifest.get("reviewed_skill_sha256") != tree_sha256(skill):
        problems.append("capability fingerprint changed")

    public_files = manifest.get("public_files")
    if not isinstance(public_files, list) or any(not isinstance(item, str) for item in public_files):
        problems.append("public_files")
        public_files = []
    else:
        inventory = set(public_files)
        if not PUBLIC_SURFACE_CORE_FILES.issubset(inventory):
            problems.append("public surface inventory incomplete")
        for suffix in INTRO_ASSET_SUFFIXES:
            if not any(item.startswith("assets/intro/") and item.endswith(suffix) for item in public_files):
                problems.append("bilingual introduction inventory incomplete")
                break
    public_digest = listed_files_sha256(publication, public_files)
    if public_digest is None or manifest.get("public_surface_sha256") != public_digest:
        problems.append("public surface fingerprint changed")

    if decision == "UPDATED":
        updated = manifest.get("updated_assets")
        if not isinstance(updated, list) or any(not isinstance(item, str) for item in updated):
            problems.append("updated_assets")
        else:
            suffixes = ("-en.svg", "-en.png", "-zh-CN.svg", "-zh-CN.png")
            for suffix in suffixes:
                if not any(item.startswith("assets/intro/") and item.endswith(suffix) for item in updated):
                    problems.append("bilingual editable/rendered asset update incomplete")
                    break

    if not problems:
        return []
    return [
        finding(
            "warning",
            "VISUAL ASSET STALE",
            "; ".join(dict.fromkeys(problems)),
            check_id="pub.surface_stale",
        )
    ]


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


def _token_config() -> dict:
    cfg = {}
    for key, (env, default) in TOKEN_ENV.items():
        raw = os.environ.get(env, "").strip()
        if raw:
            try:
                cfg[key] = float(raw) if "coef" in key else int(float(raw)); continue
            except ValueError:
                pass
        cfg[key] = default
    return cfg


def count_cjk_chars(text: str) -> int:
    total = 0
    for ch in text:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in CJK_RANGES):
            total += 1
    return total


def estimate_tokens(text: str, cjk_coef: float = 1.0, other_coef: float = 0.25) -> int:
    cjk = count_cjk_chars(text)
    other = len(text) - cjk
    return math.ceil(cjk * cjk_coef + other * other_coef)


def _tok_k(n) -> str:
    if n is None:
        return "N/A"
    return f"{n/1000:.1f}K" if n >= 1000 else str(n)


def has_runnable_command(skill_text: str) -> bool:
    return bool(RUNNABLE_FENCE.search(skill_text) or RUNNABLE_LINE.search(skill_text))


def has_quickstart_section(skill_text: str) -> bool:
    for line in skill_text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            low = s.lstrip("#").strip().lower()
            if any(h in low for h in QUICKSTART_HEADINGS):
                return True
    return False


def has_progressive_disclosure(skill_text: str) -> bool:
    return bool(
        PROGRESSIVE_WORDING.search(skill_text)
        or PROGRESSIVE_POINTER.search(skill_text)
        or PROGRESSIVE_NATURAL.search(skill_text)
    )


def collect_layer_token_stats(skill: Path) -> dict:
    cfg = _token_config()
    cc, oc = cfg["cjk_coef"], cfg["other_coef"]

    def est_file(path: Path) -> int:
        try:
            if path.stat().st_size > MAX_TEXT_BYTES:
                return math.ceil(path.stat().st_size / 3.5)
            return estimate_tokens(read_text(path), cc, oc)
        except OSError:
            return 0

    entry = references_total = assets_text_total = all_text_full = 0
    ref_singles = []
    heaviest = []
    byte_estimated = False
    skill_md = skill / "SKILL.md"
    if skill_md.is_file():
        entry = est_file(skill_md)
    for path in iter_paths(skill):
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        rel = safe_relative(path, skill)
        tok = est_file(path)
        try:
            if path.stat().st_size > MAX_TEXT_BYTES:
                byte_estimated = True
        except OSError:
            pass
        all_text_full += tok
        parts = Path(rel).parts
        top = parts[0] if parts else ""
        if top == "references":
            references_total += tok
            ref_singles.append(tok)
        elif top == "assets":
            assets_text_total += tok
        if top in ("references", "assets"):
            heaviest.append((rel, tok))
    agent_facing_full = entry + references_total + assets_text_total
    ref_singles.sort()
    ref_median = ref_singles[len(ref_singles) // 2] if ref_singles else None
    typical = (entry + 2 * ref_median) if ref_median is not None else None
    heaviest.sort(key=lambda x: x[1], reverse=True)
    return {
        "entry": entry,
        "references_total": references_total,
        "assets_text_total": assets_text_total,
        "agent_facing_full": agent_facing_full,
        "all_text_full": all_text_full,
        "references_median_single": ref_median,
        "typical_task_estimate": typical,
        "heaviest": heaviest,
        "byte_estimated": byte_estimated,
        "thresholds": {"entry": cfg["entry"], "full": cfg["full"], "heavy_file": cfg["heavy_file"]},
    }


def check_onboarding_and_token(
    skill: Path,
    skill_text: str,
    skill_type: str,
    examples_present: bool,
    publication_examples_present: bool,
) -> tuple[list[dict[str, str]], dict]:
    findings: list[dict[str, str]] = []
    layers = collect_layer_token_stats(skill)
    cfg = layers["thresholds"]
    has_guidance = has_progressive_disclosure(skill_text)
    layers["has_progressive_disclosure"] = has_guidance
    # 1. first-success（傻瓜引导核心）
    first_success = (
        has_runnable_command(skill_text)
        or has_quickstart_section(skill_text)
        or examples_present
        or publication_examples_present
    )
    if not first_success:
        sev = "warning" if skill_type in ("tool", "meta") else "note"
        findings.append(
            finding(
                sev,
                "first-success path missing",
                "add a runnable command (```bash), a quickstart section, or a "
                "non-empty examples/ so a new user can succeed on first run",
                check_id="onboarding.first_success",
            )
        )
    # 2. 大而无引导（合并 token 消耗结构）
    big = layers["agent_facing_full"] > cfg["full"]
    if big and not has_guidance:
        sev = "note" if skill_type == "domain" else "warning"
        findings.append(
            finding(
                sev,
                "large skill without progressive disclosure",
                f"agent-facing text is ~{_tok_k(layers['agent_facing_full'])} tokens but "
                "SKILL.md shows no on-demand/layered-read guidance; add a references index "
                "or 'read as needed' pointers (estimated, not a precise tokenizer)",
                check_id="onboarding.large_no_progressive",
            )
        )
        layers["structure_verdict"] = "unhealthy"
    else:
        layers["structure_verdict"] = "healthy" if big else "small"
    # 3. 重文件未引导（预读地雷）
    for rel, tok in layers["heaviest"]:
        if tok > cfg["heavy_file"] and Path(rel).name not in skill_text:
            sev = "note" if skill_type == "domain" else "warning"
            findings.append(
                finding(
                    sev,
                    "heavy file not guided",
                    f"{rel} is ~{_tok_k(tok)} tokens and is not named in SKILL.md; "
                    "point to it for on-demand reading or split it",
                    check_id="onboarding.heavy_file",
                )
            )
    # 4. entry 过重（一律 note）
    if layers["entry"] > cfg["entry"]:
        findings.append(
            finding(
                "note",
                "entry SKILL.md is heavy",
                f"SKILL.md is ~{_tok_k(layers['entry'])} tokens (always pre-read); "
                "consider moving detail into references",
                check_id="onboarding.entry_heavy",
            )
        )
    return findings, layers


def render_token_table(layers: dict) -> list[str]:
    def f(n):
        return "N/A" if n is None else f"~{_tok_k(n)}"

    lines = [
        "Token consumption magnitude (estimated, not a precise tokenizer):",
        f"  entry SKILL.md     {f(layers['entry'])}",
        f"  references total   {f(layers['references_total'])}",
        f"  assets text total  {f(layers['assets_text_total'])}",
        f"  agent-facing full  {f(layers['agent_facing_full'])}",
        f"  all text full      {f(layers['all_text_full'])}",
        f"  typical task       {f(layers.get('typical_task_estimate'))} (entry + on-demand 1-2 refs)",
        f"  progressive guidance: {'detected' if layers.get('has_progressive_disclosure') else 'not detected'}",
        f"  structure: {layers.get('structure_verdict','small')}",
    ]
    if layers.get("byte_estimated"):
        lines.append("  (some files > 2MB estimated by byte magnitude)")
    return lines


def check_skill(
    skill: Path,
    publication_provided: bool = False,
    publication_examples_present: bool = False,
) -> tuple[list[dict[str, str]], str | None, dict]:
    findings: list[dict[str, str]] = []
    skill_text = ""
    if not skill.is_dir():
        return [
            finding(
                "critical",
                "Skill directory is missing",
                "requested Skill directory does not exist",
            )
        ], None, {}

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
            # ③ 命名规则:配了前缀 → 核验遵守;没配 → 提醒建立统一命名规则
            name_prefix = os.environ.get(NAME_PREFIX_ENV, "").strip()
            if name_prefix:
                if not skill_name.startswith(name_prefix):
                    findings.append(
                        finding(
                            "warning",
                            "Skill name does not follow the configured naming convention",
                            f"expected name to start with {name_prefix!r} "
                            f"(configured via {NAME_PREFIX_ENV})",
                        )
                    )
            else:
                findings.append(
                    finding(
                        "note",
                        "no naming convention configured",
                        "establish ONE unified naming rule for your Skills "
                        f"(e.g. <org>-<domain>-<purpose>); set {NAME_PREFIX_ENV} "
                        "to enforce and verify your own rule",
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
                        check_id="desc.use_when",
                    )
                )
            if "Do not" not in description and "不要" not in description:
                findings.append(
                    finding(
                        "warning",
                        "description lacks do-not-use boundary",
                        "add an adjacent-task exclusion",
                        check_id="desc.do_not",
                    )
                )
        for group in CORE_GROUPS:
            if not any(term in text for term in group):
                findings.append(
                    finding(
                        "warning",
                        "SKILL.md may miss a core section",
                        " / ".join(group),
                        check_id="core.section",
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

    # O2:读 skill_type;自包含域 Skill 对工具类策略检查(OCR/token/companion/独立入口)N/A,降为 NOTE
    skill_type = ""
    _rp = skill / "agents" / "risk-profile.json"
    if _rp.is_file():
        try:
            skill_type = str(json.loads(read_text(_rp)).get("skill_type", "")).lower()
        except (json.JSONDecodeError, OSError):
            skill_type = ""

    lower_text = all_text.lower()
    for label, terms in POLICY_GROUPS.items():
        missing = [term for term in terms if term.lower() not in lower_text]
        if missing:
            severity = (
                "note"
                if skill_type == "domain" and label in TOOL_ONLY_POLICY
                else "warning"
            )
            findings.append(
                finding(
                    severity,
                    f"missing or weak {label}",
                    ", ".join(missing),
                )
            )

    findings.extend(check_risk_profile(skill, skill_text, risk_text))

    examples_dir = skill / "examples"
    examples_present = examples_dir.is_dir() and any(examples_dir.iterdir())
    onboarding_findings, token_layers = check_onboarding_and_token(
        skill, skill_text, skill_type, examples_present, publication_examples_present
    )
    findings.extend(onboarding_findings)
    return findings, skill_name, token_layers


def check_publication(
    publication: Path,
    skill: Path,
    skill_name: str | None,
    audience_public: bool = False,
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
    findings.extend(check_public_surface_review(publication, skill, skill_name))

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
                    check_id="pub.intro_asset",
                )
            )

    issue_dir = publication / ".github" / "ISSUE_TEMPLATE"
    if not issue_dir.is_dir() or not any(path.is_file() for path in issue_dir.iterdir()):
        findings.append(
            finding(
                "warning",
                "issue template is missing",
                ".github/ISSUE_TEMPLATE",
                check_id="pub.issue_template",
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
                        check_id="pub.readme_installer",
                    )
                )
            if "docs/INSTALLATION.md" not in text:
                findings.append(
                    finding(
                        "warning",
                        "README does not link installation guide",
                        readme_name,
                        check_id="pub.readme_install_guide",
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
                            check_id="pub.readme_intro_route",
                        )
                    )

    for term in ("Quick Start", "Installation", "Security", "Contributing", "License"):
        if term.lower() not in publication_text.lower():
            findings.append(
                finding(
                    "note",
                    "publication may miss a GitHub usability term",
                    term,
                    check_id="pub.usability_term",
                )
            )

    # public-only 加分 NOTE：仅当对外视角生效（effective_public）时门控生成。
    # default/private-无 pubdir 下 audience_public=False → 根本不生成（护 default 恒等）。
    if audience_public:
        missing_highstar = [
            term
            for term in HIGHSTAR_TERMS
            if term.lower() not in publication_text.lower()
        ]
        if missing_highstar:
            findings.append(
                finding(
                    "note",
                    "pub.highstar_addon",
                    "缺高星常见门面标题："
                    + ", ".join(missing_highstar)
                    + "（Troubleshooting/Roadmap 让陌生第三方更好上手；note 级不改判定）",
                    check_id="pub.highstar_addon",
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


def summarize(
    findings: list[dict[str, str]], stage: str = "final"
) -> dict[str, int | str]:
    critical = sum(item["severity"] == "critical" for item in findings)
    warning = sum(item["severity"] == "warning" for item in findings)
    note = sum(item["severity"] == "note" for item in findings)
    if stage == "start":
        # 引导模式恒 DRAFTING（绝不复用 CLEAN），无论有多少 critical/warning。
        verdict = "DRAFTING"
    elif critical:
        verdict = "BLOCK"
    elif warning:
        verdict = "CONCERNS"
    else:
        verdict = "CLEAN"
    summary: dict[str, int | str] = {
        "verdict": verdict,
        "critical": critical,
        "warning": warning,
        "note": note,
    }
    # 只有 start 追加 stage 键；final 不加 → default 的 summary 与今天逐字一致。
    if stage == "start":
        summary["stage"] = stage
    return summary


def exit_code(summary: dict[str, int | str]) -> int:
    if summary["verdict"] == "BLOCK":
        return 2
    if summary["verdict"] == "CONCERNS":
        return 1
    return 0  # CLEAN 与 DRAFTING 同为 0（DRAFTING 只出现在 --stage start）


def read_declared_audience(skill: Path) -> str | None:
    """读 agents/risk-profile.json 顶层 audience；仅当 ∈{public,private} 才返回。

    缺失/非法/读失败一律 None（永不抛异常）。
    """
    path = skill / "agents" / "risk-profile.json"
    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = json.loads(read_text(path)).get("audience")
    except (json.JSONDecodeError, OSError):
        return None
    return value if value in AUDIENCE_VALUES else None


def resolve_audience(
    cli_audience: str | None, profile_audience: str | None
) -> tuple[str | None, str]:
    """优先级 CLI > risk-profile > None，返回 (mode, source)。任一非法→(None,'default')。"""
    if cli_audience in AUDIENCE_VALUES:
        return cli_audience, "cli"
    if profile_audience in AUDIENCE_VALUES:
        return profile_audience, "risk-profile"
    return None, "default"


def apply_audience_perspective(
    findings: list[dict[str, str]],
    mode: str | None,
    effective_public: bool,
    publication_provided: bool,
) -> None:
    """视角版核心（原地改 findings）。仅在 stage=='final' 调用（RT1#2）。

    mode is None → 直接 return（default 对 findings 零改动，护恒等，RT1#1）。
    effective_public → LIFT：FACADE_LIFT_SET 里的 note→warning（首行跳过 critical）。
    else（private 且无 pubdir）→ SUPPRESS：删除 FACADE_SET 里的非 critical 项 + 汇总 NOTE。
    绝不产生 info、绝不 warning→note、绝不碰 critical。
    """
    if mode is None:
        return
    if effective_public:
        for item in findings:
            if item["severity"] == "critical":
                continue  # critical 全模式免疫（belt 1）
            if item.get("_check_id", "") in FACADE_LIFT_SET and item["severity"] == "note":
                item["severity"] = "warning"  # 解除私用软化、还原门面固有 severity
        if mode == "public" and not publication_provided:
            findings.append(
                finding(
                    "note",
                    "audience.publication_unevaluated",
                    "对外门面项未评估；发布前补 --publication-dir 一并按公开门面清单静态核验发布门面",
                    check_id="audience.publication_unevaluated",
                )
            )
        elif mode == "private":  # 即 private + publication_provided（publishing=strict）
            findings.append(
                finding(
                    "note",
                    "audience.private_publishing_conflict",
                    "视角=自用但检测到发布包；发布=对外，已按对外门面视角静态核验"
                    "（publishing=strict，堵死发布放水）。确为自用勿打发布包；要发布改 --audience public",
                    check_id="audience.private_publishing_conflict",
                )
            )
    else:
        # private 且无 pubdir → 把对外门面整组移出审计范围（SUPPRESS，绝不降 severity）。
        findings[:] = [
            item
            for item in findings
            if not (item.get("_check_id", "") in FACADE_SET and item["severity"] != "critical")
        ]
        findings.append(
            finding(
                "note",
                "audience.facade_unaudited",
                "自用视角：上手路径（first-success）已移出范围"
                "（给陌生第三方看，自用场景不相关，非降级而是移出审计）；"
                "README 介绍 / 双语资产 / 安全安装入口 / GitHub 可用性 / 门面指纹等对外门面"
                "需 --publication-dir 才审，本次未评估。要公开发布请用 --audience public 并加 --publication-dir",
                check_id="audience.facade_unaudited",
            )
        )


def audience_notice(
    mode: str | None,
    source: str,
    publication_provided: bool,
    effective_public: bool,
) -> dict:
    """常驻 audience 块（进 payload.audience，CI 可读）。视角措辞，无严/松词。"""
    if mode is None:
        return {
            "mode": None,
            "source": source,
            "switch_hint": "以对外门面视角审加 --audience public；以自用视角审加 --audience private",
        }
    if mode == "public":
        lens = (
            "以对外发布、陌生第三方使用者为尺子；按公开门面清单静态核验："
            "介绍是否讲清价值、陌生人能否上手、双语与门面是否完整、GitHub 可用性"
        )
        scope = "对外门面纳入审计并提为主线；通用/结构/安全/描述照审、audience 不碰"
    else:
        lens = (
            "以作者本人自用为尺子；审结构、功能与你在意的正确性和安全；"
            "不审吸引陌生人的对外门面（未审项见汇总 NOTE）"
        )
        scope = "对外门面移出审计范围；通用/结构/安全/描述照审、全强度"
    return {
        "mode": mode,
        "source": source,
        "lens": lens,
        "scope": scope,
        "switch_hint": "换视角：--audience public（对外门面）/ --audience private（自用）",
    }


def classify_lane(check_id: str) -> str:
    """按 check_id 归车道（第二维标签，独立于 severity）。"""
    if check_id == "onboarding.first_success":
        return LANE_ONBOARDING
    if check_id == "pub.highstar_addon":
        return LANE_HIGHSTAR
    if check_id.startswith("pub."):
        return LANE_PUBLISH
    return LANE_QUALITY  # catch-all：结构/描述/安全/无 check_id 一律不吞


def build_remediation_plan(findings: list[dict[str, str]]) -> list[dict]:
    """②修复优先级：按 (severity, lane, 原序 index) 稳定排序。在 pop _check_id 之前构建。"""
    entries = []
    for index, item in enumerate(findings):
        check_id = item.get("_check_id", "")
        lane = classify_lane(check_id)
        entries.append(
            {
                "index": index,
                "check_id": check_id,
                "lane": lane,
                "severity": item["severity"],
                "title": item["title"],
            }
        )
    entries.sort(
        key=lambda e: (
            _SEVERITY_RANK.get(e["severity"], 9),
            _LANE_RANK.get(e["lane"], 9),
            e["index"],
        )
    )
    return entries


def render_audience_banner(notice: dict) -> list[str]:
    """终端顶部 audience 块（视角措辞，无绝对路径、无严/松词）。"""
    if notice.get("mode") is None:
        return []  # default 走文本页脚，不打横幅
    lines = [f"审计视角：{notice['mode']}"]
    source_line = f"  来源：{notice.get('source', 'default')}"
    if notice.get("overrides"):
        source_line += f"（cli overrides {notice['overrides']}）"
    lines.append(source_line)
    if notice.get("lens"):
        lines.append(f"  尺子：{notice['lens']}")
    if notice.get("scope"):
        lines.append(f"  审哪些：{notice['scope']}")
    if notice.get("switch_hint"):
        lines.append(f"  {notice['switch_hint']}")
    return lines


def render_remediation(
    plan: list[dict], findings: list[dict[str, str]], lane_by_index: dict[int, str]
) -> list[str]:
    """findings 后打印建议修复顺序 + 拎出排头「先修这条」。findings 保持原序不重排。"""
    if not findings:
        return []
    lines = ["", "建议修复顺序（按 严重度 → 车道 → 原序）："]
    for rank, entry in enumerate(plan, start=1):
        lane = lane_by_index.get(entry["index"], LANE_QUALITY)
        lines.append(
            f"  {rank}. [{entry['severity'].upper()}·{lane}] {entry['title']}"
        )
    if plan:
        head = plan[0]
        head_lane = lane_by_index.get(head["index"], LANE_QUALITY)
        lines.append(
            f"先修这条：[{head['severity'].upper()}·{head_lane}] {head['title']}"
        )
    return lines


def render_scaffold(
    findings: list[dict[str, str]], token_layers: dict, audience_mode: str | None
) -> list[str]:
    """--stage start：好 Skill 要件全景（目标态），START_GLYPHS 三键、恒 exit 0。"""
    lines = [
        "引导模式（--stage start）：好 Skill 要件全景，非发布裁决；发布前用 --stage final 重跑。",
        "",
        "当前缺口：",
    ]
    order = ("critical", "warning", "note")
    grouped: dict[str, list[str]] = {sev: [] for sev in order}
    for item in findings:
        if item["severity"] in grouped:
            grouped[item["severity"]].append(item["title"])
    any_gap = False
    for sev in order:
        for title in grouped[sev]:
            any_gap = True
            lines.append(f"  {START_GLYPHS[sev]}：{title}")
    if not any_gap:
        lines.append("  （暂无缺口）")

    lines.append("")
    lines.append("要件全景（目标态）：")
    private = audience_mode == "private"
    deferred: list[str] = []
    for family_name, ids, is_gh in SCAFFOLD_FAMILIES:
        entry = f"  {family_name}：" + " / ".join(ids)
        if is_gh and private:
            deferred.append(entry)
        else:
            lines.append(entry)
    if deferred:
        lines.append("")
        lines.append("自用视角：以后开源再看（仍列出，不默认隐藏 GitHub 引导）：")
        lines.extend(deferred)

    if token_layers:  # 空 dict 兜空不崩
        lines.append("")
        lines.extend(render_token_table(token_layers))
    return lines


def _md_cell(text: str) -> str:
    """表格单元转义：包 code span + 转义竖线，防 markdown 注入破表。"""
    safe = (
        str(text)
        .replace("`", "'")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )
    return f"`{safe}`"


def render_report(
    findings: list[dict[str, str]],
    summary: dict,
    skill_sha256: str,
    stage: str,
    notice: dict,
    lane_by_index: dict[int, str],
) -> str:
    """③体检卡（markdown）。诚实声明 + tree_sha256 指纹 + verdict→建议 + L 段未完成。"""
    verdict = str(summary.get("verdict", ""))
    advice = VERDICT_ADVICE.get(verdict, "见 findings")
    icons = {"critical": "🔴", "warning": "🟡", "note": "🔵"}
    lines = [
        "# Skill Quality Gate Report",
        "",
        "> 诚实声明：本卡为静态机器扫描，按公开门面清单静态核验，非生产质量认证；"
        "不含 7 角色人工评审与真实业务行为测试；唯有读者自己对当前 Skill 重跑门禁方可采信。",
        f"> 目标 Skill 指纹（tree_sha256）：`{skill_sha256}`",
        "",
        "## 结论",
        f"- 判定：{verdict}（建议：{advice}）",
        f"- 视角：{notice.get('mode') or '未声明'}（来源 {notice.get('source', 'default')}）",
        "- 等级：L1 / L2 / L3 / L4 段 —— 未完成·需人工（机器判不了）",
        "",
    ]
    section = (
        ("critical", "## 🔴 严重"),
        ("warning", "## 🟡 警告"),
        ("note", "## 🔵 建议"),
    )
    for severity, heading in section:
        lines.append(heading)
        rows = [
            (index, item)
            for index, item in enumerate(findings)
            if item["severity"] == severity
        ]
        if rows:
            lines.append("| 项 | 车道 | 说明 |")
            lines.append("| --- | --- | --- |")
            for index, item in rows:
                lane = lane_by_index.get(index, LANE_QUALITY)
                lines.append(
                    f"| {icons[severity]} {_md_cell(item['title'])} "
                    f"| {lane} | {_md_cell(item['detail'])} |"
                )
        else:
            lines.append("（无）")
        lines.append("")
    lines.append("## 7 角色摘要")
    lines.append("未完成·需人工（静态门禁不替代 7 角色人工评审）。")
    lines.append("")
    lines.append("## 下一步最小修复包")
    if findings:
        for rank, item in enumerate(findings, start=1):
            lane = lane_by_index.get(rank - 1, LANE_QUALITY)
            lines.append(f"{rank}. [{item['severity'].upper()}·{lane}] {_md_cell(item['title'])}")
    else:
        lines.append("（无待修项）")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit an Agent Skill and optional publication package."
    )
    parser.add_argument("skill_dir")
    parser.add_argument("--publication-dir")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true")
    output_group.add_argument("--report", action="store_true")
    parser.add_argument("--stage", choices=["start", "final"], default="final")
    parser.add_argument("--audience", choices=["public", "private"], default=None)
    parser.add_argument("--print-skill-sha256", action="store_true")
    args = parser.parse_args()

    skill = Path(args.skill_dir).expanduser().resolve()
    if args.print_skill_sha256:
        if not skill.is_dir():
            print("BLOCK: Skill directory is missing")
            return 2
        print(tree_sha256(skill))
        return 0

    publication_provided = args.publication_dir is not None
    pub_examples = False
    if publication_provided:
        _pub = Path(args.publication_dir).expanduser().resolve()
        pub_examples = (_pub / "examples" / "example-prompts.md").is_file()

    # RT1#3：effective_public 在此集中算一次，同喂 check_publication 与 apply_audience_perspective。
    profile_audience = read_declared_audience(skill)
    mode, source = resolve_audience(args.audience, profile_audience)
    effective_public = (mode == "public") or (
        mode == "private" and publication_provided
    )
    stage = args.stage

    findings, skill_name, token_layers = check_skill(
        skill, publication_provided, pub_examples
    )
    if publication_provided:
        publication = Path(args.publication_dir).expanduser().resolve()
        findings.extend(
            check_publication(
                publication, skill, skill_name, audience_public=effective_public
            )
        )

    # RT1#2：suppress/lift 只在 final 跑；start 绝不删/改 finding（只在脚手架重分组）。
    if stage == "final":
        apply_audience_perspective(findings, mode, effective_public, publication_provided)

    findings = deduplicate(findings)

    # C：在 pop 内部 _check_id 之前构建修复计划与车道映射。
    plan = build_remediation_plan(findings)
    lane_by_index = {entry["index"]: entry["lane"] for entry in plan}

    # RT2#4：输出前对每个 finding pop 掉内部 check_id，findings 严格保持三键。
    for item in findings:
        item.pop("_check_id", None)

    summary = summarize(findings, stage=stage)
    notice = audience_notice(mode, source, publication_provided, effective_public)
    if source == "cli" and profile_audience in AUDIENCE_VALUES:
        notice["overrides"] = f"risk-profile:{profile_audience}"

    payload = {
        "summary": summary,
        "findings": findings,
        "token_layers": token_layers,
        "audience": notice,
        "remediation_plan": plan,
    }

    if args.report:
        print(render_report(findings, summary, tree_sha256(skill), stage, notice, lane_by_index))
        return exit_code(summary)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return exit_code(summary)

    if stage == "start":
        print(f"Skill Quality Gate: {summary['verdict']}")
        print(
            f"critical={summary['critical']} "
            f"warning={summary['warning']} note={summary['note']}"
        )
        for line in render_audience_banner(notice):
            print(line)
        print("")
        for line in render_scaffold(findings, token_layers, mode):
            print(line)
        return exit_code(summary)

    # stage == final 文本渲染
    print(f"Skill Quality Gate: {summary['verdict']}")
    print(
        f"critical={summary['critical']} "
        f"warning={summary['warning']} note={summary['note']}"
    )
    for line in render_audience_banner(notice):
        print(line)
    icons = {"critical": "🔴", "warning": "🟡", "note": "🔵"}
    for index, item in enumerate(findings):
        lane = lane_by_index.get(index, LANE_QUALITY)
        print(
            f"{icons[item['severity']]} {item['severity'].upper()}: "
            f"{item['title']} — {item['detail']} [{lane}]"
        )
    for line in render_remediation(plan, findings, lane_by_index):
        print(line)
    if token_layers:
        print("")
        for line in render_token_table(token_layers):
            print(line)
    if mode is None:
        print("")
        print(DEFAULT_AUDIENCE_FOOTER)

    return exit_code(summary)


if __name__ == "__main__":
    raise SystemExit(main())
