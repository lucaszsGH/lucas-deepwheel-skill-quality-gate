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

## Low-budget review

```text
Perform the lowest-cost useful audit first. Check structure, safety, capability boundaries, and publication blockers. Ask before any real behavior test that would require tools or generate artifacts.
```
