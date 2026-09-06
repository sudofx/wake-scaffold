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
            for name in (
                "MEMORY", "JOURNAL", "IDENTITY_DIR", "MEMORIES_DIR",
                "WORKSPACE_DIR", "TOOLS_DIR", "TOOL_RUNS_FILE",
                "PERSONA_DIR", "BLOG_DIR", "BLOG_HTML_DIR",
                "EPISTEMIC_STATE_FILE", "CORE_MANIFEST_FILE",
            )
        }
        wake.MEMORY = self.memory
        wake.JOURNAL = self.memory / "journal"
        wake.IDENTITY_DIR = self.memory / "core_identity"
        wake.MEMORIES_DIR = self.memory / "core_memories"
        wake.WORKSPACE_DIR = self.memory / "core_workspace"
        wake.TOOLS_DIR = self.memory / "core_workspace" / "tools"
        wake.TOOL_RUNS_FILE = self.memory / "core_workspace" / "tool_runs.json"
        wake.PERSONA_DIR = self.memory / "core_public_facing_persona"
        wake.BLOG_DIR = self.memory / "core_public_facing_persona" / "blog"
        wake.BLOG_HTML_DIR = self.memory / "core_public_facing_persona" / "blog" / "html"
        wake.EPISTEMIC_STATE_FILE = self.memory / "core_memories" / "epistemic_state.json"
        wake.CORE_MANIFEST_FILE = self.memory / "core_manifest.json"

    def tearDown(self):
        for name, value in self._orig.items():
            setattr(wake, name, value)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def blog_posts(self):
        return json.loads((self.memory / "core_public_facing_persona" / "blog" / "blog_posts.json").read_text())["posts"]


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

        blog_html = (self.memory / "core_public_facing_persona" / "blog" / "html" / "index.html").read_text()
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

    def test_blog_post_records_wake_context_and_escapes_code_snippet(self):
        model_output = (
            "```blog-post\n"
            '{"title": "Explaining the work", '
            '"body_html": "<p>Plain-language result.</p>", '
            '"work_summary": "Checked the memory layout", '
            '"code_snippet": "print(<unsafe>)"}\n'
            "```\n"
        )
        wake.apply_self_edits(model_output, {}, FIXED_NOW, "test-journal.md")

        post = self.blog_posts()[0]
        self.assertEqual(post["wake_number"], 1)
        self.assertEqual(post["work_summary"], "Checked the memory layout")
        self.assertEqual(post["code_snippet"], "print(<unsafe>)")

        blog_html = (self.memory / "core_public_facing_persona" / "blog" / "html" / "index.html").read_text()
        self.assertIn("Wake 1", blog_html)
        self.assertIn("https://github.com/sudofx/wake-scaffold/tree/master", blog_html)
        self.assertIn("https://github.com/sudofx/wake-scaffold/tree/master/memory", blog_html)
        self.assertIn("What this wake changed:</strong> Checked the memory layout", blog_html)
        self.assertIn("print(&lt;unsafe&gt;)", blog_html)
        self.assertNotIn("print(<unsafe>)", blog_html)

    def test_blog_html_caps_recent_posts_without_discarding_source_history(self):
        original_limit = wake.load_config
        wake.load_config = lambda: {"github": {
            "owner": "sudofx", "repo": "wake-scaffold", "branch": "master"
        }, "recent_blog_posts": 2}
        self.addCleanup(setattr, wake, "load_config", original_limit)

        for index in range(3):
            model_output = (
                "```blog-post\n"
                + json.dumps({
                    "title": f"Post {index}",
                    "body_html": f"<p>Post {index}</p>",
                })
                + "\n```\n"
            )
            wake.apply_self_edits(
                model_output, {}, FIXED_NOW.replace(second=index),
                f"test-journal-{index}.md",
            )

        posts = self.blog_posts()
        self.assertEqual(len(posts), 3)
        blog_html = (self.memory / "core_public_facing_persona" / "blog" / "html" / "index.html").read_text()
        self.assertIn("Post 2", blog_html)
        self.assertIn("Post 1", blog_html)
        self.assertNotIn("Post 0", blog_html)

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

    def test_full_mock_provider_combined_round_trip_never_hits_fallback(self):
        """Same coverage as the two-pass test above, but for the single-
        call combined path (build_combined_prompt / split_combined_output)
        — confirms the merge didn't drop or corrupt any of the work
        instructions the two-pass version relied on."""
        provider = MockProvider()
        raw_output = provider.generate(
            wake.build_combined_prompt(FIXED_NOW, enable_pull_requests=False),
            "reflect then act",
        )

        reflection, journal_output = wake.split_combined_output(raw_output)
        self.assertTrue(reflection.strip())
        self.assertNotIn(wake.WAKE_SPLIT_MARKER, reflection)
        self.assertNotIn(wake.WAKE_SPLIT_MARKER, journal_output)
        self.assertIn("```blog-post", journal_output)

        result = wake.apply_self_edits(journal_output, {"enable_pull_requests": False},
                                        FIXED_NOW, "test-journal.md")
        self.assertNotIn("WARNING: no blog-post block this wake", result)

        posts = self.blog_posts()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["title"], "Mock test post")
        self.assertIn("IGNORED unauthorized identity fields", result)
        self.assertIn("WROTE tools/mock_tool.py", result)
        self.assertIn("RAN tools/mock_tool.py", result)

    def test_split_combined_output_falls_back_gracefully_without_marker(self):
        """If the model ever skips the marker, the whole response should
        become the work output rather than raising or silently dropping
        text."""
        reflection, work = wake.split_combined_output("no marker anywhere in this text")
        self.assertIn("No split marker found", reflection)
        self.assertEqual(work, "no marker anywhere in this text")

    def test_split_combined_output_splits_on_marker(self):
        raw = f"my reflection\n\n{wake.WAKE_SPLIT_MARKER}\n\nmy journal entry"
        reflection, work = wake.split_combined_output(raw)
        self.assertEqual(reflection, "my reflection")
        self.assertEqual(work, "my journal entry")


