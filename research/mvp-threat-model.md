# CapabilityProof hostile-input threat model and security acceptance checklist

- **Status:** Proposed security gate for the non-executing MVP
- **Date:** 2026-07-13
- **Scope:** Exact-version, Level 1-3 static inspection of Agent Skill artifacts containing a root `SKILL.md`
- **Internal basis:** `AGENTS.md`, `CHARTER.md`, `RISK_REGISTER.md`, and `OFFER.md`
- **Budget assumption:** USD $0; controls use application and operating-system facilities, free test tooling, and pinned dependencies

## Decision summary

The safe MVP shape is deliberately narrow:

1. Treat every submitted byte, path, filename, metadata field, Markdown fragment, YAML value, URL, command, and finding excerpt as attacker-controlled data.
2. Accept a ZIP byte stream for externally supplied artifacts. A local-directory mode may exist for an operator, but it must capture a bounded no-follow snapshot and must never be exposed as an arbitrary remote filesystem path.
3. Hash the immutable bytes that are actually parsed. Never hash one source and later parse or fetch another.
4. Inspect ZIP entries without extracting them to the host filesystem. Accept only regular files and directories; reject links and special files.
5. Do not import, execute, compile, render, preview, shell out to, install from, or semantically follow any artifact content. Artifact text is never control-plane input.
6. Do not fetch submitted URLs in this MVP. HTTP accepts uploaded bytes; remote MCP accepts an opaque upload handle. Safe repository fetching is a separate, deferred component.
7. Enforce limits while streaming, not only from attacker-controlled metadata.
8. Emit a canonical, schema-valid receipt whose payload is bound to the submitted envelope, logical file tree, methodology, policy limits, and time. Digest-only receipts are explicitly unauthenticated until signing is implemented.

This model does **not** establish that an artifact is safe, benign, complete, licensed, or fit to execute. It establishes only what deterministic, bounded, non-executing checks observed for exact captured bytes.

## Normative language and release profiles

- **MUST / MUST NOT**: launch-blocking requirements for the applicable profile.
- **SHOULD**: expected defense in depth; a deviation needs a written rationale and compensating control.
- **DEFERRED**: intentionally absent from the non-executing MVP and must not be reached through a fallback path.

Two profiles are distinct:

- **Local development profile:** synthetic/public fixtures only, no network listener, no customer data, and no claim of production readiness.
- **External launch profile:** any untrusted third party can submit or cause inspection of an artifact through HTTP, remote MCP, CI, or another service. All local requirements plus the external ingress, tenant isolation, worker containment, signing, and operational gates apply.

The numeric limits below are CapabilityProof MVP policy choices, not limits prescribed by the cited standards. They MUST be centralized, versioned, recorded in each receipt, and changed only with a methodology/policy version bump and regression review.

## Security objectives, assets, and non-goals

### Assets to protect

- Owner and service host: source tree, SSH keys, cloud credentials, environment variables, browser/session data, user files, and operating-system integrity.
- Service integrity: inspector code, pinned dependency set, methodology/rules, schemas, signing key, and configuration.
- Evidence integrity: submitted envelope digest, logical-tree digest, file inventory, findings, coverage/unknowns, timestamps, expiry, and receipt authenticity.
- Customer boundaries: private artifacts, upload/receipt ownership, request metadata, and non-public findings.
- Availability: CPU, memory, disk, file descriptors, worker slots, queue capacity, and log capacity.
- Product trust: no “safe” or “certified” claim and no silent expansion from static evidence into behavior claims.

### Threat actors

- A malicious skill publisher who intentionally constructs hostile bytes and misleading instructions.
- An anonymous or authenticated remote caller seeking denial of service, host access, or another tenant’s receipt.
- A compromised repository, release asset, redirect target, DNS answer, or upstream account.
- A local process able to race or replace files in an operator-scoped input directory.
- An honest user submitting malformed, oversized, ambiguous, or mutable input.
- A compromised dependency or service host. This is residual supply-chain/host risk; the MVP reduces its reach but cannot prove it absent.

### Explicit non-goals

- Executing the artifact, installing its dependencies, running its tests, or evaluating runtime behavior.
- Malware-free, vulnerability-free, “safe,” “certified,” or complete-detection claims.
- Parsing/rendering PDFs, Office files, images, audio, video, SVG, HTML, or other rich formats.
- Following instructions, includes, transclusions, links, redirects, package references, Git submodules, or nested archives.
- Legal/license advice, ownership verification, or authorization beyond the submitter’s representation.
- Defending against a fully compromised host, kernel, runtime, build pipeline, or signing key.

## System model and trust boundaries

| Boundary | Untrusted side | Trusted side | Required boundary behavior |
|---|---|---|---|
| TB-1 Client ingress | CLI arguments, HTTP, MCP/JSON-RPC | Request validator | Authenticate where remote; parse once; reject unknown fields, ambiguous framing, unsupported types, and oversize input before expensive work. |
| TB-2 Artifact capture | Request stream or scoped directory | Immutable job blob/snapshot | Generate storage names server-side; ignore supplied filenames; no-follow reads; digest and parse the same captured bytes. |
| TB-3 Container | ZIP metadata and entries | Logical artifact inventory | No extraction; validate every entry; stream caps; reject links, special files, duplicates, collisions, encryption, and unsupported methods. |
| TB-4 Content parsing | `SKILL.md` and referenced bytes | Deterministic parser/rule engine | Data-only parsing; no import/exec/render/fetch; bounded structures and regexes; explicit partial/unknown results. |
| TB-5 Worker | Potential parser exploit/resource bomb | Host and service control plane | Separate killable worker, least privilege, no secrets, no network, isolated temporary storage, hard resource ceilings. |
| TB-6 Receipt construction | Untrusted derived strings/findings | Canonicalizer, schema validator, signer | Encode evidence as data; canonicalize; bind subject/method/policy; signer never parses artifacts. |
| TB-7 Receipt delivery/cache | Artifact and receipt handles | Authorized caller/verifier | Object-level authorization, opaque identifiers, cache-key separation, expiry/invalidation, safe content type, no cross-tenant existence leak. |
| TB-8 Deferred fetcher | URLs, DNS, redirects, remote servers | Immutable downloaded blob | Not present in MVP. If added, isolate egress and validate every resolution and redirect before bytes reach TB-2. |

The most important architectural invariant is that artifact-derived data flows only left-to-right toward evidence. It must never flow backward into process control, import names, filesystem roots, template/rendering engines, network destinations, log format strings, MCP method names, or signer configuration.

## Prioritized abuse cases

Priority meanings: **P0** = potential host compromise, secret loss, arbitrary cross-boundary access, or receipt forgery; **P1** = material denial of service, tenant breach, or evidence corruption; **P2** = bounded spoofing, privacy, or operational degradation.

