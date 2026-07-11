#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
SKILL_NAME = "lucas-deepwheel-skill-quality-gate"
SKILL_DIR = ROOT / "skills" / SKILL_NAME
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)

def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)

if not VERSION_FILE.is_file():
    fail("missing VERSION")

version = VERSION_FILE.read_text(encoding="utf-8").strip()
if not SEMVER.fullmatch(version):
    fail("VERSION is not valid semantic versioning")
if not CHANGELOG_FILE.is_file():
    fail("missing CHANGELOG.md")
changelog = CHANGELOG_FILE.read_text(encoding="utf-8")
if f"## [{version}]" not in changelog:
    fail("CHANGELOG.md does not contain the current VERSION")
if not (SKILL_DIR / "SKILL.md").is_file():
    fail(f"missing skills/{SKILL_NAME}/SKILL.md")

print(f"PASS: version {version}")
