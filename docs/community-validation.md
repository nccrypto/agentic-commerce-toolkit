# Community validation protocol

## Purpose

Phase 4 tests whether the toolkit is useful to people outside its maintainers. This protocol gives external users a reproducible, network-free way to exercise the Phase 3 Virtuals ACP reference service and return bounded public evidence.

Running the protocol does not contact Reppo, Virtuals, GitHub, a wallet, an inference provider, or any other remote service. Nothing is uploaded automatically.

## What the harness checks

`scripts/run_community_validation.py` exercises four synthetic behaviors:

1. the published evidence bundle produces a passing receipt and exit code `0`;
2. a provenance mismatch produces a completed finding and exit code `2`;
3. bounded retry exhaustion produces a sanitized failed receipt and exit code `1`;
4. the passing flow remains local, zero-cost, and explicitly simulated.

The result conforms to `schemas/community-validation-result-v1.schema.json`. It intentionally excludes usernames, hostnames, architecture, local paths, wallets, accounts, raw logs, and environment variables.

## Tester protocol

### 1. Use a clean public checkout

Clone the public repository or update an existing public-only checkout. Do not run this protocol from a directory containing copied private artifacts.

Record the public revision:

```bash
git rev-parse --short=12 HEAD
```

### 2. Run the complete repository checks

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -B \
  -m unittest discover -s tests -q
python3 scripts/check_public_boundary.py .
git diff --check
python3 -m compileall -q src scripts tests
```

No package installation is required for the runtime harness. The complete schema-contract tests require the repository's documented development environment.

### 3. Generate the bounded validation result

The maintainer should assign a non-personal validation ID such as `community:test-run:001`. Do not put a name, email address, account ID, wallet address, hostname, or local directory in the ID.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.11 -B \
  scripts/run_community_validation.py \
  --validation-id community:test-run:001 \
  --revision YOUR_PUBLIC_REVISION \
  --pretty > community-validation-result.json
```

Expected command exit code: `0`.

Expected result:

- top-level `status` is `passed`;
- all four checks have `status: pass`;
- `errors` is empty;
- both `sharing` flags are `false`.

The false sharing flags are deliberate. Generation is not publication approval.

### 4. Review before sharing

Open `community-validation-result.json` and verify that it contains no:

- local or home-directory path;
- username, hostname, email address, or contact detail;
- account, wallet, transaction, or payment identifier;
- credential, token, cookie, environment variable, or raw log;
- private project name, communication, research, or report.

After completing that human review, a tester who chooses to submit the record may set:

```json
"sharing": {
  "reviewedForSensitiveData": true,
  "publicSubmissionApproved": true
}
```

Do not change those flags on another person's behalf.

### 5. Provide bounded feedback

Use `examples/community-validation/feedback-template.md`. A tester may submit the reviewed JSON and feedback through a public GitHub issue or pull request when the maintainer opens an approved collection channel.

Until such a channel exists, keep the result local. Do not send it through private communications for later copying into this repository.

## What counts as an external test user

A Phase 4 test counts only when all of the following are true:

- the person is not acting as the toolkit maintainer for that run;
- they run the protocol against a public revision;
- the machine-readable result passes the schema contract;
- they provide at least one concrete observation in the feedback template;
- they intentionally approve any public submission;
- the maintainer records a public evidence link after review.

Expressions of interest, maintainers running the harness three times, copied results, or unpublished private feedback do not count toward the roadmap target.

Recommended tester mix:

1. one schema consumer;
2. one command-line user working from a fresh checkout;
3. one ACP builder able to assess the offering and lifecycle mapping.

## Maintainer evidence table

Do not add a row until public evidence exists.

| Validation ID | Public revision | Tester perspective | Result evidence | Feedback evidence | Counted |
|---|---|---|---|---|---|

The table must link only to intentionally public artifacts. It must not record private contact details or summarize private conversations.

## Decision criteria

After at least three qualifying tests and upstream review attempts, record one outcome:

- **continue** — repeat use and a concrete next integration need are demonstrated;
- **narrow** — schemas or inspection are useful, but a live ACP provider is not justified;
- **archive** — external reproduction or demand is not demonstrated.

Inference credits alone cannot determine the outcome.

## Sponsorship gate

Do not request inference sponsorship until:

- three external test users have qualifying public evidence;
- Reppo and Virtuals review requests have been made through approved public channels;
- a real inference-backed next step is identified;
- expected usage has been measured or bounded without inventing demand.

The current local service uses no inference, so it provides no evidence for a credit amount. Any later request should state an exact 60-day term, a hard total cap, periodic caps, permitted public workloads, data-retention terms, revocation conditions, expiry behavior, and the absence of any assumed token launch, exclusivity, wallet custody, or private-data access.

Record the outcome even if no applicable program exists, terms are unsuitable, or sponsorship is unnecessary.
