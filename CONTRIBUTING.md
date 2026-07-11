# Contributing

Contributions are welcome when they make agentic-commerce integrations more useful, reproducible, safe, or interoperable.

## Before opening a pull request

1. Confirm the change addresses a documented issue or clearly described user problem.
2. Use public sources and compatible licenses.
3. Do not include production credentials, wallet data, private logs, or copied private research.
4. Add tests or reproducible verification notes.
5. Preserve structured outputs and stable error behavior where applicable.
6. Run:

```bash
python3 scripts/check_public_boundary.py .
python3 -m unittest discover -s tests -v
```

## Pull-request expectations

Describe:

- the problem;
- the public sources or upstream APIs used;
- security and privacy implications;
- commands used to verify the change;
- compatibility or rollback considerations.

Protocol write operations require dry-run support, bounded budgets, idempotency, and explicit documentation of signing behavior.
