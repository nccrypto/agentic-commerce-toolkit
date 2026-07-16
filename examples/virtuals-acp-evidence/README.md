# Virtuals ACP public-evidence examples

These synthetic fixtures exercise the Phase 3 local buyer/provider reference flow:

- `request-v1.example.json` bundles the existing public source-manifest and agent-job result examples.
- `receipt-v1.example.json` is the deterministic provider output at `2026-07-15T12:15:00Z` with zero elapsed time.
- `offering-v1.example.json` maps the job to the current public ACP CLI offering fields but remains hidden and unregistered.

Regenerate the receipt from the request:

```bash
PYTHONPATH=src python3.11 - <<'PY'
import json
from pathlib import Path
from agentic_commerce.acp_evidence import run_local_evidence_job

request = json.loads(
    Path("examples/virtuals-acp-evidence/request-v1.example.json").read_text()
)
receipt = run_local_evidence_job(
    request,
    clock=lambda: "2026-07-15T12:15:00Z",
    monotonic=lambda: 100.0,
)
print(json.dumps(receipt, indent=2))
PY
```

The committed request conforms to `schemas/acp-evidence-request-v1.schema.json`. The receipt conforms to the existing `schemas/agent-job-result-v1.schema.json`.

The fixtures contain no ACP authentication, wallet identifiers, signatures, transactions, account data, paid inference, private runtime state, or claims of live marketplace execution.
