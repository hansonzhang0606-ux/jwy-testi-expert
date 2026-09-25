import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


CORE = Path(__file__).resolve().parents[1] / "packages" / "jwy-requirement-pipeline-core"
MODULE_PATH = CORE / "scripts" / "pipeline_state.py"


def load_pipeline_state():
    spec = importlib.util.spec_from_file_location("pipeline_state", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PipelineTrackingTests(unittest.TestCase):
    def test_completed_step3_variant_is_the_only_eligible_branch(self):
        pipeline = load_pipeline_state()
        with tempfile.TemporaryDirectory() as output:
            pipeline.record_step(output, "step1", ["requirement.docx"])
            pipeline.record_step(output, "step3-2", ["api.xmind"])
            state = json.loads((Path(output) / ".jwy_pipeline_state.json").read_text(encoding="utf-8"))

        self.assertEqual(state["tracking"]["eligible"], ["P1", "P3-2"])
        self.assertNotIn("P2", state["tracking"]["eligible"])
        self.assertNotIn("P3-1", state["tracking"]["eligible"])
        self.assertNotIn("P3-3", state["tracking"]["eligible"])

    def test_step4_remains_blocked_after_direct_dmp_variant(self):
        pipeline = load_pipeline_state()
        with tempfile.TemporaryDirectory() as output:
            pipeline.record_step(output, "step3-3", ["dmp.xmind"])
            result = pipeline.check_step(output, "step4")

        self.assertFalse(result["allowed"])
        self.assertIn("无step4", result["reason"])

