# Provenance schemas

The toolkit's provenance schemas provide portable, public-only records for the sources and evidence behind agentic-commerce artifacts.

## Source manifest v1

`schemas/source-manifest-v1.schema.json` defines a manifest for documenting public sources used by a job, dataset, inspector output, compatibility check, or future reference service.

A conforming manifest records:

- `schemaVersion` — currently `1.0`;
- `manifestId` — a stable, non-secret identifier;
- `generatedAt` — when the manifest was produced;
- `subject` — the public artifact or topic the manifest describes;
- `sources` — one or more public source records;
- optional `notes` — bounded public notes.

Each source record includes:

- a stable `sourceId`;
- title, URL, type, publisher, and access time;
- optional license, version, retrieval time, or SHA-256 digest;
- a `usage` section describing why the source was used, what public facts were derived, and known limitations.

## Boundary rules

Source manifests must not contain credentials, private keys, wallet exports, local runtime state, private communications, unpublished research, or absolute local paths. Use public URLs, intentionally authored descriptions, and synthetic examples.

Manifests are provenance records, not proof that a source is still reachable or authoritative. Consumers should treat them as evidence to review and should re-check upstream sources when freshness matters.

## Example

See `examples/source-manifest/reppo-public-api-manifest-v1.example.json` for a synthetic manifest describing public Reppo inspector inputs.
