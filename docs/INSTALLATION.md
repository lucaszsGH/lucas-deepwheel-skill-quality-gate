# Installation

## Safe installer

Run from the repository root:

```bash
python3 scripts/install-local.py
```

The default target root is `$HOME/.codex/skills`. Without `--apply`, the command only reports the Skill, version, target, whether the target exists, and the next confirmation gate.

It does not create, replace, move, or delete files.

## Fresh installation

After reviewing the dry run and explicitly approving installation:

```bash
python3 scripts/install-local.py --apply
```

## Existing installation

`--apply` alone refuses to replace an existing installation and exits with code `2`.

Only after explicit replacement confirmation may this path be used:

```bash
python3 scripts/install-local.py --apply --replace-after-confirmation
```

The previous installation is moved to a timestamped backup before the new copy is installed. Backups are never deleted automatically.

## Recovery

If copying fails, the installer attempts to remove the incomplete target and restore the previous backup. Any later rollback or deletion still requires explicit approval.

## Custom target root

```bash
python3 scripts/install-local.py --target-root /path/to/skills
```

Review the dry run before adding `--apply`.

## Verify

```bash
python3 scripts/verify-installed-copy.py
```

`RESULT=MATCH` means the installed Skill body matches the repository source. `RESULT=DRIFT` means the copies differ; it is not permission to replace either copy.

## What this installs

This installs the Quality Gate Skill only. It does not install OCR, browser automation, document export, image generation, GitHub CLI, or other Skills.
