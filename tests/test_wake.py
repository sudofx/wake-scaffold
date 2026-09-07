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


class ConfigValidationTests(unittest.TestCase):
    def test_valid_config_is_accepted(self):
        wake.validate_config({
            "provider": "mock",
            "timezone": "America/Los_Angeles",
            "gemini_fallback_models": [],
            "daily_review_hour": 21,
            "index_consolidation_interval_wakes": 15,
            "recent_blog_posts": 20,
        })

    def test_invalid_provider_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown provider"):
            wake.validate_config({"provider": "missing"})

    def test_invalid_timezone_and_limits_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid timezone"):
            wake.validate_config({"timezone": "Not/AZone"})
        with self.assertRaisesRegex(ValueError, "daily_review_hour"):
            wake.validate_config({"daily_review_hour": 24})
        with self.assertRaisesRegex(ValueError, "recent_blog_posts"):
            wake.validate_config({"recent_blog_posts": 0})


class WakeTestCase(unittest.TestCase):
    """Base case: points every module-level memory path at a throwaway
    temp directory seeded from base_memory/, and restores the real
    paths afterward no matter what happens in the test."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="wake-scaffold-test-")
        self.memory = Path(self.tmpdir) / "memory"
        shutil.copytree(wake.BASE_MEMORY, self.memory)
        (self.memory / "core_workspace" / "journal").mkdir(exist_ok=True)

        self._orig = {
            name: getattr(wake, name)
            for name in (
                "MEMORY", "JOURNAL", "IDENTITY_DIR", "MEMORIES_DIR",
                "WORKSPACE_DIR", "TOOLS_DIR", "TOOL_RUNS_FILE", "SYNTHESIS_DIR",
                "PERSONA_DIR", "BLOG_DIR", "BLOG_HTML_DIR",
                "EPISTEMIC_STATE_FILE", "CORE_MANIFEST_FILE", "PROMPTS_DIR",
            )
        }
        wake.MEMORY = self.memory
        wake.JOURNAL = self.memory / "core_workspace" / "journal"
        wake.IDENTITY_DIR = self.memory / "core_identity"
        wake.MEMORIES_DIR = self.memory / "core_memories"
        wake.WORKSPACE_DIR = self.memory / "core_workspace"
        wake.TOOLS_DIR = self.memory / "core_workspace" / "tools"
        wake.TOOL_RUNS_FILE = self.memory / "core_workspace" / "tool_runs.json"
        wake.SYNTHESIS_DIR = self.memory / "core_synthesis"
        wake.PERSONA_DIR = self.memory / "core_persona"
        wake.BLOG_DIR = self.memory / "core_persona" / "blog"
        wake.BLOG_HTML_DIR = self.memory / "core_persona" / "blog" / "html"
        wake.EPISTEMIC_STATE_FILE = self.memory / "core_memories" / "epistemic_state.json"
        wake.CORE_MANIFEST_FILE = self.memory / "core_manifest.json"
        wake.PROMPTS_DIR = self.memory / "core_workspace" / "prompts"

    def tearDown(self):
        for name, value in self._orig.items():
            setattr(wake, name, value)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def blog_posts(self):
        return json.loads((self.memory / "core_persona" / "blog" / "blog_posts.json").read_text())["posts"]


class MemoryValidationTests(WakeTestCase):
    def test_manifest_persistence_matches_successful_journal_history(self):
        journal = self.memory / "core_workspace" / "journal" / "2026-08-31-090000.md"
        journal.write_text("# Reflection 2026-08-31-090000\n")
        wake.write_core_manifest("Ada")
        self.assertEqual(wake.validate_active_memory(), [])

    def test_validation_detects_manifest_wake_count_drift(self):
        journal = self.memory / "core_workspace" / "journal" / "2026-08-31-090000.md"
        journal.write_text("# Reflection 2026-08-31-090000\n")
        wake.write_core_manifest("Ada")
        manifest_path = self.memory / "core_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["total_wakes"] = 0
        manifest_path.write_text(json.dumps(manifest) + "\n")

        findings = wake.validate_active_memory()
        self.assertTrue(any("manifest wake count drift" in item for item in findings))

    def test_clean_seeded_memory_passes_validation(self):
        self.assertEqual(wake.validate_active_memory(), [])

    def test_validation_reports_corrupt_json_without_repairing_it(self):
        commitments = self.memory / "core_memories" / "commitments.json"
        original = commitments.read_text()
        commitments.write_text("not json")

        findings = wake.validate_active_memory()

        self.assertTrue(any("invalid JSON" in finding for finding in findings))
        self.assertEqual(commitments.read_text(), "not json")
        self.assertNotEqual(original, commitments.read_text())

    def test_validation_reports_stale_manifest_layout(self):
        manifest = self.memory / "core_manifest.json"
        manifest.write_text(json.dumps({"layout": {"persona": "core_public_facing_persona"}}))

        findings = wake.validate_active_memory()

        self.assertTrue(any("stale manifest layout" in finding for finding in findings))

    def test_validation_reports_broken_blog_journal_link(self):
        posts_path = self.memory / "core_persona" / "blog" / "blog_posts.json"
        posts = json.loads(posts_path.read_text())
        (self.memory / "core_workspace" / "journal" / "real-journal.md").write_text("entry")
        posts["posts"].append({
            "id": "post-test",
            "date_sortable": "2026-08-31-090000",
            "title": "Test",
            "body_html": "<p>Test</p>",
            "journal_entry": "missing-journal.md",
        })
        posts_path.write_text(json.dumps(posts))

        findings = wake.validate_active_memory()

        self.assertTrue(any("broken blog journal link" in finding for finding in findings))


class SynthesisStorageTests(WakeTestCase):
    def test_atomic_write_replaces_content_without_temp_files(self):
        target = self.memory / "core_memories" / "atomic-test.json"
        wake.atomic_write_text(target, '{"version": 1}\n')
        wake.atomic_write_text(target, '{"version": 2}\n')

        self.assertEqual(target.read_text(), '{"version": 2}\n')
        self.assertEqual(list(target.parent.glob(".atomic-test.json.*.tmp")), [])

    def test_reflection_is_stored_in_dated_internal_stream(self):
        first = wake.write_synthesis_entry(
            FIXED_NOW, "2026-08-31-090000.md", "Choose a capability and test it."
        )
        second = wake.write_synthesis_entry(
            FIXED_NOW, "2026-08-31-090000.md", "A second reflection must not overwrite the first."
        )

        self.assertEqual(first.parent, self.memory / "core_synthesis" / "2026" / "08" / "31")
        self.assertEqual(first.name, "2026-08-31-090000.md")
        self.assertEqual(second.name, "2026-08-31-090000-2.md")
        self.assertIn("Choose a capability", first.read_text())
        self.assertIn("2026-08-31-090000.md", second.read_text())

        daily = wake.write_daily_synthesis_index(FIXED_NOW)
        self.assertEqual(
            daily,
            self.memory / "core_synthesis" / "daily" / "2026" / "08" / "31.md",
        )
        daily_text = daily.read_text()
        self.assertIn("Successful wakes: 2", daily_text)
        self.assertIn("../../../../core_workspace/journal/2026-08-31-090000.md", daily_text)
        self.assertIn("Choose a capability and test it.", daily_text)
        self.assertIn("A second reflection must not overwrite the first.", daily_text)

        prompt = wake.build_daily_summary_prompt(FIXED_NOW)
        self.assertIn("2026-08-31", prompt)
        self.assertIn("Separate observed work from interpretation", prompt)
        self.assertIn("Choose a capability and test it.", prompt)

        summary = wake.write_semantic_daily_summary(
            FIXED_NOW, "## Themes\n\nThe reflections point toward deliberate testing."
        )
        self.assertEqual(summary.name, "31-summary.md")
        self.assertIn("Semantic daily summary", summary.read_text())
        self.assertIn("deliberate testing", summary.read_text())
        self.assertIn("A second reflection", second.read_text())


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

        blog_html = (self.memory / "core_persona" / "blog" / "html" / "index.html").read_text()
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

    def test_blog_post_rejects_executable_html(self):
        notes = wake.apply_blog_post(
            json.dumps({
                "title": "Unsafe post",
                "body_html": '<p>Hello</p><script>alert("x")</script>',
            }),
            FIXED_NOW,
            "test-journal.md",
        )

        self.assertTrue(any("executable HTML" in note for note in notes))
        self.assertEqual(self.blog_posts(), [])

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

        blog_html = (self.memory / "core_persona" / "blog" / "html" / "index.html").read_text()
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
        blog_html = (self.memory / "core_persona" / "blog" / "html" / "index.html").read_text()
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

    def test_growth_status_transitions_are_forward_only(self):
        add = json.dumps({"add": [{
            "title": "Forward-only lifecycle test",
            "capability": "Validate monotonic project status history.",
            "next_step": "Advance through each allowed state.",
        }]})
        wake.apply_growth_plan_update(add, FIXED_NOW)
        project_path = self.memory / "core_memories" / "growth_plan.json"
        project_id = json.loads(project_path.read_text())["projects"][0]["id"]

        def change(status):
            return wake.apply_growth_plan_update(json.dumps({"status_change": [{
                "id": project_id, "new_status": status, "evidence": "observed test result"
            }]}), FIXED_NOW)

        self.assertTrue(any("not a forward transition" in note for note in change("complete")))
        self.assertTrue(any(note.startswith("UPDATED capability project") for note in change("active")))
        self.assertTrue(any("not a forward transition" in note for note in change("proposed")))
        self.assertTrue(any(note.startswith("UPDATED capability project") for note in change("complete")))
        self.assertTrue(any("not a forward transition" in note for note in change("blocked")))

        project = json.loads(project_path.read_text())["projects"][0]
        self.assertEqual(project["status"], "complete")

    def test_duplicate_check_ignores_closed_projects(self):
        first = json.dumps({"add": [{
            "title": "Memory Integrity Validator",
            "capability": "Validate JSON structure of workspace memory files.",
            "next_step": "Run it.",
        }]})
        wake.apply_growth_plan_update(first, FIXED_NOW)
        existing_id = json.loads((self.memory / "core_memories" / "growth_plan.json").read_text())["projects"][0]["id"]
        wake.apply_growth_plan_update(json.dumps({"status_change": [
            {"id": existing_id, "new_status": "active", "evidence": "Started the validation."},
            {"id": existing_id, "new_status": "complete", "evidence": "Ran it, works."},
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
        (self.memory / "core_workspace" / "journal" / f"{stamp}{suffix}").write_text("entry")

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


class PromptLoggingTests(WakeTestCase):
    """Item under test: log_prompt_exchange and its wiring into _run_wake —
    real evidence that what the model actually received gets recorded,
    not just what it decided to do afterward. Uses provider: mock and a
    real _run_wake() call end to end where possible, per this repo's own
    standard of not trusting an implementation until it's actually run."""

    def _base_config(self, **overrides):
        cfg = {
            "provider": "mock",
            "timezone": "America/Los_Angeles",
            "enable_pull_requests": False,
            "daily_review_hour": 21,
            "index_consolidation_interval_wakes": 15,
            "recent_blog_posts": 20,
            "log_prompts": True,
        }
        cfg.update(overrides)
        return cfg

    def setUp(self):
        super().setUp()
        self._orig_load_config = wake.load_config
        self.addCleanup(setattr, wake, "load_config", self._orig_load_config)

    def _prompt_files(self):
        d = self.memory / "core_workspace" / "prompts"
        return list(d.glob("*.json")) if d.exists() else []

    def test_direct_call_writes_expected_fields(self):
        wake.log_prompt_exchange(
            {"log_prompts": True}, "2026-09-07-000000.md",
            "sys prompt text", "user prompt text", raw_output="model said this",
        )
        files = self._prompt_files()
        self.assertEqual(len(files), 1)
        record = json.loads(files[0].read_text())
        self.assertEqual(record["system_prompt"], "sys prompt text")
        self.assertEqual(record["user_prompt"], "user prompt text")
        self.assertEqual(record["raw_output"], "model said this")
        self.assertNotIn("error", record)
        self.assertEqual(files[0].name, "2026-09-07-000000.json")

    def test_direct_call_records_error_not_raw_output(self):
        wake.log_prompt_exchange(
            {"log_prompts": True}, "2026-09-07-FAILED-000000.md",
            "sys", "user", error=RuntimeError("503 model overloaded"),
        )
        files = self._prompt_files()
        self.assertEqual(len(files), 1)
        record = json.loads(files[0].read_text())
        self.assertIn("RuntimeError", record["error"])
        self.assertIn("503 model overloaded", record["error"])
        self.assertNotIn("raw_output", record)

    def test_disabled_writes_nothing(self):
        wake.log_prompt_exchange(
            {"log_prompts": False}, "2026-09-07-000000.md",
            "sys", "user", raw_output="should never be written",
        )
        self.assertEqual(self._prompt_files(), [])

    def test_defaults_on_when_key_absent(self):
        wake.log_prompt_exchange(
            {}, "2026-09-07-000000.md", "sys", "user", raw_output="x",
        )
        self.assertEqual(len(self._prompt_files()), 1)

    def test_end_to_end_successful_wake_logs_full_exchange(self):
        wake.load_config = lambda: self._base_config()
        wake._run_wake()
        files = self._prompt_files()
        self.assertEqual(len(files), 1, files)
        record = json.loads(files[0].read_text())
        self.assertIn("IDENTITY", record["system_prompt"])
        self.assertIn("new wake cycle", record["user_prompt"])
        self.assertIn("mock reflection for testing", record["raw_output"])
        # The logged filename should match the journal entry this same
        # wake actually produced, so the two can be correlated by name.
        journal_files = list((self.memory / "core_workspace" / "journal").glob("*.md"))
        self.assertEqual(len(journal_files), 1)
        self.assertEqual(files[0].stem, journal_files[0].stem)

    def test_end_to_end_disabled_produces_no_prompt_log(self):
        wake.load_config = lambda: self._base_config(log_prompts=False)
        wake._run_wake()
        self.assertEqual(self._prompt_files(), [])
        # The wake itself should still have run normally.
        journal_files = list((self.memory / "core_workspace" / "journal").glob("*.md"))
        self.assertEqual(len(journal_files), 1)

    def test_end_to_end_failed_generate_still_logs_prompt_with_error(self):
        wake.load_config = lambda: self._base_config()

        def boom(*args, **kwargs):
            raise RuntimeError("simulated provider failure")

        orig_retry = wake.generate_with_retry
        wake.generate_with_retry = boom
        self.addCleanup(setattr, wake, "generate_with_retry", orig_retry)

        rc = wake._run_wake()
        self.assertEqual(rc, 1)

        files = self._prompt_files()
        self.assertEqual(len(files), 1, files)
        record = json.loads(files[0].read_text())
        self.assertIn("simulated provider failure", record["error"])
        self.assertNotIn("raw_output", record)
        self.assertIn("IDENTITY", record["system_prompt"])


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


    def test_hypothesis_scope_is_persisted_and_invalid_scope_is_rejected(self):
        bad = json.dumps({"add": [{"prediction": "This should produce a checkable result outside the scaffold",
                                    "test_method": "compare the result with an independent task outcome",
                                    "scope": "sideways"}]})
        notes = wake.apply_hypotheses_update(bad, FIXED_NOW)
        self.assertTrue(any("scope must be internal or external" in n for n in notes))
        data = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())
        self.assertEqual(data["hypotheses"], [])

        good = json.dumps({"add": [{"prediction": "This should produce a checkable result outside the scaffold",
                                     "test_method": "compare the result with an independent task outcome",
                                     "scope": "external"}]})
        wake.apply_hypotheses_update(good, FIXED_NOW)
        data = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())
        self.assertEqual(data["hypotheses"][0]["scope"], "external")

    def test_hypothesis_format_marks_scope(self):
        data = {"hypotheses": [{"id": "h-ext", "status": "untested",
                                 "scope": "external", "prediction": "A checkable external result will occur",
                                 "test_method": "compare against an independent task"}]}
        (self.memory / "core_memories" / "hypotheses.json").write_text(json.dumps(data))
        formatted = wake.format_hypotheses_for_prompt()
        self.assertIn("(external validation)", formatted)

    def test_resolved_hypothesis_status_is_immutable(self):
        # Regression test: a resolved hypothesis's status must never be
        # rewritten by a later status_change block. The only sanctioned
        # path for a changed claim is 'revise', which creates a new,
        # separately-tracked hypothesis linked back to the original —
        # the original's resolved outcome must stay historically final.
        data = {"hypotheses": [{
            "id": "h-test-0", "status": "confirmed",
            "prediction": "X is true", "test_method": "ran it",
            "scope": "internal", "boundary": "same_wake",
            "history": [{"date": "earlier", "status": "confirmed",
                         "evidence": "real evidence", "conclusion": "X held"}],
        }]}
        (self.memory / "core_memories" / "hypotheses.json").write_text(json.dumps(data))

        notes = wake.apply_hypotheses_update(json.dumps({
            "status_change": [{"id": "h-test-0", "new_status": "refuted",
                                "evidence": "changed my mind",
                                "conclusion": "actually false"}]
        }), FIXED_NOW)

        self.assertTrue(any("already resolved" in n for n in notes), notes)
        hyps = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())["hypotheses"]
        self.assertEqual(hyps[0]["status"], "confirmed")
        self.assertEqual(len(hyps[0]["history"]), 1)