class LimitationSpawnsGrowthProjectTests(WakeTestCase):
    """Item under test: a recorded limitation spawns a real growth_plan.json entry."""

    def test_known_limitation_spawns_growth_project(self):
        block = json.dumps({
            "current_focus": "unchanged",
            "known_limitations_add": ["Cannot verify claims about the outside world without a tool."],
        })
        notes = wake.apply_identity_update(block, FIXED_NOW)
        self.assertTrue(any(n.startswith("SPAWNED (from new limitation)") for n in notes))

        growth = json.loads((self.memory / "core_memories" / "growth_plan.json").read_text())
        self.assertEqual(len(growth["projects"]), 1)
        project = growth["projects"][0]
        self.assertIn("Cannot verify claims about the outside world", project["title"])
        self.assertEqual(project["status"], "proposed")
        self.assertIn("never misrepresent", project["capability"])


class GrowthPlanDuplicateTests(WakeTestCase):
    """Item under test: near-duplicate growth-plan proposals are rejected
    at the mechanism level, not just discouraged in prose (HANDOFF item 2)."""

    def test_near_duplicate_title_is_rejected_with_pointer_to_existing_id(self):
        first = json.dumps({"add": [{
            "title": "Workspace & Memory Integrity Validator",
            "capability": "Programmatically check workspace JSON schemas and memory formatting integrity.",
            "next_step": "Run it.",
        }]})
        notes = wake.apply_growth_plan_update(first, FIXED_NOW)
        self.assertTrue(any(n.startswith("ADDED capability project") for n in notes))
        existing_id = json.loads((self.memory / "core_memories" / "growth_plan.json").read_text())["projects"][0]["id"]

        second = json.dumps({"add": [{
            "title": "Automated workspace integrity validator",
            "capability": "Ability to verify that all core memory and state files exist and contain valid JSON/Markdown",
            "next_step": "Run it too.",
        }]})
        notes = wake.apply_growth_plan_update(second, FIXED_NOW)
        self.assertTrue(any(n.startswith("REJECTED growth project") for n in notes), notes)
        self.assertTrue(any(existing_id in n for n in notes), notes)
        projects = json.loads((self.memory / "core_memories" / "growth_plan.json").read_text())["projects"]
        self.assertEqual(len(projects), 1, "the near-duplicate must not have been appended")

    def test_genuinely_different_project_is_accepted(self):
        first = json.dumps({"add": [{
            "title": "Memory Integrity Validator",
            "capability": "Validate JSON structure of workspace memory files.",
            "next_step": "Run it.",
        }]})
        wake.apply_growth_plan_update(first, FIXED_NOW)

        second = json.dumps({"add": [{
            "title": "Blog RSS Feed Generator",
            "capability": "Produce a valid RSS feed from blog_posts.json for external readers.",
            "next_step": "Write feed.py and run it against the current blog_posts.json.",
        }]})
        notes = wake.apply_growth_plan_update(second, FIXED_NOW)
        self.assertTrue(any(n.startswith("ADDED capability project") for n in notes), notes)
        projects = json.loads((self.memory / "core_memories" / "growth_plan.json").read_text())["projects"]
        self.assertEqual(len(projects), 2)

    def test_duplicate_check_ignores_closed_projects(self):
        first = json.dumps({"add": [{
            "title": "Memory Integrity Validator",
            "capability": "Validate JSON structure of workspace memory files.",
            "next_step": "Run it.",
        }]})
        wake.apply_growth_plan_update(first, FIXED_NOW)
        existing_id = json.loads((self.memory / "core_memories" / "growth_plan.json").read_text())["projects"][0]["id"]
        wake.apply_growth_plan_update(json.dumps({"status_change": [
            {"id": existing_id, "new_status": "complete", "evidence": "Ran it, works."}
        ]}), FIXED_NOW)

        second = json.dumps({"add": [{
            "title": "Memory Integrity Validator v2",
            "capability": "Validate JSON structure of workspace memory files.",
            "next_step": "Run it.",
        }]})
        notes = wake.apply_growth_plan_update(second, FIXED_NOW)
        self.assertTrue(any(n.startswith("ADDED capability project") for n in notes), notes)