| ID | Priority | Abuse case and attacker goal | Required prevention / detection |
|---|---:|---|---|
| AC-01 | P0 | Put “ignore prior instructions; run this command” in `SKILL.md`, filenames, front matter, or referenced text to induce execution or data exfiltration. | No LLM in inspection; no instruction following; no subprocess, shell, import, plugin, template, renderer, browser, package manager, or network path reachable from artifact data. |
| AC-02 | P0 | Exploit a Markdown/YAML/archive/parser vulnerability to execute code in the service process. | Minimal pinned parsers, restricted grammar, fuzz/adversarial tests, separate low-privilege worker with no secrets or egress, hard kill limits. |
| AC-03 | P0 | Read host files through `../`, absolute paths, drive/UNC paths, `file:` URIs, symlinks, hardlinks, junctions, reparse points, or an MCP path argument. | Logical-path validation, no-follow snapshot, reject all links/special files, configured root fixed at startup, remote APIs use opaque handles only. |
| AC-04 | P0 | Write/overwrite host files with Zip Slip, archive links, alternate data streams, device names, or predictable temp paths. | Never extract; server-generated exclusive temp names; reject ambiguous/platform-special paths; owner-only temp root outside repository; safe cleanup. |
| AC-05 | P0 | Forge, substitute, replay, or stale-cache a receipt for different bytes or methodology. | Envelope/tree/file digests, canonical payload hash, exact methodology/policy binding, cache key by all security-relevant inputs, expiry; public launch requires signature and invalidation. |
| AC-06 | P0 | Make the service fetch metadata endpoints, localhost, internal services, or attacker-controlled redirects. | MVP accepts no URL/URI fetch input. A future fetcher needs scheme/host allowlisting, DNS/IP/redirect validation at every hop, egress policy, no ambient credentials, and immutable capture. |
| AC-07 | P1 | Exhaust CPU, memory, disk, file descriptors, logs, or worker slots with a ZIP bomb, many entries, huge paths, parser nesting, pathological regex input, or slow HTTP body. | Streaming byte/file/ratio/depth limits, bounded algorithms, worker quotas/deadlines, ingress timeouts, rate/concurrency/queue limits, bounded output/logging. |
| AC-08 | P1 | Confuse path identity with duplicate entries, case folding, Unicode normalization, trailing dots/spaces, slash variants, or reserved names. | Require one canonical logical-path profile and reject any original or collision key that is ambiguous; never silently rewrite. |
| AC-09 | P1 | Race a local directory between validation, hashing, and parsing so the receipt describes different bytes. | Open without following links, copy once to an immutable job snapshot, hash and parse the snapshot, re-enumerate/detect replacement, and label local capture as non-atomic. Public exact receipts require an immutable envelope. |
| AC-10 | P1 | Smuggle a second HTTP request or bypass the body cap with conflicting framing/content encoding. | Deployed ingress and app agree on RFC 9112 framing; reject duplicate/conflicting `Content-Length`, `Content-Length` plus `Transfer-Encoding`, malformed chunking, unsupported transfer codings, and all request `Content-Encoding`. |
| AC-11 | P1 | Use guessed upload/receipt IDs, stolen sessions, or cache timing to access another tenant. | At least 128 bits of randomness, principal-bound handles, authorization on every object access, uniform not-found response, no shared user-visible content-addressed IDs. |
| AC-12 | P1 | Abuse MCP Origin, protocol version, sessions/SSE, token passthrough, resources, sampling, or server-initiated calls to widen authority. | Minimal stdio or stateless Streamable HTTP profile; Origin validation; audience-bound auth; no sessions/SSE; one bounded tool; no other capabilities. |
| AC-13 | P2 | Inject terminal escapes, CR/LF, Markdown/HTML, fake JSON-RPC, or sensitive bytes into logs, human summaries, or a client model’s context. | Structured logs without excerpts; reject control characters in paths; base64 exact evidence; JSON-only response as attachment; no artifact-derived Markdown or MCP unstructured content. |
| AC-14 | P2 | Store illegal/sensitive/malware bytes indefinitely or redistribute them. | Data-minimal retention, no public artifact echo, deletion on success/failure, explicit authorization/licensing policy, and only hashes/evidence returned by default. |

## Mandatory MVP control specification

### 1. Input forms and immutable capture

**IN-01 — External input type.** External HTTP upload MUST accept exactly one raw ZIP payload with `Content-Type: application/zip`. It MUST reject multipart, TAR, gzip, 7z, RAR, Git bundles, executable installers, and MIME sniffing fallbacks. ZIP validity is established by full bounded parsing, not filename or magic bytes alone.

**IN-02 — No submitted fetch targets.** The MVP schemas MUST contain no `url`, `uri`, repository, redirect, package-registry, `file://`, Git remote, or webhook field. A discovered URL is a finding string only and MUST NOT be dereferenced.

**IN-03 — Server-owned storage identity.** If buffering is needed, create an unpredictable job directory and blob name with exclusive-create semantics in a service-owned private temp root. Never use `filename`, `Content-Disposition`, archive name, skill name, digest, or customer field as a host path. The temp root MUST not be the source repository, current working directory, import path, static-file root, or executable search path.

**IN-04 — Same bytes.** Compute `envelope_sha256` while streaming the accepted request into the immutable blob. Parse that blob through an already-open handle or immutable descriptor. Never reopen by an attacker-controlled name, refetch, or hash metadata in place of content.

**IN-05 — Local directory mode.** A local-only CLI/stdio mode MAY accept a relative path beneath one operator-configured input root fixed at process start. It MUST:

- reject absolute, drive-relative, UNC, device-namespace, and URI inputs;
- enumerate without following links/reparse points;
- accept regular files and directories only;
- copy accepted bytes into the private immutable job snapshot before parsing;
- use opened-handle identity/metadata checks rather than “check path, then reopen path”;
- repeat enumeration or otherwise detect entry replacement/addition/removal during capture;
- emit `capture_mode: "non_atomic_directory_snapshot"` and capture start/end times; and
- fail closed on platforms where no-follow/type/containment cannot be established.

A local directory receipt MUST NOT claim to digest an original directory “byte stream,” because a directory has no single portable byte representation. External/public exact-version receipts MUST use an immutable submitted envelope.

**IN-06 — Retention.** Raw private uploads and snapshots MUST be deleted after the job on success and failure, with a maximum orphan TTL of one hour. Cleanup MUST operate only on the service-generated job root and MUST not follow links. Artifact bytes, evidence excerpts, tokens, headers, and secrets MUST NOT enter logs, crash reports, analytics, or error traces.

### 2. Central MVP limits

The following are the initial acceptance caps:

