import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import wake


class WakeEnvironmentTests(unittest.TestCase):
    def test_template_does_not_require_runtime_tools_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for subdir, name in wake.TEMPLATE_FILES:
                path = base / subdir / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if name.endswith(".json"):
                    path.write_text("{}" if name == "blog_posts.json" else "{}", encoding="utf-8")
                else:
                    path.write_text("", encoding="utf-8")
            (base / "core_synthesis").mkdir()
            with patch.object(wake, "BASE_MEMORY", base):
                wake.verify_template()

    def test_validate_active_memory_does_not_require_tools_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = Path(tmp)
            files = {
                "core_identity/identity.md": "**Name:** Bob\n",
                "core_identity/rules.md": "",
                "core_identity/failure_modes.md": "",
                "core_memories/index.md": "",
                "core_memories/commitments.json": '{"commitments": []}',
                "core_memories/growth_plan.json": '{"projects": []}',
                "core_memories/hypotheses.json": '{"hypotheses": []}',
                "core_memories/semantic_memory.json": '{"memories": []}',
                "core_workspace/tool_runs.json": '{"runs": []}',
                "core_persona/blog/blog_posts.json": '{"posts": []}',
                "core_persona/blog/html/index.html": "<html></html>",
            }
            for rel, content in files.items():
                p = memory / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
            (memory / "core_workspace/journal").mkdir()
            (memory / "core_synthesis").mkdir()
            (memory / "core_manifest.json").write_text(json.dumps({
                "schema_version": 1,
                "identity_name": "Bob",
                "layout": {
                    "identity": "core_identity",
                    "memories": "core_memories",
                    "workspace": "core_workspace",
                    "synthesis": "core_synthesis",
                    "persona": "core_persona",
                    "journal": "core_workspace/journal",
                    "prompts": "core_workspace/prompts",
                },
                "last_wake": "",
                "total_wakes": 0,
            }), encoding="utf-8")
            patches = {
                "MEMORY": memory,
                "IDENTITY_DIR": memory / "core_identity",
                "MEMORIES_DIR": memory / "core_memories",
                "WORKSPACE_DIR": memory / "core_workspace",
                "TOOLS_DIR": memory / "core_workspace" / "tools",
                "SYNTHESIS_DIR": memory / "core_synthesis",
                "PERSONA_DIR": memory / "core_persona",
                "BLOG_DIR": memory / "core_persona/blog",
                "BLOG_HTML_DIR": memory / "core_persona/blog/html",
                "JOURNAL": memory / "core_workspace/journal",
                "CORE_MANIFEST_FILE": memory / "core_manifest.json",
            }
            with patch.multiple(wake, **patches):
                self.assertEqual(wake.validate_active_memory(), [])

    def test_tool_write_creates_runtime_tools_lazily(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp) / "tools"
            with patch.object(wake, "TOOLS_DIR", tools):
                result = wake.apply_tool_write(
                    json.dumps({"files": [{"filename": "hello.py", "content": "print('hello')"}]}),
                    wake.now_local(),
                    "wake-test.md",
                )
            self.assertTrue((tools / "hello.py").is_file())
            self.assertTrue(any("WROTE tools/hello.py" in item for item in result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
