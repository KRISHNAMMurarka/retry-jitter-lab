# Releasing

Releases package a reviewed, immutable `v*` tag. The release workflow does not
publish to PyPI; it creates a GitHub release containing a wheel, source
distribution, SHA-256 checksums, and the exact source commit.

## Maintainer checklist

1. Merge the version and changelog update through a pull request.
2. Confirm CI and CodeQL pass on `main`.
3. Create and push an annotated tag whose version matches `pyproject.toml`.
4. Run the `Release` workflow with that existing tag.
5. Approve the protected `release` environment only after the verification job
   succeeds.
6. Install the published wheel in a clean environment and compare its checksum
   with `SHA256SUMS`.

Release tags are protected against update and deletion. A failed release must
be corrected with a new version; do not move an existing tag.
