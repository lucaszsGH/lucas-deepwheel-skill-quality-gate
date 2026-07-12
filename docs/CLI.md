# CLI contract

## Commands

Audit a Skill:

```bash
python3 skills/lucas-deepwheel-skill-quality-gate/scripts/skill_quality_gate.py /path/to/target-skill
```

Audit a Skill and publication package:

```bash
python3 skills/lucas-deepwheel-skill-quality-gate/scripts/skill_quality_gate.py /path/to/target-skill --publication-dir /path/to/publication-package
```

JSON output:

```bash
python3 skills/lucas-deepwheel-skill-quality-gate/scripts/skill_quality_gate.py /path/to/target-skill --json
```

Read-only release-state reconciliation:

```bash
python3 skills/lucas-deepwheel-skill-quality-gate/scripts/reconcile_release_state.py /path/to/repository --json
```

The reconciler reports `MATCH`, `DRIFT`, `NOT PUSHED`, `PR OPEN`, `ACTIONS PENDING`, `ACTIONS FAILED`, `INSTALL OUTDATED`, `UNRELEASED`, and `NOT CHECKED`. It does not fetch, commit, push, merge, publish, Tag, Release, install, or replace files.

## Exit codes

| Code | Verdict | Meaning |
|---|---|---|
| 0 | CLEAN | No critical or warning finding |
| 1 | CONCERNS | One or more warning findings |
| 2 | BLOCK | Critical finding or invalid requested path |

Notes do not change a CLEAN exit code.

## Output safety

- Do not echo matched credential or PII values.
- Do not echo the requested absolute target path.
- Report relative file paths only.
- JSON and human-readable output use the same findings and exit semantics.

## Limits

The static gate does not prove real business behavior, visual quality, export quality, copyright compliance, dependency safety, or production readiness. Public-surface fingerprint checks prove that review evidence targets the current files, not that a design is aesthetically correct.