| Limit | MVP value | Enforcement point |
|---|---:|---|
| Raw ZIP/request body | 16 MiB | Count bytes while reading; stop and reject at byte 16 MiB + 1. |
| ZIP entries, including directory entries | 512 | Count central-directory and streamed entries. |
| Actual total expanded regular-file bytes | 64 MiB | Count bytes produced while reading entries; do not trust declared sizes. |
| Actual bytes in one regular file | 8 MiB | Count streamed bytes per entry. |
| Root `SKILL.md` bytes | 512 KiB | Before text/YAML/Markdown parsing. |
| Other text analyzed per file | 2 MiB | Larger accepted files are hash/inventory only with explicit `not_analyzed:size_limit`. |
| Total text analyzed | 16 MiB | Count decoded source bytes across the job. |
| Compression ratio | 100:1 per entry and aggregate | Compare actual expanded bytes to compressed bytes; define zero-byte edge cases explicitly. |
| Logical path | 240 UTF-8 bytes, 16 segments | Validate before reference resolution. |
| One path segment | 100 UTF-8 bytes | Validate before inventory insertion. |
| Lexically referenced files | 128, maximum depth 4 | Deduplicate by canonical path; detect cycles. |
| Findings | 256 | Stop adding findings and record truncation/coverage loss. |
| Exact evidence excerpt | 512 source bytes | Store base64 plus digest/byte range, not raw rendered text. |
| Receipt output | 2 MiB | Fail with explicit output-limit error; never silently drop inventory. |
| Worker wall time | 15 seconds | Supervisor hard-kills the worker. |
| Worker CPU time | 10 seconds | OS/process limit where supported; wall limit remains mandatory. |
| Worker memory | 256 MiB RSS/commit | OS job/container/process limit; out-of-limit is a rejected inspection. |
| Per-job temporary disk | 128 MiB | Dedicated quota or counted writes. |

**LIMIT-01.** Declared ZIP sizes, CRCs, offsets, counts, and compression ratios are preflight hints only. Every byte cap MUST also be enforced on actual streamed output.

**LIMIT-02.** A limit violation is an inspection rejection, not a partial success, except for the documented per-file text-analysis cap. A receipt for a partial analysis MUST expose every skipped/truncated area and MUST never imply full coverage.

**LIMIT-03.** Limit failures MUST release file handles, memory, worker slots, and temporary disk. Repeated failures MUST not cause unbounded error logging.

### 3. ZIP, path, and filesystem rules

**PATH-01 — No extraction.** The MVP MUST read entries through the ZIP library and logical inventory. It MUST NOT call generic extract/extract-all APIs.

**PATH-02 — Supported ZIP subset.** Accept only unencrypted ZIP entries using Stored (method 0) or Deflate (method 8). Reject encryption, unsupported compression, multi-disk archives, ZIP64, malformed/truncated structures, CRC mismatch, inconsistent sizes, overlapping/ambiguous entries, and any entry the library cannot classify deterministically. Nested archive files are opaque regular files and MUST NOT be recursively opened.

**PATH-03 — Entry types.** Accept logical directories and regular files only. Reject symbolic links, hardlinks, Windows shortcuts treated as links, junctions, reparse points, devices, sockets, FIFOs, and unknown types. ZIP external attributes MUST be inspected; missing or inconsistent type metadata fails closed when it prevents classification.

**PATH-04 — Canonical logical path profile.** Every entry path MUST:

