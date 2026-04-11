from __future__ import annotations

import json
from hashlib import sha512

import pytest

from orchestrator.services.policy_parser import PolicyParser


def build_policy(**overrides):
    policy = {
        "policy_id": "policy-test",
        "version": "1.0.0",
        "description": "Test policy",
        "target": {"os": ["linux", "windows"], "device_groups": ["test"]},
        "ipsec_policy": {
            "mode": "tunnel",
            "key_exchange": "ikev2",
            "authentication": {"type": "psk", "secret_ref": "psk_test"},
            "crypto": {
                "ike": {"encryption": "AES_GCM_256", "integrity": "HMAC_SHA2_512", "dh_group": "ECP_384", "pfs": True},
                "esp": {"encryption": "AES_GCM_256", "integrity": "HMAC_SHA2_512", "dh_group": "ECP_384", "pfs": True},
            },
            "connections": [
                {
                    "name": "conn1",
                    "local_ip": "10.0.0.10",
                    "local_subnet": "10.0.0.0/24",
                    "remote_ip": "10.1.0.10",
                    "remote_subnet": "10.1.0.0/24",
                    "auto_start": True,
                }
            ],
        },
        "execution": {"retry_count": 3, "timeout_seconds": 60, "rollback_on_failure": True},
        "compliance": {"require_strong_crypto": True, "require_pfs": True},
    }
    for key, value in overrides.items():
        policy[key] = value
    return policy


class TestBasicParsing:
    def test_valid_policy_parses_successfully(self):
        result = PolicyParser().parse(json.dumps(build_policy()).encode("utf-8"))
        assert result.is_valid is True
        assert result.policy_id == "policy-test"
        assert result.version == "1.0.0"
        assert result.input_hash == sha512(json.dumps(build_policy()).encode("utf-8")).hexdigest()
        assert set(result.os_configs.keys()) == {"linux", "windows"}

    def test_invalid_json_returns_error(self):
        result = PolicyParser().parse(b"{not-json")
        assert result.is_valid is False
        assert any("Malformed JSON" in error for error in result.errors)

    def test_missing_required_top_level_keys_returns_errors(self):
        policy = build_policy()
        del policy["execution"]
        del policy["compliance"]
        result = PolicyParser().parse(json.dumps(policy).encode("utf-8"))
        assert result.is_valid is False
        assert "execution" in result.errors[0]
        assert "compliance" in result.errors[0]

    def test_empty_file_returns_error(self):
        result = PolicyParser().parse(b"")
        assert result.is_valid is False
        assert result.errors

    def test_empty_connections_list_returns_error(self):
        policy = build_policy()
        policy["ipsec_policy"]["connections"] = []
        result = PolicyParser().parse(json.dumps(policy).encode("utf-8"))
        assert result.is_valid is False
        assert any("connections" in error for error in result.errors)

    def test_unknown_os_returns_error(self):
        policy = build_policy()
        policy["target"]["os"] = ["linux", "haiku"]
        result = PolicyParser().parse(json.dumps(policy).encode("utf-8"))
        assert result.is_valid is False
        assert any("Unsupported OS targets" in error for error in result.errors)

    def test_empty_target_os_returns_error(self):
        policy = build_policy()
        policy["target"]["os"] = []
        result = PolicyParser().parse(json.dumps(policy).encode("utf-8"))
        assert result.is_valid is False
        assert any("target.os" in error for error in result.errors)


