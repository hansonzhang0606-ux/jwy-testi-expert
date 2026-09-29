#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
register_sync_tasks.py — 自动注册 time-tracking 定时同步任务（自定位 / 幂等）

设计目标（v5.8 引入，修复 v5.3 的「占位符路径不可靠」问题）：
  让「任何测试人员 / 任何机器」在首次使用内嵌本 skill 的测试专家时，
  AI 只需运行一句命令即可在本机「任务计划程序」自动建好
  09:00 / 12:00 / 18:00 三个每日任务，无需人工打开 CMD、无需模型填写绝对路径。

关键特性：
  - 自定位：用 __file__ 推断 scripts 目录，找到同目录的 sync_task.bat，
            不需要任何路径参数，彻底消除跨机器路径不确定性。
  - 幂等：已注册的任务自动跳过（不重复创建、不报错）。
  - 自愈：已注册任务会校验 /tr 指向的 bat 是否与当前期望路径一致；
          专家包版本升级或 cache 被清理导致路径漂移时，自动用 /f 重建，
          避免任务「显示就绪但永远执行失败」的假死状态。
  - 多业务线：任务名带业务线前缀，不同业务线互不冲突。
  - 失败友好：注册失败打印明确原因与手动命令，不阻塞 AI 其余流程。
  - 时机无关：业务线一确定即可调用，不要求 MySQL 配置已填写。