class NarrowDomainNudgeTests(WakeTestCase):
    """Item under test: soft prompt-level nudge when recent growth-plan
    history clusters in one domain (HANDOFF item 3)."""

    def _add_project(self, title, capability):
        wake.apply_growth_plan_update(json.dumps({"add": [{
            "title": title, "capability": capability, "next_step": "next",
        }]}), FIXED_NOW)

    def test_no_nudge_with_too_little_history(self):
        self._add_project("Memory Validator", "Validate memory JSON files.")
        self.assertIsNone(wake.detect_narrow_domain_nudge())

    def test_nudge_fires_when_recent_projects_cluster(self):
        # Each title distinct enough to dodge the duplicate check, but all
        # sharing "memory"/"validator"/"validate" as a topic.
        titles = [
            ("Memory Integrity Validator", "Validate JSON structure of workspace memory files."),
            ("Blog RSS Feed Generator", "Produce a valid RSS feed from blog_posts.json."),
            ("Deep Memory Schema Validator", "Item-level schema validation for memory files."),
            ("Workspace Memory Validation Tool", "Discover and validate memory files across contexts."),
            ("Memory File Validator Extension", "Extend validation coverage to more memory files."),
        ]
        for title, capability in titles:
            self._add_project(title, capability)
        nudge = wake.detect_narrow_domain_nudge()
        self.assertIsNotNone(nudge)
        self.assertIn("memory", nudge.lower())


