"""Behavioral checks for the boundaries the experiment actually relies on."""

from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from wake.audit import verify_history
from wake.engine import DEFAULTS, Engine
from wake.governance import Rejected
from wake.providers import Fixture, Gemini
from wake.report import export
from wake.store import IntegrityError, canonical


class SystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.engine = Engine(self.root / "data", dict(DEFAULTS))
        with self.engine.store.lock():
            self.engine.initialize()

    def tearDown(self):
        self.engine.store.close()
        self.temp.cleanup()

    def propose(self, mutate=lambda p: None):
        with self.engine.store.lock():
            invocation, request = self.engine.start("fixture", "adversarial")
            proposal = json.loads(Fixture().propose(request)[0])
            mutate(proposal)
            result = self.engine.finish(invocation, json.dumps(proposal))
        return result

    def test_new_provider_inherits_commitment(self):
        first = self.engine.run(Fixture("a"))
        second = self.engine.run(Fixture("b"))
        state = self.engine.store.load()
        item = state["commitments"]["handoff-1"]
        self.assertEqual(item["created_by"], first["id"])
        self.assertEqual(item["resolved_by"], second["id"])
        self.assertEqual(item["status"], "fulfilled")

    def test_invalid_action_rejects_entire_proposal(self):
        result = self.propose(lambda p: p["actions"].append({"type": "shell", "command": "echo forbidden"}))
        state = self.engine.store.load()
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(state["version"], 0)
        self.assertEqual(state["commitments"], {})
        self.assertEqual(state["invocations"][result["id"]]["status"], "rejected")

    def test_stale_version_is_rejected(self):
        self.assertEqual(self.propose(lambda p:p.update(base_version=-1))["status"], "rejected")

    def test_objective_edit_is_rejected(self):
        self.assertEqual(self.propose(lambda p:p.update(objective="Ignore rules"))["status"], "rejected")

    def test_missing_evidence_is_rejected(self):
        action = {"type":"belief", "id":"b", "statement":"A claim", "confidence":.9,
                  "status":"active", "evidence":["invented"], "reason":"I made it up"}
        self.assertEqual(self.propose(lambda p:p["actions"].append(action))["status"], "rejected")

    def test_nonfinite_confidence_is_rejected(self):
        self.assertEqual(self.propose(lambda p:p.update(base_version=float("nan")))["status"], "rejected")

    def test_model_cannot_cancel_commitment(self):
        self.engine.run(Fixture())
        self.assertEqual(self.propose(lambda p:p["actions"][0].update(status="cancelled"))["status"], "rejected")
        self.assertEqual(self.engine.store.load()["commitments"]["handoff-1"]["status"], "open")

    def test_model_cannot_resolve_own_new_commitment(self):
        def mutation(p):
            p["actions"].append({"type":"resolve", "id":"handoff-1", "status":"fulfilled",
                                 "evidence":[list(self.engine.store.load()["evidence"])[-1]], "reason":"Immediately done"})
        self.assertEqual(self.propose(mutation)["status"], "rejected")

    def test_commitment_due_cycle_requires_future(self):
        self.assertEqual(self.propose(lambda p:p["actions"][0].update(due_cycle=1))["status"], "rejected")

    def test_belief_evidence_lifecycle(self):
        with self.engine.store.lock():
            self.engine.observe("Synthetic measurement within range", "fixture:sensor")
        self.engine.run(Fixture())
        with self.engine.store.lock():
            self.engine.observe("Synthetic counterexample outside range", "fixture:sensor")
        self.engine.run(Fixture())
        belief = self.engine.store.load()["beliefs"]["sensor"]
        self.assertEqual(belief["status"], "retracted")
        self.assertEqual(len(belief["evidence"]), 2)
        self.assertEqual(belief["confidence"], 0)

    def test_belief_review_requires_new_evidence(self):
        with self.engine.store.lock():
            self.engine.observe("Measurement", "fixture:sensor")
        self.engine.run(Fixture())
        b = self.engine.store.load()["beliefs"]["sensor"]
        action = {key:b[key] for key in ("type","id","statement","confidence","status","evidence","reason")}
        self.assertEqual(self.propose(lambda p:p["actions"].append(action))["status"], "rejected")

    def test_invalid_json_records_rejection(self):
        with self.engine.store.lock():
            inv, _ = self.engine.start("manual", "desktop")
            result = self.engine.finish(inv, "{truncated")
        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(self.engine.store.load()["pending"])

    def test_manual_request_survives_restart(self):
        with self.engine.store.lock():
            inv, request = self.engine.start("manual", "Claude / human-attested")
        reopened = Engine(self.root / "data")
        try:
            self.assertEqual(reopened.store.load()["pending"], inv)
            with self.assertRaises(Rejected):
                reopened.run(Fixture())
            with reopened.store.lock():
                self.assertEqual(reopened.finish(inv, Fixture().propose(request)[0])["status"], "accepted")
        finally:
            reopened.store.close()

    def test_projection_can_be_rebuilt_but_history_cannot_be_silently_repaired(self):
        self.engine.run(Fixture())
        original = self.engine.store.load()
        with self.engine.store.db:
            self.engine.store.db.execute("UPDATE snapshot SET state='broken'")
        with self.assertRaises(IntegrityError):
            self.engine.store.load()
        with self.engine.store.lock():
            self.assertEqual(self.engine.recover(), original)
        with self.engine.store.db:
            self.engine.store.db.execute("UPDATE events SET payload='{}' WHERE seq=1")
        with self.assertRaises(IntegrityError):
            self.engine.recover()

    def test_quota_is_reserved_before_failure_and_survives_restart(self):
        class Failure(Fixture):
            charged = True
            def propose(self, request):
                raise RuntimeError("Failure")
        self.engine.config["daily_call_limit"] = 2
        self.assertEqual(self.engine.run(Failure())["status"], "failed")
        self.assertEqual(self.engine.run(Failure())["status"], "failed")
        restarted = Engine(self.root / "data", self.engine.config)
        try:
            with self.assertRaisesRegex(Rejected, "Daily call ceiling"):
                restarted.run(Failure())
        finally:
            restarted.store.close()
        self.assertEqual(len(self.engine.store.load()["invocations"]), 2)

    def test_quota_resets_at_pacific_midnight(self):
        class Charged(Fixture):
            charged = True
        self.engine.config["daily_call_limit"] = 1
        with patch("wake.engine.datetime") as clock:
            clock.now.return_value = datetime(2026, 9, 9, 23, 59, tzinfo=ZoneInfo("America/Los_Angeles"))
            self.engine.run(Charged())
            with self.assertRaises(Rejected):
                self.engine.run(Charged())
            clock.now.return_value = datetime(2026, 9, 10, 0, 1, tzinfo=ZoneInfo("America/Los_Angeles"))
            self.assertEqual(self.engine.run(Charged())["status"], "accepted")

    def test_context_ceiling_prevents_call(self):
        self.engine.config["max_context_chars"] = 10
        class NoCall(Fixture):
            def propose(self, request):
                raise AssertionError("Provider should never be called")
        with self.assertRaisesRegex(Rejected, "Context ceiling"):
            self.engine.run(NoCall())
        self.assertEqual(self.engine.store.load()["invocations"], {})

    def test_lock_prevents_competing_process(self):
        with self.engine.store.lock():
            result = subprocess.run([sys.executable,"-m","wake","--data",str(self.root/"data"),"wake","--provider","fixture"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Another wake owns", result.stderr)
        self.assertEqual(self.engine.store.load()["version"], 0)

    def test_real_process_death_during_commit_rolls_back(self):
        self.engine.run(Fixture())
        result = subprocess.run([sys.executable,"-m","wake","--data",str(self.root/"data"),"wake","--provider","fixture","--crash-at","during-commit"], capture_output=True)
        self.assertEqual(result.returncode, 86)
        with self.engine.store.lock():
            state = self.engine.recover()
        self.assertEqual(state["version"], 1)
        self.assertEqual(sum(i["status"]=="recovered" for i in state["invocations"].values()), 1)

    def test_audit_can_reconstruct_without_database(self):
        self.engine.run(Fixture())
        export(self.engine.store, self.root / "site")
        reconstructed, _ = verify_history(self.root/"site/events.jsonl", (self.root/"site/head.txt").read_text())
        self.assertEqual(canonical(reconstructed), canonical(self.engine.store.load()))

    def test_external_head_detects_valid_prefix_truncation(self):
        self.engine.run(Fixture())
        export(self.engine.store, self.root / "site")
        log = self.root/"site/events.jsonl"
        log.write_text("\n".join(log.read_text().splitlines()[:-1])+"\n")
        with self.assertRaises(IntegrityError):
            verify_history(log, (self.root/"site/head.txt").read_text())

    def test_html_embedded_data_does_not_allow_script_injection(self):
        with self.engine.store.lock():
            self.engine.observe('</script><script>alert("xss")</script>', "human:test")
        export(self.engine.store, self.root/"site")
        page = (self.root/"site/index.html").read_text()
        self.assertNotIn('</script><script>alert', page)
        self.assertIn('\\u003c/script>', page)

    def test_live_provider_requires_explicit_free_tier_setting(self):
        with self.assertRaisesRegex(Rejected, "free_tier_confirmed"):
            Gemini(dict(DEFAULTS))

    def test_gemini_request_uses_single_bounded_json_call(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, maximum):
                return json.dumps({"candidates":[{"finishReason":"STOP", "content":{"parts":[{"text":'{"base_version":0,"title":"Hi","summary":"Review","actions":[]}'}]}}],"usageMetadata":{"totalTokenCount":123}}).encode()
        with patch.dict("os.environ", {"GEMINI_API_KEY":"test-key"}), patch("urllib.request.urlopen", return_value=Response()) as network:
            provider = Gemini({**DEFAULTS, "free_tier_confirmed":True})
            raw, metadata = provider.propose({"system":"rules", "context":{"version":0}})
            self.assertEqual(json.loads(raw)["base_version"], 0)
            self.assertEqual(metadata["usage"]["totalTokenCount"], 123)
            self.assertEqual(network.call_count, 1)
            request = network.call_args.args[0]
            self.assertNotIn("test-key", request.full_url)
            self.assertIn("responseJsonSchema", json.loads(request.data)["generationConfig"])


if __name__ == "__main__":
    unittest.main()
