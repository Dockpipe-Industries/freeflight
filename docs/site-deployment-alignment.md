# DockPipe Cloud deployment alignment

Status: architecture review hold; no infrastructure operations performed.
The owner requested Cloud's existing workflow rather than a separate manual
FreeFlight receiver setup. PR #35 must remain draft until its deployment path
implements this alignment and passes the corresponding tests.

## Inspected source

Reference: Dockpipe-Industries/dockpipe-cloud staging commit
`4f55a5ae632a4de0bcf79662dd8441a5eaac9279`.
Paths below are relative to that repository.

| Concern | Cloud implementation | PR35 difference / required correction |
| --- | --- | --- |
| Operator entry point | `workflows/infra.up/config.yml` and `README.md`: one DockPipe operation, one `op run` credential session | Replace manual credential/bootstrap checklist with the same coordinator pattern |
| Credential sources | `dockpipe.config.json`, `infra.up/config.yml`: infrastructure Environment, existing Cloudflare item references, existing `gh` login | Select the explicitly approved staging Environment; do not inherit another Environment ID or read additional credential items implicitly |
| Infrastructure ownership | `infra/terraform/digitalocean/staging-bootstrap.tf`: Terraform owns host/bootstrap/release keys in private state | Reuse infrastructure owner's state/trust handoff; no manually generated CI key or independent state owner for the same host |
| SSH trust | `workflows/infra.up/assets/scripts/ssh-session.ts`: pinned Terraform host key, bootstrap key in private ephemeral agent | Remove dependence on manually copied trust and account installation |
| Delivery privilege | `infra/deploy/receive.ts`, `activate.ts`: unprivileged receiver, bounded static bundle, atomic symlink activation and rollback | Replace privileged Docker/Compose activation; retain container build/audit as qualification evidence if useful |
| Delivery isolation | `infra/deploy/release-sshd.conf`, `bootstrap.sh`: fixed unprivileged account, root-owned command/keys, dedicated release listener | Extend reviewed shared implementation with a separate fixed FreeFlight service scope; do not give existing company receiver arbitrary product/path arguments |
| Payload | `workflows/site.release/assets/scripts/bundle.ts`: gzip JSON, fixed product/files, per-file hashes and size bounds | Add a fixed FreeFlight bundle schema/allowlist through shared code; do not disguise FreeFlight as product `dockpipe` |
| Staging bootstrap | `workflows/infra.up/assets/scripts/up.ts`: verify providers/artifact/sender, review plan, recover state, bootstrap, verify HTTPS, then configure GitHub | Implement equivalent sequencing; keep delivery disabled until first readiness succeeds |
| Private HTTPS | `cloudflare.ts`, `tunnel.ts`, `readiness.ts` under `infra.up/assets/scripts`: operator-IP restriction and exact hostname identity | Preserve existing staging access controls; bootstrap checks public HTTPS from authorized operator context, CI receiver checks local identity |
| CI | `.github/workflows/site-staging.yml`: tested retained artifact, restricted SSH sender, staging enable flag | Reuse transport contract; keep explicit reporting when setup is incomplete |
| Production | `workflows/infra.up/assets/scripts/production-up.ts`: explicit invocation, exact current-master artifact, reviewed plan, verified ingress and routing rollback | Preserve explicit production hold; no master push deployment or live production setup |
| Native releases | Cloud site delivery activates a site artifact; it is not FreeFlight's multi-platform release publisher | Retain FreeFlight's exact-source CI/CodeQL, promotion evidence and prerelease publication gates |

## Important boundaries

The inspected Cloud configuration points its infrastructure aliases at a different
Environment from the staging Environment supplied for this task. That is source
configuration evidence, not authorization to access the other Environment.
Successful staging Environment inspection established provider/state variable
names only. It did not establish that those credentials can access Cloud's existing
state or providers.

Cloud's current receiver is not a generic package. Its product, file allowlist,
repository, account, ports and serving paths are fixed. Calling it directly with a
FreeFlight payload will correctly reject the payload. Relaxing that restriction or
copying the entire coordinator into FreeFlight would not constitute safe reuse.
The shared abstraction must preserve fixed service scopes and be introduced in an
isolated, reviewed infrastructure-owner change, not the active Cloud checkout.

Cloud's documented setup may replace its staging machine when immutable bootstrap
changes. That is not authorized for this shared existing host. The FreeFlight
extension must reject host/database/production replacement and unrelated routing
changes, or stop with the exact proposed plan for approval.

The earlier proposal that GitHub runners require public staging HTTPS access is
withdrawn: Cloud performs local receiver health checks and operator-side private
HTTPS readiness. Preserve operator restrictions instead of opening preview access
to accommodate a different sender probe.

## Minimal aligned implementation and setup sequence

1. Read-only verification of the approved staging provider/state access, under
   one Environment injection. Establish whether the infrastructure owner's
   existing Terraform outputs provide this host's bootstrap identity and trust.
   Do not read another Environment, export keys or create a second state owner.
2. Prepare a scoped shared Cloud deployment extension: fixed FreeFlight identity,
   public-file allowlist, serving root and loopback endpoint; reuse bounded
   decoding, unprivileged activation/rollback, SSH session and provider clients.
   No production/company receiver scope may be expanded by client input.
3. Wire FreeFlight DockPipe workflows to the pinned shared implementation. Keep
   release qualification/publishing; transform the verified site artifact to the
   shared static delivery contract. Remove the superseded privileged activation
   dependency once the replacement is tested.
4. Add infrastructure-owner planning for this isolated service, existing private
   tunnel and exact hostname. Preserve existing routes/operator allowlists and
   state. Test plan rejection of unrelated destructive actions and privilege
   expansion. Do not execute `infra.up` from the current Cloud checkout unchanged.
5. After specific setup approval, use the coordinator to provision the approved
   scope, load state-owned keys into ephemeral agents, verify host identity and
   private HTTPS, then reconcile the restricted GitHub delivery credential and
   enable flag. No manual key transfer/checklist is the intended normal flow.
6. Only after separate PR promotion approval, qualify and promote through
   `js/dev -> dev -> staging`, then verify actual prerelease download and site
   activation independently. Production remains wiring-only.

No shared package extraction, provider access, state read, credential transfer,
host installation or activation has occurred as part of this comparison.

## Implemented code alignment

The subsequent code change replaces the privileged receiver with unprivileged
static activation and adds `workflows/infra.up`. The isolated Cloud extension
contains `freeflight.tf`, `freeflight-up.ts`, `freeflight-routing.ts` and offline
routing/coordinator tests. It imports existing Cloud SSH, provider and apply helpers;
private Cloud implementation has not been copied into this public repository.
The FreeFlight bundle/receiver use the same bounded static-delivery pattern with a
separate fixed product allowlist. See `site-deployment.md` for the implemented
contract and remaining execution gates. The earlier architecture hold now applies
to live validation and approval, not absence of replacement code.