class HypothesisGapTests(WakeTestCase):
    """Item under test: a silent hypothesis gap is surfaced, not just left
    quiet (HANDOFF item 4)."""

    def _touch_journal(self, stamp, failed=False):
        suffix = "-FAILED.md" if failed else ".md"
        (self.memory / "journal" / f"{stamp}{suffix}").write_text("entry")

    def test_gap_counts_successful_wakes_since_last_hypothesis(self):
        wake.apply_hypotheses_update(json.dumps({"add": [
            {"prediction": "x", "test_method": "y"}
        ]}), datetime(2026, 8, 30, 10, 0, 0, tzinfo=FIXED_NOW.tzinfo))
        # Three successful wakes after the hypothesis, one failed wake
        # (should not count), all with later filename stamps.
        for stamp in ("2026-08-30-110000", "2026-08-30-120000", "2026-08-30-130000"):
            self._touch_journal(stamp)
        self._touch_journal("2026-08-30-140000", failed=True)
        self.assertEqual(wake.wakes_since_last_hypothesis(), 3)

    def test_gap_is_total_successful_wakes_when_no_hypothesis_ever_recorded(self):
        for stamp in ("2026-08-30-110000", "2026-08-30-120000"):
            self._touch_journal(stamp)
        self._touch_journal("2026-08-30-130000", failed=True)
        self.assertEqual(wake.wakes_since_last_hypothesis(), 2)


class OfflineFallbackTests(WakeTestCase):
    """Item under test: run_offline_fallback and write_failure_record's
    fallback_notes wiring — the $0, no-model-call path that runs when
    generate() fails outright, verified against a real subprocess run
    and a real failure file, not just by reading the code."""

    def test_offline_fallback_reports_unavailable_when_no_tool_exists(self):
        notes = wake.run_offline_fallback(FIXED_NOW, "test-journal-FAILED.md")
        self.assertTrue(any("No offline fallback available" in n for n in notes), notes)

    def test_offline_fallback_runs_validate_memory_and_records_it(self):
        validator = (
            "import sys\n"
            "print('offline fallback probe ran')\n"
            "sys.exit(0)\n"
        )
        write_block = json.dumps({"files": [{"filename": "validate_memory.py", "content": validator}]})
        write_notes = wake.apply_tool_write(write_block, FIXED_NOW, "test-journal.md")
        self.assertTrue(any(n.startswith("WROTE") for n in write_notes), write_notes)

        notes = wake.run_offline_fallback(FIXED_NOW, "test-journal-FAILED.md")
        self.assertTrue(any(n.startswith("RAN tools/validate_memory.py") for n in notes), notes)

        runs = json.loads(wake.TOOL_RUNS_FILE.read_text())["runs"]
        self.assertEqual(runs[-1]["exit_code"], 0)
        self.assertIn("offline fallback probe ran", runs[-1]["stdout"])

    def test_write_failure_record_includes_fallback_notes(self):
        path = wake.write_failure_record(
            "gemini", "generate", RuntimeError("503 UNAVAILABLE"),
            fallback_notes=["RAN tools/validate_memory.py [] -> exit code 0."],
            now=FIXED_NOW, filename="test-journal-FAILED.md",
        )
        text = path.read_text()
        self.assertIn("Offline fallback (no model call, $0 cost)", text)
        self.assertIn("RAN tools/validate_memory.py", text)


class HypothesesTests(WakeTestCase):
    """Item under test: hypotheses.json add + evidence-gated status change."""

    def test_add_and_confirm_with_evidence(self):
        add_block = json.dumps({
            "add": [{"prediction": "validate_memory.py exits 0 on a clean memory dir",
                     "test_method": "run it via tool-run against this temp memory dir"}]
        })
        notes = wake.apply_hypotheses_update(add_block, FIXED_NOW)
        self.assertTrue(any(n.startswith("ADDED hypothesis") for n in notes))

        hyp_id = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())["hypotheses"][0]["id"]

        # Rejected: no evidence supplied for a non-"testing" status.
        bad_change = json.dumps({"status_change": [
            {"id": hyp_id, "new_status": "confirmed", "conclusion": "it works"}
        ]})
        notes = wake.apply_hypotheses_update(bad_change, FIXED_NOW)
        self.assertTrue(any("requires real 'evidence'" in n for n in notes))
        hyps = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())["hypotheses"]
        self.assertEqual(hyps[0]["status"], "untested")

        # Accepted: real evidence supplied.
        good_change = json.dumps({"status_change": [
            {"id": hyp_id, "new_status": "confirmed",
             "evidence": "tool_runs.json shows exit_code 0 for the last run",
             "conclusion": "prediction held"}
        ]})
        notes = wake.apply_hypotheses_update(good_change, FIXED_NOW)
        self.assertTrue(any(n.startswith("UPDATED hypothesis") for n in notes))
        hyps = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())["hypotheses"]
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


