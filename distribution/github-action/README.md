# CapabilityProof composite action (local prototype)

This action is a source prototype, not a published GitHub Marketplace action. It installs
the exact repository checkout and generates an unsigned Level 1/3 evidence receipt. Pin a
future public action by commit SHA; do not use an unpinned branch in a production workflow.

`skill-path` must be relative to `GITHUB_WORKSPACE`. The prototype writes
`capability-receipt.json` at the workspace root. It is a local CI integration only, not an
external artifact-intake service.
