#!/usr/bin/env python3
from argparse import ArgumentParser
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json
import shutil

SKILL_NAME = "lucas-deepwheel-skill-quality-gate"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / SKILL_NAME
VERSION_FILE = ROOT / "VERSION"
DEFAULT_TARGET_ROOT = Path.home() / ".codex" / "skills"

def tree_hash(root: Path) -> str:
    digest = sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != ".DS_Store":
            digest.update(str(path.relative_to(root)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()

parser = ArgumentParser(description="Safely install the repository Skill into a local Skills directory.")
parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
parser.add_argument("--apply", action="store_true", help="Perform the installation. Without this flag, only show the plan.")
parser.add_argument(
    "--replace-after-confirmation",
    action="store_true",
    help="Replace an existing installation after explicit user confirmation; the previous copy is moved to a timestamped backup.",
)
args = parser.parse_args()

if not SOURCE.is_dir() or not (SOURCE / "SKILL.md").is_file():
    print("FAIL: source Skill is missing")
    raise SystemExit(1)
if not VERSION_FILE.is_file():
    print("FAIL: VERSION is missing")
    raise SystemExit(1)

version = VERSION_FILE.read_text(encoding="utf-8").strip()
target_root = args.target_root.expanduser().resolve()
target = target_root / SKILL_NAME
exists = target.exists()

print(f"skill={SKILL_NAME}")
print(f"version={version}")
print(f"target={target}")
print(f"target_exists={'yes' if exists else 'no'}")

if not args.apply:
    print("ACTION=DRY_RUN")
    if exists:
        print("NEXT=explicit confirmation is required before replacement")
    else:
        print("NEXT=rerun with --apply to install")
    raise SystemExit(0)

if exists and not args.replace_after_confirmation:
    print("FAIL: existing installation will not be replaced without --replace-after-confirmation")
    raise SystemExit(2)

target_root.mkdir(parents=True, exist_ok=True)
backup = None
if exists:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target_root / f"{SKILL_NAME}.backup-{timestamp}"
    if backup.exists():
        print("FAIL: backup path already exists")
        raise SystemExit(1)
    target.rename(backup)

try:
    shutil.copytree(SOURCE, target)
    (target / ".installed-version").write_text(version + "\n", encoding="utf-8")
    manifest = {
        "skill": SKILL_NAME,
        "version": version,
        "installed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_tree_sha256": tree_hash(SOURCE),
    }
    manifest_dir = target_root / ".lucas-deepwheel-install-manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / f"{SKILL_NAME}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
except Exception:
    if target.exists():
        shutil.rmtree(target)
    if backup and backup.exists():
        backup.rename(target)
    raise

print("ACTION=INSTALLED")
if backup:
    print(f"backup={backup}")