class GeminiFallbackTests(unittest.TestCase):
    """GeminiProvider: real evidence that a transient error on one model
    moves on to try the next free model (a separate quota bucket) rather
    than giving up, that a non-transient error does NOT trigger that
    fallback, and that the original error surfaces once every model is
    exhausted. No real network or credentials involved — google.genai is
    replaced with a fake module for the duration of each test."""

    def setUp(self):
        os.environ["GEMINI_API_KEY"] = "test-key"
        self.addCleanup(os.environ.pop, "GEMINI_API_KEY", None)
        sys.modules.pop("providers.gemini", None)
        self.addCleanup(sys.modules.pop, "google", None)
        self.addCleanup(sys.modules.pop, "google.genai", None)
        self.addCleanup(sys.modules.pop, "providers.gemini", None)

    def _install_fake_genai(self, generate_side_effect):
        import types

        class FakeResponse:
            def __init__(self, text):
                self.text = text

        class FakeModels:
            def __init__(self):
                self.calls = []

            def generate_content(self, model, contents, config):
                self.calls.append(model)
                result = generate_side_effect(model)
                if isinstance(result, Exception):
                    raise result
                return FakeResponse(result)

        class FakeClient:
            def __init__(self, api_key):
                self.models = FakeModels()

        fake_genai = types.ModuleType("google.genai")
        fake_genai.Client = FakeClient
        fake_google = types.ModuleType("google")
        fake_google.genai = fake_genai
        sys.modules["google"] = fake_google
        sys.modules["google.genai"] = fake_genai
        return fake_genai

    def test_falls_back_to_next_model_on_transient_error(self):
        def side_effect(model):
            if model == "gemini-3.6-flash":
                return RuntimeError("429 RESOURCE_EXHAUSTED: quota")
            return f"ok from {model}"

        self._install_fake_genai(side_effect)
        from providers.gemini import GeminiProvider
        provider = GeminiProvider(fallback_models=["gemini-3.5-flash", "gemini-3.1-flash-lite"])
        result = provider.generate("sys", "user")

        self.assertEqual(result, "ok from gemini-3.5-flash")
        # Confirms it actually tried the primary model first, then moved
        # to the fallback — not just that the fallback alone was called.
        self.assertEqual(provider.client.models.calls, ["gemini-3.6-flash", "gemini-3.5-flash"])

    def test_does_not_fall_back_on_non_transient_error(self):
        def side_effect(model):
            return RuntimeError("400 INVALID_ARGUMENT: malformed request")

        self._install_fake_genai(side_effect)
        from providers.gemini import GeminiProvider
        provider = GeminiProvider(fallback_models=["gemini-3.5-flash"])
        with self.assertRaises(RuntimeError):
            provider.generate("sys", "user")

    def test_raises_last_error_when_every_model_exhausted(self):
        def side_effect(model):
            return RuntimeError(f"503 UNAVAILABLE: {model} overloaded")

        self._install_fake_genai(side_effect)
        from providers.gemini import GeminiProvider
        provider = GeminiProvider(fallback_models=["gemini-3.5-flash"])
        with self.assertRaises(RuntimeError) as ctx:
            provider.generate("sys", "user")
        # Last model tried should be the one named in the surfaced error.
        self.assertIn("gemini-3.5-flash", str(ctx.exception))

    def test_default_and_explicit_fallback_models_are_deduplicated(self):
        self._install_fake_genai(lambda model: "ok")
        from providers.gemini import GeminiProvider
        provider = GeminiProvider(model="gemini-3.5-flash", fallback_models=["gemini-3.5-flash", "gemini-3.1-flash-lite"])
        self.assertEqual(provider.models, ["gemini-3.5-flash", "gemini-3.1-flash-lite"])


