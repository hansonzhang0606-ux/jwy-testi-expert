import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_packages.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_packages", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackageBuildTests(unittest.TestCase):
    def test_build_creates_workbuddy_and_vscode_packages_with_manifest(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as output:
            result = builder.build_packages(ROOT / "packages" / "jwy-requirement-pipeline-core", Path(output))
            workbuddy = Path(result["workbuddy"])
            vscode = Path(result["vscode"])

            plugin = json.loads((workbuddy / ".codebuddy-plugin" / "plugin.json").read_text(encoding="utf-8"))
            self.assertEqual(plugin["name"], "jingweiyun-testing-expert")
            self.assertEqual(plugin["skills"], ["./skills/jwy-testing-expert-skill"])
            self.assertTrue((workbuddy / "skills" / "jwy-testing-expert-skill" / "SKILL.md").is_file())
            self.assertTrue((vscode / "SKILL.md").is_file())
            tracking_config = (vscode / "time-tracking" / "config" / "time_tracking_config.yaml").read_text(encoding="utf-8")
            tracking_prompt = (vscode / "time-tracking" / "prompts" / "time_tracking.md").read_text(encoding="utf-8")
            self.assertIn('default_biz_line: "泾渭云"', tracking_config)
            self.assertIn('step_code: "P3-2"', tracking_config)
            self.assertIn("P3-1/P3-2/P3-3", tracking_prompt)
            self.assertEqual(list((vscode / "modules").rglob("*.pyc")), [])
            self.assertTrue((Path(output) / "MANIFEST.sha256").is_file())

    def test_v2_xmind_quality_tools_are_in_shared_core(self):
        core = ROOT / "packages" / "jwy-requirement-pipeline-core"
        self.assertTrue((core / "skills" / "xmind-testcase" / "scripts" / "lint_brackets.py").is_file())
        self.assertTrue((core / "skills" / "xmind-testcase" / "scripts" / "lint_case_args.py").is_file())
        self.assertTrue((core / "skills" / "xmind-testcase" / "scripts" / "merge_brackets.py").is_file())
        self.assertFalse((core / "skills" / "xmind-testcase" / "_user_meta.json").exists())
