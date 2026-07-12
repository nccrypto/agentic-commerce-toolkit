# Read-only maintenance automation

The toolkit includes two public, dependency-free automation helpers. They never modify repository files or call GitHub write commands.

## Reppo compatibility watchdog

`scripts/reppo_compat_watchdog.py` probes the same three public Reppo routes used by the inspector and persists a compact compatibility signature in the user state directory.

The scheduled watchdog is pinned to the canonical `https://reppo.ai/api/v1` base; it does not accept arbitrary hosts. Its state path must remain outside the repository and is atomically written with user-only permissions.

The signature tracks only meaningful drift:

- HTTP status;
- expected JSON collection shape;
- whether the one-item pagination request is honored;
- response-size band relative to the 8 MiB cap;
- stable error category.

The first run establishes a baseline without output. Unchanged runs are also silent. A changed signature emits a concise alert once and updates the baseline, so normal catalog growth does not generate recurring noise.

This is intentionally a coarse compatibility monitor, not a complete schema-diff engine. It detects route availability, expected collection wrappers, pagination behavior, error class, and large response-size changes; deeper field-level contract checks belong in versioned fixtures and tests.

```bash
PYTHONPATH=src python3 scripts/reppo_compat_watchdog.py
```

For tests or isolated runs, use `--state-file PATH`. The default state file is outside the repository under the platform user-state directory.

## Weekly maintainer context

`scripts/toolkit_maintainer_context.py` collects bounded JSON context for a human or reasoning agent:

- local Git status;
- canonical public Git remote identity;
- unit-test result;
- public-boundary result;
- public GitHub repository metadata;
- recent GitHub Actions runs;
- open public issues.

Its command inventory is deliberately read-only: `git remote get-url`, `git status`, tests, the boundary checker, and `gh repo view`, `gh run list`, and `gh issue list`.

Before collection, the script verifies the expected public remote and required toolkit files. It does not accept another local repository while labeling it as this project. Python checks receive a minimal allowlisted environment with token/secret variables removed, bytecode writes disabled, and an isolated home. If present, `GH_TOKEN` or `GITHUB_TOKEN` is passed only to the fixed read-only `gh` commands. Tests run in a disposable copy outside the working tree, while the boundary scanner reads the real tree so forbidden files cannot be hidden by snapshot exclusions. Neither check creates or modifies repository files.

```bash
python3 scripts/toolkit_maintainer_context.py --repo .
```

The script only collects evidence. Any issue, patch, commit, push, pull request, release, merge, or repository-setting change requires separate human approval.
