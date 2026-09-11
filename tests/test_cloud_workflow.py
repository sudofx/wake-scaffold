"""A failed inference is publishable; a failed state checkpoint is not."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import github_wake
from wake.audit import verify_history
from wake.engine import DEFAULTS
from wake.governance import Rejected
from wake.providers import Fixture, Gemini


class CloudWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project, self.remote = self.root/"project", self.root/"remote.git"
        self.git("init", self.project)
        self.git("init", "--bare", self.remote)
        (self.project/"README.md").write_text("Source files must never be the Pages artifact.")
        self.git("-C", self.project, "add", "README.md")
        self.git("-C", self.project, "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-m", "Source")
        self.git("-C", self.project, "remote", "add", "origin", self.remote)

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *map(str,args)], check=True, capture_output=True, text=True)

    def run_cloud(self, provider, publish_only=False, scheduled=False):
        with patch.object(github_wake, "ROOT", self.project), \
             patch.object(github_wake, "config", return_value=dict(DEFAULTS)), \
             patch.object(github_wake, "Gemini", return_value=provider), \
             patch.object(github_wake, "collect", lambda engine: None), \
             patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}):
            return github_wake.main(publish_only=publish_only, scheduled=scheduled)

    def test_failure_is_counted_once_exported_pushed_and_followed_by_recovery(self):
        class Failure(Fixture):
            charged = True
            calls = 0
            def propose(self, request):
                self.calls += 1
                raise Rejected("Gemini HTTP 503; attempt counted, no automatic retry")
        provider = Failure()
        self.assertEqual(self.run_cloud(provider), 2)
        self.assertEqual(provider.calls, 1)
        public = json.loads(self.git("--git-dir", self.remote, "show", "wake-state:site/state.json").stdout)
        self.assertEqual(len(public["invocations"]), 1)
        self.assertTrue(next(iter(public["invocations"].values()))["charged"])
        operation = json.loads(self.git("--git-dir", self.remote, "show", "wake-state:site/operation.json").stdout)
        self.assertEqual(operation["status"], "failed")
        self.assertIn("503", operation["reason"])
        self.assertTrue((self.project/"site/index.html").is_file())
        verify_history(self.project/"site/events.jsonl", (self.project/"site/head.txt").read_text())
        self.assertEqual(self.run_cloud(Fixture()), 0)
        public = json.loads(self.git("--git-dir", self.remote, "show", "wake-state:state.json").stdout)
        self.assertEqual(public["version"], 1)
        self.assertEqual([i["status"] for i in public["invocations"].values()], ["failed", "accepted"])

    def test_republishing_preserves_the_accepted_wake_without_calling_gemini(self):
        self.assertEqual(self.run_cloud(Fixture()), 0)
        before = json.loads((self.project/"site/state.json").read_text())
        with patch.object(github_wake, "Gemini", side_effect=AssertionError("No model initialization")), \
             patch.object(github_wake, "ROOT", self.project), \
             patch.object(github_wake, "config", return_value=dict(DEFAULTS)), \
             patch.object(github_wake, "collect", side_effect=AssertionError("No collection")), \
             patch.dict("os.environ", {"GITHUB_ACTIONS":"true"}):
            self.assertEqual(github_wake.main(publish_only=True), 0)
        after = json.loads((self.project/"site/state.json").read_text())
        self.assertEqual(before, after)
        result = json.loads((self.project/"site/operation.json").read_text())
        self.assertEqual(result["status"], "accepted")
        self.assertTrue(result["publication_only"])

    def test_backup_schedule_skips_a_recent_wake_without_calling_provider(self):
        class ChargedFixture(Fixture):
            charged = True
        self.assertEqual(self.run_cloud(ChargedFixture()), 0)
        class NeverCall(Fixture):
            charged = True
            def propose(self, request): raise AssertionError("Recent scheduled wake must suppress the model call")
        provider = NeverCall()
        self.assertEqual(self.run_cloud(provider, scheduled=True), 0)
        public = json.loads(self.git("--git-dir", self.remote, "show", "wake-state:state.json").stdout)
        self.assertEqual(len(public["invocations"]), 1)

    def test_scheduled_due_uses_the_durable_charged_invocation_time(self):
        old = (datetime.now(timezone.utc) - timedelta(minutes=56)).isoformat()
        state = {"invocations": {"wake": {"charged": True, "time": old}}}
        due, _ = github_wake.scheduled_wake_due(state)
        self.assertTrue(due)
        state["invocations"]["wake"]["time"] = datetime.now(timezone.utc).isoformat()
        due, next_eligible = github_wake.scheduled_wake_due(state)
        self.assertFalse(due)
        self.assertGreater(next_eligible, datetime.now(timezone.utc))

    def test_failed_checkpoint_never_exports_or_calls_provider(self):
        class NeverCall(Fixture):
            def propose(self, request): raise AssertionError("Provider must not be called")
        with patch.object(github_wake.StateBranch, "checkpoint", side_effect=OSError("Push failed")):
            with self.assertRaises(OSError): self.run_cloud(NeverCall())
        self.assertFalse((self.project/"site/index.html").exists())

    def test_workflow_publishes_generated_reports_even_after_provider_failure(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root/".github/workflows/wake.yml").read_text()
        report = workflow.split("- name: Confirm report is ready", 1)[1].split("- name:", 1)[0]
        self.assertIn("steps.cycle.outputs.skipped != 'true'", report)
        self.assertNotIn("steps.cycle.outcome", report)
        self.assertIn("test -f site/index.html", report)
        self.assertIn("needs.wake.outputs.report_ready == 'true'", workflow)
        self.assertIn("if: always() && steps.cycle.outcome == 'failure'", workflow)
        self.assertIn("path: site", workflow)
        self.assertIn("github-pages-${{ github.run_id }}-${{ github.run_attempt }}", workflow)
        self.assertIn("cron: '12,27,42,57 * * * *'", workflow)
        self.assertIn("python scripts/github_wake.py --scheduled", workflow)
        self.assertIn("artifact_name: ${{ needs.wake.outputs.artifact_name }}", workflow)
        self.assertFalse((root/".github/workflows/static.yml").exists())
        self.assertFalse((root/".github/workflows/jekyll-gh-pages.yml").exists())

    def test_provider_schema_prevents_the_observed_mixed_project_shape(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, maximum):
                return json.dumps({"candidates":[{"finishReason":"STOP", "content":{"parts":[{"text":"{}"}]}}]}).encode()
        with patch.dict("os.environ", {"GEMINI_API_KEY":"test-key"}), patch("urllib.request.urlopen", return_value=Response()) as network:
            Gemini({**DEFAULTS, "free_tier_confirmed":True}).propose({"system":"rules", "context":{}})
        body = json.loads(network.call_args.args[0].data)
        self.assertNotIn("responseJsonSchema", body["generationConfig"])
        schema = json.loads(body["systemInstruction"]["parts"][0]["text"].split("Response contract (JSON Schema):\n")[1])
        variants = {s["properties"]["type"]["enum"][0]:s for s in schema["properties"]["actions"]["items"]["anyOf"]}
        project = variants["project"]
        self.assertEqual(set(project["properties"]), set("type id title question domain status next_step reason".split()))
        self.assertIn("status", project["required"])
        self.assertFalse(project["additionalProperties"])
        self.assertIn("domain", variants["research"]["required"])
        self.assertNotIn("findings", variants["research"]["properties"])


if __name__ == "__main__": unittest.main()
