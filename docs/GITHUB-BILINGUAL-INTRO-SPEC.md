# Skill Quality Gate GitHub Bilingual Introduction Spec

Status: reviewed bilingual repository-visual specification.

## Audience and first-screen outcome

The first screen serves a new GitHub visitor, a potential Skill user, and a contributor evaluating scope. Within about ten seconds it must explain what the Skill does, the evidence or output it produces, and where its automation boundary stops.

The production order is fixed: define the terminal user and use scenario, write the belief and next action from the consumer's point of view, apply `lucas-deepwheel-brand-apply`, edit the bilingual SVG sources, render the PNG derivatives, then run the consumer/brand contract check and the full Quality Gate. Do not start from decoration or retrofit a consumer story after rendering.

## Language and asset strategy

- English README uses the English pair; Chinese README uses the Chinese pair.
- Both variants share geometry, hierarchy, colors, and components.
- `DeepWheel`, `AGENT SKILL`, and stable product labels may remain in English where they function as brand taxonomy.
- SVG is the editable source; PNG is the GitHub README display asset.

```text
assets/intro/
  quality-gate-hero-en.svg / .png
  quality-gate-hero-zh-CN.svg / .png
  quality-gate-workflow-en.svg / .png
  quality-gate-workflow-zh-CN.svg / .png
  source/deepwheel-mark-color.svg
  source/visual-tokens.json
```

## DeepWheel brand rules

- Canvas: 1600 x 900, 16:9, exact-size PNG export.
- Ink `#101722`; brand blue `#0071E3`; body gray `#42474F`; caption gray `#5C626B`; Mist `#F2F5F9`; Hairline `#E1E6EE`; white `#FFFFFF`.
- Avenir Next 600 for English display; Inter fallback. Avenir Next -> PingFang SC -> Inter for Chinese.
- Use the current soft-rounded D mark with one structural blue node.
- Use an asymmetric 12-column layout, 64px outer margin, strong negative space, and one content-level blue focus per image.
- Blue area stays below roughly ten percent.
- Only the outer facade card may use shadow. Internal panels use white/Mist fills plus Hairline outlines.
- Offset sheets create depth without internal shadows.

Forbidden: old brand colors, purple glow, gradient spheres, glassmorphism, fake dashboards, equal-width feature-card rows, decorative repeated blue dots, button-like controls in static images, and unverified capability claims.

## Hero role

The hero is a value proposition plus one editorial record. It must not repeat the numbered workflow. The right-side record uses one blue structural spine; all metadata fields remain neutral.

The current hero must communicate three distinct responsibilities: Skill quality, post-change state reconciliation, and public-surface freshness. It must not imply that the gate performs repairs, image generation, or GitHub writes.

English product label: `Skill Quality Gate`
Chinese product label: `Skill 质量门禁`

`AGENT SKILLS` is the suite label; `DEEPWHEEL · AGENT SKILL` identifies this repository as one member of the suite.

## Workflow role

The workflow owns process explanation. It uses three unequal stages: input/target, the Skill engine, and the resulting package/report. The engine header is the only content-level blue plane; arrows, numbering, labels, and state text remain neutral.

The rc.5 workflow explicitly shows: validate Skill and safety; reconcile GitHub, Actions and installation; check README/SVG/PNG freshness; issue a verdict and AI-ready repair requirements. Its footer distinguishes MATCH, DRIFT, NOT PUSHED, PR OPEN and VISUAL ASSET STALE.

## README placement

1. repository title and current status;
2. language-matched hero;
3. plain-language product definition;
4. language-matched workflow near the first scope or process explanation;
5. detailed documentation.

Use concise, meaningful alt text. Do not repeat the entire image copy in alt attributes.

## QA gates

- exact bilingual copy and geometry review;
- current logo, colors, font stack, spacing, shadow policy, and blue budget;
- no clipped or overflowing text;
- 1600 x 900 export and approximately 720px README-width inspection;
- SVG title/desc accessibility metadata;
- PNG/SVG parity;
- version, product-specific, and generic package validators;
- installed-copy read-only comparison;
- sensitive-value, PII, local-path, and raw-residue scan;
- Claude brand co-review before template lock;
- GitHub Actions on the pull request and merged main.

The machine-readable consumer and brand production contract lives in `docs/PUBLIC-SURFACE-REVIEW.json`. Rendering uses `scripts/render-intro-assets.py`; `--write` requires an explicit Brand Apply declaration and consumer-review acknowledgement.