class TemporalContextTests(WakeTestCase):
    """wakes_today()/build_temporal_context() — Bob wakes many times a
    day, so 'today' has to be derived from real journal filenames, not
    assumed."""

    def test_wakes_today_excludes_other_days_and_failed_entries(self):
        (self.memory / "journal" / "2026-08-31-060000.md").write_text("x")
        (self.memory / "journal" / "2026-08-31-090000.md").write_text("x")
        # Earlier today but failed — should not count.
        (self.memory / "journal" / "2026-08-31-070000-FAILED.md").write_text("x")
        # Successful, but the previous calendar day — should not count.
        (self.memory / "journal" / "2026-08-30-235900.md").write_text("x")

        result = wake.wakes_today(FIXED_NOW)

        self.assertEqual(len(result), 2)
        # Oldest first.
        self.assertLess(result[0], result[1])
        self.assertEqual(result[0].hour, 6)
        self.assertEqual(result[1].hour, 9)

    def test_build_temporal_context_first_wake_of_day(self):
        context = wake.build_temporal_context(FIXED_NOW)
        self.assertIn("first wake today", context)
        self.assertIn("this wake", context)

    def test_build_temporal_context_reports_prior_wake_count(self):
        (self.memory / "journal" / "2026-08-31-060000.md").write_text("x")
        context = wake.build_temporal_context(FIXED_NOW)
        self.assertIn("already woken 1 time(s) today", context)

    def test_build_temporal_context_nudges_past_review_hour(self):
        late = FIXED_NOW.replace(hour=22)
        context = wake.build_temporal_context(late)
        self.assertIn("review hour", context)


class HypothesesFormattingTests(WakeTestCase):
    """format_hypotheses_for_prompt() should show every unresolved
    hypothesis in full but cap resolved ones to the 3 most recent."""

    def _add(self, prediction: str, now: datetime = FIXED_NOW) -> str:
        block = json.dumps({"add": [
            {"prediction": prediction, "test_method": "inspect a file"}
        ]})
        wake.apply_hypotheses_update(block, now)
        hyps = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())["hypotheses"]
        return hyps[-1]["id"]

    def _resolve(self, hyp_id: str, status: str):
        block = json.dumps({"status_change": [
            {"id": hyp_id, "new_status": status, "evidence": "observed x", "conclusion": "y"}
        ]})
        wake.apply_hypotheses_update(block, FIXED_NOW)

    def test_shows_all_unresolved_and_caps_resolved_to_three(self):
        # Each add uses a distinct second so hypothesis ids (derived from
        # filename_stamp) don't collide within this single test.
        from datetime import timedelta
        times = iter(FIXED_NOW + timedelta(seconds=i) for i in range(1, 20))

        # Two unresolved: one left untested, one moved to testing.
        untested_id = self._add("prediction A", next(times))
        testing_id = self._add("prediction B", next(times))
        self._resolve(testing_id, "testing")

        # Five resolved hypotheses, in order.
        resolved_ids = []
        for i in range(5):
            hid = self._add(f"resolved prediction {i}", next(times))
            self._resolve(hid, "confirmed")
            resolved_ids.append(hid)

        formatted = wake.format_hypotheses_for_prompt()

        self.assertIn(untested_id, formatted)
        self.assertIn(testing_id, formatted)
        # Only the last 3 resolved should be shown.
        for hid in resolved_ids[:2]:
            self.assertNotIn(hid, formatted)
        for hid in resolved_ids[2:]:
            self.assertIn(hid, formatted)
        self.assertIn("2 earlier resolved hypothesis(es) not shown", formatted)

    def test_no_omission_note_when_three_or_fewer_resolved(self):
        from datetime import timedelta
        times = iter(FIXED_NOW + timedelta(seconds=i) for i in range(1, 10))
        for i in range(2):
            hid = self._add(f"prediction {i}", next(times))
            self._resolve(hid, "refuted")
        formatted = wake.format_hypotheses_for_prompt()
        self.assertNotIn("not shown", formatted)


