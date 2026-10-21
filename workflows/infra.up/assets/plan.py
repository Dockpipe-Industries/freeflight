"""Pure additive-plan gate shared by the Cloud coordinator and offline tests."""
import json
import sys

ALLOWED = {"tls_private_key.freeflight_staging_release[0]", "digitalocean_firewall.freeflight_staging_release[0]"}


def review(plan):
    changes = []
    resources = plan.get("prior_state", {}).get("values", {}).get("root_module", {}).get("resources", [])
    staging = [item for item in resources if item.get("address") == "digitalocean_droplet.staging"]
    if len(staging) != 1 or not staging[0].get("values", {}).get("id"):
        raise ValueError("Existing staging host identity required")
    host_id = str(staging[0]["values"]["id"])
    if plan.get("resource_drift"):
        raise ValueError("Reconcile infrastructure drift before FreeFlight setup")
    for item in plan.get("resource_changes", []):
        actions = item["change"]["actions"]
        if actions == ["no-op"] or item.get("mode") == "data" and actions == ["read"]:
            continue
        if item["address"] not in ALLOWED or actions != ["create"]:
            raise ValueError("Plan changes infrastructure outside additive FreeFlight scope")
        after = item["change"].get("after", {})
        if item["address"].startswith("tls_private_key") and after.get("algorithm") != "ED25519":
            raise ValueError("Only the fixed Ed25519 release identity is permitted")
        if item["address"].startswith("digitalocean_firewall"):
            if [str(value) for value in after.get("droplet_ids", [])] != [host_id]:
                raise ValueError("Firewall must attach only to the existing staging host")
            rules = after.get("inbound_rule", [])
            if len(rules) != 1 or rules[0].get("protocol") != "tcp" or rules[0].get("port_range") != "2223" or rules[0].get("source_addresses") != ["0.0.0.0/0"]:
                raise ValueError("Unexpected release firewall scope")
            if after.get("outbound_rule"):
                raise ValueError("FreeFlight extension may not expand outbound access")
        changes.append(item["address"])
    return changes


if __name__ == "__main__":
    print(json.dumps(review(json.load(sys.stdin))))
