"""Exercise publishing against a disposable local Git remote, never GitHub."""

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from wake.engine import Engine
from wake.providers import Fixture
from wake.report import export


class PublishingTests(unittest.TestCase):
    def test_publish_is_isolated_and_repeatable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project, remote = root / "project", root / "remote.git"
            project.mkdir()
            subprocess.run(["git", "init", "--quiet", str(project)], check=True)
            subprocess.run(["git", "init", "--quiet", "--bare", str(remote)], check=True)
            subprocess.run(["git", "-C", str(project), "remote", "add", "origin", str(remote)], check=True)
            (project/"scripts").mkdir()
            shutil.copyfile(Path(__file__).resolve().parents[1]/"scripts/publish.py", project/"scripts/publish.py")
            spec = importlib.util.spec_from_file_location("local_publish_test", project/"scripts/publish.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            engine = Engine(project/"data")
            try:
                engine.run(Fixture())
                export(engine.store, project/"site")
                for name in ("events.md", "events.html", "state.md", "state.html"):
                    self.assertTrue((project/"site"/name).is_file())
                module.publish(project/"site")
                module.publish(project/"site")
                count = subprocess.check_output(["git", "--git-dir", str(remote), "rev-list", "--count", "journal-pages"],text=True).strip()
                self.assertEqual(count, "1")
                engine.run(Fixture())
                export(engine.store, project/"site")
                module.publish(project/"site")
                count = subprocess.check_output(["git", "--git-dir", str(remote), "rev-list", "--count", "journal-pages"],text=True).strip()
                self.assertEqual(count, "2")
                files = subprocess.check_output(["git", "--git-dir", str(remote), "ls-tree", "--name-only", "journal-pages"],text=True).splitlines()
                self.assertEqual(set(files), {
                    ".nojekyll", "index.html", "journal.md",
                    "state.json", "state.md", "state.html",
                    "events.jsonl", "events.md", "events.html",
                    "head.txt",
                })
                self.assertFalse((project/"index.html").exists())
                (project/"site/state.json").write_text('{}')
                with self.assertRaises(SystemExit):
                    module.publish(project/"site")
            finally:
                engine.store.close()


if __name__ == "__main__":
    unittest.main()
