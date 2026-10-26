import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sync_to_mysql as sync_module


class CaptureCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.connection.calls.append((sql, params))

    def fetchone(self):
        return self.connection.fetchone_result


class CaptureConnection:
    def __init__(self, fetchone_result=None):
        self.calls = []
        self.fetchone_result = fetchone_result or {}

    def cursor(self):
        return CaptureCursor(self)


def _find_insert_call(conn):
    """upsert_record 在 INSERT 前会先执行 record_key_exists / business_dup_exists 的
    SELECT，因此 INSERT 不一定是 calls[0]。定位真正的 INSERT 调用。"""
    for sql, params in conn.calls:
        if sql.strip().upper().startswith("INSERT INTO"):
            return sql, params
    raise AssertionError("未捕获到 INSERT 调用")


def sample_record(include_ai_field=True):
    record = {
        "timestamp": "2026-08-31T10:20:30+08:00",
        "date": "2026-08-31",
        "biz_line": "效贷",
        "employee": "测试用户",
        "user_story": "US-001",
        "user_story_code": "US-001",
        "step": "文档整理",
        "step_code": "01",
        "time_saved_hours": 3.0,
        "time_saved_pd": 0.38,
        "total_hours": 3.0,
        "agent_start_time": "2026-08-31T10:18:00+08:00",
        "agent_end_time": "2026-08-31T10:20:30+08:00",
        "agent_duration_minutes": 2.5,
        "remark": "",
    }
    if include_ai_field:
        record["ai_estimated_time_saved_hours"] = 2.5
    return record


class SyncToMysqlV59Tests(unittest.TestCase):
    def test_record_key_is_unchanged_from_v58(self):
        key = sync_module.compute_record_key(sample_record(), "XD")

        self.assertEqual(key, "eb4d7ae359fa0cc8e1904d33911fd229")

    def test_detects_ai_estimate_column(self):
        conn = CaptureConnection({"column_count": 1})

        result = sync_module.table_has_column(
            conn, "agent_time_tracking", "ai_estimated_time_saved_hours"
        )

        self.assertTrue(result)
        sql, params = conn.calls[0]
        self.assertIn("information_schema.COLUMNS", sql)
        self.assertEqual(
            params,
            ("agent_time_tracking", "ai_estimated_time_saved_hours"),
        )

    def test_v59_upsert_includes_ai_estimate(self):
        conn = CaptureConnection()

        sync_module.upsert_record(
            conn,
            "agent_time_tracking",
            sample_record(),
            "效贷",
            "XD",
            include_ai_estimate=True,
        )

        sql, params = _find_insert_call(conn)
        self.assertIn("ai_estimated_time_saved_hours", sql)
        self.assertEqual(params["ai_estimated_time_saved_hours"], 2.5)

    def test_v59_upsert_treats_missing_ai_estimate_as_null(self):
        conn = CaptureConnection()

        sync_module.upsert_record(
            conn,
            "agent_time_tracking",
            sample_record(include_ai_field=False),
            "效贷",
            "XD",
            include_ai_estimate=True,
        )

        _, params = _find_insert_call(conn)
        self.assertIsNone(params["ai_estimated_time_saved_hours"])

    def test_v58_compatibility_upsert_omits_ai_estimate(self):
        conn = CaptureConnection()

        sync_module.upsert_record(
            conn,
            "agent_time_tracking",
            sample_record(),
            "效贷",
            "XD",
            include_ai_estimate=False,
        )

        sql, params = _find_insert_call(conn)
        self.assertNotIn("ai_estimated_time_saved_hours", sql)
        self.assertNotIn("ai_estimated_time_saved_hours", params)
        self.assertEqual(params["time_saved_hours"], 3.0)

    def test_upsert_includes_digital_employee_code(self):
        conn = CaptureConnection()
        record = sample_record()
        record["digital_employee_code"] = "DE-025"

        sync_module.upsert_record(
            conn,
            "agent_time_tracking",
            record,
            "泾渭云",
            "JWY",
            include_digital_employee=True,
        )

        sql, params = _find_insert_call(conn)
        self.assertIn("digital_employee_code", sql)
        self.assertEqual(params["digital_employee_code"], "DE-025")
        # UPDATE 用 COALESCE 保护已回填值，不被空值冲掉
        self.assertIn("COALESCE(NULLIF(VALUES(digital_employee_code)", sql)

    def test_upsert_omits_digital_employee_code_when_disabled(self):
        conn = CaptureConnection()

        sync_module.upsert_record(
            conn,
            "agent_time_tracking",
            sample_record(),
            "效贷",
            "XD",
            include_digital_employee=False,
        )

        sql, params = _find_insert_call(conn)
        self.assertNotIn("digital_employee_code", sql)
        self.assertNotIn("digital_employee_code", params)


if __name__ == "__main__":
    unittest.main()

