# Dedicated site container: operator handoff

## Architecture review hold

The owner requested the actual DockPipe Cloud provisioning and delivery pattern.
The manual receiver/key/listener setup described below is withdrawn as an operator
procedure. Do not install it or enable the deployment job. PR #35 remains draft;
its privileged container activation implementation is a tested prototype, not the
accepted deployment architecture. See [the source-based alignment plan](site-deployment-alignment.md).
Release publication qualification remains independently useful. No infrastructure
or production change is authorized by this document.

## Pipeline publication and activation

`.github/workflows/staging.yml` runs automatically on canonical staging pushes.
It selects a successful exact-tree `js/dev` push qualification, checks CodeQL and
the `js/dev -> dev -> staging` promotion chain, then verifies the retained bytes.
It publishes a prerelease named by VERSION, qualification run and source SHA:
`vVERSION.staging.RUN.SHA` for prerelease versions, or
`vVERSION-staging.RUN.SHA` for numeric versions. Bundled VERSION is unchanged.
Staging publication uses the Ubuntu 22.04-compatible Linux x64 bundle, the other
three native platforms, corresponding sources, and site/container/audit artifacts.
It never promotes master or marks the prerelease latest.

The separate deployment job reacquires the published site bytes and verifies their
GitHub digests, manifest, exact-source successful CI/CodeQL, promotion tree, source
notices, image scan, and container/site binding. DockPipe `site.deploy.bundle`
constructs a bounded delivery containing only the image, metadata and audit.
`site.deploy.send` streams it using pinned SSH trust to a **FreeFlight-specific**
forced-command receiver. It does not use the DockPipe company-site receiver.

Publication is independent of hosting setup. Missing hosting settings fail the
deployment job explicitly; they do not prevent the prerelease becoming downloadable.
After configuring hosting, rerun the failed deployment job, not a successful
publication job. An existing tag/release stops publication for reconciliation;
the pipeline never overwrites or deletes it automatically. Inspect retained
publication evidence after any uncertain write.

`.github/workflows/site-production.yml` is manual, canonical-master-only, and uses
the production environment. It accepts only a published stable `vVERSION` release
whose target matches current master and whose successful source qualification has
the same tree. It selects the production site artifact, never the staging image.
Configure required production-environment reviewers before enabling it. Neither
staging pushes nor ordinary master pushes activate production.

### Receiver setup: explicit infrastructure boundary

No pipeline creates users, credentials, host keys, SSH listeners, Docker authority,
DNS records or TLS routes. An operator must approve and install the restricted
receiver on the existing selected host. Required environment settings are:

| Setting | Contract |
| --- | --- |
| `FREEFLIGHT_SITE_DEPLOY_ENABLED` | `true` only after the receiver and ingress are verified |
| `FREEFLIGHT_SITE_DEPLOY_HOST` | Approved existing host |
| `FREEFLIGHT_SITE_DEPLOY_SSH_PORT` | Approved dedicated receiver listener port |
| `FREEFLIGHT_SITE_DEPLOY_KNOWN_HOSTS` | Independently verified `[host]:port` host-key entry |
| `FREEFLIGHT_SITE_DEPLOY_PRIVATE_KEY` | Secret for the FreeFlight-only forced-command identity |

Use separate staging and production environment values/identities. The sender
loads the key only into an ephemeral SSH agent and does not write it to disk.
Do not reuse an administrator key, copy DockPipe's release identity, disable host
verification, or grant the release account unrestricted Docker-group membership.

The host installation consists of a root-owned reviewed receiver checkout at
`/opt/freeflight/receiver`, the pinned DockPipe runtime at
`/opt/freeflight/receiver-runtime`, and `/etc/freeflight-site/receiver.json` based
on `site/container/receiver.example.json`. The configured state directory must
already exist, be owner-controlled, and contain no unowned service state. Port
18080 is a proposal, not a reservation; actual capacity, port, runtime and host
identity must be checked first.

`forced-command.sh` is a proposed root-owned fixed entry point at
`/usr/local/libexec/freeflight-site-activate`. If the approved host uses privileged
Docker, the `freeflight-release` SSH identity needs permission for only this exact
sudo entry point, passing its single `SSH_ORIGINAL_COMMAND` argument. This is a
new privileged grant requiring explicit approval; it is not installed by this PR.
Its environment is cleared, paths are fixed, and the receiver accepts only
`deploy ENVIRONMENT SHA256` matching its operator-owned configuration. Disable
shell/TTY, forwarding, user environment, and other commands for that identity.
Never broaden an existing listener or identity to satisfy this setup implicitly.

The receiver checks transfer and image/audit hashes, environment/release identity,
Linux x64 runtime, disk/memory headroom, available first-install port, image ID,
and existing project ownership. It generates its own fixed Compose configuration:
loopback-only binding, UID 101, read-only filesystem, dropped capabilities and
bounded memory/CPU/PIDs. It accepts no uploaded Compose, arbitrary mounts or
commands. Local and public HTTPS probes verify health, source receipt and every
served asset. Five bounded attempts precede rollback to the recorded prior image;
failed first activation removes only its own Compose project.

Candidates and failure evidence are retained. A failed/uncertain activation retains
`deploy.lock`; inspect process/container/current-state evidence before an operator
removes that lock. No automatic pruning or blind retry occurs. The sender repeats
public identity/hash verification after a successful receiver response.