"""
import argparse
import os
import re
import subprocess
import sys

# 早 / 午 / 晚 三个触发时间点
SCHEDULES = [
    ("早", "09:00"),
    ("午", "12:00"),
    ("晚", "18:00"),
]


def resolve_persistent_bat_path(current_bat_path):
    """优先使用持久安装路径（plugins/marketplaces/my-experts/plugins/...），避免 cache/1.0.0 版本升级后任务失效。

    当脚本在 cache 中运行时（如 WorkBuddy 解压的 1.0.0 缓存），尝试推断并切换到
    my-experts 持久安装路径；若持久路径不存在或当前已在持久路径，则返回当前路径。
    """
    norm = os.path.normpath(current_bat_path)
    if "marketplaces" + os.sep + "my-experts" + os.sep + "plugins" in norm:
        return norm
    # 匹配 plugins\cache\my-experts\<expert-id>\<version>\<remainder>
    m = re.search(
        r"plugins" + re.escape(os.sep) + r"cache" + re.escape(os.sep) + r"my-experts" + re.escape(os.sep) + r"([^" + re.escape(os.sep) + r"]+)" + re.escape(os.sep) + r"([^" + re.escape(os.sep) + r"]+)" + re.escape(os.sep) + r"(.*)$",
        norm,
    )
    if not m:
        return norm
    expert_id, _version, remainder = m.groups()
    home = os.path.expanduser("~")
    candidate = os.path.join(
        home, ".workbuddy", "plugins", "marketplaces", "my-experts", "plugins", expert_id, remainder
    )
    if os.path.isfile(candidate):
        return candidate
    return norm


def run(cmd):
    """执行命令，返回 (returncode, stdout, stderr)。schtasks 输出为 GBK，按 gbk 解码。"""
    try:
        p = subprocess.run(
            cmd, shell=True, capture_output=True,
            encoding="gbk", errors="ignore", timeout=60,
        )
        return p.returncode, p.stdout, p.stderr
    except Exception as e:  # noqa: BLE001
        return -1, "", str(e)


def task_exists(task_name):
    rc, _out, _err = run('schtasks /query /tn "%s"' % task_name)
    return rc == 0


def get_task_command(task_name):
    """读取已注册任务的 /tr 命令行；不存在或解析失败返回 None。

    用于检测「路径漂移」：任务指向的 bat 已随 cache 版本升级/清理而消失时，
    任务仍显示"就绪"却永远不会成功执行（假死），必须比对后重建。
    """
    rc, out, _err = run('schtasks /query /tn "%s" /fo list /v' % task_name)
    if rc != 0:
        return None
    for line in out.splitlines():
        if "要运行的任务" in line or "Task To Run" in line:
            parts = line.split(":", 1)
            return parts[1].strip() if len(parts) == 2 else ""
    return None


def create_task(task_name, bat_path, biz_line, hhmm):
    """（重）创建一个每日任务；/f 表示已存在时直接覆盖。返回 (rc, err)。"""
    # /tr 值整体用外层双引号包裹；bat 路径内含空格需自带 \" 转义，末尾传业务线参数
    tr_value = '"\\"%s\\" %s"' % (bat_path, biz_line)
    cmd = (
        'schtasks /create /tn "%s" /tr %s /sc daily /st %s /f'
        % (task_name, tr_value, hhmm)
    )
    rc, _out, err = run(cmd)
    return rc, err


def register_one(bat_path, biz_line, label, hhmm, force=False):
    """注册单个任务。已存在时校验 /tr 是否仍指向期望 bat，漂移则自动重建（自愈）。"""
    task_name = "%s时间同步-%s" % (biz_line, label)
    if task_exists(task_name):
        current = get_task_command(task_name)
        if current is not None and bat_path in current and not force:
            return task_name, "已存在(路径正确,跳过)"
        rc, err = create_task(task_name, bat_path, biz_line, hhmm)
        if rc == 0:
            return task_name, "已修复路径漂移(%s)" % hhmm
        return task_name, "重建失败(rc=%d) %s" % (rc, err.strip()[:160])
    rc, err = create_task(task_name, bat_path, biz_line, hhmm)
    if rc == 0:
        return task_name, "已创建(%s)" % hhmm
    return task_name, "失败(rc=%d) %s" % (rc, err.strip()[:160])


def main():
    ap = argparse.ArgumentParser(description="注册 time-tracking 定时同步任务（自定位/幂等）")
    ap.add_argument("--biz-line", required=True, help="业务线名称，如 效贷")
    ap.add_argument("--dry-run", action="store_true", help="只检查与打印，不真正创建")
    ap.add_argument("--force", action="store_true",
                    help="即使任务已存在且路径正确，也强制重建（用于手工重置）")
    args = ap.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    bat_path = resolve_persistent_bat_path(os.path.join(script_dir, "sync_task.bat"))
    if not os.path.isfile(bat_path):
        print("[ERROR] 未找到同目录的 sync_task.bat：%s" % bat_path)
        print("        请确认 register_sync_tasks.py 与 sync_task.bat 处于同一 scripts 目录。")
        return 2

    print("[INFO] scripts 目录: %s" % script_dir)
    print("[INFO] 目标 bat    : %s" % bat_path)
    if bat_path != os.path.join(script_dir, "sync_task.bat"):
        print("[INFO] 已切换至持久安装路径，避免 cache 版本升级后任务失效。")
    print("[INFO] 业务线      : %s" % args.biz_line)
    print("[INFO] 计划注册 3 个每日任务(09:00/12:00/18:00)")
    print("[INFO] 已存在任务会校验 bat 路径，漂移时自动重建（防升级后假死）\n")

    if args.dry_run:
        for label, hhmm in SCHEDULES:
            name = "%s时间同步-%s" % (args.biz_line, label)
            if not task_exists(name):
                state = "将创建@" + hhmm
            else:
                cur = get_task_command(name) or ""
                state = ("已存在(路径正确)" if bat_path in cur
                         else "将修复路径漂移 -> %s" % bat_path)
            print("  [DRY] %s -> %s" % (name, state))
        return 0

    results = [register_one(bat_path, args.biz_line, l, t, args.force) for l, t in SCHEDULES]
    ok = 0
    for name, status in results:
        print("  %s: %s" % (name, status))
        if "已创建" in status or "已存在" in status or "已修复" in status:
            ok += 1

    print("\n[SUMMARY] %d/%d 任务就绪（早/午/晚）" % (ok, len(results)))
    if ok == len(results):
        print("[OK] 定时同步任务已就绪，无需手动操作。MySQL 配置补齐后，数据将每日自动入库。")
        return 0
    print("[WARN] 部分任务未创建成功，可能需管理员权限（schtasks 被禁用或权限不足）。")
    print("       手动备选：以管理员身份 CMD 执行：")
    print('         schtasks /create /tn "%s时间同步-早" /tr "\\"%s\\" %s" /sc daily /st 09:00 /f'
          % (args.biz_line, bat_path, args.biz_line))
    return 1


if __name__ == "__main__":
    sys.exit(main())
