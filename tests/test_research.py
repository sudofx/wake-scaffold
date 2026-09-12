"""Exercise scientific provenance, bounded autonomy and durable cloud handoffs offline."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.github_wake import StateBranch
from wake.audit import verify_history
from wake.engine import DEFAULTS, Engine
from wake.governance import Rejected
from wake.providers import Fixture
from wake.research import allowed_url, collect
from wake.report import export


def project(identifier="p", status="active"):
    return dict(type="project", id=identifier, title="Comparing explanations", question="What distinguishes the explanations?",
                domain="philosophy", status=status, next_step="Compare collected sources", reason="A tractable question")


def notebook(evidence, findings="A bounded comparison [s1] [s2]."):
    return dict(type="notebook", id="n", project="p", title="A comparison", summary="A provisional distinction",
                findings=findings, limitations="Synthetic test sources, not scientific results.",
                next_questions="Obtain stronger evidence", evidence=evidence, reason="Make the distinction explicit")


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.engine = Engine(self.root/"data", {**DEFAULTS, "mission":"Explore big ideas through small useful projects."})
        with self.engine.store.lock():
            self.engine.initialize()

    def tearDown(self):
        self.engine.store.close()
        self.temp.cleanup()

    def propose(self, actions):
        with self.engine.store.lock():
            invocation, request = self.engine.start("fixture", "research-test")
            return self.engine.finish(invocation, json.dumps(dict(base_version=request["context"]["version"],
                title="Research fixture", summary="Offline boundary test", actions=actions)))

    def source(self, identifier, url=None, status="collected", source_scope="synthetic test fixture"):
        with self.engine.store.lock():
            self.engine.store.append("observation", dict(id=identifier, source=url or "https://plato.stanford.edu/entries/"+identifier,
                content=json.dumps({"scope":source_scope, "excerpt":"Only a fixture"}), actor="collector", scope=status))

    def test_existing_pet_name_is_migrated_through_an_audited_event(self):
        legacy = Engine(self.root/"legacy", {**DEFAULTS, "mission":"Explore big ideas.", "pet_name":"Wake"})
        try:
            with legacy.store.lock():
                legacy.initialize()
            legacy.config["pet_name"] = "WAKE✳"
            with legacy.store.lock():
                state = legacy.initialize()
            self.assertEqual(state["pet_name"], "WAKE✳")
            event = legacy.store.events()[-1]
            self.assertEqual(event["kind"], "pet_renamed")
            self.assertEqual(event["payload"], {"pet_name": "WAKE✳", "actor": "operator"})
            reconstructed, _ = legacy.store.replay()
            self.assertEqual(reconstructed, state)
        finally:
            legacy.store.close()

    def test_new_projects_are_bounded_and_rejection_is_atomic(self):
        result = self.propose([project(str(i)) for i in range(4)])
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.engine.store.load()["projects"], {})
        self.assertEqual(self.propose([project(str(i)) for i in range(3)])["status"], "accepted")

    def test_completion_requires_a_notebook(self):
        self.propose([project()])
        self.assertEqual(self.propose([project(status="completed")])["status"], "rejected")

    def test_notebooks_reject_receipts_and_failed_sources(self):
        self.propose([project()])
        self.source("s1")
        self.source("s2", status="failed")
        self.assertEqual(self.propose([notebook(["s1", "s2"])])["status"], "rejected")
        receipt = next(e["id"] for e in self.engine.store.load()["evidence"].values() if e["actor"] == "runtime")
        self.assertEqual(self.propose([notebook(["s1", receipt])])["status"], "rejected")

    def test_two_fetches_of_same_url_are_not_two_sources(self):
        self.propose([project()])
        self.source("s1", "https://plato.stanford.edu/entries/consciousness/")
        self.source("s2", "https://plato.stanford.edu/entries/consciousness/")
        self.assertEqual(self.propose([notebook(["s1", "s2"])])["status"], "rejected")

    def test_revision_requires_changed_findings_and_new_evidence(self):
        self.source("s1")
        self.source("s2")
        self.assertEqual(self.propose([project(), notebook(["s1", "s2"])])["status"], "accepted")
        self.assertEqual(self.propose([notebook(["s1", "s2"], "Changed")])["status"], "rejected")
        self.source("s3")
        self.assertEqual(self.propose([notebook(["s1", "s3"], "Changed with evidence [s3]."), project(status="completed")])["status"], "accepted")
        export(self.engine.store, self.root/"site")
        reconstructed, _ = verify_history(self.root/"site/events.jsonl", (self.root/"site/head.txt").read_text())
        self.assertEqual(reconstructed, self.engine.store.load())
        self.assertEqual(reconstructed["notebooks"]["n"]["revision"], 2)
        self.assertIn("Changed with evidence", (self.root/"site/notebooks/n.md").read_text())

    def test_sources_and_notebook_text_cannot_inject_scripts(self):
        self.source("s1")
        self.source("s2")
        self.propose([project(), notebook(["s1", "s2"], '</script><script>alert("no")</script>')])
        export(self.engine.store, self.root/"site")
        self.assertNotIn('</script><script>alert', (self.root/"site/index.html").read_text())

    def blog(self, evidence=("s1", "s2"), **changes):
        action = dict(type="blog", id="post-one", project="p", title="The useful disagreement",
            lede="Two sources describe the same problem from different angles.",
            body=("The notebook exposed a useful disagreement between the collected accounts. "
                  "Neither source settles the question alone, and the limitation matters. "
                  "The interesting result is the shape of the disagreement: each account measures "
                  "a different part of the problem, so treating them as direct rivals would hide "
                  "what each can actually support. The next investigation should test that gap."),
            notebooks=["n"], evidence=list(evidence),
            reason="A new source-backed notebook exposed a substantive disagreement worth explaining.",
            lens="Good observation leaves room for the observed to change the map.")
        action.update(changes)
        return action

    def test_boring_wake_produces_no_blog_post(self):
        self.assertEqual(self.propose([project()])["status"], "accepted")
        self.assertEqual(self.engine.store.load()["posts"], {})

    def test_significant_notebook_can_create_a_durable_blog_post(self):
        self.source("s1")
        self.source("s2")
        result = self.propose([project(), notebook(["s1", "s2"]), self.blog()])
        self.assertEqual(result["status"], "accepted")
        state = self.engine.store.load()
        self.assertEqual(state["posts"]["post-one"]["created_by"], result["id"])
        reconstructed, _ = self.engine.store.replay()
        self.assertEqual(reconstructed["posts"], state["posts"])
        export(self.engine.store, self.root/"site")
        markdown = (self.root/"site/blog/post-one.md").read_text()
        html = (self.root/"site/index.html").read_text()
        self.assertIn("Bob's Lens — philosophical reflection", markdown)
        self.assertIn("Exact wake and decision", markdown)
        self.assertIn("The useful disagreement", html)

    def test_unsupported_blog_claims_are_rejected_atomically(self):
        self.source("s1")
        self.source("s2")
        bad = self.blog(["s1", "missing"])
        result = self.propose([project(), notebook(["s1", "s2"]), bad])
        self.assertEqual(result["status"], "rejected")
        state = self.engine.store.load()
        self.assertEqual(state["projects"], {})
        self.assertEqual(state["notebooks"], {})
        self.assertEqual(state["posts"], {})

    def test_blog_requires_significant_work_in_the_same_wake(self):
        self.source("s1")
        self.source("s2")
        self.propose([project(), notebook(["s1", "s2"])])
        self.assertEqual(self.propose([self.blog()])["status"], "rejected")
        self.assertEqual(self.engine.store.load()["posts"], {})

    def test_blog_context_survives_fresh_invocation_without_full_bodies(self):
        self.source("s1")
        self.source("s2")
        self.propose([project(), notebook(["s1", "s2"]), self.blog()])
        with self.engine.store.lock():
            invocation, request = self.engine.start("fixture", "fresh")
            context = request["context"]["recent_blog"]
            self.assertEqual(context[0]["id"], "post-one")
            self.assertNotIn("body", context[0])
            self.engine.store.append("failed", {"id": invocation, "reason": "test cleanup"})

    def test_blog_does_not_add_a_provider_call(self):
        self.source("s1")
        self.source("s2")
        outer = self
        class OneCall(Fixture):
            calls = 0
            def propose(self, request):
                self.calls += 1
                proposal = dict(base_version=request["context"]["version"], title="Research fixture",
                    summary="One model response contains research and optional editorial work.",
                    actions=[project(), notebook(["s1", "s2"]), outer.blog()])
                return json.dumps(proposal), {"simulated": True}
        provider = OneCall()
        self.assertEqual(self.engine.run(provider)["status"], "accepted")
        self.assertEqual(provider.calls, 1)
        self.assertIn("post-one", self.engine.store.load()["posts"])

    def test_quantum_metaphor_cannot_masquerade_as_scientific_causation(self):
        self.source("s1")
        self.source("s2")
        bad = self.blog(body=("Quantum mechanics proves empathy and explains relationships. " * 20))
        self.assertEqual(self.propose([project(), notebook(["s1", "s2"]), bad])["status"], "rejected")
        self.assertEqual(self.engine.store.load()["posts"], {})

    def test_honest_quantum_boundary_is_allowed(self):
        self.source("s1")
        self.source("s2")
        safe = self.blog(body=("Quantum mechanics does not explain consciousness. "
                               "The useful connection here is a philosophical prompt about observation, "
                               "uncertainty, and the limits of intuition. The research notebook keeps "
                               "measurement separate from interpretation and links every claim to its "
                               "source. That boundary is part of the result, not a footnote. " * 2))
        self.assertEqual(self.propose([project(), notebook(["s1", "s2"]), safe])["status"], "accepted")

    def test_abstract_only_sources_cannot_support_inflated_certainty(self):
        self.source("s1", source_scope="abstract only")
        self.source("s2", source_scope="preprint abstract")
        inflated = self.blog(body=("The sources provide definitive and conclusive proof. " * 10))
        self.assertEqual(self.propose([project(), notebook(["s1", "s2"]), inflated])["status"], "rejected")
        self.assertEqual(self.engine.store.load()["posts"], {})

    def test_correction_preserves_the_original_post(self):
        self.source("s1")
        self.source("s2")
        self.assertEqual(self.propose([project(), notebook(["s1", "s2"]), self.blog()])["status"], "accepted")
        self.source("s3")
        correction = self.blog(id="post-two", evidence=["s1", "s3"], supersedes="post-one",
            title="A correction to the useful disagreement",
            body=("A newly collected source changes how the earlier disagreement should be described. "
                  "The original post remains in the record, but this note replaces its conclusion. "
                  "The evidence now supports a narrower comparison and leaves the broader claim open. "
                  "That is a meaningful change rather than a cosmetic rewrite, and the linked notebook "
                  "records the new source, revised finding, limitation, and next question."))
        revised = notebook(["s1", "s3"], "A narrower comparison follows the new evidence [s1] [s3].")
        self.assertEqual(self.propose([revised, correction])["status"], "accepted")
        posts = self.engine.store.load()["posts"]
        self.assertEqual(posts["post-one"]["status"], "superseded")
        self.assertEqual(posts["post-one"]["superseded_by"], "post-two")
        self.assertEqual(posts["post-two"]["supersedes"], "post-one")

    def test_collector_attempts_two_requests_and_records_failures(self):
        actions = [project()]+[dict(type="research", id=f"q{i}", project="p", query="consciousness", domain="philosophy", reason="Compare") for i in range(4)]
        self.propose(actions)
        calls=[]
        def fetch(url):
            calls.append(url)
            if len(calls)==1: raise OSError("Unavailable")
            return dict(url=url, scope="synthetic test fixture", excerpt="Test source")
        with self.engine.store.lock(): collect(self.engine, fetcher=fetch)
        state=self.engine.store.load()
        self.assertEqual(len(calls), 2)
        self.assertEqual([r["status"] for r in state["research"].values()], ["failed","collected","queued","queued"])

    def test_source_url_allowlist_and_input_types(self):
        for url in ("http://arxiv.org/", "https://127.0.0.1/", "https://arxiv.org.evil.example/", "https://a@arxiv.org/", "https://arxiv.org:444/", {}, None):
            with self.subTest(url=url), self.assertRaises(ValueError): allowed_url(url)
        self.assertEqual(allowed_url("https://arxiv.org/abs/1234.56789"), "https://arxiv.org/abs/1234.56789")

    def test_failed_remote_checkpoint_prevents_model_request(self):
        class NeverCall(Fixture):
            charged=True
            def propose(self, request): raise AssertionError("Model must not be called")
        def failure(): raise OSError("Push failed")
        with self.assertRaises(OSError): self.engine.run(NeverCall(), checkpoint=failure)
        self.assertIsNotNone(self.engine.store.load()["pending"])


class CloudPersistenceTests(unittest.TestCase):
    def test_new_runner_recovers_reserved_attempt_without_refund(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def git(*args): return subprocess.run(["git", *map(str,args)],check=True,capture_output=True,text=True)
            remote, runner = root/"remote.git", root/"runner"
            git("init","--bare",remote)
            git("init",runner)
            (runner/"README.md").write_text("Source stays separate")
            git("-C",runner,"add","README.md")
            git("-C",runner,"-c","user.name=test","-c","user.email=test@example.com","commit","-m","Source")
            git("-C",runner,"remote","add","origin",remote)
            branch=StateBranch(runner,root/"state-one")
            branch.open()
            settings={**DEFAULTS,"daily_call_limit":1}
            engine=Engine(branch.checkout/"data",settings)
            try:
                with engine.store.lock():
                    engine.initialize()
                    engine.start("gemini","test",charged=True)
                    branch.checkpoint()
            finally: engine.store.close()
            # A genuinely separate clone reads only the remotely checkpointed record.
            git("clone","--branch","wake-state",remote,root/"fresh-runner")
            other=StateBranch(root/"fresh-runner",root/"state-two")
            other.open()
            reopened=Engine(other.checkout/"data",settings)
            try:
                with reopened.store.lock():
                    state=reopened.recover()
                    self.assertEqual(next(iter(state["invocations"].values()))["status"],"recovered")
                    with self.assertRaisesRegex(Rejected,"Daily call ceiling"):
                        reopened.start("gemini","test",charged=True)
                self.assertFalse((other.checkout/"README.md").exists())
            finally: reopened.store.close()


if __name__ == "__main__": unittest.main()