- be valid UTF-8 and already Unicode NFC; reject rather than normalize/rewrite;
- use `/` as the only separator and contain no backslash;
- be relative with no leading slash, drive letter, UNC/device prefix, colon, NUL, C0/DEL control, bidi-format control, empty segment, `.`, or `..` segment;
- contain no trailing dot or space in a segment;
- avoid Windows reserved device basenames, case-insensitively, including `CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, and `LPT1`-`LPT9` even with an extension; and
- satisfy the segment/depth/byte limits.

Do not URL-decode, HTML-decode, shell-expand, environment-expand, case-normalize, or Unicode-normalize attacker paths.

**PATH-05 — Collision rejection.** Reject exact duplicate entry names and any collision under:

1. NFC plus Unicode case fold;
2. Windows trailing-dot/space and reserved-name behavior; or
3. the service’s logical separator rules.

The receipt may preserve the accepted original logical path, but only one unambiguous identity can enter the inventory.

**PATH-06 — Required skill file.** Exactly one regular file named `SKILL.md` MUST exist at the logical artifact root with that exact case. A missing, duplicate, case-colliding, linked, oversized, or non-regular `SKILL.md` rejects the artifact.

**PATH-07 — Reference closure.** Referenced-file discovery is a deterministic lexical rule, not instruction following. Resolve only relative logical paths already present in the accepted inventory. Record external schemes, absolute paths, missing files, and out-of-root paths as findings without opening them. Apply the same path profile, cycle detection, depth, file-count, and text-byte limits. Never resolve includes, Markdown images, HTML, package imports, symlinks, Git submodules, or nested archives.

**PATH-08 — No TOCTOU by pathname.** All local reads and cleanup use already-validated handles/descriptors or service-generated paths beneath the private job root. A successful string-prefix check on a path is not sufficient containment.

### 4. Parser and rule-engine rules

**PARSE-01 — Forbidden capabilities.** Production inspector code reachable from artifact processing MUST NOT invoke or dynamically select:

- `eval`, `exec`, dynamic import/module loading, reflection-based constructors, or unsafe deserialization;
- shell/process APIs, interpreters, compilers, package managers, build tools, Git, hooks, or test runners;
- template engines, Markdown/HTML/SVG renderers, browsers, document/image/media parsers, or UI previews;
- sockets, HTTP clients, DNS, cloud SDKs, webhooks, telemetry exporters, or model/sampling APIs; or
- artifact-supplied plugins, schemas, regexes, configuration, encodings, locales, or output formats.

Static source scanning may identify command-like text but must never tokenize it with a shell or pass it to an interpreter.

**PARSE-02 — Bytes first.** Hash and inventory raw bytes before text decoding. `SKILL.md` MUST be valid UTF-8 under one documented BOM/newline policy. Invalid encoding or NUL rejects `SKILL.md`. Other non-text or invalid UTF-8 files remain hash/inventory-only and are marked as not text-analyzed.

**PARSE-03 — Front matter.** If YAML front matter is supported, use a restricted data-only grammar and schema. Reject custom tags, object construction, anchors, aliases, merge keys, duplicate keys, complex keys, multiple documents, non-finite numbers, timestamps with implicit types, excessive nesting, and unknown top-level fields where the Agent Skill schema does not allow them. Prefer an allowlisted scalar/list/map schema over a general YAML loader; “safe load” alone is not the acceptance criterion.

**PARSE-04 — Markdown as source text.** Parse Markdown only to the minimum needed for structural evidence. Disable plugins/extensions and embedded rendering. HTML, SVG, images, data URIs, autolinks, fenced commands, comments, directives, and include-like syntax remain inert source spans. Do not make callbacks from the parser to resolve paths or URLs.

**PARSE-05 — Bounded algorithms.** Regexes MUST be fixed by the methodology, reviewed for catastrophic backtracking, and tested with long/adversarial inputs. Prefer linear scans or a regex engine with enforceable time limits. Recursion/nesting must be bounded. Worker deadline expiration is a rejection, never a “clean” result.

**PARSE-06 — Deterministic failure.** Malformed content produces a stable typed error/finding without stack traces, host paths, parser internals, or fallback parsing. Do not retry with a more permissive parser or renderer.

**PARSE-07 — Dependency boundary.** Pin the runtime and direct/transitive parser dependencies with hashes where the ecosystem supports them. Keep the parsing dependency set minimal. Before external launch, review known advisories for the exact locked versions and rerun the hostile corpus after any update.

### 5. Worker containment and side-effect controls

Worker containment protects the host from defects in trusted parser code; it is not permission to execute artifact code.

**WORK-01.** External untrusted jobs MUST run in a separate supervisor-controlled worker process under a dedicated unprivileged identity or equivalent restricted process profile. The worker MUST receive only an immutable input handle/blob and policy values.

**WORK-02.** The worker environment MUST contain no signing key, customer credentials, cloud metadata credentials, SSH material, browser data, source repository write access, or unrelated environment variables. Use an explicit allowlist of environment variables and a fixed working directory outside the repository.

**WORK-03.** The worker MUST have outbound network denied at the operating-system/container policy layer for external launch. Application tests that monkeypatch HTTP are useful but are not an egress boundary.

**WORK-04.** Code/runtime files MUST be read-only to the worker. The only writable location is its private quota-bound job temp root. Do not place that root on `PATH`, `PYTHONPATH`, module search paths, plugin paths, or a web static root.

**WORK-05.** The supervisor MUST enforce the central wall/CPU/memory/disk/file-count limits, kill on violation, collect only a bounded structured result, and clean the job root. A worker crash, signal, out-of-memory, timeout, or malformed result is a failed inspection and MUST NOT be signed.

**WORK-06.** Signing MUST occur in a separate component after schema validation and recomputation of the subject/payload digests. The signer accepts only the canonical receipt payload and never receives or parses artifact bytes.

For local fixture-only development, hard OS isolation may be staged, but the process must still have no network-fetch path and must not contain secrets. Lack of WORK-01 through WORK-05 blocks accepting any external untrusted artifact.

### 6. Output, evidence, logging, and privacy

**OUT-01.** Artifact-derived strings are always data fields, never format strings, Markdown, HTML, terminal output, log messages, filenames, headers, status text, MCP method/tool names, or templates.

**OUT-02.** Exact evidence MUST use source path plus byte start/end offsets, source-file SHA-256, and at most 512 source bytes encoded as base64. A separately derived printable preview MAY be offered outside MCP only if C0/DEL/bidi controls are escaped and it is unmistakably labeled untrusted; the base64 bytes remain authoritative.

**OUT-03.** Externally returned JSON uses `Content-Type: application/json; charset=utf-8`, `X-Content-Type-Options: nosniff`, and a download-oriented `Content-Disposition` with a server-generated ASCII filename. Do not serve receipts as HTML or render them inline with artifact content.

**OUT-04.** Logs use a fixed structured schema with server-generated request/job IDs, outcome code, duration bucket, byte/file counts, and methodology version. Do not log raw paths, excerpts, artifact bytes, authorization headers/tokens, URLs with query strings, request bodies, or full exception objects. Sanitize any bounded diagnostic label before terminal output.

**OUT-05.** External errors are typed and generic, for example `invalid_archive`, `limit_exceeded`, `unsupported_entry`, or `inspection_failed`. Detailed diagnostics remain bounded and local, with no host absolute paths or secrets.

**OUT-06.** Do not return or redistribute submitted artifact bytes by default. Return evidence, digests, inventory, and findings. Retaining or exposing a public artifact requires a separate explicit policy and authorization check.

## HTTP acceptance profile

These controls apply at the actual deployed edge and application together. A unit test of the application behind a differently parsing proxy is not sufficient.

### Request and protocol controls

**HTTP-01.** External listeners require TLS and authentication. A local unauthenticated listener, if any, binds only to `127.0.0.1`/`::1` and is disabled by default. Do not bind local development to `0.0.0.0`.

**HTTP-02.** Authorize every upload, inspection, receipt retrieval, and deletion. Artifact/receipt handles contain at least 128 random bits, are principal-bound, expire, and return the same not-found response for absent and unauthorized objects.

**HTTP-03.** Upload body cap is 16 MiB; JSON control requests are at most 64 KiB, depth 16, and 256 aggregate object members/array elements. Reject duplicate JSON property names, invalid UTF-8, non-finite numbers, unknown fields, and schema type coercion. Header block is at most 16 KiB, 100 fields, and request target 4 KiB.

**HTTP-04.** Reject before application dispatch:

- conflicting or repeated `Content-Length` values;
- any request containing both `Content-Length` and `Transfer-Encoding`;
- malformed/non-final/multiply applied chunking or unsupported transfer coding;
- any request `Content-Encoding`, including gzip/br/deflate;
- an upload without an enforceable length/framing policy;
- unsupported method, media type, route, or HTTP upgrade.

Close the HTTP/1.1 connection after framing errors. Configure proxy and origin to parse and normalize framing consistently, following RFC 9112’s request-smuggling guidance.

**HTTP-05.** Stream and count bytes. Do not read an unbounded body into memory. Use a 5-second header deadline, 5-second body idle deadline, and 30-second total upload deadline for the MVP; make them versioned configuration. A timeout releases the worker/queue reservation.

**HTTP-06.** Default authenticated limits are 10 submitted jobs per minute and 2 concurrent jobs per principal and source IP, a global queue of 16, and a host-sized global worker cap (initially 2). Exceeding a cap returns a bounded retryable error before artifact parsing. Global disk/memory pressure fails closed.

**HTTP-07.** CORS is disabled unless a browser client is intentionally shipped. If enabled later, use an exact Origin allowlist, never wildcard with credentials, and add CSRF protection for cookie-based sessions. Do not reflect arbitrary Origin.

**HTTP-08.** Upload handles expire within one hour; snapshots are deleted after inspection. Receipt cache records are keyed and authorized independently from blob storage. Hash equality must not leak another tenant’s artifact existence or result.

**HTTP-09.** Responses are capped at 2 MiB and never gzip/compress artifact-derived data until compression side channels and limits are reviewed. Error and success responses include a server-generated request ID but no artifact content.

### URL and repository fetching

**HTTP-10 — MVP rule.** Direct URL/repository fetching is disabled and absent from the public schema. This is the simplest complete SSRF control for the USD $0 MVP.

If fetching is later added, it requires a separate threat review and at minimum:

- HTTPS only and an explicit repository-host/path allowlist;
- immutable commit/release identifier resolution, while still digesting downloaded bytes;
- URL parsing by one standards-based library, with no userinfo or non-default ports unless allowlisted;
- DNS resolution whose every IPv4/IPv6 result excludes loopback, private, link-local, multicast, unspecified, documentation, reserved, and cloud-metadata ranges;
- the same validation on every redirect, with a small hop limit and no cross-host redirect unless allowlisted;
- protection against DNS rebinding by pinning/validating the connected address, not only a preflight lookup;
- no ambient credentials, cookies, proxy credentials, SSH agent, local Git config, submodules, LFS smudge filters, hooks, or `file://`/custom schemes;
- isolated egress proxy/network policy, strict response byte/time limits, and no decompression beyond the artifact limits; and
- one immutable downloaded blob hashed and parsed once, with the original URL recorded only as provenance, never as identity.

