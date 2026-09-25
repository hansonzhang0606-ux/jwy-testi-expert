import importlib.util
import tempfile
import unittest
from pathlib import Path


CORE = Path(__file__).resolve().parents[1] / "packages" / "jwy-requirement-pipeline-core"
MODULE_PATH = CORE / "scripts" / "jwy_tracking.py"


def load_tracking():
    spec = importlib.util.spec_from_file_location("jwy_tracking", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JwyTrackingTests(unittest.TestCase):
    def test_only_completed_pipeline_steps_are_missing(self):
        tracking = load_tracking()
        state = {"tracking": {"eligible": ["P1", "P3-2", "P5"]}}

        self.assertEqual(tracking.missing_tracking_ids(state, {"P1"}), ["P3-2", "P5"])

    def test_pipeline_branch_metadata_is_preserved_in_record(self):
        tracking = load_tracking()
        record = tracking.build_record("P3-2", "接口脑图", 4.5)

        self.assertEqual(record["tracking_id"], "P3-2")
        self.assertEqual(record["pipeline_step"], "step3-2")
        self.assertEqual(record["step"], "接口脑图")

