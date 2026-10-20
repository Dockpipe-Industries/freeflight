# Static site deployment through DockPipe Cloud

PR #35 remains draft. The privileged Docker/Compose receiver has been replaced
with unprivileged static delivery following DockPipe Cloud's existing architecture.
No infrastructure, credentials, permissions or release branches have been changed.

## Publication and delivery

The staging workflow retains the exact-source CI/CodeQL and promotion gates, then
publishes a unique staging prerelease. The site collector validates the published
site, container/audit and corresponding-source artifacts. Container scanning remains
qualification evidence; deployment no longer imports or runs container images.

`site.deploy.bundle` emits `site.bundle.gz`: a bounded gzip JSON document with fixed
product/environment identity, release metadata, an exact public-file allowlist and
per-file digests. `site.deploy.send` uses a dedicated release key in an ephemeral
SSH agent, pinned host trust and `deploy SHA256`, matching Cloud's transport pattern.

The root-owned receiver program runs as `freeflight-release`, rejects root execution,
and cannot invoke Docker, sudo, shell commands or arbitrary paths. It writes a
candidate under `/srv/freeflight-staging/releases`, atomically switches `current`,
checks the served receipt and every asset on loopback, and restores the previous
release if health fails. A failed rollback or uncertain write retains its lock.
Candidates remain available for reconciliation. The fixed Nginx allowlist does not
serve internal activation records, configuration or arbitrary files.

Hosted CI does not require public access to the private staging site. The operator
coordinator verifies private HTTPS before enabling automatic delivery. Existing
Cloud operator-IP restrictions and unrelated hostnames remain intact.

## Coordinated setup

`dockpipe --workflow infra.up` delegates to a pinned, clean, reviewed Cloud extension
checkout. The extension reuses Cloud's process helper, Terraform exact-plan apply
and recovery-copy workflow, `SshSession` and Cloudflare client. It does not invoke
Cloud's original whole-host bootstrap. The extension is prepared in an isolated
local checkout and has not been pushed to Cloud or provisioned.

Inputs are selected by the operator, not hard-coded secret identifiers:

- `FREEFLIGHT_CLOUD_CHECKOUT`: reviewed Cloud extension checkout.
- `FREEFLIGHT_CLOUD_COMMIT`: exact reviewed extension commit.
- `FREEFLIGHT_INFRA_ENVIRONMENT_ID`: explicitly approved staging Environment.
- Existing approved Cloudflare secret references and GitHub CLI authentication.
- Existing initialized Cloud Terraform workspace and backend; no second state owner.

One `op run` session injects credentials. Default execution creates and reviews a
plan only. `FREEFLIGHT_INFRA_APPLY_SHA256` selects an already reviewed saved plan;
apply never regenerates that plan. The policy permits creation only of the isolated
staging release key and a firewall attached solely to the existing staging host,
opening only release port 2223. Host replacement, production changes, unrelated
resources, outbound expansion and infrastructure drift are rejected.

After explicit setup approval, apply retains Cloud's private state recovery copies.
The coordinator takes host trust/bootstrap keys from existing state into memory,
installs only FreeFlight-owned receiver/Nginx/listener files, and verifies isolation.
The account has no sudo or Docker-group grant. Local endpoints are 18080 for health
and static assets and 18081 for operator-restricted tunnel ingress. Existing company
ports, account, paths and serving configuration are preserved.

The coordinator requires the matching sender already on staging and a selected
published `FREEFLIGHT_DEPLOY_RELEASE_TAG`. It verifies published bytes before
mutating infrastructure, activates them through the restricted sender, adds only
the FreeFlight tunnel/DNS/header scope, verifies private HTTPS and then reconciles
GitHub settings. The private key goes to GitHub via stdin, never a command argument
or key file. Mutations are not blindly retried. Setup failure leaves CI disabled;
inspect retained plan/host state before resuming.

GitHub's **staging environment** contains:

| Kind | Name | Meaning |
| --- | --- | --- |
| Variable | `FREEFLIGHT_SITE_DEPLOY_ENABLED` | `true` only after coordinated readiness |
| Variable | `FREEFLIGHT_SITE_DEPLOY_HOST` | State-verified staging host |
| Variable | `FREEFLIGHT_SITE_DEPLOY_SSH_PORT` | Scoped release listener, planned 2223 |
| Variable | `FREEFLIGHT_SITE_DEPLOY_KNOWN_HOSTS` | State-pinned host key |
| Secret | `FREEFLIGHT_SITE_DEPLOY_PRIVATE_KEY` | State-owned FreeFlight release key |

No administrator SSH key, provider token or state credential is installed in the
GitHub deployment job. Manual key generation/copying and privileged receiver setup
are superseded, not prerequisites for this architecture.

## Remaining gates

Offline tests cover static bytes, source/product boundaries, rollback, additive
plans, private ingress rendering and coordinator sequencing with fake providers.
They do not establish live Terraform/provider compatibility, host installation,
certificate coverage, private HTTPS readiness or GitHub credential availability.
Terraform validation and Linux bootstrap integration still require suitable tooling
and a disposable fixture; no live infrastructure command has been run.

Provider/state inspection needs a separately approved bounded read scope. The
existing Cloud backend is shared platform state; reading it may materialize
sensitive state beyond FreeFlight even when only staging outputs are selected.
Do not read it or another 1Password Environment implicitly. Cloud extension review
and publication, setup grants, and PR promotion remain distinct approvals.

The production workflow remains explicitly invoked, stable-release/master gated
wiring. This coordinator accepts staging only; production provisioning and live
activation remain excluded. `site.deploy.prepare` still provides an offline
container qualification receipt, but it is not the deployment implementation.
