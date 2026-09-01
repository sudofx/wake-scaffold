"""
Tests for wake.py's self-edit mechanics — run with:

    python tests/test_wake.py

No API key, no network access, and no waiting for a scheduled live
wake are needed: everything here runs against a throwaway temp
directory shaped like memory/, monkeypatching wake.py's module-level
path constants for the duration of each test and restoring them
afterward. The real memory/ directory is never touched.

Two things this specifically exists to verify with real evidence
rather than by inspecting the code and assuming:
  1. The mandatory blog-post fallback (compose_fallback_blog_post +
     apply_blog_post, wired through apply_self_edits) actually fires
     when journal output has no blog-post block, and does NOT fire
     when it does.
  2. The tool-run sandbox (stripped env, restricted cwd) actually
     holds when a real subprocess is executed, not just that the code
     reads as if it should.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import wake
from providers.mock import MockProvider


FIXED_NOW = datetime(2026, 8, 31, 9, 0, 0, tzinfo=ZoneInfo("America/Los_Angeles"))


class WakeTestCase(unittest.TestCase):
    """Base case: points every module-level memory path at a throwaway
    temp directory seeded from base_memory/, and restores the real
    paths afterward no matter what happens in the test."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="wake-scaffold-test-")
        self.memory = Path(self.tmpdir) / "memory"
        shutil.copytree(wake.BASE_MEMORY, self.memory)
        (self.memory / "journal").mkdir(exist_ok=True)

        self._orig = {
            name: getattr(wake, name)
            for name in ("MEMORY", "JOURNAL", "TOOLS_DIR", "TOOL_RUNS_FILE")
        }
        wake.MEMORY = self.memory
        wake.JOURNAL = self.memory / "journal"
        wake.TOOLS_DIR = self.memory / "tools"
        wake.TOOL_RUNS_FILE = self.memory / "tool_runs.json"

    def tearDown(self):
        for name, value in self._orig.items():
            setattr(wake, name, value)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def blog_posts(self):
        return json.loads((self.memory / "blog_posts.json").read_text())["posts"]


class BlogFallbackTests(WakeTestCase):
    """Item under test: the mandatory blog-post fallback."""

    def test_fallback_triggers_when_model_skips_blog_post(self):
        model_output = (
            "```commitments-update\n"
            "not valid json on purpose\n"
            "```\n"
        )
        result = wake.apply_self_edits(model_output, {}, FIXED_NOW, "test-journal.md")

        self.assertIn("WARNING: no blog-post block this wake", result)
        self.assertIn("ADDED blog post", result)
        self.assertIn("WARNING: no tool-write or tool-run this wake", result)

        posts = self.blog_posts()
        self.assertEqual(len(posts), 1, "fallback should add exactly one post")
        self.assertTrue(posts[0]["title"].startswith("Wake notes —"))
        # Real (if rejected) activity happened this wake, so the fallback
        # post should report it rather than claim a quiet wake.
        self.assertIn("REJECTED commitments-update", posts[0]["body_html"])
        self.assertNotIn("Quiet wake", posts[0]["body_html"])

        blog_html = (self.memory / "blog.html").read_text()
        self.assertIn("Wake notes —", blog_html, "blog.html must be re-rendered to include the fallback post")

    def test_truly_quiet_wake_gets_generic_fallback_message(self):
        """A wake where literally nothing applied (no self-edit blocks of
        any kind, including no tool work) should hit the genuinely
        empty branch of compose_fallback_blog_post — "Quiet wake,
        nothing to report" — rather than a warning being mistaken for
        something having happened. This was previously unreachable: the
        missing-tool-work warning was appended to all_notes before the
        fallback check ran, so prior_notes was never actually empty."""
        model_output = "## What I did\nAbsolutely nothing this wake — pure smoke test.\n"
        result = wake.apply_self_edits(model_output, {}, FIXED_NOW, "test-journal.md")

        posts = self.blog_posts()
        self.assertEqual(len(posts), 1)
        self.assertIn("Quiet wake", posts[0]["body_html"])
        self.assertIn("Nothing to report yet", posts[0]["body_html"])
        # The tool-work warning must still land in the overall journal
        # notes, just not inside the fallback post body itself.
        self.assertIn("WARNING: no tool-write or tool-run this wake", result)

    def test_fallback_summarizes_other_self_edits_when_present(self):
        model_output = (
            "```identity-update\n"
            '{"current_focus": "Testing the fallback alongside a real self-edit"}\n'
            "```\n"
        )
        result = wake.apply_self_edits(model_output, {}, FIXED_NOW, "test-journal.md")

        self.assertIn("WARNING: no blog-post block this wake", result)
        posts = self.blog_posts()
        self.assertEqual(len(posts), 1)
        # The fallback post should reflect what actually happened this
        # wake (the identity-update outcome), not a generic "nothing
        # happened" message.
        self.assertIn("APPLIED current_focus", posts[0]["body_html"])
        self.assertNotIn("Quiet wake", posts[0]["body_html"])

    def test_fallback_does_not_trigger_when_model_posts_for_real(self):
        model_output = (
            "```blog-post\n"
            '{"title": "A real post", "body_html": "<p>Hi there.</p>"}\n'
            "```\n"
        )
        result = wake.apply_self_edits(model_output, {}, FIXED_NOW, "test-journal.md")

        self.assertNotIn("WARNING: no blog-post block this wake", result)
        posts = self.blog_posts()
        self.assertEqual(len(posts), 1, "should be exactly the real post, no fallback added on top")
        self.assertEqual(posts[0]["title"], "A real post")

    def test_full_mock_provider_round_trip_never_hits_fallback(self):
        """Runs the actual two-pass prompts through MockProvider (never a
        live API) end to end, confirming the normal happy path — where
        the model behaves — never triggers the fallback."""
        provider = MockProvider()
        reflection = provider.generate(wake.build_reflection_prompt(FIXED_NOW), "reflect")
        self.assertTrue(reflection.strip())

        journal_output = provider.generate(
            wake.build_journal_prompt(reflection, FIXED_NOW, enable_pull_requests=False),
            "act",
        )
        self.assertIn("```blog-post", journal_output)

        result = wake.apply_self_edits(journal_output, {"enable_pull_requests": False},
                                        FIXED_NOW, "test-journal.md")
        self.assertNotIn("WARNING: no blog-post block this wake", result)

        posts = self.blog_posts()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["title"], "Mock test post")

        # The mock output also unlocks the tool-write/tool-run path, the
        # identity-update path (including the "unauthorized field
        # ignored" case), the hypothesis path is untouched since the
        # mock doesn't include one, and the growth-plan path is
        # likewise untouched — confirms nothing crashes when some
        # blocks are simply absent.
        self.assertIn("IGNORED unauthorized identity fields", result)
        self.assertIn("WROTE tools/mock_tool.py", result)
        self.assertIn("RAN tools/mock_tool.py", result)


