# Security Policy

## Sensitive data

Do not store, commit, echo, or share credentials, cookies, session material, passwords, private keys, verification codes, one-time login data, embedded URL credentials, or complete sensitive logs.

Findings must identify only the risk category and relative file. Never print the matched value.

## Privacy and source boundary

Do not include private customer material, machine-specific absolute paths, real contact details, or protected commercial assets in tests, examples, issues, pull requests, or releases.

Use synthetic fixtures. Security tests must construct credential-shaped values at runtime so the repository itself does not contain reusable or credential-shaped test data.

## Restricted actions

This Skill audits and reports. It must not automatically install tools, modify the target Skill, upload files, send messages, change repository visibility, push, create a Tag or Release, or delete branches.

## Reporting

Report security concerns privately to the repository owner. Do not include reusable login information or private source material in an issue.
