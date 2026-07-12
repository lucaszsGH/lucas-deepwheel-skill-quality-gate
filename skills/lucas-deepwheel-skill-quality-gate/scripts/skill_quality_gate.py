#!/usr/bin/env python3
"""Audit an Agent Skill and optional publication package without exposing matched values."""
from __future__ import annotations

import argparse
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
    "docs/TEST-RUNS.md",
    "docs/VERSIONING.md",
    "examples/example-prompts.md",
    "scripts/install-local.py",
    "scripts/validate-lucas-deepwheel-skill.py",
    "scripts/validate-version.py",
    "scripts/verify-installed-copy.py",
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


def finding(severity: str, title: str, detail: str) -> dict[str, str]:
    return {"severity": severity, "title": title, "detail": detail}


def safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return "<outside-target>"


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


def parse_frontmatter(text: str) -> tuple[str, str] | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    frontmatter = match.group(1)
    keys = [
        line.split(":", 1)[0].strip()
        for line in frontmatter.splitlines()
        if ":" in line
    ]
    if keys != ["name", "description"]:
        return "", ""
    name_match = re.search(r"^name:\s*([^\n]+)$", frontmatter, re.M)
    description_match = re.search(
        r'^description:\s*"(.*)"\s*$', frontmatter, re.M
    )
    name = name_match.group(1).strip() if name_match else ""
    description = description_match.group(1).strip() if description_match else ""
    return name, description


def check_skill(skill: Path) -> tuple[list[dict[str, str]], str | None]:
    findings: list[dict[str, str]] = []
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
    args = parser.parse_args()

    skill = Path(args.skill_dir).expanduser().resolve()
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