Until all of those are implemented and tested, any endpoint that accepts a fetch target is a launch blocker.

## MCP acceptance profile

The MVP should expose the smallest possible MCP surface. As of this review, the implementation profile is pinned to protocol revision `2025-11-25`; upgrades require spec-diff review and security regression.

### Local stdio

**MCP-01.** Prefer stdio for local integration. Stdout contains valid newline-delimited MCP JSON-RPC messages only; logs go to stderr. Enforce a 64 KiB maximum input line before JSON parsing and reject embedded framing ambiguity, invalid UTF-8, arrays/batches, duplicate object keys, multiple messages in one frame, and unknown methods.

**MCP-02.** The process start command, configured input root, policy, and environment are operator-owned startup configuration. Artifact content and tool arguments cannot alter them. The tool accepts only a bounded relative path beneath that root or, preferably, an opaque pre-created local upload handle.

### Streamable HTTP

**MCP-03.** Remote MCP uses the HTTP controls above and accepts an opaque principal-bound upload handle only—never a server path, `file://` URI, repository URL, resource URI, base64 artifact, command, or environment selection.

**MCP-04.** Validate `Origin` on every connection. Reject a present but unallowlisted, malformed, multiple, or `null` Origin with HTTP 403. A missing Origin may be accepted only for authenticated non-browser clients under explicit policy. Local HTTP binds only to loopback.

**MCP-05.** Require the negotiated/supported `MCP-Protocol-Version` and return 400 for invalid/unsupported versions. Do not silently activate backward-compatibility transports.

**MCP-06.** Return one `application/json` response to POST. Do not implement SSE, resumability, server-to-client notifications, or sessions. GET returns 405. This removes event replay and session-hijack state from the MVP.

**MCP-07.** External MCP authentication validates expiry, signature/issuer as applicable, scopes, and that the token was issued specifically for this MCP server/audience. Authorization is present on every HTTP request. Never accept tokens from another service, place tokens in query strings, pass client tokens downstream, or log them.

### MCP capability minimization

**MCP-08.** Expose one tool, conceptually `inspect_uploaded_skill`. Its input schema has an exact object shape, one bounded artifact-handle string, and `additionalProperties: false`. Its output schema is the versioned receipt/result object. Validate at runtime; schema annotations are not authorization.

**MCP-09.** Do not expose prompts, resources, resource templates, roots, sampling, elicitation, tasks, subscriptions, completion, logging of artifact text, server-initiated tool calls, or arbitrary URI resolution. Do not advertise capabilities that are not implemented.

**MCP-10.** Return receipt data in `structuredContent` conforming to `outputSchema`. Unstructured `content`, if compatibility requires it, contains only a fixed server-authored status and digest—never artifact excerpts, instructions, paths, URLs, Markdown, images, audio, embedded resources, or resource links. Exact evidence remains base64 inside explicitly labeled untrusted data fields.

**MCP-11.** A string inside an artifact that looks like JSON-RPC, an MCP method, tool definition, tool result, prompt, or “system instruction” remains source bytes. It cannot change the server capability list, invoke another method, or be copied to stdout as a protocol frame.

## Receipt integrity requirements

### Subject binding

**REC-01 — SHA-256.** Use SHA-256 for envelope, file, logical-manifest, methodology, policy/lock, and receipt-payload digests, always with lowercase 64-character hexadecimal encoding and an explicit algorithm identifier. SHA-256 is standardized in FIPS 180-4; a digest detects byte change but does not authenticate who produced it.

**REC-02 — Envelope digest.** For ZIP input, `subject.envelope.sha256` is the digest of the exact accepted request-body bytes. Record exact envelope size and media/profile. Any byte change anywhere in the ZIP—including metadata—changes this digest.

**REC-03 — File inventory.** For every accepted regular file, record canonical logical path, raw byte size, SHA-256, analysis disposition, and any supported type/mode metadata. Sort inventory by UTF-8 bytes of the accepted logical path. List every checked file; do not silently omit unsupported or size-limited analysis.

**REC-04 — Logical-tree digest.** Construct a versioned logical manifest object such as:

`{"profile":"capabilityproof-tree-v1","files":[{"path":"SKILL.md","sha256":"...","size":123}]}`

where files are sorted as above and fields/types are fixed by schema. Compute `subject.tree.sha256 = SHA256(JCS(manifest))`. This tree digest permits comparison of content trees; it does not replace the envelope digest or claim identical ZIP metadata.

**REC-05 — Same snapshot.** File hashes, evidence offsets, and parser results MUST be derived from the exact immutable entry bytes represented in the manifest. If identity or consistency cannot be established, issue no success receipt.

### Canonical receipt payload

**REC-06 — Payload structure.** Use a top-level wrapper with:

- `payload`: all substantive receipt claims;
- `integrity.profile`: for example `capabilityproof-receipt-v1`;
- `integrity.payload_sha256`: SHA-256 of `JCS(payload)`; and
- `integrity.signature`: null/absent only for an explicitly unauthenticated local MVP receipt.

Hashing the `payload` subtree avoids a self-referential “hash of a receipt containing its own hash.”

**REC-07 — JCS constraints.** Canonicalize with RFC 8785 JCS and validate the RFC’s I-JSON constraints: no duplicate object names, invalid Unicode, NaN/Infinity, or unsupported numeric values. Account for the verified RFC 8785 negative-zero erratum by rejecting `-0`. JCS deliberately does not Unicode-normalize strings; the path profile therefore rejects non-NFC paths before receipt construction.

**REC-08 — Domain separation and signature.** Before external production, sign:

`UTF8("CapabilityProof Receipt v1") || 0x00 || JCS(payload)`

with one allowlisted algorithm/profile (Ed25519 is a suitable candidate specified in RFC 8032), and include `alg`, `key_id`, and base64 signature. Verifiers MUST reject unknown algorithms/profiles and malformed/non-canonical keys/signatures; never accept attacker-selected algorithm implementations.

**REC-09 — Key boundary.** The signing key is unavailable to ingress and parser workers. The signer recomputes/validates the payload digest, schema, methodology/policy identifiers, and success state before signing. Publish the verification key through an authenticated channel distinct from the receipt.

**REC-10 — Required payload context.** The signed/hashed payload MUST contain:

- schema and receipt profile versions;
- envelope and tree subject digests and sizes;
- complete file inventory and per-file digests;
- findings with rule ID/version, severity rationale, exact evidence reference, and confidence/limitations;
- analysis coverage, skipped/unsupported/truncated areas, and unknowns;
- methodology/ruleset version **and digest**, runtime/parser version, dependency-lock digest, and policy/limit profile;
- capture/inspection timestamps, expiry, and capture mode;
- explicit `non_executing: true` and a machine-readable limitations set; and
- no `safe`, `certified`, `malware_free`, or equivalent universal conclusion.