class TestAliasNormalisation:
    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("aes-gcm-256", "aes256gcm16"),
            ("aes256gcm16", "aes256gcm16"),
            ("aes_gcm_256", "aes256gcm16"),
            ("aes-256-gcm", "aes256gcm16"),
            ("chacha20poly1305", "chacha20poly1305"),
        ],
    )
    def test_encryption_aliases(self, alias, expected):
        policy = build_policy()
        policy["ipsec_policy"]["crypto"]["ike"]["encryption"] = alias
        policy["ipsec_policy"]["crypto"]["esp"]["encryption"] = alias
        result = PolicyParser().parse(json.dumps(policy).encode("utf-8"))
        assert result.os_configs["linux"].ike_encryption == expected
        assert result.os_configs["linux"].esp_encryption == expected

    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("sha2-256", "sha256"),
            ("sha256", "sha256"),
            ("hmac-sha256", "sha256"),
            ("sha2-512", "sha512"),
        ],
    )
    def test_integrity_aliases(self, alias, expected):
        policy = build_policy()
        policy["ipsec_policy"]["crypto"]["ike"]["integrity"] = alias
        policy["ipsec_policy"]["crypto"]["esp"]["integrity"] = alias
        result = PolicyParser().parse(json.dumps(policy).encode("utf-8"))
        assert result.os_configs["linux"].ike_integrity == expected
        assert result.os_configs["linux"].esp_integrity == expected

    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("modp2048", "modp2048"),
            ("group14", "modp2048"),
            ("ecp256", "ecp256"),
            ("group20", "ecp384"),
        ],
    )
    def test_dh_group_aliases(self, alias, expected):
        policy = build_policy()
        policy["ipsec_policy"]["crypto"]["ike"]["dh_group"] = alias
        policy["ipsec_policy"]["crypto"]["esp"]["dh_group"] = alias
        result = PolicyParser().parse(json.dumps(policy).encode("utf-8"))
        assert result.os_configs["linux"].ike_dh_group == expected
        assert result.os_configs["linux"].esp_dh_group == expected


class TestOSSpecificOutput:
    def test_linux_and_windows_outputs(self):
        result = PolicyParser().parse(json.dumps(build_policy()).encode("utf-8"))
        linux_config = result.os_configs["linux"]
        windows_config = result.os_configs["windows"]

        assert linux_config.raw_driver_block["connections"]["conn1"]["proposals"] == "aes256gcm16-sha512-ecp384"
        assert linux_config.raw_driver_block["connections"]["conn1"]["children"]["conn1-child"]["esp_proposals"] == "aes256gcm16-sha512-ecp384"
        assert windows_config.raw_driver_block["commands"][0]["cmdlet"] == "New-NetIPsecMainModeRule"
        assert windows_config.raw_driver_block["commands"][1]["cmdlet"] == "New-NetIPsecMainModeCryptoSet"
        assert windows_config.raw_driver_block["commands"][2]["cmdlet"] == "New-NetIPsecQuickModeCryptoSet"

    def test_single_os_target_builds_only_that_os(self):
        policy = build_policy()
        policy["target"]["os"] = ["linux"]
        result = PolicyParser().parse(json.dumps(policy).encode("utf-8"))
        assert set(result.os_configs.keys()) == {"linux"}
        assert "windows" not in result.os_configs

    def test_linux_and_windows_native_formats(self):
        result = PolicyParser().parse(json.dumps(build_policy()).encode("utf-8"))
        linux_config = result.os_configs["linux"]
        windows_config = result.os_configs["windows"]
        assert linux_config.ike_encryption == "aes256gcm16"
        assert linux_config.esp_dh_group == "ecp384"
        assert windows_config.ike_encryption == "AESGCM256"
        assert windows_config.esp_dh_group == "ECP384"
        assert "conn1" in linux_config.raw_driver_block["connections"]
        assert isinstance(windows_config.raw_driver_block["commands"], list)


class TestComplianceChecks:
    def test_weak_algo_with_strong_crypto_true_errors(self):
        policy = build_policy()
        policy["ipsec_policy"]["crypto"]["esp"]["encryption"] = "AES-128"
        result = PolicyParser().parse(json.dumps(policy).encode("utf-8"))
        assert result.is_valid is False
        assert any("Weak algorithm" in error for error in result.errors)

    def test_pfs_required_without_dh_group_warns(self):
        policy = build_policy()
        policy["ipsec_policy"]["crypto"]["esp"]["dh_group"] = None
        result = PolicyParser().parse(json.dumps(policy).encode("utf-8"))
        assert result.is_valid is True
        assert any("PFS required" in warning for warning in result.warnings)

    def test_input_hash_length_and_determinism(self):
        raw = json.dumps(build_policy()).encode("utf-8")
        result_a = PolicyParser().parse(raw)
        result_b = PolicyParser().parse(raw)
        result_c = PolicyParser().parse(json.dumps(build_policy(description="changed")).encode("utf-8"))
        assert len(result_a.input_hash) == 128
        assert result_a.input_hash == result_b.input_hash
        assert result_a.input_hash != result_c.input_hash
