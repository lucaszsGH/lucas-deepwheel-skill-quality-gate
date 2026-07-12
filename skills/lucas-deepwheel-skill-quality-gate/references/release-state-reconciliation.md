# Release state reconciliation

## Purpose

A local quality result does not prove that GitHub or an installed copy is current. After a Skill changes, reconcile the full delivery chain before saying it is usable or released.

```text
single editable source
→ local branch and worktree
→ GitHub branch / main / PR
→ Actions for the exact HEAD
→ VERSION / Tag / Release
→ installed Skill snapshot
```

## Read-only command

```bash
python3 scripts/reconcile_release_state.py /path/to/repository --json
```

Optional controls:

- `--skill-dir`: select the packaged Skill when discovery is ambiguous;
- `--installed-skill-dir`: compare a non-default installation path;
- `--offline`: use local origin refs and skip live GitHub/Actions reads;
- `--require-installed`: treat a missing installation as DRIFT;
- `--require-release`: require the current VERSION to have both Tag and Release.

The command may read Git and GitHub state. It must not fetch, commit, push, create or merge a PR, change visibility, create a Tag or Release, or install/replace a Skill.

## Status vocabulary

- `MATCH`: the compared states agree;
- `DRIFT`: states disagree or an expected transition is incomplete;
- `NOT PUSHED`: local HEAD is absent from or differs from the GitHub branch;
- `PR OPEN`: the current pushed HEAD is still under review and not on main;
- `ACTIONS PENDING`: no final Actions result exists for the exact HEAD;
- `ACTIONS FAILED`: one or more Actions runs for the exact HEAD failed;
- `INSTALL OUTDATED`: the installed Skill differs from the unique source;
- `UNRELEASED`: the current VERSION intentionally has no matching Tag and Release;
- `NOT CHECKED`: live evidence was not requested or unavailable.

`PR OPEN` and `UNRELEASED` are not defects by themselves, but they prevent claiming that GitHub main, release, or installation is already current.

## Repair boundary

Quality Gate reports the mismatch and the smallest repair sequence. Commit, push, PR creation, merge, Tag, Release and installation remain separate confirmed actions. After AI performs an approved repair, run reconciliation again against the new exact HEAD.
