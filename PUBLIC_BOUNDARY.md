# Public Repository Boundary

## Rule

Everything committed here must be suitable for permanent public distribution.

The repository is intentionally separated from private research, runtime, investment, content, and wallet projects. “Useful internally” does not mean “safe to copy from an internal repository.” Public artifacts must be recreated from public sources or deliberately authored for this project.

## Allowed

- Public protocol documentation and API behavior, with attribution
- Public open-source code used under compatible licenses
- Synthetic or sanitized fixtures
- Generic operational safety patterns
- Reproducible benchmarks that contain no private account data
- Public issue discussions and intentionally submitted contributions

## Prohibited

- `.env`, auth stores, private keys, seed phrases, API tokens, cookies, session files
- Private account, wallet, transaction, budget, or strategy data unless intentionally disclosed
- Local runtime state, including memories, sessions, profile configuration, schedules, or generated reports
- Non-public research, local databases, watchlists, content queues, drafts, analytics, or unpublished interpretations
- Private DMs, partner communications, grant terms, or contact details
- Absolute local paths that expose private project structure
- Trading positions, proprietary signals, or investment recommendations
- Copied code or documents without license review and attribution

## Transfer process

When an internal need inspires a public contribution:

1. Write a clean public requirement without copying private source material.
2. Re-derive facts from public primary sources.
3. Implement in this repository using public fixtures.
4. Review the diff for private names, paths, credentials, strategy, and metadata.
5. Run `python3 scripts/check_public_boundary.py .`.
6. Obtain human review before publishing high-risk integrations.

## Enforcement

The boundary checker blocks known secret filenames, unapproved hidden or private directories, explicit named non-public system references, sensitive key patterns, and local absolute paths. Maintainers can supply an uncommitted comma-separated identifier denylist through `PUBLIC_BOUNDARY_PRIVATE_TERMS`; findings do not echo those values. Trusted pre-merge and push CI supply this denylist from a GitHub secret, while pull-request code never receives or executes with it. The checker can produce false positives and cannot prove that content is safe. Human review remains mandatory.
