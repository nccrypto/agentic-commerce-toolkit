# Community validation examples

Phase 4 uses these public-safe artifacts to collect reproducible external testing evidence:

- `test-result-v1.example.json` — deterministic output from the network-free validation harness;
- `feedback-template.md` — bounded qualitative feedback with an explicit public-sharing review.

Generate a fresh local result from the public repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -B \
  scripts/run_community_validation.py \
  --validation-id community:test-run:001 \
  --revision YOUR_PUBLIC_REVISION \
  --pretty > community-validation-result.json
```

Generated records default both sharing flags to `false`. See [`docs/community-validation.md`](../../docs/community-validation.md) before changing or submitting them.

The committed example is synthetic maintainer evidence that the harness works. It does not count as one of the three required external users and does not claim upstream review, endorsement, sponsorship, or live ACP execution.
