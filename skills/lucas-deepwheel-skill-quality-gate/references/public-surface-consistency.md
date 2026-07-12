# Public surface consistency

## Purpose

When a Skill's user-visible capability, workflow, boundary, positioning or output changes, its public explanation can become stale even when all files still exist. Quality Gate must require a review decision rather than treating image presence as semantic freshness.

## Public surface

For Lucas-DeepWheel publication packages, review at least:

- English and Chinese README;
- English and Chinese Hero and Workflow SVG sources;
- matching rendered PNG files;
- example prompts and public examples;
- installation instructions;
- Changelog and current version wording;
- screenshots or sample reports when they communicate capability.

## Machine binding

`docs/PUBLIC-SURFACE-REVIEW.json` binds:

- the exact packaged-Skill SHA-256;
- the reviewed public-file inventory and its SHA-256;
- whether the change is `user_visible` or `internal_only`;
- whether public surfaces were `UPDATED` or `NO_CHANGE_REQUIRED`;
- a human-readable reason;
- the bilingual editable and rendered assets updated for a user-visible change.

Missing, malformed or stale evidence returns `VISUAL ASSET STALE` and prevents CLEAN.

## Decision rule

- `user_visible` requires `UPDATED` plus English/Chinese SVG and PNG evidence.
- `internal_only` may use `NO_CHANGE_REQUIRED`, but the reason must explain why public understanding is unchanged.
- Updating only a fingerprint without reviewing the public surfaces is not a valid review.
- English and Chinese geometry and meaning must remain paired.

## Repair boundary

Quality Gate does not rewrite README, generate images, edit SVG/PNG or publish changes. It points to stale surfaces and supplies acceptance criteria. After Lucas confirms, AI or an appropriate design/document Skill performs the repair. Quality Gate then rechecks the exact new Skill and public-surface fingerprints.
