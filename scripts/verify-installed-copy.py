#!/usr/bin/env python3
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path

SKILL_NAME = "lucas-deepwheel-skill-quality-gate"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "skills" / SKILL_NAME
DEFAULT_TARGET = Path.home() / ".codex" / "skills" / SKILL_NAME
IGNORED = {".DS_Store", ".installed-version"}

def snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.is_dir():
        return result
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in IGNORED:
            relative = str(path.relative_to(root))
            result[relative] = sha256(path.read_bytes()).hexdigest()
    return result

parser = ArgumentParser(description="Compare repository source with a local installed Skill copy.")
parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
args = parser.parse_args()

source = snapshot(args.source.expanduser().resolve())
target = snapshot(args.target.expanduser().resolve())

if not source:
    print("FAIL: source Skill directory is missing or empty")
    raise SystemExit(1)
if not target:
    print("FAIL: installed Skill directory is missing or empty")
    raise SystemExit(1)

missing = sorted(set(source) - set(target))
extra = sorted(set(target) - set(source))
changed = sorted(path for path in set(source) & set(target) if source[path] != target[path])

print(f"source_files={len(source)}")
print(f"target_files={len(target)}")
print(f"missing={len(missing)}")
print(f"extra={len(extra)}")
print(f"changed={len(changed)}")

for label, paths in (("MISSING", missing), ("EXTRA", extra), ("CHANGED", changed)):
    for path in paths:
        print(f"{label}: {path}")

if missing or extra or changed:
    print("RESULT=DRIFT")
    raise SystemExit(2)

print("RESULT=MATCH")
