# Upstream review request drafts

These are review drafts, not evidence that outreach occurred. Sending a request, opening an issue, or submitting a pull request is a separate human-approved action.

Before using either draft:

1. verify all linked artifacts are present on the public default branch;
2. rerun the relevant live compatibility check;
3. remove observations that are stale or cannot be reproduced;
4. use an upstream project's preferred public contribution channel;
5. record only public response links in this repository.

## Reppo builder review

### Suggested title

```text
Feedback request: public inspector behavior and portable provenance contracts
```

### Draft

```text
We maintain the independent Agentic Commerce Toolkit, which includes a
standard-library, read-only inspector for Reppo's documented public catalog
endpoints and portable source-manifest / agent-job-result schemas.

Project:
https://github.com/nccrypto/agentic-commerce-toolkit

Inspector documentation:
https://github.com/nccrypto/agentic-commerce-toolkit/blob/main/docs/reppo-inspector.md

Provenance contracts:
https://github.com/nccrypto/agentic-commerce-toolkit/blob/main/docs/provenance-schemas.md

We would value upstream review of four bounded questions:

1. Are the public endpoint boundaries and partial-result semantics still
   consistent with the intended public API?
2. Is preserving upstream objects inside a stable outer envelope preferable
   to normalizing their internal field names?
3. Are the source-manifest and agent-job-result contracts useful for public
   agent workflows consuming Reppo data?
4. Did our freshly reproduced compatibility observations identify a current
   documentation or API-behavior gap that should be reported separately?

The inspector has no authentication, write, wallet, or transaction support.
Its CI tests use synthetic fixtures and do not contact live services.

We are requesting technical feedback, not endorsement. We will record any
limitations or corrections in the public project.
```

### Required fresh evidence

Do not mention an unavailable route, ignored pagination parameter, or other behavior unless it has been rerun immediately before outreach and recorded without private logs or credentials.

## Virtuals ACP builder review

### Suggested title

```text
Feedback request: local ACP public-evidence provider and receipt mapping
```

### Draft

```text
We maintain the independent Agentic Commerce Toolkit and have implemented a
network-free Virtuals ACP reference provider for one bounded job: public
evidence verification.

Project:
https://github.com/nccrypto/agentic-commerce-toolkit

Reference-service documentation:
https://github.com/nccrypto/agentic-commerce-toolkit/blob/main/docs/virtuals-acp-evidence-service.md

Synthetic offering:
https://github.com/nccrypto/agentic-commerce-toolkit/blob/main/examples/virtuals-acp-evidence/offering-v1.example.json

The buyer supplies a source manifest plus an agent-job result. The provider
checks contract shape, provenance linkage, and public HTTPS source policy,
then returns the existing agent-job-result contract as a machine-readable
receipt.

Local mode simulates open → budget_set → funded → submitted → completed, but
performs no ACP authentication, registration, signing, wallet operation,
payment, settlement, inference, or network request. The offering example is
hidden and has not been registered.

We would value review of five bounded questions:

1. Do the requirement and deliverable shapes map cleanly to the current ACP
   offering model?
2. Is reusing a structured agent-job result as the provider receipt practical?
3. Does the documentation distinguish simulated lifecycle states clearly
   enough from live on-chain settlement?
4. What boundary would you recommend for a future adapter to acp-cli or
   acp-node-v2 while keeping the verifier itself deterministic and testable?
5. Is this provider-side evidence job sufficiently distinct from existing
   evaluator/recompute examples?

We are requesting technical feedback, not endorsement, credits, listing, or
promotion. Corrections and limitations will be recorded publicly.
```

## Upstream contribution rule

A review request is not permission to create unrelated upstream work. Open an issue or pull request only when a fresh, reproducible observation identifies a concrete documentation, compatibility, or interoperability gap. If no useful contribution is warranted, record that outcome instead of manufacturing activity.

## Review evidence record

Do not populate this table with private messages or contact information.

| Upstream | Public request URL | Public response URL | Material correction or recommendation | Status |
|---|---|---|---|---|
| Reppo | — | — | — | not sent |
| Virtuals | — | — | — | not sent |

## Bounded 60-day sponsorship request outline

This outline is intentionally incomplete until community testing demonstrates an inference-backed need.

```text
Subject: Bounded 60-day public integration validation request

Shipped evidence:
- public repository and release/commit;
- qualifying community-validation evidence;
- upstream technical review links;
- exact proposed inference-backed workload;
- measured or conservatively bounded usage.

Requested term:
- exactly 60 days;
- exact total credit cap: TO BE DERIVED FROM MEASURED USAGE;
- exact daily or weekly cap: TO BE DERIVED FROM MEASURED USAGE;
- permitted use: public toolkit validation workload only;
- automatic expiry after the term;
- no production-wallet custody or private-data processing.

Terms to clarify:
- eligible models and endpoints;
- telemetry and data retention;
- rate limits and revocation;
- unused-credit expiry;
- attribution requirements;
- whether exclusivity, token launch, deposits, or other obligations apply.

The toolkit does not assume approval, renewal, endorsement, or future credits.
```

Record one public outcome: accepted, declined, no applicable program, unsuitable terms, unnecessary, or deferred for insufficient demand.
