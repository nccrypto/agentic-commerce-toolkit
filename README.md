# Agentic Commerce Toolkit

Open-source tools, adapters, schemas, and operational patterns for agent-native commerce, starting with Reppo and Virtuals ACP.

> **Status:** Public-foundation scaffold. The first executable integration is planned but not yet released.

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

This is a **standalone public project**. It is not a mirror of any private research, content, investment, wallet, or Hermes runtime repository.

Specifically, it must not import or publish private material from:

- Hermes Guardian or the wider private Hermes agent fleet;
- Reppo Helper research briefs and local operating state;
- CNC strategy, content queues, or unpublished drafts;
- private wallet, inference, trading, or partner data;
- local agent memories, sessions, credentials, logs, or generated reports.

Public contributions must be independently reviewable from public sources or intentionally created for this repository. See [PUBLIC_BOUNDARY.md](PUBLIC_BOUNDARY.md).

## Initial roadmap

1. **Public foundation** — governance, security, CI, and boundary checks.
2. **Reppo read-only inspector** — public API/RPC discovery and diagnostics with stable JSON.
3. **Provenance schemas** — source manifests and structured agent-job results.
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
├── tests/
└── .github/workflows/
```

## Development

The current boundary checker uses only Python's standard library:

```bash
python3 scripts/check_public_boundary.py .
python3 -m unittest discover -s tests -v
```

## Project status and affiliation

This is an independent community project. It is not endorsed by, operated by, or officially affiliated with Reppo Labs, Virtuals Protocol, or their contributors unless an explicit written relationship is later documented.

## License

MIT — see [LICENSE](LICENSE).
