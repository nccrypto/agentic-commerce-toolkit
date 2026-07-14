# Agent job result example

This directory contains synthetic examples for `schemas/agent-job-result-v1.schema.json`.

The v1 envelope records a stable public job identifier, job type and status, timestamps, a bounded request summary, structured output, source-manifest provenance, errors, and limitations. A failed job uses `null` for `result` and includes at least one error; successful and partial jobs include a structured result object.

The example is intentionally public-only and bounded:

- request inputs are named scalar values or bounded scalar arrays;
- result strings, arrays, and objects have per-container and finite nesting limits;
- provenance refers to a public source manifest by stable identifier and optional public URL;
- no credentials, wallets, account identifiers, local paths, private runtime state, or unbounded blobs are included.

Cost, timeout, and freshness fields are intentionally deferred to the next Phase 2 roadmap item.
