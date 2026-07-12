# Publication Checklist

- [x] VERSION matches CHANGELOG.
- [x] English and Chinese READMEs expose the dry-run installer and installation guide.
- [x] CLI documents CLEAN / CONCERNS / BLOCK and exit codes 0 / 1 / 2.
- [x] Missing Skill and missing requested publication package return BLOCK.
- [x] A same-named scanner file is still scanned.
- [x] Generic home paths are detected without maintainer-specific hardcoding.
- [x] Findings do not echo matched values or target absolute paths.
- [x] Positive and negative behavior tests pass.
- [x] Version, generic package, and Quality Gate-specific gates pass independently.
- [x] Safe installer dry run and existing-target refusal are verified.
- [x] Original draft and installed copy remain unchanged during source preparation.
- [x] Clean private-repository clone test passes before Tag or Release.
- [x] Read-only reconciliation distinguishes local, GitHub main/PR, Actions, release metadata and installed-snapshot states.
- [x] Public-surface review binds the exact Skill state to reviewed README, examples, installation guidance and bilingual introduction assets.
- [x] User-visible capability changes require refreshed English/Chinese SVG and PNG assets; stale evidence cannot return CLEAN.
- [x] Quality Gate reports required repairs but does not modify README or image assets itself.
- [x] No public visibility change, direct main push, Tag, Release, branch deletion, or installation replacement occurs without separate confirmation.