class LimitationSpawnsGrowthProjectTests(WakeTestCase):
    """Item under test: a recorded limitation spawns a real growth_plan.json entry."""

    def test_known_limitation_spawns_growth_project(self):
        block = json.dumps({
            "current_focus": "unchanged",
            "known_limitations_add": ["Cannot verify claims about the outside world without a tool."],
        })
        notes = wake.apply_identity_update(block, FIXED_NOW)
        self.assertTrue(any(n.startswith("SPAWNED (from new limitation)") for n in notes))

        growth = json.loads((self.memory / "growth_plan.json").read_text())
        self.assertEqual(len(growth["projects"]), 1)
        project = growth["projects"][0]
        self.assertIn("Cannot verify claims about the outside world", project["title"])
        self.assertEqual(project["status"], "proposed")
        self.assertIn("never misrepresent", project["capability"])


class HypothesesTests(WakeTestCase):
    """Item under test: hypotheses.json add + evidence-gated status change."""

    def test_add_and_confirm_with_evidence(self):
        add_block = json.dumps({
            "add": [{"prediction": "validate_memory.py exits 0 on a clean memory dir",
                     "test_method": "run it via tool-run against this temp memory dir"}]
        })
        notes = wake.apply_hypotheses_update(add_block, FIXED_NOW)
        self.assertTrue(any(n.startswith("ADDED hypothesis") for n in notes))

        hyp_id = json.loads((self.memory / "hypotheses.json").read_text())["hypotheses"][0]["id"]

        # Rejected: no evidence supplied for a non-"testing" status.
        bad_change = json.dumps({"status_change": [
            {"id": hyp_id, "new_status": "confirmed", "conclusion": "it works"}
        ]})
        notes = wake.apply_hypotheses_update(bad_change, FIXED_NOW)
        self.assertTrue(any("requires real 'evidence'" in n for n in notes))
        hyps = json.loads((self.memory / "hypotheses.json").read_text())["hypotheses"]
        self.assertEqual(hyps[0]["status"], "untested")

        # Accepted: real evidence supplied.
        good_change = json.dumps({"status_change": [
            {"id": hyp_id, "new_status": "confirmed",
             "evidence": "tool_runs.json shows exit_code 0 for the last run",
             "conclusion": "prediction held"}
        ]})
        notes = wake.apply_hypotheses_update(good_change, FIXED_NOW)
        self.assertTrue(any(n.startswith("UPDATED hypothesis") for n in notes))
        hyps = json.loads((self.memory / "hypotheses.json").read_text())["hypotheses"]
        self.assertEqual(hyps[0]["status"], "confirmed")


