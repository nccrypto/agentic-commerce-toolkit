# Reppo read-only ecosystem inspector

Version 0.1.0 inspects only these unauthenticated public GET endpoints:

- `GET /stats`
- `GET /public/subnets?page=&limit=&search=`
- `GET /public/pods?page=&limit=&search=&filters[currentEpoch]=&filters[subnet]=`

The default API base is `https://reppo.ai/api/v1`. `--base-url` supports a public-compatible mirror or local test server; URLs containing credentials, query strings, or fragments are rejected.

## Install and run

Python 3.11 or newer is required. Runtime code uses only the standard library. Install into an isolated environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
agentic-commerce reppo status --pretty
agentic-commerce reppo datanets --page 1 --limit 20 --search text
agentic-commerce reppo pods --datanet public-id --epoch 0 --limit 20
agentic-commerce reppo snapshot --limit 10 --pretty
```

All successful command execution and handled failures write one JSON document to stdout. The stable top-level fields are `schemaVersion`, `command`, `generatedAt`, `ok`, `partial`, `sources`, `data`, and `errors`. Upstream objects are preserved under `data`; the inspector does not rename or synthesize upstream fields. The contract is described by [`schemas/inspector-envelope-v1.schema.json`](../schemas/inspector-envelope-v1.schema.json).

## Exit codes

- `0`: every requested public endpoint succeeded.
- `1`: validation failed, an individual command failed, or every status/snapshot source failed.
- `2`: status or snapshot retained some successful sources while one or more other sources failed.

## Safety and failure behavior

The client sends an explicit user agent and `Accept: application/json`, refuses redirects to other routes, applies a bounded timeout and an 8 MiB response cap, and validates JSON response shape. Page, limit, and timeout must be positive; epoch must be nonnegative. Errors use fixed codes and generic messages so exception details and response bodies do not leak into output.

The inspector validates the documented `data.subnets` and `data.pods` arrays. Because the public pods route ignored `limit` during the 2026-07-11 compatibility check, the inspector also slices a successfully parsed collection to the requested limit before writing JSON. The transport cap remains authoritative: if the upstream catalog grows beyond 8 MiB, the request fails with `RESPONSE_TOO_LARGE` instead of consuming unbounded memory.

The inspector has no authentication support and does not call account, wallet, transaction, or other protected routes. Tests use only synthetic fixtures and never call the live service.

## Current upstream compatibility

Live verification on 2026-07-11 produced:

- public datanets: HTTP 200, documented nested collection shape;
- public pods: HTTP 200, documented nested collection shape, pagination ignored upstream;
- documented public stats route: HTTP 404.

Accordingly, `datanets` and `pods` can succeed independently. `status` and `snapshot` currently return exit code `2` with `partial: true`, retain successful datanet/pod data, and record the stats 404 as `HTTP_ERROR`. This is intentional evidence of source health, not a fabricated healthy result.

## Difference from an official CLI

This project provides a narrow, read-only, JSON-contract inspector for automation and diagnostics. It is not an account or wallet client, does not submit transactions, and is not intended to replace an official Reppo CLI or SDK.
