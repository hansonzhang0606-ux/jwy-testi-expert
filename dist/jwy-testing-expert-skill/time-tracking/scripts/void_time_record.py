#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工时记录「软作废」工具 v1.0（通用多业务线版）

背景: 同步账号（如 appuser）通常只有 SELECT/INSERT/UPDATE，没有 DELETE 权限
      （报错 1142: DELETE command denied）。一旦误记录或产生测试数据，无法物理删除。
方案: 软作废 —— 把该条记录的工时字段归零并在 remark 打 [作废] 标记，
      同时把其 record_key 写入本机作废名单 voided.json；
      sync_to_mysql.py 同步时会跳过作废名单中的 record_key，避免被重新 upsert "复活"。

用法:
  # 按数据库主键作废（最精确，推荐）
  python void_time_record.py --id 3245 --reason "E2E 测试数据"
  # 按幂等键作废
  python void_time_record.py --record-key 0bbe0578... --reason "录错了"
  # 按业务字段作废（须唯一命中，否则报错要求加条件）
  python void_time_record.py --employee 张云星 --user-story PRJ-00772768 --step-code P5
  # 试运行，只看不写
  python void_time_record.py --id 3245 --dry-run

副作用: 若该记录在本地 records.jsonl 中仍存在，会一并从本地移除（--keep-local 可保留）。
"""

import argparse
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(os.path.join(SCRIPT_DIR, "pymysql")):
    sys.path.insert(0, SCRIPT_DIR)

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("ERROR: pymysql 未打包进脚本目录。请确认 scripts/pymysql/ 存在。", file=sys.stderr)
    sys.exit(1)

from biz_line_helper import resolve_biz_line, BIZ_LINE_CODE_MAP
from sync_to_mysql import (
    get_data_dir,
    load_mysql_config,
    get_connection,
    compute_record_key,
)

VOID_PREFIX = "[作废]"


def voided_path(biz_line):
    return os.path.join(get_data_dir(biz_line), "voided.json")


def load_voided(biz_line):
    p = voided_path(biz_line)
    if not os.path.exists(p):
        return {"voided": []}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "voided" not in data:
            return {"voided": []}
        return data
    except Exception:
        return {"voided": []}


def save_voided(biz_line, data):
    p = voided_path(biz_line)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def locate(conn, table, biz_line_code, args):
    """按 id / record_key / 业务字段定位待作废记录；返回 (rows, used_desc)"""
    if args.id:
        sql = f"SELECT id, record_key, employee, user_story_code, step_code, time_saved_hours, remark " \
              f"FROM {table} WHERE id=%s"
        params = (args.id,)
        desc = f"id={args.id}"
    elif args.record_key:
        sql = f"SELECT id, record_key, employee, user_story_code, step_code, time_saved_hours, remark " \
              f"FROM {table} WHERE record_key=%s"
        params = (args.record_key,)
        desc = f"record_key={args.record_key}"
    elif args.employee and args.user_story and args.step_code:
        sql = f"SELECT id, record_key, employee, user_story_code, step_code, time_saved_hours, remark " \
              f"FROM {table} WHERE biz_line_code=%s AND employee=%s AND user_story_code=%s AND step_code=%s"
        params = (biz_line_code, args.employee, args.user_story, args.step_code)
        desc = f"{args.employee}/{args.user_story}/{args.step_code}"
    else:
        print("ERROR: 请指定定位条件之一：--id 或 --record-key "
              "或 (--employee + --user-story + --step-code)", file=sys.stderr)
        sys.exit(1)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return rows, desc


def remove_from_local(biz_line, record_key):
    """从本地 records.jsonl 移除该 record_key 对应记录（若存在）"""
    jsonl = os.path.join(get_data_dir(biz_line), "records.jsonl")
    if not os.path.exists(jsonl):
        return 0
    with open(jsonl, "r", encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    kept, removed = [], 0
    biz_code = BIZ_LINE_CODE_MAP.get(biz_line, "")
    for l in lines:
        try:
            rec = json.loads(l)
        except json.JSONDecodeError:
            kept.append(l)
            continue
        if compute_record_key(rec, biz_code) == record_key:
            removed += 1
            continue
        kept.append(l)
    if removed:
        with open(jsonl, "w", encoding="utf-8") as f:
            f.write("\n".join(kept) + ("\n" if kept else ""))
    return removed


def main():
    parser = argparse.ArgumentParser(description="工时记录软作废（无 DELETE 权限时的替代方案）")
    parser.add_argument("--biz-line", default="", help="业务线（未指定时读取 config 中 default_biz_line）")
    parser.add_argument("--id", type=int, default=0, help="数据库主键 id（最精确）")
    parser.add_argument("--record-key", default="", help="幂等键 record_key（32 位）")
    parser.add_argument("--employee", default="", help="员工姓名（与 --user-story --step-code 组合定位）")
    parser.add_argument("--user-story", default="", help="用户故事编号，如 PRJ-00772768")
    parser.add_argument("--step-code", default="", help="步骤代码，如 P5")
    parser.add_argument("--reason", default="", help="作废原因，写入 remark 与作废名单")
    parser.add_argument("--keep-local", action="store_true", help="保留本地 records.jsonl 中的该条记录")
    parser.add_argument("--dry-run", action="store_true", help="试运行，只看不写")
    args = parser.parse_args()

    biz_line = resolve_biz_line(args.biz_line)
    biz_line_code = BIZ_LINE_CODE_MAP.get(biz_line, "")
    cfg = load_mysql_config(biz_line)
    table = cfg.get("table", "agent_time_tracking")

    conn = get_connection(cfg)
    rows, desc = locate(conn, table, biz_line_code, args)

    print("=" * 62)
    print(f"工时记录软作废 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)
    print(f"业务线: {biz_line} ({biz_line_code})   定位条件: {desc}")

    if not rows:
        print("⚠️  未匹配到任何记录，无需作废。")
        conn.close()
        return
    if len(rows) > 1:
        print(f"⚠️  匹配到 {len(rows)} 条记录，条件不唯一。请改用 --id 精确指定：")
        for r in rows:
            print(f"   id={r['id']} | {r['employee']} | {r['user_story_code']} | "
                  f"{r['step_code']} | {r['time_saved_hours']}h")
        conn.close()
        sys.exit(1)

    row = rows[0]
    already = str(row.get("remark") or "").startswith(VOID_PREFIX)
    print(f"\n命中记录:")
    print(f"   id={row['id']} | {row['employee']} | {row['user_story_code']} | "
          f"{row['step_code']} | {row['time_saved_hours']}h")
    print(f"   record_key = {row['record_key']}")
    print(f"   原 remark  = {row.get('remark') or '(空)'}")
    if already:
        print("   ℹ️  该记录已是作废状态。")

    if args.dry_run:
        print(f"\n🔍 试运行 — 将执行:")
        print(f"   1) MySQL: UPDATE {table} SET time_saved_hours=0, time_saved_pd=0, "
              f"total_hours=0, remark='{VOID_PREFIX}...' WHERE id={row['id']}")
        print(f"   2) 本机作废名单: {voided_path(biz_line)}")
        if not args.keep_local:
            print(f"   3) 从本地 records.jsonl 移除该条（--keep-local 可保留）")
        print("   （未实际写入）")
        conn.close()
        return

    # 1) 远端软作废
    reason = args.reason or "未注明原因"
    old_remark = row.get("remark") or ""
    base = old_remark[len(VOID_PREFIX):] if already else old_remark
    new_remark = f"{VOID_PREFIX}{reason}｜原:{base}" if base else f"{VOID_PREFIX}{reason}"
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {table} SET time_saved_hours=0, time_saved_pd=0, total_hours=0, "
            f"remark=%s WHERE id=%s",
            (new_remark, row["id"]),
        )
    conn.commit()

    # 2) 写入本机作废名单（sync 时跳过，防止复活）
    data = load_voided(biz_line)
    keys = {v.get("record_key") for v in data["voided"]}
    if row["record_key"] not in keys:
        data["voided"].append({
            "record_key": row["record_key"],
            "id": row["id"],
            "employee": row["employee"],
            "user_story_code": row["user_story_code"],
            "step_code": row["step_code"],
            "reason": reason,
            "voided_at": datetime.now().isoformat(timespec="seconds"),
        })
        save_voided(biz_line, data)

    # 3) 本地 records.jsonl 移除
    removed = 0 if args.keep_local else remove_from_local(biz_line, row["record_key"])

    # 回读校验
    with conn.cursor() as cur:
        cur.execute(f"SELECT time_saved_hours, total_hours, remark FROM {table} WHERE id=%s", (row["id"],))
        after = cur.fetchone()
    conn.close()

    print(f"\n✅ 已软作废: id={row['id']}")
    print(f"   工时归零: time_saved_hours={after['time_saved_hours']} / total_hours={after['total_hours']}")
    print(f"   新 remark: {after['remark']}")
    print(f"   作废名单: {voided_path(biz_line)}（共 {len(data['voided'])} 条）")
    print(f"   本地 JSONL 移除: {removed} 条")
    print("\n说明: 该行仍物理存在于表中（账号无 DELETE 权限），但工时为 0，不影响统计汇总；")
    print("      后续同步会跳过该 record_key，不会被重新写回。如需物理删除请联系数据库管理员。")


if __name__ == "__main__":
    main()
