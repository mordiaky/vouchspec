# VouchSpec publisher CI profile

The source action is public. A publisher must pin it by full commit SHA:

```yaml
- uses: mordiaky/vouchspec/distribution/github-action@4404b7a9a2d3dc45b621ea694d2ca7ad666b9898
  with:
    skill-path: path/to/skill
```

The action confirms that `GITHUB_SHA` equals the clean checkout, runs
`inspect-git` against the exact repository bytes, and emits:

- `receipt.json` — an inner receipt draft bound to repository, commit, path, and digest;
- `publisher-ci-request.json` — repository, workflow ref, run, action ref, commit, and receipt
  hash binding.

The publisher then uses GitHub's pinned artifact-attestation action to attest both outputs.
VouchSpec must independently verify GitHub's attestation, workflow/repository/commit/action
bindings, and receipt hash before adding `PUBLISHER_CI_ATTESTED`, issuer-signing the receipt,
and publishing it.

The action output by itself is not a VouchSpec-signed receipt and does not carry
`PUBLISHER_CI_ATTESTED`. Publisher CI evidence is also not equivalent to
`INDEPENDENT_STATIC_SCAN` or sandbox behavior.

The action accepts a relative `skill-path` only through an environment variable and never
executes artifact content.
