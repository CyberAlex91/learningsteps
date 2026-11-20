# Zweck: Prüft die Offline-Sicherungen, Projektgrenzen und sichere Wiederaufnahme ohne echte Cloud-Aufrufe.
"""Synthetic encrypted fixtures; no Azure, Docker or existing notes are used."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import lifecycle


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root_patch = patch.object(lifecycle, "ROOT", self.root)
        self.root_patch.start();self.addCleanup(self.root_patch.stop)
        for directory in ("artifacts/backups", "artifacts/recovery", ".secrets/backups", ".state"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        self.key = AESGCM.generate_key(bit_length=256)
        (self.root / ".secrets/backups/test.key").write_bytes(self.key)
        rows = [{"id": "synthetic", "data": {"work": "test"}}]
        digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        nonce = b"123456789012"
        data = b"LSBACKUP1" + nonce + AESGCM(self.key).encrypt(nonce, json.dumps(rows).encode(), b"learningsteps-entries-v1")
        (self.root / "artifacts/backups/test.enc").write_bytes(data)
        info = {"isolated_restore_verified": True, "count": 1, "data_sha256": digest,
                "encrypted_file": "artifacts/backups/test.enc", "key_file": ".secrets/backups/test.key",
                "encrypted_sha256": hashlib.sha256(data).hexdigest()}
        self.manifest = self.root / "artifacts/backups/test.json"
        self.manifest.write_text(json.dumps(info))
        cert = {"letsencrypt": {"Certificates": [{"domain": {"main": lifecycle.recovery.HOST}}]}}
        cert_nonce = b"abcdefghijkl"
        encrypted = b"LSACME01" + cert_nonce + AESGCM(self.key).encrypt(cert_nonce, json.dumps(cert).encode(), b"learningsteps-acme-v1")
        (self.root / "artifacts/recovery/cert.enc").write_bytes(encrypted)
        (self.root / "artifacts/recovery/api.tar").write_bytes(b"synthetic image archive")
        self.release = {"data_backup": "artifacts/backups/test.json", "data_sha256": digest,
                        "images": {"api": {"archive": "artifacts/recovery/api.tar", "archive_sha256": lifecycle.recovery.sha(self.root / "artifacts/recovery/api.tar")}},
                        "certificates": {"file": "artifacts/recovery/cert.enc", "sha256": hashlib.sha256(encrypted).hexdigest()}}

    def test_complete_bundle_decrypts_and_verifies(self):
        info, key = lifecycle.validate_release(self.release)
        self.assertEqual(info["count"], 1);self.assertEqual(key, self.key)

    def test_modified_ciphertext_is_rejected(self):
        path = self.root / "artifacts/backups/test.enc"
        path.write_bytes(path.read_bytes() + b"modified")
        with self.assertRaisesRegex(RuntimeError, "integrity"):
            lifecycle.validate_release(self.release)

    def test_wrong_private_key_is_rejected(self):
        (self.root / ".secrets/backups/test.key").write_bytes(AESGCM.generate_key(bit_length=256))
        with self.assertRaises(InvalidTag):lifecycle.validate_release(self.release)

    def test_manifest_count_must_match_encrypted_records(self):
        info = json.loads(self.manifest.read_text());info["count"] = 99
        self.manifest.write_text(json.dumps(info))
        with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
            lifecycle.validate_release(self.release)

    def test_backup_path_cannot_escape_project_backup_directory(self):
        info = json.loads(self.manifest.read_text());info["encrypted_file"] = "../outside.enc"
        self.manifest.write_text(json.dumps(info))
        with self.assertRaisesRegex(RuntimeError, "paths outside"):
            lifecycle.validate_release(self.release)

    def test_missing_actual_restore_proof_is_rejected(self):
        info = json.loads(self.manifest.read_text());info["isolated_restore_verified"] = False
        self.manifest.write_text(json.dumps(info))
        with self.assertRaisesRegex(RuntimeError, "isolated restore"):
            lifecycle.validate_release(self.release)

    def test_changed_image_is_rejected(self):
        (self.root / "artifacts/recovery/api.tar").write_bytes(b"different image")
        with self.assertRaisesRegex(RuntimeError, "Image archive"):
            lifecycle.validate_release(self.release)

    def test_group_scope_is_exact_and_never_calls_azure_for_foreign_group(self):
        with patch.object(lifecycle, "az") as azure:
            with self.assertRaisesRegex(RuntimeError, "outside project"):
                lifecycle.group_exists("rg-learningsteps-evolution-foreign")
            azure.assert_not_called()

    def test_inventory_preserves_unrelated_resources_and_detects_project_tags(self):
        rows = [{"resourceGroup": "other", "name": "unrelated", "tags": {}},
                {"resourceGroup": "rg-learningsteps-evolution-foreign", "name": "lookalike"},
                {"resourceGroup": "other", "name": "tagged", "tags": {"project": "LearningSteps"}}]
        self.assertEqual([r["name"] for r in lifecycle.project_inventory(rows)], ["tagged"])

    def test_completed_down_step_is_not_repeated(self):
        with patch.object(lifecycle, "save") as save:
            def forbidden():raise AssertionError("completed step repeated")
            lifecycle.step({"down_step": 3}, 2, "already complete", forbidden)
            save.assert_not_called()

    def test_incomplete_restore_is_not_silently_reset_by_down(self):
        context = {"phase": "up", "up_step": 2, "cycle": "preserve-me"}
        with patch.object(lifecycle, "command") as external:
            with self.assertRaisesRegex(RuntimeError, "Restore is incomplete"):
                lifecycle.down(context)
            external.assert_not_called()
        self.assertEqual(context["up_step"], 2)

    def test_backend_does_not_overwrite_foreign_group(self):
        with patch.object(lifecycle, "group_exists", return_value=True), \
                patch.object(lifecycle, "az", return_value={"tags": {"project": "Other"}}), \
                patch.object(lifecycle, "command") as external:
            with self.assertRaisesRegex(RuntimeError, "not owned"):
                lifecycle.backend()
            external.assert_not_called()

    def test_state_snapshot_is_encrypted_and_roundtrips(self):
        path = self.root / ".state/release.json";path.write_text(json.dumps(self.release))
        state = {"resources": [{"instances": [{"attributes": {"value": "synthetic-sensitive-only"}}]}]}
        context = {"cycle": "synthetic-cycle"}
        with patch.object(lifecycle.recovery, "RELEASE", path), patch.object(lifecycle, "save"), \
                patch.object(lifecycle, "tf", return_value=json.dumps(state)):
            lifecycle.encrypted_state(context, "state-before-destroy")
        blob = (self.root / context["state-before-destroy"]["file"]).read_bytes()
        self.assertNotIn(b"synthetic-sensitive-only", blob)
        self.assertEqual(json.loads(AESGCM(self.key).decrypt(blob[8:20], blob[20:], b"learningsteps-state-v1")), state)

    def test_old_bootstrap_flags_reset_once_per_new_up_cycle(self):
        path = self.root / ".state/release.json"
        self.release.update(database_restored=True, bootstrap_verified_at="old", restored_images={})
        path.write_text(json.dumps(self.release))
        context = {"phase": "down"}
        with patch.object(lifecycle.recovery, "RELEASE", path), \
                patch.object(lifecycle, "save"), patch.object(lifecycle, "command", return_value=""), \
                patch.object(lifecycle, "cloud_delivery"), \
                patch.object(lifecycle, "backend", side_effect=RuntimeError("controlled backend failure")):
            with self.assertRaisesRegex(RuntimeError, "controlled"):
                lifecycle.up(context)
            first = json.loads(path.read_text());self.assertNotIn("database_restored", first)
            first["database_restored"] = True;path.write_text(json.dumps(first))
            with self.assertRaisesRegex(RuntimeError, "controlled"):
                lifecycle.up(context)
            self.assertTrue(json.loads(path.read_text())["database_restored"])


if __name__ == "__main__":unittest.main()
