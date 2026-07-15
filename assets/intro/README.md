# Skill Quality Gate intro assets

This folder contains the reviewed bilingual GitHub introduction system for this Skill.

## Language pairing

- English README: `quality-gate-hero-en.png` and `quality-gate-workflow-en.png`
- Chinese README: `quality-gate-hero-zh-CN.png` and `quality-gate-workflow-zh-CN.png`

The SVG files are editable sources. PNG files are exact 1600 x 900 README exports.

## Visual roles

- Hero: value proposition plus one editorial record covering structure, synchronization and public-surface review; not a mini workflow.
- Workflow: the only process explanation, now including GitHub/Actions/install reconciliation and bilingual README/SVG/PNG freshness; the engine header is the single content-level blue focus.
- Internal panels use Hairline outlines only. Decorative shadow is limited to the outer facade card.

The embedded mark and visual tokens come from the current DeepWheel brand system. Do not replace them with older colors or historical monograms.

## Generation order

1. Lock the terminal user, use scenario, desired belief and next action in `docs/PUBLIC-SURFACE-REVIEW.json`.
2. Use `lucas-deepwheel-brand-apply` before composing; DeepWheel is precise, restrained, credible and ordered.
3. Write consumer-facing bilingual copy in the SVG sources. English and Chinese are equal release surfaces, not primary and secondary variants.
4. Render PNG derivatives with `scripts/render-intro-assets.py --write --brand-skill lucas-deepwheel-brand-apply --consumer-reviewed`.
5. Run the renderer check, product-specific validator, generic Quality Gate and visual inspection at full size and README width.

The renderer is not a substitute for Brand Apply or human visual review; it only makes the SVG-to-PNG step reproducible and checks the encoded contract.
It prefers Node `sharp` when available (`NODE_BIN` / `NODE_PATH` may be supplied), then falls back to a local Chromium renderer. No renderer is installed automatically.
