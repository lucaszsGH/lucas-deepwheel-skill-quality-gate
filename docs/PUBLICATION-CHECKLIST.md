# Publication Checklist

- [ ] VERSION matches CHANGELOG.
- [ ] English and Chinese READMEs expose the dry-run installer and installation guide.
- [ ] CLI documents CLEAN / CONCERNS / BLOCK and exit codes 0 / 1 / 2.
- [ ] Missing Skill and missing requested publication package return BLOCK.
- [ ] A same-named scanner file is still scanned.
- [ ] Generic home paths are detected without maintainer-specific hardcoding.
- [ ] Findings do not echo matched values or target absolute paths.
- [ ] Positive and negative behavior tests pass.
- [ ] Version, generic package, and Quality Gate-specific gates pass independently.
- [ ] Safe installer dry run and existing-target refusal are verified.
- [ ] Original draft and installed copy remain unchanged during source preparation.
- [ ] Clean private-repository clone test passes before Tag or Release.
- [ ] No public visibility change, direct main push, Tag, Release, branch deletion, or installation replacement occurs without separate confirmation.
