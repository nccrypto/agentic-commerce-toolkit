# Reppo inspector examples

Install the package from the repository root in an isolated environment, then produce a bounded public snapshot:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
agentic-commerce reppo snapshot --limit 5 --pretty > snapshot.json
```

For a deterministic offline demonstration, run the unit tests. They inject synthetic public-shaped fixtures into the same inspector core and make no network requests:

```bash
python3 -m unittest discover -s tests -v
```

[`datanets-envelope-v1.example.json`](datanets-envelope-v1.example.json) is a synthetic instance of the published inspector-envelope schema. The schema contract test validates this fixture with a development-only JSON Schema dependency.

Consumers should check `ok`, `partial`, and the process exit code before reading `data`. A partial snapshot keeps successful upstream objects and records the failed public source in both `sources` and `errors`.

The documented public stats route returned HTTP 404 during the 2026-07-11 compatibility check, so a live snapshot may validly return exit code `2` while still containing datanet and pod data.
