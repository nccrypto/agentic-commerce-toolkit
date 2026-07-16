# Virtuals ACP public-evidence reference service

## Selected Phase 3 job

**Job type:** `virtuals-acp.public-evidence-verification`

A buyer supplies two public artifacts:

1. a candidate `source-manifest-v1` document;
2. a candidate `agent-job-result-v1` document.

The provider checks both contracts, verifies manifest and source-identifier linkage, applies a public HTTPS source-location policy, and returns an `agent-job-result-v1` receipt. This is narrowly useful for buyers that need a portable checker before accepting or composing an agent deliverable.

The first implementation is deterministic **local mode**. It performs no ACP authentication, agent registration, wallet operation, signing, transaction, escrow funding, payment, inference call, or network request.

## Why this job

The job reuses the toolkit's provenance and result contracts instead of creating a parallel vocabulary. Its output can be checked independently, does not need inference, and remains useful without a grant, token, or hosted agent.

It complements rather than duplicates current official examples:

- the active ACP CLI supports offerings with JSON-schema requirements and deliverables;
- the ACP Node SDK v2 documents an event-driven buyer/provider lifecycle and role-gated actions;
- the official aiport showcase recomputes on-chain actions in ACP's evaluator role, whereas this service checks portable public evidence as a provider deliverable;
- the official Agent Supply Chain showcase demonstrates deterministic local buyer-side planning, but not this evidence contract.

## Public upstream observations

Observed at `2026-07-15T12:09:27Z` from public Virtuals Protocol repositories:

| Source | Observation |
|---|---|
| [`Virtual-Protocol/acp-cli`](https://github.com/Virtual-Protocol/acp-cli) | Active package version observed as `1.0.24`; supports JSON output, offering requirement/deliverable schemas, job queries, and the documented job lifecycle. |
| [`Virtual-Protocol/acp-node-v2`](https://github.com/Virtual-Protocol/acp-node-v2) | Current Node v2 SDK documents event-driven `AcpAgent`/`JobSession` behavior and role-gated job tools. |
| [`Virtual-Protocol/acp-cli-demos`](https://github.com/Virtual-Protocol/acp-cli-demos) | Public showcases include evaluator verification and deterministic local orchestration patterns. |
| [`Virtual-Protocol/acp-python`](https://github.com/Virtual-Protocol/acp-python) | Public Python SDK remains available, but its documented live examples require wallet and agent configuration that local mode intentionally avoids. |

The official repositories identify `openclaw-acp` and the older `acp-node` surface as deprecated. This reference therefore documents future integration against `acp-cli`/`acp-node-v2`, not those retired interfaces. Upstream behavior can drift; the offering example remains hidden and is not registered automatically.

## Contracts

### Request

`schemas/acp-evidence-request-v1.schema.json` defines the bounded transport envelope:

- stable request ID and job type;
- explicit `local` or future `virtuals-acp` mode;
- candidate source manifest;
- candidate agent-job result;
- no undeclared transport fields.

The candidate documents are intentionally accepted as bounded objects at the transport boundary. The provider must be able to return useful contract findings for a malformed candidate rather than having the marketplace reject it before verification.

The runtime also enforces a 1,000,000-byte canonical request limit.

### Receipt

The provider reuses `schemas/agent-job-result-v1.schema.json`. A successful service run records:

- `verdict`: `pass` or `fail`;
- four named checks and bounded findings;
- sanitized public source references;
- lifecycle states;
- attempt count;
- zero measured local cost;
- timeout and freshness observations;
- explicit limitations.

A `fail` verdict means verification completed and found a contract, linkage, or location-policy problem. It is not a provider crash. Provider timeout or retry exhaustion instead returns `status: failed`, `result: null`, and a stable error code.

## Run local mode

From the repository root, without installation:

```bash
PYTHONPATH=src python3.11 -m agentic_commerce \
  virtuals-acp verify-evidence \
  --request examples/virtuals-acp-evidence/request-v1.example.json \
  --pretty
```

The synthetic fixture returns exit code `0` and matches `receipt-v1.example.json` apart from ordinary clock/elapsed fields when a real clock is used.

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | Provider completed verification and every check passed. |
| `1` | Input could not be read, or the provider timed out/failed. |
| `2` | Provider completed verification and one or more checks failed. |

## Local buyer/provider lifecycle

The passing fixture records:

```text
open → budget_set → funded → submitted → completed
```

These are simulated protocol states. `funded` means only that the synthetic buyer advanced through the local state machine; no funds are created or moved. A service-level failure ends at `rejected`.

The provider retries only `TransientProviderError`, at most three attempts by default and never more than ten. Other exceptions fail immediately and their private exception text is not copied into the public receipt. Timeout is measured across all attempts.

## Offering mapping

`examples/virtuals-acp-evidence/offering-v1.example.json` is shaped for the current ACP CLI offering fields:

- name and description;
- fixed public price;
- five-minute SLA;
- JSON-schema requirements and deliverable summaries;
- `requiredFunds: false`;
- `isHidden: true`.

The `0.01` price is illustrative metadata for a future test offering. Local execution always reports zero cost. The example has not been submitted to Virtuals ACP and must not be treated as a live listing.

A future live adapter must remain separate from the verifier and require explicit approval before registration, job creation, funding, submission, completion, or rejection. It must not collect private keys or print authentication material.

## Verification scope and limitations

The provider checks:

- bounded v1 contract shape and field semantics;
- RFC 3339 timestamps and result timing order;
- provenance manifest-ID equality;
- referenced source IDs exist in the manifest;
- source and manifest locations are public HTTPS URLs without user info, private IP literals, local hostnames, or non-HTTPS ports.

A pass does **not** prove:

- that a publisher's claims are true;
- that a URL remains available;
- that content has not changed unless a separately verified digest is present;
- that an ACP payment or settlement occurred;
- that a real provider, buyer, or evaluator participated.

No live ACP operation should be inferred from the synthetic receipt.
