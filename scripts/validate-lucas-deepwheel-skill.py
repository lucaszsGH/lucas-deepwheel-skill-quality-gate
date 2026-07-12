#!/usr/bin/env python3
"""Validate a Lucas-DeepWheel Skill bundle and publication package.

This validator is intentionally product-agnostic. Product behavior belongs in
the companion product-specific validator (for example, Capture or
Reproduction), so CI can prove that the generic and product-specific gates are
independent.
"""
from __future__ import annotations

from pathlib import Path
import re
import stat
import sys


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
    "docs/ROADMAP.md",
    "docs/TEST-RUNS.md",
    "docs/VERSIONING.md",
    "examples/example-prompts.md",
    "scripts/install-local.py",
    "scripts/validate-version.py",
    "scripts/verify-installed-copy.py",
)

EXECUTABLE_SCRIPTS = (
    "scripts/install-local.py",
    "scripts/validate-lucas-deepwheel-skill.py",
    "scripts/validate-version.py",
    "scripts/verify-installed-copy.py",
)

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

SEMVER = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)

SENSITIVE_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "provider key": re.compile(
        rb"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|"
        rb"github_pat_[A-Za-z0-9_]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16}|"
        rb"xox[baprs]-[A-Za-z0-9-]{10,})\b"
    ),
    "jwt": re.compile(
        rb"\beyJ[A-Za-z0-9_-]{8,}\."
        rb"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
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

# Split stable path fragments so this validator does not flag its own source.
LOCAL_PATH_PATTERNS = {
    "macOS home path": re.compile(rb"/" + rb"Users/" + rb"[^/\s`\"']+"),
    "Linux home path": re.compile(rb"/" + rb"home/" + rb"[^/\s`\"']+"),
    "Windows home path": re.compile(
        rb"[A-Za-z]:\\" + rb"Users\\" + rb"[^\\\s`\"']+"
    ),
    "macOS volume path": re.compile(rb"/" + rb"Volumes/" + rb"[^\s`\"']+"),
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


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def tree_snapshot(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    if not root.is_dir():
        return snapshot
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts or "__pycache__" in relative.parts or path.name == ".DS_Store":
            continue
        if path.is_file() and not path.is_symlink():
            snapshot[str(relative)] = path.read_bytes()
    return snapshot


def scan_tree(root: Path, errors: list[str]) -> None:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts or "__pycache__" in relative.parts or path.name == ".DS_Store":
            continue
        label = str(relative)
        if path.is_symlink():
            errors.append(f"symbolic link is not allowed: {label}")
            continue
        if not path.is_file():
            continue
        if path.name.lower() in RAW_RESIDUE_NAMES:
            errors.append(f"raw capture or debug residue is not allowed: {label}")
        data = path.read_bytes()
        for category, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(data):
                errors.append(f"{category} shaped value found: {label}")
        for category, pattern in LOCAL_PATH_PATTERNS.items():
            if pattern.search(data):
                errors.append(f"{category} found: {label}")
        for category, pattern in PII_PATTERNS.items():
            if pattern.search(data):
                errors.append(f"{category} found: {label}")


def check_skill(skill_dir: Path, errors: list[str]) -> str | None:
    add(errors, skill_dir.is_dir(), "Skill directory is missing")
    if not skill_dir.is_dir():
        return None

    skill_md = skill_dir / "SKILL.md"
    add(errors, skill_md.is_file(), "SKILL.md is missing")
    if not skill_md.is_file():
        return None

    text = read_text(skill_md)
    frontmatter = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    add(errors, frontmatter is not None, "SKILL.md YAML frontmatter is missing")
    if frontmatter is None:
        return None

    frontmatter_text = frontmatter.group(1)
    keys = [
        line.split(":", 1)[0].strip()
        for line in frontmatter_text.splitlines()
        if ":" in line
    ]
    add(
        errors,
        keys == ["name", "description"],
        "SKILL.md frontmatter must contain only name and description",
    )

    name_match = re.search(r"^name:\s*([^\n]+)$", frontmatter_text, re.M)
    description_match = re.search(
        r'^description:\s*"(.*)"\s*$', frontmatter_text, re.M
    )
    name = name_match.group(1).strip() if name_match else ""
    description = description_match.group(1).strip() if description_match else ""
    add(errors, bool(name), "Skill name is missing")
    add(
        errors,
        bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", name))
        and "--" not in name,
        "Skill name format is invalid",
    )
    add(errors, name == skill_dir.name, "Skill name does not match its directory")
    add(errors, 1 <= len(description) <= 1024, "Skill description length is invalid")
    add(
        errors,
        "Use when" in description,
        "Skill description must explain when to use the Skill",
    )
    add(
        errors,
        "Do not" in description or "不要" in description,
        "Skill description must include an adjacent-task exclusion",
    )

    references = skill_dir / "references"
    add(errors, references.is_dir(), "references directory is missing")
    if references.is_dir():
        nested_directories = [path for path in references.rglob("*") if path.is_dir()]
        add(
            errors,
            not nested_directories,
            "references must remain one level deep",
        )

    for reference in sorted(set(re.findall(r"`references/([^`]+)`", text))):
        add(
            errors,
            (references / reference).is_file(),
            f"referenced file is missing: references/{reference}",
        )

    add(
        errors,
        (skill_dir / "agents" / "openai.yaml").is_file(),
        "agents/openai.yaml is missing",
    )
    forbidden_top_level = {
        "changelog.md",
        "quick-reference.md",
        "quick_reference.md",
        "readme.md",
    }
    unexpected = [
        path.name
        for path in skill_dir.iterdir()
        if path.is_file() and path.name.lower() in forbidden_top_level
    ]
    add(
        errors,
        not unexpected,
        "README, CHANGELOG, or quick-reference files belong outside the Skill bundle",
    )
    return name or None


def check_publication(
    skill_dir: Path, publication_dir: Path, skill_name: str | None, errors: list[str]
) -> None:
    add(errors, publication_dir.is_dir(), "Publication directory is missing")
    if not publication_dir.is_dir():
        return

    for relative in REQUIRED_PUBLICATION_FILES:
        add(
            errors,
            (publication_dir / relative).is_file(),
            f"publication file is missing: {relative}",
        )

    issue_templates = publication_dir / ".github" / "ISSUE_TEMPLATE"
    issue_template_files = (
        [path for path in issue_templates.iterdir() if path.is_file()]
        if issue_templates.is_dir()
        else []
    )
    add(errors, bool(issue_template_files), "at least one issue template is required")

    version_file = publication_dir / "VERSION"
    version = read_text(version_file).strip() if version_file.is_file() else ""
    add(errors, bool(SEMVER.fullmatch(version)), "VERSION is not valid semantic versioning")
    changelog = publication_dir / "CHANGELOG.md"
    if version and changelog.is_file():
        add(
            errors,
            f"## [{version}]" in read_text(changelog),
            "CHANGELOG.md does not contain the current VERSION",
        )

    license_file = publication_dir / "LICENSE"
    if license_file.is_file():
        add(errors, "MIT License" in read_text(license_file), "LICENSE is not MIT")

    for readme_name in ("README.md", "README.zh-CN.md"):
        readme = publication_dir / readme_name
        if readme.is_file():
            readme_text = read_text(readme)
            add(
                errors,
                "scripts/install-local.py" in readme_text,
                f"{readme_name} does not expose the safe installer",
            )
            add(
                errors,
                "docs/INSTALLATION.md" in readme_text,
                f"{readme_name} does not link the installation guide",
            )

    installation = publication_dir / "docs" / "INSTALLATION.md"
    if installation.is_file():
        installation_text = read_text(installation)
        add(
            errors,
            "python3 scripts/install-local.py" in installation_text,
            "installation guide does not show the dry-run command",
        )
        add(
            errors,
            "--apply" in installation_text,
            "installation guide does not explain the apply gate",
        )

    workflow = publication_dir / ".github" / "workflows" / "validate.yml"
    if workflow.is_file():
        workflow_text = read_text(workflow)
        workflow_terms = (
            "permissions:",
            "contents: read",
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "Validate version metadata",
            "Validate skill package",
            "validate-lucas-deepwheel-skill.py",
        )
        for term in workflow_terms:
            add(errors, term in workflow_text, f"workflow is missing: {term}")
        validation_steps = len(
            re.findall(r"^\s+- name:\s+Validate ", workflow_text, re.M)
        )
        add(
            errors,
            validation_steps >= 3,
            "workflow must contain version, generic package, and product-specific gates",
        )

    for relative in EXECUTABLE_SCRIPTS:
        script = publication_dir / relative
        if script.is_file():
            add(
                errors,
                bool(script.stat().st_mode & stat.S_IXUSR),
                f"script is not executable: {relative}",
            )

    if skill_name:
        packaged_skill = publication_dir / "skills" / skill_name
        add(
            errors,
            packaged_skill.is_dir(),
            f"publication Skill directory is missing: skills/{skill_name}",
        )
        if packaged_skill.is_dir():
            add(
                errors,
                tree_snapshot(skill_dir) == tree_snapshot(packaged_skill),
                "provided Skill and publication Skill contents do not match",
            )


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            "Usage: validate-lucas-deepwheel-skill.py "
            "<skill_dir> [publication_dir]"
        )
        return 2

    skill_dir = Path(sys.argv[1]).expanduser().resolve()
    publication_dir = (
        Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) == 3 else None
    )
    errors: list[str] = []
    skill_name = check_skill(skill_dir, errors)
    if publication_dir is not None:
        check_publication(skill_dir, publication_dir, skill_name, errors)
        if publication_dir.is_dir():
            scan_tree(publication_dir, errors)
    elif skill_dir.is_dir():
        scan_tree(skill_dir, errors)

    unique_errors = sorted(set(errors))
    if unique_errors:
        for error in unique_errors:
            print(f"FAIL: {error}")
        print(f"FAIL: generic package validation found {len(unique_errors)} issue(s)")
        return 1

    print("PASS: generic package validation ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