**REC-11 — Determinism.** With volatile time/request fields fixed by the harness, the same envelope, methodology, dependency lock, and policy MUST produce byte-for-byte identical canonical JSON and payload digest. Findings and files have specified stable sort keys. Locale, host path, random IDs, concurrency, map iteration, ZIP order, and operating-system newline behavior MUST not affect the payload.

**REC-12 — Cache identity.** Cache only by a versioned tuple including envelope/tree digest, schema, methodology/ruleset digest, dependency-lock digest, policy/limit profile, and relevant feature flags. Never cache solely by URL, repository/tag, filename, publisher, skill name, or prior receipt ID. Do not reuse a partial/error result as a success.

**REC-13 — Freshness and invalidation.** A verifier reports digest/signature validity separately from freshness, methodology status, and revocation/invalidation. An expired or invalidated receipt may be historically authentic but MUST NOT be reported current. Before external production, publish and test key rotation/revocation and receipt/methodology invalidation behavior.

**REC-14 — Honest digest-only state.** Until REC-08, REC-09, and REC-13 are live, receipts MUST state `integrity_assurance: "digest-only-unauthenticated"`. They may support local deterministic testing but must not be marketed as issuer-authenticated or tamper-proof against an attacker who can replace both receipt and digest.

## Required security test suite

Every test asserts a typed reject/safe result, bounded resource use, no external side effect, and no secret/artifact leakage in output or logs. Fixtures are generated locally and never executed.

### A. Non-execution and containment

- **T-EXEC-01:** Put shell, PowerShell, Python, Node, package-manager, Git-hook, and “ignore previous instructions” payloads in every parsed field, filename, Markdown block, HTML comment, and referenced file. Assert no subprocess/import/render/network API is invoked and sentinel files/environment secrets are absent from results/logs.
- **T-EXEC-02:** Include HTML, SVG, Markdown images, data URIs, remote links, `file://` links, include/transclusion syntax, model prompts, MCP/JSON-RPC frames, and terminal escapes. Assert they remain inert bytes and no renderer/browser/MCP callback runs.
- **T-EXEC-03:** Run a hostile job in the production worker profile. Assert source tree and outside-root sentinel files are unchanged/unread, outbound network is denied, environment is allowlisted, temp quota applies, and the signer key is inaccessible.
- **T-EXEC-04:** Force worker crash, invalid result, timeout, memory limit, disk limit, and supervisor cancellation. Assert no signed/success receipt, resources released, private temp cleanup, and bounded generic errors.

### B. Archive and path adversarial matrix

- **T-PATH-01:** Reject `../x`, `..\x`, absolute POSIX paths, `C:\x`, `C:x`, UNC/device paths, repeated/empty segments, dot segments, NUL, backslash, colon/ADS, trailing dot/space, control/bidi characters, overlong paths/segments, and over-depth paths.
- **T-PATH-02:** Reject exact duplicate entries plus `SKILL.md`/`skill.md`, NFC/NFD equivalents, Unicode case-fold collisions, and Windows reserved/device-name variants including those with extensions.
- **T-PATH-03:** Reject ZIP symlink/hardlink attributes, local filesystem symlink, junction/reparse point, FIFO/socket/device, Windows shortcut classified as a link, and unknown file type. Assert no target outside the root is read.
- **T-PATH-04:** Race a local file/directory by replacing, linking, truncating, and adding entries during capture. Assert detection/rejection or a receipt bound only to captured immutable bytes with non-atomic capture labeling—never a hash/parse mismatch.
- **T-ZIP-01:** Reject encrypted, multi-disk, ZIP64, unsupported compression, truncated headers/directory, bad CRC, false sizes, overlapping/duplicate entries, malformed extra fields, and invalid path encodings without crash.
- **T-ZIP-02:** Test exactly-at and one-over for 16 MiB envelope, 512 entries, 64 MiB expanded total, 8 MiB single file, and 100:1 ratio. Metadata that lies below the cap but streams above it must be stopped at the actual cap.
- **T-ZIP-03:** Include nested ZIP/TAR/gzip files. Assert they are hash/inventory-only and never recursively opened.
- **T-ZIP-04:** A traversal archive must not create, overwrite, or delete any host file because no extraction API is reachable.

### C. Parser complexity and ambiguity

- **T-PARSE-01:** Test missing/multiple/case-colliding `SKILL.md`, invalid UTF-8, BOM policy, NUL, huge line, mixed newlines, exactly-at/over 512 KiB, and binary `SKILL.md`.
- **T-PARSE-02:** Test YAML tags/object constructors, anchors/aliases and alias bombs, merge keys, duplicate/complex keys, multiple documents, deep nesting, huge scalar/key counts, implicit timestamps, NaN/Infinity/`-0`, and unknown schema fields. Assert deterministic reject and no object construction.
- **T-PARSE-03:** Feed pathological Markdown nesting, brackets, fences, HTML, comments, links, and long repeated strings. Assert completion under the worker limit with stable output.
- **T-PARSE-04:** Exercise every fixed regex with adversarial near-matches and maximum-length lines. Add a regression fixture for any timeout found.
- **T-REF-01:** Test nonexistent, absolute, external-scheme, cyclic, duplicate, depth-5, and 129th referenced paths. Assert no fetch/out-of-root read and explicit coverage/findings.
- **T-FUZZ-01:** Run mutation/property fuzzing over ZIP metadata, paths, front matter, Markdown, and receipt verification. The release corpus must complete at least 10,000 generated/mutated cases with no crash, hang, escape, unbounded allocation, or nondeterministic success.

### D. HTTP

- **T-HTTP-01:** Reject missing/invalid auth and verify object-level authorization for upload, inspect, receipt, and delete. Principal B receives the same not-found behavior for Principal A’s valid ID as for a random ID.
- **T-HTTP-02:** Test valid, duplicate, conflicting, signed/overflowing, and comma-list `Content-Length`; `Content-Length` plus `Transfer-Encoding`; malformed/double/non-final chunking; request `Content-Encoding`; body with trailing bytes; and proxy/origin parsing agreement. Ambiguous requests never reach the app worker.
- **T-HTTP-03:** Test body/header/target/JSON depth/member/string limits at boundary and one over, including chunked bodies. Assert streaming rejection and no large error/log.
- **T-HTTP-04:** Test slow header/body, idle timeout, total timeout, disconnect, retry storm, queue full, per-principal/IP rate and concurrency limits, and global worker/disk pressure. Assert recovery for a subsequent valid request.
- **T-HTTP-05:** Reject multipart, media-type confusion, executable/polyglot inputs that are not valid bounded ZIP, unsupported methods/routes/upgrades, duplicate JSON keys, unknown fields, type coercion, and invalid UTF-8.
- **T-HTTP-06:** Verify TLS/external binding configuration, CORS disabled/default-deny, no reflected Origin, download JSON headers, ≤2 MiB responses, sanitized errors, and no secrets/artifacts in logs.
- **T-HTTP-07:** Assert the public schema and routes contain no URL/repository/URI fetch capability and that network instrumentation sees zero outbound requests during inspection.

