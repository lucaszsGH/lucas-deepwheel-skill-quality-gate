#!/usr/bin/env python3
"""Read-only reconciliation across source, GitHub, release, and installation state."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any
from urllib.parse import quote


SKIP_PARTS = {".git", "__pycache__"}
SKIP_NAMES = {".DS_Store", ".installed-version"}
CONCERN_CODES = {
    "DRIFT", "NOT PUSHED", "PR OPEN", "ACTIONS PENDING", "INSTALL OUTDATED",
}
BLOCK_CODES = {"ACTIONS FAILED"}


def run(command: list[str], cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode, completed.stdout.strip()


def git(repo: Path, *args: str) -> tuple[int, str]:
    return run(["git", *args], repo)


def safe_tree(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.is_dir():
        return result
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        if path.name in SKIP_NAMES or path.is_symlink() or not path.is_file():
            continue
        result[str(relative)] = sha256(path.read_bytes()).hexdigest()
    return result


def discover_skill(repo: Path, explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_absolute():
            candidate = repo / candidate
        candidate = candidate.resolve()
        if not candidate.is_dir() or not (candidate / "SKILL.md").is_file():
            raise ValueError("declared Skill directory is missing")
        return candidate
    candidates = [
        path for path in sorted((repo / "skills").glob("*"))
        if path.is_dir() and (path / "SKILL.md").is_file()
    ]
    if len(candidates) != 1:
        raise ValueError("repository must contain exactly one discoverable Skill")
    return candidates[0].resolve()


def repository_slug(remote: str) -> str | None:
    value = remote.strip()
    if value.endswith(".git"):
        value = value[:-4]
    if value.startswith("git" + "@" + "github.com:"):
        return value.split(":", 1)[1]
    marker = "github.com/"
    if marker in value:
        return value.split(marker, 1)[1]
    return None


def gh_json(repo: Path, command: list[str]) -> Any | None:
    code, output = run(["gh", *command], repo)
    if code != 0 or not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def live_github_state(repo: Path, slug: str, branch: str) -> dict[str, Any] | None:
    if shutil.which("gh") is None:
        return None
    metadata = gh_json(
        repo,
        ["repo", "view", slug, "--json", "defaultBranchRef,visibility,url"],
    )
    if not isinstance(metadata, dict):
        return None
    default_branch = str(metadata.get("defaultBranchRef", {}).get("name", "main"))
    default_commit = gh_json(
        repo,
        ["api", f"repos/{slug}/commits/{quote(default_branch, safe='')}"],
    )
    branch_commit = gh_json(
        repo,
        ["api", f"repos/{slug}/commits/{quote(branch, safe='')}"],
    )
    pull_requests = gh_json(
        repo,
        [
            "pr", "list", "--repo", slug, "--head", branch, "--state", "open",
            "--limit", "20", "--json", "number,url,headRefOid,baseRefName",
        ],
    )
    actions = gh_json(
        repo,
        [
            "run", "list", "--repo", slug, "--branch", branch, "--limit", "30",
            "--json", "headSha,status,conclusion,url,event",
        ],
    )
    releases = gh_json(
        repo,
        [
            "release", "list", "--repo", slug, "--limit", "100",
            "--json", "tagName,isLatest,isPrerelease,isDraft",
        ],
    )
    return {
        "default_branch": default_branch,
        "default_sha": default_commit.get("sha") if isinstance(default_commit, dict) else None,
        "branch_sha": branch_commit.get("sha") if isinstance(branch_commit, dict) else None,
        "visibility": metadata.get("visibility"),
        "pull_requests": pull_requests if isinstance(pull_requests, list) else [],
        "actions": actions if isinstance(actions, list) else [],
        "releases": releases if isinstance(releases, list) else [],
    }


def record(area: str, code: str, detail: str) -> dict[str, str]:
    return {"area": area, "code": code, "detail": detail}


def reconcile(
    repo: Path,
    skill: Path,
    installed: Path,
    *,
    online: bool,
    require_installed: bool,
    require_release: bool,
    github_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    records: list[dict[str, str]] = []
    code, head = git(repo, "rev-parse", "HEAD")
    if code != 0:
        raise ValueError("repository HEAD is unavailable")
    _, branch = git(repo, "branch", "--show-current")
    _, dirty = git(repo, "status", "--porcelain")
    records.append(
        record("local_worktree", "DRIFT" if dirty else "MATCH", "uncommitted changes present" if dirty else "worktree clean")
    )

    _, remote = git(repo, "remote", "get-url", "origin")
    slug = repository_slug(remote)
    github = github_snapshot
    evidence = "snapshot" if github_snapshot is not None else "offline"
    if online and github is None and slug:
        github = live_github_state(repo, slug, branch)
        evidence = "live" if github is not None else "unavailable"

    if github is not None:
        default_branch = str(github.get("default_branch") or "main")
        branch_sha = github.get("branch_sha")
        default_sha = github.get("default_sha")
        if branch_sha is None:
            records.append(record("github_branch", "NOT PUSHED", "current branch is absent on GitHub"))
        elif branch_sha != head:
            records.append(record("github_branch", "NOT PUSHED", "local HEAD differs from the GitHub branch"))
        elif branch == default_branch and head == default_sha:
            records.append(record("github_main", "MATCH", "local HEAD matches GitHub default branch"))
        else:
            prs = [item for item in github.get("pull_requests", []) if item.get("headRefOid") == head]
            records.append(
                record("pull_request", "PR OPEN" if prs else "DRIFT", "open PR targets the current HEAD" if prs else "pushed branch has no open PR")
            )

        runs = [item for item in github.get("actions", []) if item.get("headSha") == head]
        if not runs:
            records.append(record("actions", "ACTIONS PENDING", "no Actions result found for current HEAD"))
        elif any(item.get("status") != "completed" for item in runs):
            records.append(record("actions", "ACTIONS PENDING", "Actions are queued or running"))
        elif any(item.get("conclusion") != "success" for item in runs):
            records.append(record("actions", "ACTIONS FAILED", "one or more Actions runs failed"))
        else:
            records.append(record("actions", "MATCH", "Actions succeeded for current HEAD"))
        records.append(record("visibility", "MATCH", str(github.get("visibility") or "UNKNOWN")))
    else:
        origin_ref = f"origin/{branch}"
        ref_code, origin_sha = git(repo, "rev-parse", "--verify", origin_ref)
        if ref_code != 0:
            records.append(record("github_branch", "NOT PUSHED", "current branch is absent from local origin refs"))
        elif origin_sha != head:
            records.append(record("github_branch", "NOT PUSHED", "local HEAD differs from local origin ref"))
        else:
            records.append(record("github_branch", "MATCH", "local HEAD matches local origin ref"))
        records.append(record("pull_request", "NOT CHECKED", "live GitHub check disabled"))
        records.append(record("actions", "NOT CHECKED", "live GitHub check disabled"))

    version_path = repo / "VERSION"
    version = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else ""
    tag = "v" + version if version else ""
    releases = github.get("releases", []) if github is not None else []
    release_match = any(item.get("tagName") == tag and item.get("isDraft") is not True for item in releases)
    tag_exists = False
    if tag and online:
        tag_code, tag_output = git(repo, "ls-remote", "--tags", "origin", f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}")
        tag_exists = tag_code == 0 and bool(tag_output)
    elif tag:
        tag_code, _ = git(repo, "rev-parse", "--verify", f"refs/tags/{tag}")
        tag_exists = tag_code == 0
    if tag_exists and release_match:
        records.append(record("version_release", "MATCH", "VERSION, Tag, and Release agree"))
    elif tag_exists != release_match:
        records.append(record("version_release", "DRIFT", "Tag and Release state disagree"))
    elif require_release:
        records.append(record("version_release", "DRIFT", "current VERSION has no Tag or Release"))
    else:
        records.append(record("version_release", "UNRELEASED", "current VERSION has no Tag or Release"))

    source_tree = safe_tree(skill)
    if installed.is_dir():
        installed_tree = safe_tree(installed.resolve())
        records.append(
            record("installation", "MATCH" if source_tree == installed_tree else "INSTALL OUTDATED", "installed Skill matches source" if source_tree == installed_tree else "installed Skill differs from source")
        )
    else:
        records.append(
            record("installation", "DRIFT" if require_installed else "NOT INSTALLED", "installed Skill is missing")
        )

    codes = {item["code"] for item in records}
    verdict = "BLOCK" if codes & BLOCK_CODES else "CONCERNS" if codes & CONCERN_CODES else "CLEAN"
    return {
        "summary": {"verdict": verdict, "github_evidence": evidence},
        "repository": {"branch": branch, "version": version},
        "statuses": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only reconciliation of local source, GitHub, release, and installation state."
    )
    parser.add_argument("repository_dir", type=Path)
    parser.add_argument("--skill-dir")
    parser.add_argument("--installed-skill-dir", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--require-installed", action="store_true")
    parser.add_argument("--require-release", action="store_true")
    parser.add_argument("--github-snapshot", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    repo = args.repository_dir.expanduser().resolve()
    if not (repo / ".git").exists():
        print("FAIL: repository directory is invalid")
        return 2
    try:
        skill = discover_skill(repo, args.skill_dir)
        installed = (
            args.installed_skill_dir.expanduser().resolve()
            if args.installed_skill_dir
            else (Path.home() / ".codex" / "skills" / skill.name)
        )
        snapshot = None
        if args.github_snapshot:
            snapshot = json.loads(args.github_snapshot.read_text(encoding="utf-8"))
        result = reconcile(
            repo,
            skill,
            installed,
            online=not args.offline,
            require_installed=args.require_installed,
            require_release=args.require_release,
            github_snapshot=snapshot,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("FAIL:", str(error))
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Release State:", result["summary"]["verdict"])
        for item in result["statuses"]:
            print(f"{item['code']}: {item['area']} - {item['detail']}")
    return 2 if result["summary"]["verdict"] == "BLOCK" else 1 if result["summary"]["verdict"] == "CONCERNS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
