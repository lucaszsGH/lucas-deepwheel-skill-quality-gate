# Example prompts

## Local draft

```text
Use $lucas-deepwheel-skill-quality-gate to audit this Skill folder as an L1 local draft. Separate verified findings, inference, and items that need real behavior tests.
```

## Installation candidate

```text
Audit this Skill as an installation candidate. Check new-user capability preflight, safe installation, failure recovery, and whether the capability claims are too broad.
```

## GitHub publication candidate

```text
Audit this Skill folder and its publication package. Run the machine gate, summarize the seven reviewer roles, and give a P0/P1/P2 repair plan. Do not modify or publish anything.
```

## Post-change synchronization audit

```text
Reconcile the unique source, local branch, GitHub main or PR, Actions for the exact HEAD, VERSION, Tag, Release, and installed Skill. Report MATCH / DRIFT / NOT PUSHED / PR OPEN / ACTIONS FAILED / INSTALL OUTDATED. Do not modify any state.
```

## Public description and visual freshness

```text
Check whether the current capability still matches the English and Chinese README, Hero and Workflow SVG/PNG assets, examples, installation guide, and Changelog. Return VISUAL ASSET STALE if review evidence is missing or stale. Do not edit or generate assets; give the AI repair requirements for Lucas to confirm.
```

## Low-budget review

```text
Perform the lowest-cost useful audit first. Check structure, safety, capability boundaries, and publication blockers. Ask before any real behavior test that would require tools or generate artifacts.
```
