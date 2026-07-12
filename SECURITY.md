# Security Policy

## Reporting a vulnerability

Before a dedicated security contact is configured, open a GitHub security advisory after the public remote is created. Do not disclose exploitable vulnerabilities, credentials, or affected wallet details in a public issue.

## Credential policy

This repository must never contain live:

- private keys or seed phrases;
- API keys or bearer tokens;
- browser cookies or authentication databases;
- production wallet exports;
- private RPC credentials;
- `.env` files.

Examples must use explicit placeholders. Tests must use synthetic fixtures.

## Transaction safety

Read-only integrations are preferred. Any future write-capable integration must document:

- signer and wallet assumptions;
- chain and contract addresses;
- simulation or dry-run behavior;
- budgets and transaction caps;
- idempotency and retry behavior;
- approval boundaries;
- rollback or recovery procedure.

## Supported versions

| Version | Supported |
| --- | --- |
| `0.1.x` | Yes |
| `< 0.1` | No |

Security fixes are applied to the latest patch release in the supported minor line. The `main` branch may contain unreleased changes and is not a substitute for a tagged release.