class IdentityLifecycleTests(unittest.TestCase):
    """archive_current_identity()'s index.md self-link rewrite and the
    auto-maintained IDENTITIES.md registry — uses a throwaway ROOT so
    the real repo's IDENTITIES.md and memory_*/ archives are never
    touched."""

    def setUp(self):
        self.tmproot = Path(tempfile.mkdtemp(prefix="wake-scaffold-root-"))
        shutil.copy(wake.ROOT / "config.yaml", self.tmproot / "config.yaml")
        self._orig = {
            name: getattr(wake, name)
            for name in (
                "ROOT", "MEMORY", "JOURNAL", "IDENTITIES_FILE",
                "IDENTITY_DIR", "MEMORIES_DIR", "WORKSPACE_DIR",
                "TOOLS_DIR", "TOOL_RUNS_FILE", "PERSONA_DIR",
                "BLOG_DIR", "BLOG_HTML_DIR", "EPISTEMIC_STATE_FILE",
                "CORE_MANIFEST_FILE",
            )
        }
        wake.ROOT = self.tmproot
        wake.MEMORY = self.tmproot / "memory"
        wake.JOURNAL = wake.MEMORY / "journal"
        wake.IDENTITIES_FILE = self.tmproot / "IDENTITIES.md"
        wake.IDENTITY_DIR = wake.MEMORY / "core_identity"
        wake.MEMORIES_DIR = wake.MEMORY / "core_memories"
        wake.WORKSPACE_DIR = wake.MEMORY / "core_workspace"
        wake.TOOLS_DIR = wake.WORKSPACE_DIR / "tools"
        wake.TOOL_RUNS_FILE = wake.WORKSPACE_DIR / "tool_runs.json"
        wake.PERSONA_DIR = wake.MEMORY / "core_public_facing_persona"
        wake.BLOG_DIR = wake.PERSONA_DIR / "blog"
        wake.BLOG_HTML_DIR = wake.BLOG_DIR / "html"
        wake.EPISTEMIC_STATE_FILE = wake.MEMORIES_DIR / "epistemic_state.json"
        wake.CORE_MANIFEST_FILE = wake.MEMORY / "core_manifest.json"

    def tearDown(self):
        for name, value in self._orig.items():
            setattr(wake, name, value)
        shutil.rmtree(self.tmproot, ignore_errors=True)

    def test_bootstrap_adds_active_row_to_identities_file(self):
        wake.bootstrap_identity("Ada", "Test bootstrapping.")
        text = wake.IDENTITIES_FILE.read_text()
        self.assertIn("| Ada | active | `memory/` |", text)

    def test_archive_rewrites_index_md_self_link_and_marks_archived(self):
        wake.bootstrap_identity("Ada", "Test archiving.")
        old_url = wake.htmlpreview_url("memory/core_public_facing_persona/blog/html/index.html")
        # Seed index.md with the stale self-link a real identity would have.
        index_path = wake.MEMORIES_DIR / "index.md"
        index_path.write_text(f"## What's been built\n\n[blog]({old_url})\n")

        destination = wake.archive_current_identity("ada_v1")

        new_url = wake.htmlpreview_url("memory_ada_v1/core_public_facing_persona/blog/html/index.html")
        archived_text = (destination / "core_memories" / "index.md").read_text()
        self.assertIn(new_url, archived_text)
        self.assertNotIn(old_url, archived_text)

        identities_text = wake.IDENTITIES_FILE.read_text()
        self.assertIn("| Ada | archived | `memory_ada_v1/` |", identities_text)
        self.assertIn(new_url, identities_text)

    def test_archive_never_touches_journal_or_blog_posts(self):
        wake.bootstrap_identity("Ada", "Test immutability.")
        wake.JOURNAL.mkdir(parents=True, exist_ok=True)
        (wake.JOURNAL / "2026-08-31-090000.md").write_text("original content")
        original_blog_posts = (wake.BLOG_DIR / "blog_posts.json").read_text()

        destination = wake.archive_current_identity("ada_v2")

        self.assertEqual(
            (destination / "journal" / "2026-08-31-090000.md").read_text(),
            "original content",
        )
        self.assertEqual((destination / "core_public_facing_persona" / "blog" / "blog_posts.json").read_text(), original_blog_posts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
