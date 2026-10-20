"""Pure plan and generated host policy checks; no credentials or infrastructure."""
import copy
import unittest
from unittest.mock import patch
import plan
import bootstrap


def fixture():
    return {"prior_state": {"values": {"root_module": {"resources": [
        {"address": "digitalocean_droplet.staging", "values": {"id": "123"}}]}}},
        "resource_changes": [{"address": "digitalocean_firewall.freeflight_staging_release[0]",
            "change": {"actions": ["create"], "after": {"droplet_ids": [123], "outbound_rule": [],
                "inbound_rule": [{"protocol": "tcp", "port_range": "2223", "source_addresses": ["0.0.0.0/0"]}]}}}]}


class PlanTests(unittest.TestCase):
    def test_only_additive_existing_host_scope_passes(self):
        self.assertEqual(len(plan.review(fixture())), 1)

    def test_replacement_production_and_other_resources_fail(self):
        for address in ["digitalocean_droplet.staging", "digitalocean_database_cluster.platform",
                        "digitalocean_firewall.application[production]", "tls_private_key.other"]:
            value = fixture()
            value["resource_changes"][0]["address"] = address
            with self.assertRaises(ValueError):
                plan.review(value)
        value = fixture()
        value["resource_changes"][0]["change"]["actions"] = ["delete", "create"]
        with self.assertRaises(ValueError):
            plan.review(value)

    def test_firewall_cannot_broaden_ports_hosts_or_outbound(self):
        for field, replacement in [("droplet_ids", [456]), ("outbound_rule", [{"protocol": "tcp"}]),
                                    ("inbound_rule", [{"protocol": "tcp", "port_range": "22", "source_addresses": ["0.0.0.0/0"]}])]:
            value = fixture()
            value["resource_changes"][0]["change"]["after"][field] = replacement
            with self.assertRaises(ValueError):
                plan.review(value)

    def test_missing_state_and_drift_fail_closed(self):
        for value in [{}, {**fixture(), "resource_drift": [{"address": "other"}]}]:
            with self.assertRaises(ValueError):
                plan.review(value)

    def test_generated_host_policy_preserves_private_scope(self):
        nginx, ssh, service = bootstrap.configuration(["192.0.2.7/32"])
        self.assertIn("192.0.2.7/32 1;", nginx)
        self.assertIn("if ($freeflight_operator = 0) { return 403; }", nginx)
        self.assertIn("listen 127.0.0.1:18080", nginx)
        self.assertIn("listen 127.0.0.1:18081", nginx)
        self.assertNotIn("listen 0.0.0.0", nginx)
        self.assertIn("AllowUsers freeflight-release", ssh)
        self.assertIn("DisableForwarding yes", ssh)
        self.assertIn("PermitUserRC no", ssh)
        self.assertIn("ForceCommand /usr/local/libexec/freeflight-site-activate", ssh)
        self.assertNotIn("sudo", ssh)
        self.assertIn("freeflight-release.conf", service)

    def test_invalid_operator_network_rejected(self):
        for networks in [[], ["0.0.0.0/0; execute"], ["not-a-network"]]:
            with self.assertRaises(ValueError):
                bootstrap.configuration(networks)

    def test_unprivileged_process_cannot_run_bootstrap(self):
        with patch.object(bootstrap.os, "geteuid", return_value=1000, create=True):
            with self.assertRaisesRegex(ValueError, "requires root"):
                bootstrap.install({})


if __name__ == "__main__":
    unittest.main()
