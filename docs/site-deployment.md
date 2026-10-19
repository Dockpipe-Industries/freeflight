# Dedicated site container: operator handoff

This note is a proposed handoff, not an installed deployment workflow or evidence
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

## Smallest subsequent workflow

Once those inputs exist, author one DockPipe host workflow installed in the
approved profile. Keep the current dedicated Compose configuration as the runtime
contract. A read-only planning stage verifies the archive SHA-256 and receipt,
architecture, exact image ID selection, available loopback port, resolved Compose
settings and previous deployment receipt. It reports the intended service change;
it does not load an image, start a container or modify ingress.

An explicitly authorized apply stage can then load only that archive, verify the
loaded image ID, activate only that Compose project, and perform bounded health
and release-identity probes. On failure it restores the previous selected image
and records the result. Use DockPipe's existing remote job/result/cancellation
interfaces for orchestration; no new SSH runner, provider setup, registry or
Terraform infrastructure is necessary. Implement and test those stages only after
the host/profile and artifact contract are selected, so their checks enforce real
inputs rather than fictional infrastructure.

Container image loading and Docker access are privileged operations even when the
service process is unprivileged. Existing workflow execution permission alone
must not be interpreted as authorization to widen host or network authority.
A completed plan or a successful local container test is not a deployment result.
