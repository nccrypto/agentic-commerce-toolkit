# Roadmap

## Release policy

A phase is complete only when its artifacts are exercised and its verification gate passes. Dates are intentionally omitted until maintainers approve implementation capacity.

## Phase 0 — Public foundation

- [x] Standalone local Git repository scaffold
- [x] Public/private boundary policy
- [x] Security and contribution policies
- [x] Deterministic boundary checker and tests
- [x] Public GitHub remote created after explicit approval
- [x] Branch protection and required CI configured

**Gate:** clean boundary scan, tests pass, no remote dependency on a private project.

## Phase 1 — Reppo read-only inspector (`v0.1.0`)

- [x] Bound the implementation to the specified public `/stats`, `/public/subnets`, and `/public/pods` endpoints
- [x] Pin runtime transport to the canonical Reppo host and bound public inputs
- [x] Define a stable inspection envelope and source metadata schema
- [x] Implement datanet and pod listing, pod epoch filtering, endpoint status, and snapshot inspection
- [x] Add synthetic fixtures and deterministic contract tests
- [x] Document differences from an official Reppo CLI
- [x] Publish a reproducible offline example

**Gate:** implemented with standard-library runtime code, public-shaped synthetic fixtures, stable JSON, no authentication support, network-free CI tests, and a live compatibility check that preserves partial data when an upstream source is unavailable.

## Phase 2 — Provenance and safety (`v0.2.0`)

- [x] Versioned source-manifest schema
- [x] Structured agent-job result schema
- [x] Cost, timeout, and freshness fields
- [ ] Dry-run and approval-control reference patterns

**Gate:** another example can consume the schemas without private project context.

## Phase 3 — Virtuals ACP reference service (`v0.3.0`)

- [ ] Select one narrowly useful ACP job
- [ ] Implement local/test mode before paid inference
- [ ] Add bounded cost, timeout, and retry behavior
- [ ] Return sources, limitations, and machine-readable receipts
- [ ] Test buyer-to-provider flow

**Gate:** end-to-end test job returns a sourced result with observable cost and failure behavior.

## Phase 4 — Community and sponsorship validation

- [ ] Obtain upstream review from Reppo and Virtuals builders
- [ ] Recruit at least three external test users
- [ ] Submit useful upstream issues or pull requests where appropriate
- [ ] Ask for a bounded 60-day inference sponsorship using shipped evidence
- [ ] Document the program terms or record that none exists

**Gate:** continue, narrow, or archive based on demonstrated use—not anticipated credits.

## Phase 5 — Launch decision

Consider a Virtuals agent launch only if the service has repeat demand, stable operations, clear economics, and manageable security exposure.
