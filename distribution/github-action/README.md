# VouchSpec publisher CI profile

Use this action on trusted `main` or release workflows to create exact-commit Agent Skill
evidence. The complete public example and its attestations are in
[`mordiaky/vouchspec-demo`](https://github.com/mordiaky/vouchspec-demo).

Pin the action by full commit SHA:

```yaml
- uses: mordiaky/vouchspec/distribution/github-action@ed812a14cbc62333d59bac319f79d897f14d1b64
  with:
    skill-path: path/to/skill
```

The action creates an isolated Python 3.11 environment, installs its fully resolved Linux
runtime with `--require-hashes` and binary wheels only, confirms that `GITHUB_SHA` equals the clean checkout, runs `inspect-git` against
the exact repository bytes, and emits:

- `receipt.json`: an inner receipt draft bound to repository, commit, path, and digest;
- `publisher-ci-request.json`: repository, workflow ref, run, action ref, commit, and receipt
  hash binding;
- `structure-status`: `pass` or `fail` from the structural profile;
- `decision-status`: the receipt's evidence decision.

A structural failure is a completed evidence result: the action still emits both files so
they can be attested. Operational errors, dirty/mismatched checkouts, and unsupported inputs
still fail the action. If a publisher wants structure to be a merge or release gate, apply
that policy only after attesting the evidence.

## Complete trusted-workflow example

The workflow needs Python 3.11 on Linux x86-64 and must run before build steps modify tracked or
untracked workspace files.

```yaml
name: VouchSpec publisher evidence

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  id-token: write
  attestations: write
  artifact-metadata: write

jobs:
  inspect-and-attest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6
      - uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0
        with:
          python-version: "3.11"
      - id: vouchspec
        uses: mordiaky/vouchspec/distribution/github-action@ed812a14cbc62333d59bac319f79d897f14d1b64
        with:
          skill-path: path/to/skill
      - uses: actions/attest@a1948c3f048ba23858d222213b7c278aabede763 # v4
        with:
          subject-path: ${{ steps.vouchspec.outputs.receipt-path }}
      - uses: actions/attest@a1948c3f048ba23858d222213b7c278aabede763 # v4
        with:
          subject-path: ${{ steps.vouchspec.outputs.ci-request-path }}
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: vouchspec-publisher-evidence
          if-no-files-found: error
          path: |
            ${{ steps.vouchspec.outputs.receipt-path }}
            ${{ steps.vouchspec.outputs.ci-request-path }}
      - name: Apply the publisher's structural policy
        if: steps.vouchspec.outputs.structure-status != 'pass'
        run: exit 1
```

Attestation write permissions are unavailable to ordinary fork and Dependabot pull-request
workflows. Keep the attestation job on trusted pushes/releases, or use a separate read-only
inspection job for pull requests.

The publisher attestations establish workflow provenance for the exact files. VouchSpec
must still independently verify the GitHub attestation, workflow/repository/commit/action
bindings, and receipt hash before adding `PUBLISHER_CI_ATTESTED`, issuer-signing a receipt,
and publishing it.

The action output by itself is not a VouchSpec-signed receipt and does not carry
`PUBLISHER_CI_ATTESTED`. Publisher CI evidence is also not equivalent to
`INDEPENDENT_STATIC_SCAN` or sandbox behavior. The action accepts a relative `skill-path`
through an environment variable and never executes artifact content.

## Verify and troubleshoot

Download the workflow artifact and verify its GitHub provenance:

```bash
gh attestation verify receipt.json --repo OWNER/REPOSITORY
gh attestation verify publisher-ci-request.json --repo OWNER/REPOSITORY
```

- **Checkout mismatch:** use `actions/checkout` normally and do not replace `HEAD` before
  running VouchSpec.
- **Dirty checkout:** run VouchSpec before generated files or dependency steps write inside
  the repository.
- **Python/platform error:** use the pinned `actions/setup-python` step above on an x86-64
  Ubuntu runner; the action deliberately refuses a different runtime than its hash lock.
- **Exit after attestation:** inspect `structure-status`; a structural `fail` is evidence,
  while the optional final policy step intentionally turns it into a workflow gate.
- **Fork PR permission error:** move the attestation steps to a trusted push or release job.
