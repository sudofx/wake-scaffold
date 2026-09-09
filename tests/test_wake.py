import runpy
from pathlib import Path

source = (Path(__file__).with_name("test_wake_legacy.py")).read_text(encoding="utf-8")
source = source.replace("ManifestValidatorTests", "VerifyEnvironmentTests")
source = source.replace("_run_validator", "_run_verifier")
source = source.replace("validate_workspace.py", "verify_environment.py")
source = source.replace("manifest_validator_", "manifest_verifier_")
source = source.replace("Path(report[\"detected_root\"]).resolve()", "Path(report[\"memory_root\"]).resolve()")
source = source.replace('report["found"]', 'report["found_files"]')
source = source.replace('"identity/identity.md"', '"identity"')
source = source.replace('"memories/index.md"', '"index"')
source = source.replace('"workspace/tool_runs.json"', '"tool_runs"')
source = source.replace('report["missing"]', 'report["mechanism"]')
source = source.replace('self.assertIn("core_identity/rules.md", report["missing"])', 'self.assertIn("core_identity/rules.md", report["mechanism"])')
source = source.replace('if __name__ == "__main__":\n    unittest.main(verbosity=2)', '')
exec(compile(source, str(Path(__file__).with_name("test_wake_legacy.py")), "exec"), globals(), globals())
