# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add a versioned source-manifest schema, documentation, and synthetic conforming example for public-source provenance records.
- Add a bounded agent-job result schema, documentation, and synthetic conforming example linked to source-manifest provenance.
- Add backward-compatible cost, timeout, and freshness metadata to agent-job results.

### Security

- Generalize public-boundary policy and scanner rules so documentation does not enumerate non-public system identifiers.
- Scan public policy documents for sensitive patterns instead of exempting them from boundary checks.

## [0.1.0] - 2026-07-12

### Added

- Dependency-free, read-only Reppo public ecosystem inspector.
- Stable JSON envelope, source metadata, fixed error codes, and partial-result behavior.
- Datanet, pod, status, and snapshot commands with synthetic fixtures and deterministic tests.
- Public/private boundary policy and automated boundary scanning.
- Read-only Reppo compatibility watchdog and maintainer evidence collector.
- Conforming inspector-envelope example with JSON Schema validation.

### Security

- Refuse redirects and cap response bodies at 8 MiB.
- Pin runtime requests to the canonical Reppo public API host.
- Bound public result limits to 100 and query fields to 256 characters.
- Keep runtime authentication, wallets, transactions, and private project data out of scope.

[Unreleased]: https://github.com/nccrypto/agentic-commerce-toolkit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nccrypto/agentic-commerce-toolkit/releases/tag/v0.1.0
