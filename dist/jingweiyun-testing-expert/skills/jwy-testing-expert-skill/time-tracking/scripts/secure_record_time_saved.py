#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
secure_record_time_saved.py — 泾渭云工时追踪「提交即同步」封装 v6.2-JWY

融合方案 A+B：
  A（提交即同步）：调用 record_time_saved.py 在本地 records.jsonl 落盘成功后，
     立即调用 sync_to_mysql.py 把本次及此前所有本地记录同步到 MySQL 的
     agent_time_tracking 表，消除对定时任务的时序依赖。
  B（提示词回补兜底）：若本步骤因 MySQL 不可用 / 未初始化而同步失败，或此前只用
     纯 record_time_saved.py 记录而未同步、或人员忘了触发，可在会话任意时刻由 AI
     驱动运行 sync_to_mysql.py 回补（幂等，详见 prompts/time_tracking.md）。

机制：
  - 身份校验 / 花名册校验仍由 record_time_saved.py 负责（保持单一校验入口）。
  - 本地 records.jsonl 为 source of truth；MySQL 同步失败只告警、不阻断落盘。
  - 同步失败（MySQL 未配置 / 不可达）时打印明确告警，提示稍后由 B 回补。

退出码：
  0  本地记录成功（无论同步是否成功，本地记录已保存）
  1  record_time_saved.py 执行失败（参数错误 / 校验拒绝 / 花名册查询失败致拒绝）
"""

import argparse
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def build_record_command(args: argparse.Namespace) -> list:
    """构造调用 record_time_saved.py 的命令（保持单一校验入口）。"""
    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, "record_time_saved.py"),
        "--employee",
        args.employee.strip(),
        "--user-story",
        args.user_story,
        "--step",
        args.step,
        "--step-code",
        args.step_code,
        "--biz-line",
        args.biz_line,
    ]
    optional = (
        ("--hours", args.hours),
        ("--person-days", args.person_days),
        ("--remark", args.remark),
        ("--agent-start-time", args.agent_start_time),
        ("--agent-end-time", args.agent_end_time),
        ("--agent-duration-minutes", args.agent_duration_minutes),
        ("--ai-estimated-time-saved-hours", args.ai_estimated_time_saved_hours),
    )
    for flag, value in optional:
        if value is not None and value != "":
            cmd.extend((flag, str(value)))
    return cmd


def sync_after_record(biz_line: str) -> int:
    """v6.1 同类机制：本地落盘成功后立即同步到 MySQL，消除定时任务时序盲区。

    同步失败不阻断本地落盘（本地 records.jsonl 是 source of truth），
    但必须明确告警，便于测试人员/AI 感知并走 B 回补。
    """
    sync_script = os.path.join(SCRIPT_DIR, "sync_to_mysql.py")
    if not os.path.isfile(sync_script):
        print("⚠️  未找到 sync_to_mysql.py，跳过自动同步（本地记录已保存）。", file=sys.stderr)
        return 0
    try:
        print("\n🔄 提交即同步：尝试把本机记录同步到 MySQL（agent_time_tracking）...")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run(
            [sys.executable, sync_script, "--biz-line", biz_line],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )
        if r.returncode == 0:
            print("✅ 已自动同步到 MySQL（agent_time_tracking）。")
        else:
            tail = (r.stderr or r.stdout).strip().replace("\n", " ")[:500]
            print(
                f"⚠️  自动同步 MySQL 失败（本地记录已保存，待 B 回补兜底）：{tail}",
                file=sys.stderr,
            )
            print(
                "   回补方式：运行 python sync_to_mysql.py --biz-line 泾渭云 （幂等，可重复执行）",
                file=sys.stderr,
            )
        return r.returncode
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  自动同步异常（本地记录已保存，待 B 回补）：{e}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="泾渭云节省工时记录 + 提交即同步（v6.2-JWY）"
    )
    parser.add_argument("--employee", required=True, help="员工姓名（需在花名册中）")
    parser.add_argument("--user-story", required=True, help="用户故事名称/编号（如 PRJ-xxxxxxx）")
    parser.add_argument("--step", default="", help="步骤名称（如：需求确认）")
    parser.add_argument("--step-code", default="", help="步骤代码（P1/P2/P3-1/P3-2/P3-3/P4/P5）")
    parser.add_argument(
        "--hours", type=float, default=None, help="节省时间（小时）"
    )
    parser.add_argument(
        "--person-days", type=float, default=None, help="节省时间（人天）"
    )
    parser.add_argument(
        "--biz-line", default="", help="业务线（未指定时读取 config 中 default_biz_line，默认 泾渭云）"
    )
    parser.add_argument("--remark", default="", help="备注")
    parser.add_argument("--agent-start-time", default="", help="智能体开始处理本步骤的 ISO 时间戳")
    parser.add_argument("--agent-end-time", default="", help="智能体完成本步骤的 ISO 时间戳")
    parser.add_argument("--agent-duration-minutes", type=float, default=None, help="智能体实际执行耗时（分钟）")
    parser.add_argument(
        "--ai-estimated-time-saved-hours",
        type=float,
        default=None,
        help="AI 预估本环节可节省时间（小时，独立于人员反馈）",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="调试用：仅记录本地、不同步 MySQL",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.hours is None and args.person_days is None:
        print("错误：必须指定 --hours 或 --person-days", file=sys.stderr)
        return 1

    # 先本地落盘（含花名册校验）
    rec = subprocess.run(build_record_command(args), check=False)
    if rec.returncode != 0:
        return rec.returncode

    if args.no_sync:
        print("ℹ️  已按 --no-sync 跳过 MySQL 同步（仅本地记录）。")
        return 0

    # A：提交即同步
    sync_after_record(args.biz_line or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
