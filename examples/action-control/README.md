# Action-control examples

These synthetic examples exercise `schemas/action-control-v1.schema.json` and the deterministic evaluator in `agentic_commerce.action_control`.

- `dry-run-v1.example.json` demonstrates that a dry-run never consumes an approval and always returns `mayExecute: false`.
- `authorized-action-v1.example.json` demonstrates an unexpired human approval scoped to the exact action identifier, type, summary, and bounded parameters through a SHA-256 action digest.

An `authorized` decision is not proof of execution and does not perform an action. A separate adapter would need to re-check the decision at its execution boundary. This repository does not provide a transaction writer, signer, wallet integration, or live mutation API.

The examples contain public synthetic identifiers and parameters only. Do not place credentials, wallet or account data, private runtime state, internal budgets, private communications, or local paths in action requests or approvals.
