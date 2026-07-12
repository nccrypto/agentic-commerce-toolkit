# Release process

Releases are human-approved, tagged from a green `main` commit, and published to GitHub. PyPI publication is not part of the v0.1.0 process.

## Prepare

1. Confirm the version matches in `pyproject.toml`, `src/agentic_commerce/__init__.py`, and the changelog.
2. Move completed entries from `Unreleased` into a dated version section.
3. Confirm `SECURITY.md` names the supported version line.
4. Open a pull request and require all checks to pass before merge.
5. Verify the merge commit is present on `origin/main` and the working tree is clean.

## Verify from a clean environment

Run from the repository root:

```bash
set -e
python3 scripts/check_public_boundary.py .
release_tmp="$(mktemp -d)"
mkdir "$release_tmp/src" "$release_tmp/dist"
PYTHONPYCACHEPREFIX="$release_tmp/pycache" python3 -m compileall -q src scripts tests
git archive HEAD | tar -x -C "$release_tmp/src"
python3 -m venv "$release_tmp/venv"
(
  cd "$release_tmp/src"
  "$release_tmp/venv/bin/python" -m pip install --disable-pip-version-check '.[dev]'
  PYTHONDONTWRITEBYTECODE=1 "$release_tmp/venv/bin/python" -B -m unittest discover -s tests -v
  "$release_tmp/venv/bin/python" -m build --outdir "$release_tmp/dist"
)

mkdir "$release_tmp/sdist"
tar -xzf "$release_tmp"/dist/*.tar.gz -C "$release_tmp/sdist"
sdist_roots=("$release_tmp"/sdist/*)
(
  cd "${sdist_roots[0]}"
  "$release_tmp/venv/bin/python" scripts/check_public_boundary.py .
  PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "$release_tmp/venv/bin/python" -B -m unittest discover -s tests -v
)

python3 -m venv "$release_tmp/install"
"$release_tmp/install/bin/python" -m pip install --disable-pip-version-check --no-deps "$release_tmp"/dist/*.whl
(
  cd "$release_tmp"
  "$release_tmp/install/bin/agentic-commerce" --help
)
(
  cd "$release_tmp/dist"
  shasum -a 256 ./*.whl ./*.tar.gz | tee SHA256SUMS
)
git diff --check
git status --short --branch
```

The final status must show no tracked or untracked release artifacts. Temporary files remain outside the repository and may be removed after verification.

## Tag and publish

For version `X.Y.Z`:

```bash
git switch main
git pull --ff-only origin main
git tag -a "vX.Y.Z" -m "Release vX.Y.Z"
git push origin "vX.Y.Z"
gh release create "vX.Y.Z" \
  "$release_tmp"/dist/*.whl \
  "$release_tmp"/dist/*.tar.gz \
  "$release_tmp"/dist/SHA256SUMS \
  --repo nccrypto/agentic-commerce-toolkit \
  --verify-tag \
  --generate-notes
```

Run the verification and publication blocks in the same shell so `release_tmp` still identifies the verified artifacts. Verify the release page, attached checksums and distributions, tag target, changelog link, and required GitHub Actions run. Do not reuse or move a published version tag; correct mistakes with a new patch release.

## Rollback

Before publication, delete a mistaken local tag with `git tag -d vX.Y.Z`. After a tag or release is public, preserve history and publish a corrective patch release rather than rewriting the tag. Security incidents should follow `SECURITY.md` and use a private GitHub security advisory.
