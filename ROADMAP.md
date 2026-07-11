# Roadmap

## Release policy

A phase is complete only when its artifacts are exercised and its verification gate passes. Dates are intentionally omitted until maintainers approve implementation capacity.

## Phase 0 — Public foundation

- [x] Standalone local Git repository scaffold
- [x] Public/private boundary policy
- [x] Security and contribution policies
- [x] Deterministic boundary checker and tests
- [ ] Public GitHub remote created after explicit approval
- [ ] Branch protection and required CI configured

**Gate:** clean boundary scan, tests pass, no remote dependency on a private project.

## Phase 1 — Reppo read-only inspector (`v0.1.0`)

- [ ] Confirm supported public endpoints against current official documentation
- [ ] Define normalized status and provenance schemas
- [ ] Implement datanet, pod, epoch, and endpoint-health inspection
- [ ] Add fixtures and contract tests
- [ ] Document differences from the official Reppo CLI
- [ ] Publish a reproducible demo

**Gate:** clean install, public-source-only fixtures, stable JSON, no private key required.

## Phase 2 — Provenance and safety (`v0.2.0`)

- [ ] Versioned source-manifest schema
- [ ] Structured agent-job result schema
- [ ] Cost, timeout, and freshness fields
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
