# Dry-run and approval controls

The toolkit provides a default-deny reference pattern for evaluating bounded actions before any external execution.

## Artifacts

- `schemas/action-control-v1.schema.json` defines the portable control-decision contract.
- `agentic_commerce.action_control` computes action digests and evaluates dry-run or execute requests without performing them.
- `examples/action-control/` contains deterministic synthetic dry-run and authorized-action records.

## Decision model

Every control record contains a bounded request, an optional approval, and a decision:

| Request or approval state | Decision | `mayExecute` |
| --- | --- | --- |
| `dry-run` | `dry-run` / `DRY_RUN_ONLY` | `false` |
| `execute` without approval | `rejected` / `APPROVAL_REQUIRED` | `false` |
| rejected approval | `rejected` / `APPROVAL_REJECTED` | `false` |
| expired approval | `rejected` / `APPROVAL_EXPIRED` | `false` |
| mismatched action scope | `rejected` / `APPROVAL_SCOPE_MISMATCH` | `false` |
| valid matching approval | `authorized` / `APPROVED` | `true` |

The evaluator never executes an action. `mayExecute: true` means only that a separate execution adapter may proceed after re-checking the decision at its own boundary.

## Approval scope

An approval is bound to:

- a stable public `actionId`;
- a bounded `actionType`;
- an `actionDigest` computed over the identifier, type, summary, and ordered public parameters;
- unique parameter names, bounded scalar values, and finite numeric magnitudes;
- an issue and expiration interval;
- an explicit approved or rejected decision.

The request mode is excluded from the digest so the exact action first evaluated in dry-run mode can later be submitted in execute mode without changing its scope. Changing the action summary or any parameter changes the digest and invalidates the approval.

JSON Schema cannot compare timestamps or cross-check digest equality. The standard-library evaluator performs those checks deterministically and defaults to denial when an approval is absent, malformed, expired, or scoped to another action.

## Public boundary

Only public, bounded action summaries and parameters belong in these records. Never include credentials, signing material, wallet or account data, private billing records, internal budgets, private communications, local paths, or private runtime identifiers.

This is a control pattern, not a signing or transaction API. Future write-capable adapters must separately document simulation, idempotency, budgets, signer assumptions, and recovery behavior.
