# Schemas

- `inspector-envelope-v1.schema.json` — stable top-level contract for Reppo inspector output.
- `../examples/reppo-inspector/datanets-envelope-v1.example.json` — synthetic conforming example validated in CI.
- `source-manifest-v1.schema.json` — public-source provenance manifest for agentic-commerce artifacts.
- `../examples/source-manifest/reppo-public-api-manifest-v1.example.json` — synthetic conforming source-manifest example validated in CI.
- `agent-job-result-v1.schema.json` — bounded public result envelope for structured agent jobs, including optional cost, timeout, and freshness metadata.
- `../examples/agent-job-result/reppo-inspection-result-v1.example.json` — synthetic conforming agent-job result validated in CI.
- `action-control-v1.schema.json` — default-deny dry-run and approval-control decision contract.
- `../examples/action-control/` — synthetic dry-run and authorized-action examples validated in CI.
- `acp-evidence-request-v1.schema.json` — bounded request envelope for the Virtuals ACP public-evidence verification job.
- `../examples/virtuals-acp-evidence/` — synthetic request, receipt, and hidden offering examples validated in CI.
- `community-validation-result-v1.schema.json` — bounded, public-safe result contract for external validation runs.
- `../examples/community-validation/test-result-v1.example.json` — synthetic community-validation result validated in CI.

Versioned JSON schemas for additional safety patterns will live here.