class SameWakeDevelopmentTests(WakeTestCase):
    def test_failed_tool_can_be_revised_and_rerun_within_same_wake(self):
        journal = "2026-08-31-090000.md"
        wake.TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        wake.TOOL_RUNS_FILE.write_text(json.dumps({"runs": []}) + "\n")

        wake.apply_tool_write(
            json.dumps({"files": [{"filename": "dev_tool.py", "content": "raise SystemExit(1)\n"}]}),
            FIXED_NOW, journal,
        )
        first_notes = wake.apply_tool_run(
            json.dumps({"filename": "dev_tool.py", "args": []}), FIXED_NOW, journal,
        )
        self.assertIn("exit code 1", first_notes[0])

        failed = wake.unresolved_failed_tool_runs_for_journal(journal)
        self.assertEqual(len(failed), 1)
        system_prompt, user_prompt = wake.build_development_followup_prompt(
            "initial response", failed, FIXED_NOW, iteration=1
        )
        self.assertIn("same-wake development follow-up", system_prompt)
        self.assertIn('"exit_code": 1', user_prompt)
        self.assertIn("raise SystemExit(1)", user_prompt)

        revised_output = (
            "The failure is explained by the tool exiting immediately.\n\n"
            "```tool-write\n"
            + json.dumps({"files": [{"filename": "dev_tool.py", "content": "print('fixed')\n"}]})
            + "\n```\n\n```tool-run\n"
            + json.dumps({"filename": "dev_tool.py", "args": []})
            + "\n```"
        )
        notes, writes, runs = wake.apply_development_output(
            revised_output, FIXED_NOW, journal, remaining_writes=3, remaining_runs=4,
        )

        self.assertEqual(writes, 1)
        self.assertEqual(runs, 1)
        self.assertTrue(any("exit code 0" in note for note in notes))
        self.assertEqual(wake.unresolved_failed_tool_runs_for_journal(journal), [])

        runs_for_wake = wake.tool_runs_for_journal(journal)
        self.assertEqual(len(runs_for_wake), 2)
        self.assertEqual(runs_for_wake[0]["exit_code"], 1)
        self.assertEqual(runs_for_wake[1]["exit_code"], 0)
        self.assertEqual(runs_for_wake[0]["phase"], "work")
        self.assertNotIn("development_iteration", runs_for_wake[0])
        self.assertEqual(runs_for_wake[1]["phase"], "development")
        self.assertEqual(runs_for_wake[1]["development_iteration"], 1)

    def test_tool_run_records_hypothesis_id(self):
        journal = "2026-08-31-100000.md"
        wake.TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        wake.TOOL_RUNS_FILE.write_text(json.dumps({"runs": []}) + "\n")
        wake.apply_tool_write(
            json.dumps({"files": [{"filename": "linked.py", "content": "print('ok')\n"}]}),
            FIXED_NOW, journal,
        )
        notes = wake.apply_tool_run(
            json.dumps({"filename": "linked.py", "args": [], "hypothesis_id": "h-test-1"}),
            FIXED_NOW, journal,
            phase="development", development_iteration=2,
        )
        self.assertIn("exit code 0", notes[0])
        run = wake.tool_runs_for_journal(journal)[0]
        self.assertEqual(run["hypothesis_id"], "h-test-1")
        self.assertEqual(run["phase"], "development")
        self.assertEqual(run["development_iteration"], 2)

    def test_development_execution_budget_is_enforced(self):
        output = "```tool-run\n" + json.dumps({"filename": "missing.py", "args": []}) + "\n```"
        notes, writes, runs = wake.apply_development_output(
            output, FIXED_NOW, "budget.md", remaining_writes=0, remaining_runs=0,
        )
        self.assertEqual((writes, runs), (0, 0))
        self.assertTrue(any("budget exhausted" in note for note in notes))

    def test_prompt_log_exchange_label_keeps_multiple_same_wake_calls(self):
        wake.log_prompt_exchange(
            {}, "2026-08-31-090000.md", "system 1", "user 1", raw_output="out 1",
            exchange_label="development-1",
        )
        wake.log_prompt_exchange(
            {}, "2026-08-31-090000.md", "system 2", "user 2", raw_output="out 2",
            exchange_label="development-2",
        )
        first = wake.PROMPTS_DIR / "2026-08-31-090000-development-1.json"
        second = wake.PROMPTS_DIR / "2026-08-31-090000-development-2.json"
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())
        self.assertEqual(json.loads(first.read_text())["raw_output"], "out 1")
        self.assertEqual(json.loads(second.read_text())["raw_output"], "out 2")


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
        (self.memory / "core_workspace" / "journal" / "2026-08-31-060000.md").write_text("x")
        (self.memory / "core_workspace" / "journal" / "2026-08-31-090000.md").write_text("x")
        # Earlier today but failed — should not count.
        (self.memory / "core_workspace" / "journal" / "2026-08-31-070000-FAILED.md").write_text("x")
        # Successful, but the previous calendar day — should not count.
        (self.memory / "core_workspace" / "journal" / "2026-08-30-235900.md").write_text("x")

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
        (self.memory / "core_workspace" / "journal" / "2026-08-31-060000.md").write_text("x")
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

    def test_next_wake_boundary_is_persisted_and_shown(self):
        block = json.dumps({"add": [{
            "prediction": "a lesson will survive into the next wake",
            "test_method": "resolve it only after the next wake",
            "scope": "external",
            "boundary": "next_wake",
        }]})
        wake.apply_hypotheses_update(block, FIXED_NOW)
        data = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())
        hyp = data["hypotheses"][-1]
        self.assertEqual(hyp["boundary"], "next_wake")
        formatted = wake.format_hypotheses_for_prompt()
        self.assertIn("next_wake boundary", formatted)

    def test_next_wake_boundary_cannot_resolve_in_same_wake(self):
        block = json.dumps({"add": [{
            "prediction": "a claim will be testable after another wake",
            "test_method": "observe the next wake's behavior",
            "boundary": "next_wake",
        }]})
        wake.apply_hypotheses_update(block, FIXED_NOW)
        hyp = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())["hypotheses"][-1]
        notes = wake.apply_hypotheses_update(json.dumps({"status_change": [{
            "id": hyp["id"], "new_status": "confirmed",
            "evidence": "observed result", "conclusion": "confirmed",
        }]}), FIXED_NOW)
        self.assertIn("requires a later wake", " ".join(notes))
        data = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())
        self.assertEqual(data["hypotheses"][-1]["status"], "untested")

    def test_next_wake_boundary_can_resolve_on_later_wake(self):
        block = json.dumps({"add": [{
            "prediction": "a claim will remain useful across a wake boundary",
            "test_method": "check the persisted lesson on the next wake",
            "boundary": "next_wake",
        }]})
        wake.apply_hypotheses_update(block, FIXED_NOW)
        hyp = json.loads((self.memory / "core_memories" / "hypotheses.json").read_text())["hypotheses"][-1]
        later = FIXED_NOW.replace(second=1)
        notes = wake.apply_hypotheses_update(json.dumps({"status_change": [{
            "id": hyp["id"], "new_status": "confirmed",
            "evidence": "the persisted lesson was observed", "conclusion": "survived",
        }]}), later)
        self.assertIn(f"UPDATED hypothesis {hyp['id']} -> confirmed", notes)

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
        self._orig_layout = wake.MEMORY_LAYOUT.copy()
        wake.ROOT = self.tmproot
        wake.MEMORY = self.tmproot / "memory"
        wake.JOURNAL = wake.MEMORY / "core_workspace" / "journal"
        wake.IDENTITIES_FILE = self.tmproot / "IDENTITIES.md"
        wake.IDENTITY_DIR = wake.MEMORY / "core_identity"
        wake.MEMORIES_DIR = wake.MEMORY / "core_memories"
        wake.WORKSPACE_DIR = wake.MEMORY / "core_workspace"
        wake.TOOLS_DIR = wake.WORKSPACE_DIR / "tools"
        wake.TOOL_RUNS_FILE = wake.WORKSPACE_DIR / "tool_runs.json"
        wake.PERSONA_DIR = wake.MEMORY / "core_persona"
        wake.BLOG_DIR = wake.PERSONA_DIR / "blog"
        wake.BLOG_HTML_DIR = wake.BLOG_DIR / "html"
        wake.EPISTEMIC_STATE_FILE = wake.MEMORIES_DIR / "epistemic_state.json"
        wake.CORE_MANIFEST_FILE = wake.MEMORY / "core_manifest.json"

    def tearDown(self):
        for name, value in self._orig.items():
            setattr(wake, name, value)
        wake.MEMORY_LAYOUT.clear()
        wake.MEMORY_LAYOUT.update(self._orig_layout)
        shutil.rmtree(self.tmproot, ignore_errors=True)

    def test_bootstrap_adds_active_row_to_identities_file(self):
        wake.bootstrap_identity("Ada", "Test bootstrapping.")
        text = wake.IDENTITIES_FILE.read_text()
        self.assertIn("| Ada | active | `memory/` |", text)

    def test_bootstrap_leaves_journal_dir_git_trackable(self):
        # Regression test: git does not track empty directories. If
        # bootstrap only mkdir()s the journal folder without putting a
        # file in it, the directory vanishes the moment it's committed
        # and pushed, and the next checkout (e.g. a GitHub Actions runner)
        # fails `wake.py validate` with "missing directory:
        # core_workspace/journal" before the first wake ever runs.
        wake.bootstrap_identity("Ada", "Test journal dir survives git.")
        self.assertTrue(wake.JOURNAL.is_dir())
        self.assertTrue(
            any(wake.JOURNAL.iterdir()),
            "journal/ must contain at least one file (e.g. .gitkeep) "
            "so git actually tracks the directory",
        )
        findings = wake.validate_active_memory()
        self.assertFalse(
            any("core_workspace/journal" in f for f in findings),
            f"unexpected journal finding: {findings}",
        )

    def test_archive_rewrites_index_md_self_link_and_marks_archived(self):
        wake.bootstrap_identity("Ada", "Test archiving.")
        old_url = wake.htmlpreview_url("memory/core_persona/blog/html/index.html")
        # Seed index.md with the stale self-link a real identity would have.
        index_path = wake.MEMORIES_DIR / "index.md"
        index_path.write_text(f"## What's been built\n\n[blog]({old_url})\n")

        destination = wake.archive_current_identity("ada_v1")

        new_url = wake.htmlpreview_url("memory_ada_v1/core_persona/blog/html/index.html")
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
            (destination / "core_workspace" / "journal" / "2026-08-31-090000.md").read_text(),
            "original content",
        )
        self.assertEqual((destination / "core_persona" / "blog" / "blog_posts.json").read_text(), original_blog_posts)

    def test_migrate_persona_renames_directory_and_updates_links(self):
        wake.bootstrap_identity("Ada", "Test persona migration.")
        canonical = wake.MEMORY / "core_persona"
        legacy = wake.MEMORY / "core_public_facing_persona"
        shutil.move(canonical, legacy)
        wake.PERSONA_DIR = legacy
        wake.BLOG_DIR = legacy / "blog"
        wake.BLOG_HTML_DIR = legacy / "blog" / "html"
        old_url = wake.htmlpreview_url("memory/core_public_facing_persona/blog/html/index.html")
        new_url = wake.htmlpreview_url("memory/core_persona/blog/html/index.html")
        index_path = wake.MEMORIES_DIR / "index.md"
        index_path.write_text(f"[blog]({old_url})\n")

        destination = wake.migrate_persona_layout()

        self.assertEqual(destination, wake.MEMORY / "core_persona")
        self.assertTrue((destination / "blog" / "blog_posts.json").is_file())
        self.assertFalse((wake.MEMORY / "core_public_facing_persona").exists())
        self.assertIn(new_url, index_path.read_text())
        self.assertNotIn(old_url, index_path.read_text())
        identities_text = wake.IDENTITIES_FILE.read_text()
        self.assertIn(new_url, identities_text)
        self.assertNotIn(old_url, identities_text)
        manifest = json.loads(wake.CORE_MANIFEST_FILE.read_text())
        self.assertEqual(manifest["layout"]["persona"], "core_persona")

    def test_migrate_persona_dry_run_does_not_change_files(self):
        wake.bootstrap_identity("Ada", "Test persona migration preview.")
        canonical = wake.MEMORY / "core_persona"
        legacy = wake.MEMORY / "core_public_facing_persona"
        shutil.move(canonical, legacy)
        wake.PERSONA_DIR = legacy
        wake.BLOG_DIR = legacy / "blog"
        wake.BLOG_HTML_DIR = legacy / "blog" / "html"
        old_url = wake.htmlpreview_url("memory/core_public_facing_persona/blog/html/index.html")
        identities_before = wake.IDENTITIES_FILE.read_text()
        canonical_url = wake.htmlpreview_url("memory/core_persona/blog/html/index.html")
        identities_before = identities_before.replace(canonical_url, old_url)
        wake.IDENTITIES_FILE.write_text(identities_before)

        destination = wake.migrate_persona_layout(dry_run=True)

        self.assertEqual(destination, wake.MEMORY / "core_persona")
        self.assertTrue((wake.MEMORY / "core_public_facing_persona").is_dir())
        self.assertFalse(destination.exists())
        self.assertEqual(wake.IDENTITIES_FILE.read_text(), identities_before)
        self.assertIn(old_url, identities_before)

    def test_migrate_persona_rejects_ambiguous_layout(self):
        wake.bootstrap_identity("Ada", "Test ambiguous persona migration.")
        (wake.MEMORY / "core_public_facing_persona").mkdir()

        with self.assertRaises(RuntimeError):
            wake.migrate_persona_layout()

    def test_development_metrics_are_derived_from_execution_evidence(self):
        journal = "2026-08-31-120000.md"
        wake.TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        wake.TOOL_RUNS_FILE.write_text(json.dumps({"runs": []}) + "\n")
        wake.apply_tool_write(
            json.dumps({"files": [{"filename": "metrics_tool.py", "content": "raise SystemExit(1)\n"}]}),
            FIXED_NOW, journal,
        )
        wake.apply_tool_run(
            json.dumps({"filename": "metrics_tool.py", "args": [], "hypothesis_id": "h-metrics"}),
            FIXED_NOW, journal, phase="development", development_iteration=1,
        )
        wake.apply_tool_write(
            json.dumps({"files": [{"filename": "metrics_tool.py", "content": "print('fixed')\n"}]}),
            FIXED_NOW, journal,
        )
        wake.apply_tool_run(
            json.dumps({"filename": "metrics_tool.py", "args": [], "hypothesis_id": "h-metrics"}),
            FIXED_NOW, journal, phase="development", development_iteration=2,
        )

        metrics = wake.build_development_metrics(
            journal,
            ["DEVELOPMENT iteration 1: OVERWROTE tools/metrics_tool.py"]
        )
        self.assertIn("Development executions:** 2", metrics)
        self.assertIn("Successful executions:** 1", metrics)
        self.assertIn("Failed executions:** 1", metrics)
        self.assertIn("Distinct development targets:** 1", metrics)
        self.assertIn("Recorded development revisions:** 1", metrics)
        self.assertIn("Highest development iteration:** 2", metrics)
        self.assertIn("Same-wake recovery observed:** yes", metrics)
        self.assertIn("do not establish longitudinal learning", metrics)


