# Design

## Purpose

Agentic Commerce Toolkit is a public, protocol-aware but protocol-neutral collection of tools and reference integrations for agent-native commerce.

## Architectural principles

1. **Standalone public history.** This repository has its own Git root, issue tracker, releases, and governance.
2. **Public sources only.** Implementations derive from public documentation, public APIs, public repositories, fixtures, or intentionally contributed code.
3. **Read-only first.** New protocol integrations begin with discovery and diagnostics before transaction-writing behavior.
4. **Stable machine contracts.** Agent-facing commands prefer structured JSON, documented schemas, and stable error codes.
5. **Maker/checker separation.** Generated actions and outputs should be independently verifiable.
6. **Secrets stay outside the repo.** Examples use placeholders and fixtures; CI must not require production wallets.
7. **Complement upstream.** Do not clone official CLIs or SDKs without a demonstrated compatibility or orchestration gap.
8. **Subsidy-independent value.** The project must remain useful even if no grant or inference-credit program exists.

## Intended components

```text
public protocol sources
  -> read-only adapters
  -> normalized schemas
  -> provenance + health checks
  -> bounded reference services
  -> optional write paths with dry-run and approval controls
```

## Source-of-truth files

- `README.md` — mission and public entry point.
- `DESIGN.md` — architecture and durable decisions.
- `ROADMAP.md` — sequenced work and release gates.
- `PUBLIC_BOUNDARY.md` — separation policy.
- `SECURITY.md` — vulnerability and credential policy.
- `schemas/` — versioned machine-readable contracts.
- GitHub issues — public work queue after remote creation.

## Decisions

### D1. Standalone repository

The toolkit may be developed with private local tools, but its committed history and artifacts must stand on their own. No non-public source is required at runtime or for documentation.

### D2. Reppo first, Virtuals ACP second

Reppo provides a concrete public API/CLI surface for the first read-only utility. Virtuals ACP is the first cross-ecosystem commerce integration target.

### D3. No token or agent launch in the foundation phase

Launching a tokenized agent adds capital, inference, branding, and operational risk. A launch is considered only after a working service demonstrates demand and bounded economics.

### D4. Inference credits are an outcome to validate, not an assumption

Public contribution may strengthen a sponsorship or grant request, but roadmap economics do not assume free inference.

### D5. Public/private violations block release

Boundary checks are required in CI. Automated checks are a backstop, not a substitute for human review of every public commit.

## First implementation target

The v0.1.0 read-only Reppo ecosystem inspector:

- reads public endpoints only;
- emits stable JSON;
- reports endpoint health and freshness;
- records source URLs and timestamps;
- never requests a private key;
- complements rather than reimplements the official Reppo CLI.

### D6. Preserve upstream data inside a stable envelope

The inspector owns only the top-level envelope, source metadata, error codes, and aggregate command keys. Successful public API objects remain unchanged under `data`, avoiding a second field vocabulary that could drift from upstream. Status and snapshot probe each source independently and keep successful objects when another source fails.

### D7. Canonical standard-library HTTP with deterministic seams

Runtime networking is pinned to the canonical Reppo public API and uses `urllib` with a fixed user agent, JSON accept header, refused redirects, bounded timeout, URL encoding, and an 8 MiB response limit. The cap accommodates the current public pod catalog while still failing closed on unbounded growth. Public result limits and query lengths are bounded. The inspector accepts injected transport and clock implementations so tests are deterministic and do not contact live services or arbitrary custom hosts.

### D8. Defend against upstream pagination and availability drift

The public pod catalog currently returns the full catalog even when a smaller `limit` is requested. The inspector therefore validates `data.subnets` and `data.pods`, downloads only within the hard response cap, and slices returned collections to the caller's requested limit. The documented public stats route currently returns HTTP 404; aggregate commands preserve successful catalog data and mark the result partial rather than inventing replacement metrics.

### D9. Add operational observations to v1 without breaking existing documents

Cost, timeout, and freshness are optional, strictly bounded objects in the agent-job result v1 schema so documents created against the initial v1 contract remain valid. Costs use non-negative decimal strings rather than JSON numbers to avoid floating-point ambiguity. These fields expose public job-level observations only and exclude account, wallet, payment-credential, internal-budget, and provider-secret data.