## Staging and production preparation

`dockpipe --workflow site.deploy.prepare` validates local delivery inputs and emits
an isolated Compose project plus a preparation receipt under `bin/.local/site-delivery`.
Set `FREEFLIGHT_DEPLOY_INPUT` to an operator-owned JSON file containing:

```json
{
  "environment": "staging",
  "sourceCommit": "<40-character-qualified-source-commit>",
  "loopbackPort": 18080,
  "containerReceipt": "/absolute/container/verification.json",
  "containerArchive": "/absolute/container/freeflight-site-image.tar.gz",
  "containerArchiveSha256": "<independently-obtained-sha256>",
  "auditReceipt": "/absolute/audit/verification.json",
  "auditReport": "/absolute/audit/vulnerabilities.json",
  "correspondingSources": "/absolute/qt-corresponding-sources.zip",
  "correspondingSourcesSha256": "<independently-obtained-sha256>"
}
```

Refresh remote refs through the existing approved Git connection first. The workflow
checks local promotion ancestry/tree identity, container environment and hostname,
archive and audit binding, and the source archive digest. It does not authenticate
hosted receipts or replace hosted qualification. Hashes must come from the exact
successful source run, not from an untrusted artifact supplier. A prepared receipt
is explicitly not deployment authorization or a remote-preflight pass.

For `production`, it additionally requires a stable numeric VERSION, a matching
`vVERSION` tag, and identical qualified source/tag/master trees. RC2 preview inputs
are rejected. Use the production site's separately qualified image; staging and
production images are not interchangeable. Production preparation does not publish
a release, promote master, activate content, or configure DNS.

Generated Compose projects are `freeflight-staging` or `freeflight-production`,
with the exact image ID and a loopback-only port. The candidate port 18080 is not a
reservation: check it and host capacity before activation. Preserve read-only
filesystem, UID 101, dropped capabilities and resource limits. No remote command,
image loading, service startup or credential access occurs in this workflow.

Staging activation has owner approval, including its exact hostname route.
Operator access and trusted host identity remain prerequisites. Production-specific
DNS, certificate, strict SNI/Host routing and backend changes require separate
approval; never relax authenticated origin TLS or replace another site's receiver.
Use the existing infrastructure owner's change path. Keep private infrastructure
addresses, vault references and deployment state outside this public repository.

Before any activation, verify fresh hosted CI/CodeQL evidence, the remote artifact
hash/image ID, corresponding-source availability, host/runtime/port readiness and
an environment-specific rollback plan. After activation, verify exact HTTPS source
identity, served hashes, browser/Wasm behavior and unchanged existing site behavior.

## Infrastructure contract

The infrastructure below remains an operator handoff, not evidence
of hosted readiness. No remote command, credential access, pairing, host change,
DNS update or deployment was performed for this assessment.

## Reusable public DockPipe contract

DockPipe's existing [remote-node profile mode](https://github.com/Dockpipe-Industries/dockpipe/blob/staging/docs/runtime/remote-nodes.md)
runs an operator-installed workflow in a fixed worker-side directory. The profile
binds the workflow, timeout and result paths. Submitting a job cannot replace its
paths, environment or command arguments. This is the appropriate existing entry
point for a reviewed deployment operation on an already approved host; it is not
proof that such a profile is currently installed or authorized.

Workflow delivery is a different mode. Its current source budget is 8 MiB and
1024 files, and hidden paths/local state are excluded. Do not send a container image
archive through that channel or bypass its guards by disguising generated state.
Image staging needs an existing operator-approved artifact transfer mechanism.

## Inputs still required

- Existing target node and installed profile identity; confirm that the node is
  the intended existing host/VPC and that its operator has authorized this action.
- Target OS/architecture, Docker/Compose versions and existing effective Docker
  authority. Do not add group membership, administrator access or new credentials.
- Exact qualified image archive and receipt, their digests, image ID and target
  architecture. Identify how the approved artifact is staged into the profile's
  local workspace without rebuilding or accepting mutable image tags.
- Reserved loopback port, dedicated Compose project identity and persistent
  operator-owned deployment directory. Confirm no existing service is replaced.
- Existing ingress owner's route for the selected hostname and environment,
  including TLS/readiness expectations. A loopback container is not public HTTPS.
- Previous qualified image/receipt for rollback, or explicit first-deployment
  behavior. Retention and failure recovery must preserve unrelated services.

## Remote-profile alternative

An existing approved remote profile may host the same receiver workflow once its
artifact-transfer contract is selected. Keep the dedicated Compose configuration as the runtime
contract. A read-only planning stage verifies the archive SHA-256 and receipt,
architecture, exact image ID selection, available loopback port, resolved Compose
settings and previous deployment receipt. It reports the intended service change;
it does not load an image, start a container or modify ingress.

The implemented receiver can load only that archive, verify the
loaded image ID, activate only that Compose project, and perform bounded health
and release-identity probes. On failure it restores the previous selected image
and records the result. Use DockPipe's existing remote job/result/cancellation
interfaces for orchestration when that profile is installed. The current pipeline
implements the separately scoped forced-command transfer described above, following
the company-site delivery pattern. Neither transport is claimed installed.

Container image loading and Docker access are privileged operations even when the
service process is unprivileged. Existing workflow execution permission alone
must not be interpreted as authorization to widen host or network authority.
A completed plan or a successful local container test is not a deployment result.
