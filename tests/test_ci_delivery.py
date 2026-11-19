"""Delivery security boundary and ARM-vs-command success checks, no cloud calls."""

import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ci_deploy


class DeliveryTests(unittest.TestCase):
    def context(self, directory):
        return {
            "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push",
            "GITHUB_REPOSITORY": "CyberAlex91/learningsteps",
            "GITHUB_REF": "refs/heads/feature/user-notes-summary",
            "GITHUB_SHA": "a" * 40, "IMAGE_REF": ci_deploy.PREFIX + "b" * 64,
            "RUNNER_TEMP": directory,
        }

    def test_untrusted_contexts_never_invoke_azure(self):
        for key, invalid in (("GITHUB_EVENT_NAME", "pull_request"),
                             ("GITHUB_REPOSITORY", "other/learningsteps"),
                             ("GITHUB_REF", "refs/heads/untrusted"),
                             ("GITHUB_ACTIONS", "false")):
            context = self.context("/unused")
            context[key] = invalid
            with patch.dict(os.environ, context, clear=True), patch("ci_deploy.subprocess.run") as run:
                with self.assertRaises(SystemExit):
                    ci_deploy.main()
                run.assert_not_called()

    def test_mutable_tag_is_rejected_before_azure(self):
        context = self.context("/unused")
        context["IMAGE_REF"] = "acrlearningstepsalex0ad5f630.azurecr.io/learningsteps-api:latest"
        with patch.dict(os.environ, context, clear=True), patch("ci_deploy.subprocess.run") as run:
            with self.assertRaises(SystemExit):
                ci_deploy.main()
            run.assert_not_called()

    def test_azure_api_success_with_failed_remote_command_is_failure(self):
        context = self.context("/unused")
        response = SimpleNamespace(returncode=0, stdout=json.dumps({"exitCode": 17}), stderr="")
        with patch.dict(os.environ, context, clear=True), patch("ci_deploy.subprocess.run", return_value=response):
            with self.assertRaisesRegex(SystemExit, "rollout command failed"):
                ci_deploy.main()

    def test_success_without_digest_confirmation_is_failure(self):
        response = SimpleNamespace(returncode=0, stdout=json.dumps({"exitCode": 0, "logs": "done"}), stderr="")
        with patch.dict(os.environ, self.context("/unused"), clear=True), patch("ci_deploy.subprocess.run", return_value=response):
            with self.assertRaisesRegex(SystemExit, "not confirmed"):
                ci_deploy.main()

    def test_verified_rollout_saves_only_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self.context(directory)
            response = SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({
                "exitCode": 0, "logs": context["IMAGE_REF"],
            }))
            with patch.dict(os.environ, context, clear=True), patch("ci_deploy.subprocess.run", return_value=response):
                ci_deploy.main()
            evidence = json.loads((Path(directory) / "deployment-evidence.json").read_text())
            self.assertTrue(evidence["rollout_succeeded"])
            self.assertEqual(evidence["image"], context["IMAGE_REF"])
            self.assertFalse(evidence["database_notes_modified"])


if __name__ == "__main__":
    unittest.main()