### E. MCP

- **T-MCP-01:** For stdio, send oversize line, invalid UTF-8/JSON-RPC, batch/array, duplicate keys, multiple frames, unknown method, and embedded newlines. Assert bounded errors and that stdout always parses as MCP only.
- **T-MCP-02:** For remote MCP, reject absent/invalid auth, wrong audience, token in query, unsupported protocol version, malformed/multiple/null/unallowlisted Origin, and foreign artifact handles.
- **T-MCP-03:** Assert POST returns one JSON response, GET returns 405, and no SSE/session/event replay state exists.
- **T-MCP-04:** Tool input rejects path, URI, base64 bytes, commands, extra fields, malformed/overlong handles, and wrong types. Runtime validation matches the published JSON Schema.
- **T-MCP-05:** Assert advertised capabilities contain only the required tool. Roots, resources, prompts, sampling, elicitation, tasks, subscriptions, logging, and server-initiated calls are unavailable.
- **T-MCP-06:** Put fake tool calls, JSON-RPC, prompts, and instructions in the artifact. Assert `structuredContent` validates against the output schema; unstructured content contains no artifact-derived string; no extra frame/method/capability appears.

### F. Receipt integrity

- **T-REC-01:** With fixed volatile fields, repeated and parallel runs of identical input produce byte-identical canonical receipt bytes and payload digest across supported platforms.
- **T-REC-02:** Change one byte in each file and in ZIP metadata. Assert envelope digest always changes; relevant file/tree/payload digests change as defined; metadata-only change may leave tree digest equal but never envelope digest.
- **T-REC-03:** Reorder ZIP entries and JSON object properties. Assert the envelope digest reflects ZIP-byte change while the logical tree/JCS behavior follows the documented profile.
- **T-REC-04:** Tamper with subject, inventory, finding, evidence, methodology, limit, timestamp, expiry, or limitation. Verifier rejects the payload digest/signature.
- **T-REC-05:** Verify duplicate JSON names, invalid Unicode, NaN/Infinity, `-0`, unknown profile/algorithm/key, malformed signature, wrong key, noncanonical representation, and schema mismatch fail closed.
- **T-REC-06:** Change methodology, dependency lock, policy limit, or feature flag without changing artifact. Assert cache miss and different payload identity.
- **T-REC-07:** Verify expired, invalidated, revoked-key, and superseded-method receipts are never reported “current,” while cryptographic validity and freshness remain separate fields.
- **T-REC-08:** Before signing exists, verify every receipt says `digest-only-unauthenticated` and no UI/API describes it as signed, authentic, safe, certified, or tamper-proof.

## Independent security acceptance checklist

The reviewer checks evidence, not implementation intent. Each checked item should link to a test, configuration snapshot, or code location in the review record.

### Core non-executing inspector

- [ ] Public schemas and production code contain no artifact URL/fetch input.
- [ ] Static call-path review finds no artifact-reachable subprocess, shell, dynamic import, unsafe deserialization, renderer, browser, package manager, Git, socket, HTTP/DNS, model, plugin, or template capability.
- [ ] ZIP is the only external envelope; supported compression/types are allowlisted.
- [ ] No generic archive extraction function is reachable.
- [ ] All central limits are enforced on actual streamed bytes and recorded in receipts.
- [ ] Path rules reject traversal, absolute/device paths, link/special types, Unicode/case/platform collisions, and ambiguous `SKILL.md`.
- [ ] Local mode is startup-root scoped, no-follow, immutable-snapshot based, and absent from remote schemas.
- [ ] Parser grammar is data-only and bounded; YAML dangerous features and fallback parsers are disabled.
- [ ] Referenced-file closure is lexical, within inventory, cycle/depth/count bounded, and never fetches.
- [ ] Artifact-derived output is structured/escaped; exact evidence is bounded base64; logs contain no artifact content.
- [ ] Runtime and dependencies are pinned; exact versions have no unresolved known critical/high advisory accepted without written mitigation.
- [ ] Hostile regression corpus and ≥10,000-case fuzz/property run pass with no crash/hang/escape.

### Worker and operations

- [ ] External jobs execute in a killable, unprivileged worker separate from ingress and signer.
- [ ] Worker has no secrets/signing key, no source-tree write, private quota-bound temp, read-only code, and OS-enforced no egress.
- [ ] Wall/CPU/memory/disk/queue/concurrency limits are demonstrated at boundary and one over.
- [ ] Crash/timeout/OOM/cancel paths fail closed, sign nothing, clean temp, and recover capacity.
- [ ] Raw private artifacts are deleted after the job and orphan cleanup is bounded/no-follow.
- [ ] Production logs/errors are structured, bounded, sanitized, and reviewed for tokens, host paths, excerpts, and customer bytes.

### HTTP

- [ ] External service is TLS-only and authenticated; every artifact/receipt operation enforces ownership.
- [ ] Opaque handles have ≥128 random bits, expiry, and uniform unauthorized/not-found behavior.
- [ ] Edge and app reject ambiguous HTTP/1.1 framing, unsupported encoding, oversize/slow bodies, invalid media types, and schema ambiguity.
- [ ] Deployed proxy/origin integration tests cover `Content-Length`/`Transfer-Encoding` smuggling cases.
- [ ] Rate, concurrency, queue, response, header, body, and timeout caps are active and observable.
- [ ] CORS is disabled/default-deny; response content is JSON download with nosniff; no artifact content enters headers/errors/logs.
- [ ] Network observation confirms inspection produces no outbound traffic.

### MCP

- [ ] MCP revision is pinned and unsupported versions fail closed.
- [ ] stdio stdout contains protocol messages only and applies a pre-parse frame limit.
- [ ] Remote MCP uses authenticated, audience-bound tokens on every request and never passes them through.
- [ ] Origin validation, loopback-only local binding, and the HTTP controls are active.
- [ ] Remote tool accepts an owned upload handle only; no path/URI/base64/command inputs.
- [ ] GET=405, no SSE/sessions, and only the inspection tool is advertised.
- [ ] Tool input/output runtime validation matches exact JSON Schemas with no extra properties.
- [ ] Artifact-derived text never enters MCP unstructured content or creates a protocol frame/capability.

### Receipt

