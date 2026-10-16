"""用户故事完整性校验（v1.2.0）——编号 + 故事名称缺一不可。"""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


CORE = Path(__file__).resolve().parents[1] / "packages" / "jwy-requirement-pipeline-core"
SCRIPTS = CORE / "time-tracking" / "scripts"
MODULE_PATH = SCRIPTS / "record_time_saved.py"


def load_recorder():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("jwy_record_time_saved", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FULL_STORY = "PRJ-00884552-【泾渭云20260915】修改泾渭云使用中台数据库账号"


class UserStoryValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_recorder()

    # —— 校验函数 ——
    def test_complete_story_passes(self):
        ok, code, name, missing = self.module.validate_user_story(FULL_STORY)

        self.assertTrue(ok)
        self.assertEqual(code, "PRJ-00884552")
        self.assertEqual(name, "【泾渭云20260915】修改泾渭云使用中台数据库账号")
        self.assertEqual(missing, "")

    def test_code_only_is_rejected(self):
        ok, _code, _name, missing = self.module.validate_user_story("PRJ-00886813")

        self.assertFalse(ok)
        self.assertEqual(missing, "故事名称")

    def test_story_name_only_is_rejected(self):
        ok, _code, _name, missing = self.module.validate_user_story(
            "【泾渭云20260921】海关缴款书采集优化"
        )

        self.assertFalse(ok)
        self.assertEqual(missing, "编号")

    def test_code_plus_date_tag_only_is_rejected(self):
        ok, _code, _name, missing = self.module.validate_user_story("PRJ-00886813-【泾渭云20260921】")

        self.assertFalse(ok)
        self.assertEqual(missing, "故事名称")

    def test_empty_story_is_rejected(self):
        ok, _code, _name, missing = self.module.validate_user_story("")

        self.assertFalse(ok)
        self.assertEqual(missing, "编号、故事名称")

    def test_reminder_names_the_missing_part_and_shows_template(self):
        reminder = self.module.user_story_reminder("PRJ-00886813")

        self.assertIn("故事名称", reminder)
        self.assertIn(self.module.USER_STORY_FORMAT_EXAMPLE, reminder)

    # —— 记录入口 ——
    def record_to_temp_jsonl(self, user_story, **overrides):
        with tempfile.TemporaryDirectory() as temp_dir:
            records_path = Path(temp_dir) / "records.jsonl"
            kwargs = {
                "employee": "测试用户",
                "user_story": user_story,
                "step": "需求确认",
                "step_code": "P1",
                "hours": 4.0,
                "biz_line": "泾渭云",
                "skip_validation": True,
            }
            kwargs.update(overrides)
            with mock.patch.object(
                self.module, "get_records_path", return_value=str(records_path)
            ), mock.patch.object(self.module, "sync_to_excel_if_configured"):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                    io.StringIO()
                ):
                    result = self.module.record(**kwargs)
            saved = (
                json.loads(records_path.read_text(encoding="utf-8").strip())
                if records_path.exists()
                else None
            )
        return result, saved

    def test_record_rejects_partial_story(self):
        for partial in ("PRJ-00886813", "【泾渭云20260921】海关缴款书采集优化"):
            with self.subTest(partial=partial), self.assertRaises(
                self.module.UserStoryIncompleteError
            ):
                self.record_to_temp_jsonl(partial)

    def test_record_accepts_complete_story_and_keeps_code(self):
        result, saved = self.record_to_temp_jsonl(FULL_STORY)

        self.assertEqual(result["user_story"], FULL_STORY)
        self.assertEqual(saved["user_story"], FULL_STORY)
        self.assertEqual(saved["user_story_code"], "PRJ-00884552")

    def test_escape_hatch_allows_partial_story(self):
        _result, saved = self.record_to_temp_jsonl(
            "PRJ-00886813", allow_partial_user_story=True
        )

        self.assertEqual(saved["user_story"], "PRJ-00886813")

    # —— CLI 契约 ——
    def test_cli_exposes_escape_hatch_flag(self):
        with mock.patch.object(sys, "argv", ["record_time_saved.py", "--help"]):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                with self.assertRaises(SystemExit) as ctx:
                    self.module.main()

        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("--allow-partial-user-story", out.getvalue())

    def test_cli_exits_2_and_reminds_for_partial_story(self):
        argv = [
            "record_time_saved.py",
            "--employee", "测试用户",
            "--user-story", "PRJ-00886813",
            "--step-code", "P1",
            "--hours", "4",
            "--biz-line", "泾渭云",
            "--skip-validation",
        ]
        with mock.patch.object(sys, "argv", argv):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as ctx:
                    self.module.main()

        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("故事名称", err.getvalue())
        self.assertIn(self.module.USER_STORY_FORMAT_EXAMPLE, err.getvalue())


if __name__ == "__main__":
    unittest.main()