class ToolRunSandboxTests(WakeTestCase):
    """Item under test: tool-run's stripped env and restricted cwd, verified
    against a real subprocess, not just by reading the code."""

    SECRET_ENV_VAR = "WAKE_SCAFFOLD_TEST_SECRET"

    def setUp(self):
        super().setUp()
        os.environ[self.SECRET_ENV_VAR] = "super-secret-value-should-never-leak"
        self.addCleanup(os.environ.pop, self.SECRET_ENV_VAR, None)

    def test_subprocess_env_and_cwd_are_sandboxed(self):
        probe = (
            "import os, sys\n"
            "print('CWD:' + os.getcwd())\n"
            "print('SECRET_PRESENT:' + str('" + self.SECRET_ENV_VAR + "' in os.environ))\n"
            "print('ENV_KEYS:' + ','.join(sorted(os.environ.keys())))\n"
        )
        write_block = json.dumps({"files": [{"filename": "probe.py", "content": probe}]})
        write_notes = wake.apply_tool_write(write_block, FIXED_NOW, "test-journal.md")
        self.assertTrue(any(n.startswith("WROTE") for n in write_notes), write_notes)

        run_block = json.dumps({"filename": "probe.py", "args": []})
        run_notes = wake.apply_tool_run(run_block, FIXED_NOW, "test-journal.md")
        self.assertTrue(any(n.startswith("RAN tools/probe.py") for n in run_notes), run_notes)

        runs = json.loads(wake.TOOL_RUNS_FILE.read_text())["runs"]
        self.assertEqual(len(runs), 1)
        stdout = runs[0]["stdout"]
        self.assertEqual(runs[0]["exit_code"], 0, stdout + runs[0]["stderr"])

        # cwd must be memory/tools, resolved, not the repo root.
        expected_cwd = str(wake.TOOLS_DIR.resolve())
        self.assertIn(f"CWD:{expected_cwd}", stdout)

        # The secret set in THIS test process's environment must not be
        # visible inside the subprocess.
        self.assertIn("SECRET_PRESENT:False", stdout)
        self.assertNotIn("super-secret-value-should-never-leak", stdout)

        # Only allowlisted keys should be present at all.
        env_keys_line = next(line for line in stdout.splitlines() if line.startswith("ENV_KEYS:"))
        seen_keys = set(env_keys_line[len("ENV_KEYS:"):].split(",")) if env_keys_line[len("ENV_KEYS:"):] else set()
        self.assertTrue(seen_keys.issubset(wake.SAFE_TOOL_ENV_ALLOWLIST), seen_keys)


class _ScriptedProvider:
    """Raises a scripted sequence of exceptions, then returns a fixed
    string once the sequence is exhausted. Used to exercise
    generate_with_retry without touching a real network call."""

    def __init__(self, exceptions):
        self.exceptions = list(exceptions)
        self.calls = 0

    def generate(self, system_prompt, user_prompt):
        self.calls += 1
        if self.exceptions:
            raise self.exceptions.pop(0)
        return "ok"


class RetryTests(unittest.TestCase):
    """generate_with_retry: real evidence, not just reading the code,
    that it (a) retries transient 503/429 errors and eventually
    succeeds, (b) honors a server-supplied retryDelay when present,
    (c) never sleeps for non-transient errors, and (d) still gives up
    and raises once max_retries is exhausted — so a genuinely dead
    daily quota fails the wake in seconds, not hours."""

    def test_retries_transient_error_then_succeeds(self):
        provider = _ScriptedProvider([
            Exception("ServerError: 503 UNAVAILABLE. model overloaded"),
        ])
        with patch("wake.time.sleep") as mock_sleep:
            result = wake.generate_with_retry(provider, "sys", "user")
        self.assertEqual(result, "ok")
        self.assertEqual(provider.calls, 2)
        mock_sleep.assert_called_once()

    def test_honors_server_supplied_retry_delay(self):
        provider = _ScriptedProvider([
            Exception(
                "ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'message': "
                "'Please retry in 41.886700264s.', 'details': [{'@type': "
                "'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': "
                "'41s'}]}}"
            ),
        ])
        with patch("wake.time.sleep") as mock_sleep:
            result = wake.generate_with_retry(provider, "sys", "user")
        self.assertEqual(result, "ok")
        mock_sleep.assert_called_once_with(41.0)

    def test_does_not_retry_non_transient_error(self):
        provider = _ScriptedProvider([ValueError("GEMINI_API_KEY not set")])
        with patch("wake.time.sleep") as mock_sleep:
            with self.assertRaises(ValueError):
                wake.generate_with_retry(provider, "sys", "user")
        mock_sleep.assert_not_called()
        self.assertEqual(provider.calls, 1)

    def test_gives_up_after_max_retries(self):
        always_fails = [
            Exception("ServerError: 503 UNAVAILABLE. still overloaded")
            for _ in range(5)
        ]
        provider = _ScriptedProvider(always_fails)
        with patch("wake.time.sleep") as mock_sleep:
            with self.assertRaises(Exception):
                wake.generate_with_retry(provider, "sys", "user", max_retries=2)
        self.assertEqual(provider.calls, 3)  # initial attempt + 2 retries
        self.assertEqual(mock_sleep.call_count, 2)

    def test_delay_capped_by_max_wait(self):
        provider = _ScriptedProvider([
            Exception("429 RESOURCE_EXHAUSTED. retry in 500s"),
        ])
        with patch("wake.time.sleep") as mock_sleep:
            wake.generate_with_retry(provider, "sys", "user", max_wait=90.0)
        mock_sleep.assert_called_once_with(90.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)