- [ ] Envelope, per-file, tree, methodology, policy/lock, and payload SHA-256 values independently recompute.
- [ ] JCS implementation passes canonicalization/error vectors including duplicate keys, invalid Unicode, non-finite numbers, and `-0` rejection.
- [ ] The receipt binds complete inventory, exact evidence references, coverage/unknowns, methodology/dependency/policy versions, timestamps/expiry, and non-executing limitations.
- [ ] Fixed-time determinism is byte-for-byte, not merely semantic JSON equality.
- [ ] Cache key includes all subject and methodology/policy inputs and cannot cross tenant authorization.
- [ ] Local unsigned receipts are explicitly digest-only unauthenticated.
- [ ] Before external production: signatures verify with an authenticated public key; signer isolation, key rotation/revocation, and receipt/method invalidation are tested.
- [ ] No output or marketing surface uses universal “safe,” “certified,” “malware-free,” or equivalent assurance language.

## Launch-blocking criteria

### Block even local hostile-fixture testing

- Any artifact-reachable execution, import, render, fetch, plugin, template, shell, package-manager, or Git path.
- Any archive extraction to a host path.
- Missing actual-byte size/file/count/decompression enforcement.
- Hashing bytes different from those parsed.
- Unbounded parser/regex behavior or a known hostile fixture that crashes/escapes.
- A result that hides partial coverage or implies universal safety.

### Block any external/untrusted launch

- Any unresolved P0 or P1 finding from this checklist or independent review.
- Remote acceptance of arbitrary paths, `file://`, URLs, repository refs, base64 artifacts in MCP, or mutable fetch targets.
- No separate restricted worker, no OS-enforced egress denial, worker access to secrets/signing key/source writes, or unenforced resource limits.
- Missing path/link/collision/TOCTOU controls or archive actual-byte bomb tests.
- HTTP auth/object authorization, framing, body/time/rate/concurrency, TLS, or tenant-isolation tests missing/failing.
- MCP Origin/version/auth/capability-minimization/output-isolation tests missing/failing.
- Receipt digest mismatch, nondeterminism, ambiguous canonicalization, stale cache reuse, or silent truncation.
- Public/paid production without issuer signature, authenticated verification key, rotation/revocation, and invalidation behavior; until then only explicitly unauthenticated local/sample receipts are acceptable.
- Logs, errors, analytics, or crash reports leak customer bytes, evidence excerpts, tokens, host paths, or secrets.
- Any “safe,” “certified,” “malware-free,” penetration-tested, or runtime guarantee claim.

Passing this checklist means the implementation meets this bounded threat model under tested conditions. It is not a universal safety certification and does not eliminate parser/runtime/OS zero-days or malicious behavior that static analysis cannot observe.

## Deferred sandbox and future controls

The following are deliberately **not** MVP capabilities:

- Executing skills, commands, tests, hooks, binaries, scripts, installers, or package managers—even inside a container.
- Installing dependencies or observing runtime filesystem/network/process behavior.
- Rendering rich content or using browser/document/media engines.
- LLM-based interpretation that can follow artifact instructions.
- Generic Internet/repository crawling, mutable refs, submodules, LFS, or package-registry resolution.
- Malware detonation, behavioral scoring, penetration testing, and performance/task certification.

If dynamic observation is later approved, it needs a separate hostile-execution threat model: disposable VM-grade isolation, clean snapshots, non-root identity, syscall/device/kernel boundary, network mediation, secret-free environment, deterministic fixtures, artifact-to-host escape tests, resource quotas, provenance, and teardown verification. A container alone must not be treated as proof of safety.

Worker containment in this document is different: it confines the trusted static parser in case malformed data exploits it. It never authorizes execution of artifact code.

## External sources

All external sources were accessed **2026-07-13**. Internal product limits and launch decisions above are CapabilityProof policy derived from the threat model; the sources establish relevant standards and weakness classes.

1. NIST, **FIPS 180-4: Secure Hash Standard**, specifies SHA-256-family message digests and describes digests as detecting message changes.
   https://csrc.nist.gov/pubs/fips/180-4/upd1/final
2. RFC Editor, **RFC 8785: JSON Canonicalization Scheme (JCS)**, defines deterministic JSON property ordering/serialization, I-JSON input constraints, and preservation rather than normalization of Unicode strings.
   https://www.rfc-editor.org/rfc/rfc8785.html
3. RFC Editor, **Verified errata for RFC 8785**, includes the negative-zero ambiguity relevant to hash/signature inputs.
   https://errata.rfc-editor.org/search/?rfc_number=8785&presentation=records
4. MITRE CWE-22, **Improper Limitation of a Pathname to a Restricted Directory**, documents path-traversal consequences and why a string-prefix path check is insufficient.
   https://cwe.mitre.org/data/definitions/22.html
5. MITRE CWE-59, **Improper Link Resolution Before File Access**, covers symlink/hardlink/link-following risks, including archive escape examples.
   https://cwe.mitre.org/data/definitions/59.html
6. MITRE CWE-367, **Time-of-check Time-of-use Race Condition**, describes resource identity changing between check and use.
   https://cwe.mitre.org/data/definitions/367.html
7. MITRE CWE-409, **Improper Handling of Highly Compressed Data**, describes decompression bombs and CPU/memory availability impact.
   https://cwe.mitre.org/data/definitions/409.html
8. MITRE CWE-400, **Uncontrolled Resource Consumption**, recommends protocol scale limits, throttling, and safe failure under resource exhaustion.
   https://cwe.mitre.org/data/definitions/400.html
9. MITRE CWE-918, **Server-Side Request Forgery**, describes attacker-supplied URLs reaching internal hosts, local files, and alternate protocols.
   https://cwe.mitre.org/data/definitions/918.html
10. OWASP Cheat Sheet Series, **File Upload Cheat Sheet**, recommends upload limits, safe filenames/storage, authorization, and defense against malicious file content; it notes the broad attack surface of ZIP uploads.
    https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
11. RFC Editor, **RFC 9112: HTTP/1.1**, sections 6 and 11, defines message framing and identifies `Content-Length`/`Transfer-Encoding` ambiguity as a request-smuggling risk.
    https://www.rfc-editor.org/rfc/rfc9112.html
12. Model Context Protocol, **Transports, protocol revision 2025-11-25**, requires Origin validation for Streamable HTTP, recommends loopback binding/authentication, defines stdio stdout framing, permits GET=405 when SSE is not offered, and specifies protocol-version handling.
    https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
13. Model Context Protocol, **Authorization, protocol revision 2025-11-25**, requires audience-bound access-token validation on every HTTP request and forbids accepting/transiting tokens intended for other resources.
    https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
14. Model Context Protocol, **Security Best Practices**, documents SSRF controls, redirect/DNS validation, token-passthrough risk, session hijacking, and local-server compromise.
    https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices
15. Model Context Protocol, **Schema Reference, protocol revision 2025-11-25**, defines tool input/output schemas and notes that tool annotations are hints rather than trustworthy enforcement.
    https://modelcontextprotocol.io/specification/2025-11-25/schema
16. RFC Editor, **RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)**, specifies Ed25519/Ed448 and verification test vectors for a possible receipt-signature profile.
    https://www.rfc-editor.org/rfc/rfc8032.html
