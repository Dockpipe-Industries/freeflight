# Existing staging hostname migration

This explicitly approved, one-time workflow changes only the inactive FreeFlight
receiver's hostname from `freeflight.staging.dockpipe.com` to
`freeflight-staging.dockpipe.com`. It replaces exact reviewed bytes in the root-owned
Nginx configuration and receiver Python file. Existing operator networks, SSH
settings, keys, services and release content are preserved. No setup/apply or
activation workflow is invoked.

Provide the existing short-lived operator SSH agent in `SSH_AUTH_SOCK`, the
state-owned public pin in `FREEFLIGHT_PINNED_HOST_PUBLIC_KEY`, and
`FREEFLIGHT_HOSTNAME_STAGE=approved-flat-hostname-only`, then run
`dockpipe --workflow infra.hostname`. The private identity must remain in memory;
this workflow does not retrieve or persist credentials. Host verification pins the
previously reviewed ED25519 fingerprint. It compares Cloud/admin preservation
snapshots before and after the operation.

The origin must have the existing ownership marker, no active site and exactly the
reviewed old file hashes. Unexpected or already migrated files stop without a
retry. Nginx validation/reload failure restores the previous file bytes if no
concurrent modification occurred. The public Cloudflare routing workflow creates
the replacement first and verifies HTTPS before retiring the old route. The origin
update alone does not enable delivery or publish a site.

`release.policy` tests success, modified input, active site, validation failure and
reload rollback. The disposable Ubuntu bootstrap CI also performs the migration
against real Nginx and verifies new-host health, old-host denial and existing-site
preservation before its normal activation/rollback tests.
