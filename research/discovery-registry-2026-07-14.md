# Discovery and registry decision — 2026-07-14

## Decision

Keep the current machine-readable GitHub discovery live. Prepare, but do not submit, an
official MCP Registry listing or GitHub Marketplace action listing in this cycle.

This is an eligibility and authority decision, not a marketing delay:

- The official MCP Registry is in preview and stores metadata for a public package or public
  remote server. Its quickstart requires publishing the underlying package first, then
  authenticating `mcp-publisher` and publishing a `server.json` whose namespace and package
  metadata can be verified. VouchSpec currently installs its stdio MCP from a Git repository;
  it does not yet have a Registry-supported published package or public remote endpoint.
- GitHub Actions Marketplace requires a dedicated public repository with a root `action.yml`,
  one action metadata file, no workflow files, a unique name, a release, two-factor
  authentication, and acceptance of the Marketplace Developer Agreement. The current
  VouchSpec repository is a multi-purpose product repository with its action in a subdirectory
  and workflows present.
- Accepting new marketplace terms or performing owner-bound OAuth/2FA is reserved for the
  owner. Preparing compatible packaging and metadata remains autonomous work.

## Valid next preparation

1. Publish the stdio MCP as a supported public package with installation metadata that binds
   the registry name; generate and validate the current-schema `server.json`; then request the
   minimum owner authentication required to publish.
2. If Marketplace discovery is still valuable, split the composite action into a dedicated
   root-action repository without workflows, preserve immutable source pins and provenance,
   validate metadata/name eligibility, and stop at the Developer Agreement/2FA gate.
3. Continue current zero-cost discovery through the public repository, discovery JSON, demo,
   action documentation, and repository-specific integrations.

## Official sources checked

- [MCP Registry overview](https://modelcontextprotocol.io/registry/about)
- [MCP Registry publishing quickstart and current schema](https://modelcontextprotocol.io/registry/quickstart)
- [MCP Registry versioning](https://modelcontextprotocol.io/registry/versioning)
- [GitHub Actions Marketplace publishing prerequisites](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace)
- [GitHub Marketplace Developer Agreement](https://docs.github.com/en/site-policy/github-terms/github-marketplace-developer-agreement)

No listing was claimed, no package metadata was fabricated, and no new terms were accepted.
