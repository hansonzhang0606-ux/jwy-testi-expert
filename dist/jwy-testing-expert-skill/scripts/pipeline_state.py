#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
泾渭云需求全流程编排 —— 跨步骤状态管理脚本（标准库，无第三方依赖）

职责：
  1. 在用户指定的「输出目录」下维护 .jwy_pipeline_state.json
  2. 记录每一步（step1 / step2 / step3-选项X / step4 / step5）的产物路径
  3. 校验 step4 依赖：仅当 step3-选项1 或 step3-选项2 完成后才允许执行 step4
     （step3-选项3 已直接生成 DMP 兼容格式，无 step4）

用法：
  python pipeline_state.py init     --output-dir DIR
  python pipeline_state.py record   --output-dir DIR --step STEP [--products "p1;p2"]
  python pipeline_state.py check    --output-dir DIR --step STEP
  python pipeline_state.py products --output-dir DIR --step STEP
  python pipeline_state.py status   --output-dir DIR

输出统一为 JSON（utf-8）到 stdout，供编排 skill 解析。
"""

import argparse
import json
import os
import sys

STATE_FILENAME = ".jwy_pipeline_state.json"

# 用户口语 / 中文写法 → 规范化 step id
CANON = {
    "step1": "step1",
    "step2": "step2",
    "step3-选项1": "step3-1", "step3-1": "step3-1", "步骤3选项1": "step3-1", "step3选项1": "step3-1",
    "step3-选项2": "step3-2", "step3-2": "step3-2", "步骤3选项2": "step3-2", "step3选项2": "step3-2",
    "step3-选项3": "step3-3", "step3-3": "step3-3", "步骤3选项3": "step3-3", "step3选项3": "step3-3",
    "step4": "step4",
    "step5": "step5",
}

STEP3_OPTIONS = {"step3-1", "step3-2", "step3-3"}
# step4 仅允许在这两个选项之后
STEP3_LEADS_TO_STEP4 = {"step3-1", "step3-2"}
TRACKING_ID_BY_STEP = {
    "step1": "P1", "step2": "P2", "step3-1": "P3-1", "step3-2": "P3-2",
    "step3-3": "P3-3", "step4": "P4", "step5": "P5",
}


def state_path(output_dir):
    return os.path.join(output_dir, STATE_FILENAME)


def load_state(output_dir):
    p = state_path(output_dir)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("output_dir", output_dir)
            data.setdefault("steps_completed", [])
            data.setdefault("products", {})
            data.setdefault("last_step3", None)
            data.setdefault("tracking", {"eligible": []})
            return data
        except Exception:
            pass
    return {
        "output_dir": output_dir,
        "steps_completed": [],
        "products": {},
        "last_step3": None,
        "tracking": {"eligible": []},
    }


def save_state(output_dir, state):
    os.makedirs(output_dir, exist_ok=True)
    with open(state_path(output_dir), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def normalize(step):
    if not step:
        return None
    return CANON.get(step.strip()) or CANON.get(step.strip().lower())


def do_init(args):
    os.makedirs(args.output_dir, exist_ok=True)
    state = load_state(args.output_dir)
    save_state(args.output_dir, state)
    print(json.dumps({"ok": True, "state": state}, ensure_ascii=False))


def _refresh_tracking(state):
    state["tracking"] = {"eligible": [TRACKING_ID_BY_STEP[step] for step in state["steps_completed"] if step in TRACKING_ID_BY_STEP]}


def record_step(output_dir, step, products=None):
    state = load_state(output_dir)
    canon = normalize(step)
    if not canon:
        raise ValueError(f"未知 step: {step}")
    products = products or []
    if canon not in state["steps_completed"]:
        state["steps_completed"].append(canon)
    if products:
        state["products"].setdefault(canon, [])
        for product in products:
            if product not in state["products"][canon]:
                state["products"][canon].append(product)
    if canon in STEP3_OPTIONS:
        state["last_step3"] = canon
    _refresh_tracking(state)
    save_state(output_dir, state)
    return state


def check_step(output_dir, step):
    state = load_state(output_dir)
    canon = normalize(step)
    if canon != "step4":
        return {"allowed": True, "reason": ""}
    last = state.get("last_step3")
    if last in STEP3_LEADS_TO_STEP4:
        return {"allowed": True, "reason": ""}
    if last == "step3-3":
        return {"allowed": False, "reason": "step3-选项3 无step4（选项3 已直接生成 DMP 兼容格式，无需转换，可直接走 step5 归档）"}
    return {"allowed": False, "reason": "请先完成 step3（选项1 或 选项2）后再执行 step4；当前尚未完成可转 DMP 的脑图步骤"}


def do_record(args):
    products = [x.strip() for x in (args.products or "").split(";") if x.strip()] if args.products else []
    try:
        state = record_step(args.output_dir, args.step, products)
    except ValueError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        sys.exit(2)
    print(json.dumps({"ok": True, "state": state}, ensure_ascii=False))

def do_check(args):
    out = check_step(args.output_dir, args.step)
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out["allowed"] else 3)


def do_products(args):
    state = load_state(args.output_dir)
    if args.step == "step3-inputs":
        # step3 可复用 step1（需求确认 docx）/ step2（代码分析）的产物
        paths = []
        for k in ("step1", "step2"):
            paths.extend(state["products"].get(k, []))
        print(json.dumps({"products": paths}, ensure_ascii=False))
    else:
        canon = normalize(args.step)
        print(json.dumps({"products": state["products"].get(canon, [])}, ensure_ascii=False))


def do_status(args):
    state = load_state(args.output_dir)
    print(json.dumps(state, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="泾渭云需求全流程编排状态管理")
    sub = ap.add_subparsers(dest="action", required=True)

    p = sub.add_parser("init")
    p.add_argument("--output-dir", required=True)

    p = sub.add_parser("record")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--step", required=True)
    p.add_argument("--products", default="")

    p = sub.add_parser("check")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--step", required=True)

    p = sub.add_parser("products")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--step", required=True)

    p = sub.add_parser("status")
    p.add_argument("--output-dir", required=True)

    args = ap.parse_args()
    {
        "init": do_init,
        "record": do_record,
        "check": do_check,
        "products": do_products,
        "status": do_status,
    }[args.action](args)


if __name__ == "__main__":
    main()