if __name__ == "__main__":
    unittest.main(verbosity=2)

class DevelopmentCausalTraceTests(WakeTestCase):
    def test_causal_trace_preserves_failure_and_success_and_marks_longitudinal_pending(self):
        journal = "2026-08-31-110000.md"
        wake.TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        wake.TOOL_RUNS_FILE.write_text(json.dumps({"runs": []}) + "\n")
        wake.apply_tool_write(
            json.dumps({"files": [{"filename": "trace_tool.py", "content": "raise SystemExit(1)\n"}]}),
            FIXED_NOW, journal,
        )
        wake.apply_tool_run(
            json.dumps({"filename": "trace_tool.py", "args": [], "hypothesis_id": "h-trace"}),
            FIXED_NOW, journal,
        )
        wake.apply_tool_write(
            json.dumps({"files": [{"filename": "trace_tool.py", "content": "print('fixed')\n"}]}),
            FIXED_NOW, journal,
        )
        wake.apply_tool_run(
            json.dumps({"filename": "trace_tool.py", "args": [], "hypothesis_id": "h-trace"}),
            FIXED_NOW, journal, phase="development", development_iteration=1,
        )

        trace = wake.build_development_causal_trace(journal, ["revised after observed failure"])
        self.assertIn("Result 1", trace)
        self.assertIn("failure (exit 1)", trace)
        self.assertIn("Result 2", trace)
        self.assertIn("success", trace)
        self.assertIn("h-trace", trace)
        self.assertIn("revised after observed failure", trace)
        self.assertIn("Local development result", trace)
        self.assertIn("Longitudinal validation", trace)
