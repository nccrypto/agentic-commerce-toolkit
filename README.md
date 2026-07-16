# Agentic Commerce Toolkit

Open-source tools, adapters, schemas, and operational patterns for agent-native commerce, starting with Reppo and Virtuals ACP.

> **Status:** v0.1.0 released; the deterministic local Virtuals ACP reference service is currently unreleased.

## Mission

Make it easier for developers and AI agents to discover, evaluate, integrate, and safely operate agentic-commerce protocols.

Every shipped artifact should do at least one of the following:

- remove integration friction;
- provide a tested reference implementation;
- make agent actions safer or easier to audit;
- normalize ecosystem data into stable machine-readable formats;
- improve provenance, cost visibility, or operational reliability;
- solve a problem used by this project itself.

## Independence and public boundary

This is a **standalone public project**, not a mirror of or index to any non-public system. It must not depend on or disclose private repositories, local runtime state, unpublished research or content, account data, internal communications, or operational records.

Public contributions must be independently reviewable from public sources or intentionally created for this repository. See [PUBLIC_BOUNDARY.md](PUBLIC_BOUNDARY.md).

## Initial roadmap

1. **Public foundation** — governance, security, CI, and boundary checks.
2. **Reppo read-only inspector** — public API discovery and diagnostics with stable JSON.
3. **Provenance and safety schemas** — source manifests, structured agent-job results, and default-deny action controls.
4. **Virtuals ACP reference integration** — a bounded, observable example service.
5. **Community validation** — upstream feedback, external users, and a documented inference-sponsorship decision.

See [ROADMAP.md](ROADMAP.md) for release gates.

## Repository layout

```text
agentic-commerce-toolkit/
├── README.md
├── DESIGN.md
├── ROADMAP.md
├── PUBLIC_BOUNDARY.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
├── docs/
├── examples/
├── schemas/
├── scripts/
├── src/agentic_commerce/
├── tests/
└── .github/workflows/
```

## Development

Python 3.11 or newer is required. Install the console script in an isolated environment and inspect the public Reppo ecosystem:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
agentic-commerce reppo status --pretty
agentic-commerce reppo datanets --limit 20
agentic-commerce reppo pods --limit 20
agentic-commerce reppo snapshot --limit 10 --pretty
agentic-commerce virtuals-acp verify-evidence \
  --request examples/virtuals-acp-evidence/request-v1.example.json \
  --pretty
```

Runtime code uses only Python's standard library. Install the development-only schema and build tools before running the complete verification suite:

```bash
python -m pip install -e '.[dev]'
python3 -m compileall -q src scripts tests
python3 scripts/check_public_boundary.py .
python3 -m unittest discover -s tests -v
python3 -m build
```

See [docs/reppo-inspector.md](docs/reppo-inspector.md) for the JSON contract, canonical-host policy, input limits, exit codes, endpoint boundary, and failure behavior. Release maintainers should follow [docs/releasing.md](docs/releasing.md).

For portable public-source provenance records and bounded structured job results, see [docs/provenance-schemas.md](docs/provenance-schemas.md), `schemas/source-manifest-v1.schema.json`, and `schemas/agent-job-result-v1.schema.json`.

For deterministic dry-run and default-deny approval decisions, see [docs/action-controls.md](docs/action-controls.md), `schemas/action-control-v1.schema.json`, and `agentic_commerce.action_control`. The evaluator authorizes or rejects bounded actions but never executes them.

For the selected Phase 3 Virtuals ACP job, see [docs/virtuals-acp-evidence-service.md](docs/virtuals-acp-evidence-service.md), `schemas/acp-evidence-request-v1.schema.json`, and `agentic_commerce.acp_evidence`. Local mode simulates a buyer/provider evidence-verification lifecycle, emits a conforming job-result receipt, and performs no wallet, payment, signing, inference, or network operation.

For silent compatibility drift detection and bounded weekly project evidence, see [docs/automation.md](docs/automation.md). These helpers are read-only and never perform GitHub mutations.

At the 2026-07-11 compatibility check, the datanet and pod catalogs were live. The documented public stats route returned HTTP 404, so `status` and `snapshot` correctly returned partial result code `2` while preserving catalog data. The upstream pods route also ignored its requested page size; the client applies the requested limit after a capped download.

## Project status and affiliation

This is an independent community project. It is not endorsed by, operated by, or officially affiliated with Reppo Labs, Virtuals Protocol, or their contributors unless an explicit written relationship is later documented.

## License

MIT — see [LICENSE](LICENSE).
