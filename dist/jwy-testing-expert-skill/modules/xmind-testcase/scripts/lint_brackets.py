# -*- coding: utf-8 -*-
"""界面文字『』标识校验（生成 .xmind 后跑一遍）

背景
----
脑图里同时存在「界面上的字」（列头、按钮、枚举值）和「测试描述」。
约定：界面文字必须用『』包裹，例如
    『任务状态』分别选『执行中/解析中/已完成/已停止/失败』
漏加『』时评审分不清「下拉框选项」和「测试步骤」，本脚本负责兜底。

检查项
------
1. ERROR  『』不成对（『 与 』数量不一致）              -> 退出码 1
2. ERROR  『』嵌套（一个『』区间内又出现 『）             -> 退出码 1
3. ERROR  枚举值列表未包裹（≥2 个枚举值用 / 连接却没进『』）-> 退出码 1  ← 高精度，主规则
4. ERROR  碎片化包裹（『A』/『B』、『A』、『B』应合并为一对『』）-> 退出码 1 ← 用户明确要求
5. ERROR  L1/L2 节点带『』（场景/分类名不框，『』只用于 L3+）-> 退出码 1 ← 用户明确要求
6. HINT   命中界面词表但未包裹（泛动词居多，需人工判断）  -> 默认退出码 0
7. WARN   误用其他引号「」“”‘’代替『』                  -> 默认退出码 0

用法
----
    python lint_brackets.py 输出文件.xmind                     # 标准校验
    python lint_brackets.py 输出文件.xmind --keywords ui.txt    # 追加界面词（每行一个）
    python lint_brackets.py 输出文件.xmind --strict            # HINT/WARN 也算失败
    python lint_brackets.py 输出文件.xmind --all               # 显示全部 HINT 明细

修复碎片化包裹：`python merge_brackets.py 输出文件.xmind`

退出码：0 = 通过；1 = 存在失败项；2 = 用法错误
"""
import io
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = "{urn:xmind:xmap:xmlns:content:2.0}"
MAX_HINT_DETAIL = 20

# ---------------------------------------------------------------------------
# 枚举值（高精度主规则用）：这些值以 / 连接出现时，几乎一定是界面下拉选项
# ---------------------------------------------------------------------------
ENUM_VALUES = [
    "执行中", "解析中", "已完成", "已停止", "失败",
    "自研", "首展", "蚂蚁", "全选", "我创建的",
    "覆盖度查询", "密文税号解析",
    "解析失败", "执行失败", "部分成功",
]

# 界面词表（低精度参考用）：字段名 / 按钮 / 弹窗名
DEFAULT_KEYWORDS = [
    # ---- 列表列头 / 表格字段 ----
    "任务名称", "导入文件", "数据源", "总税号数", "查询进度", "任务状态", "任务类型",
    "创建人", "创建时间", "加密税号", "明文税号", "单税是否查得", "单票是否查得",
    "税+票是否查得", "查得路由", "路由配置",
    # ---- 表单 / 弹窗 / 页面 ----
    "导入 Excel", "新增覆盖度查询", "极简覆盖度查询",
    # ---- 按钮 / 操作入口 ----
    "停止任务", "结果Excel", "结果 Excel", "清除筛选", "开始解析", "新增",
    "提交", "下载", "查看", "导出", "导入", "上传", "编辑", "删除", "取消", "确定",
]

BAD_QUOTES = ["「", "」", "“", "”", "‘", "’"]

SEP = r"\s*/\s*"
ENUM_ALT = "|".join(re.escape(v) for v in sorted(ENUM_VALUES, key=len, reverse=True))
# 2 个及以上枚举值用 / 连接
ENUM_RUN_RE = re.compile(r"(?:%s)(?:%s(?:%s))+" % (ENUM_ALT, SEP, ENUM_ALT))

# 碎片化包裹：『A』/『B』 或 『A』、『B』（并列关键字应合并为一对『』）
NOTE = r"(?:[(（][^『』()（）<>]*[)）])?"
_ITEM = r"『[^『』<>]*』"
FRAG_RE = re.compile(_ITEM + r"(?:" + NOTE + r"\s*(?:/|、)\s*" + NOTE + _ITEM + r")+")


def read_titles(path):
    """读取节点文本，返回 [(depth, text)]，跳过 L0 根节点和画布名。"""
    if path.lower().endswith(".xmind") or zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            content = z.read("content.xml").decode("utf-8")
        root = ET.fromstring(content)
        sheet = root.find(NS + "sheet")
        if sheet is None:
            return []
        items = []

        def walk(topic, depth):
            t = topic.find(NS + "title")
            items.append((depth, (t.text or "") if t is not None else ""))
            ch = topic.find(NS + "children")
            if ch is None:
                return
            for topics in ch.findall(NS + "topics"):
                for sub in topics.findall(NS + "topic"):
                    walk(sub, depth + 1)

        walk(sheet.find(NS + "topic"), 0)
        # 跳过 L0 根（需求名，不是界面文字）与画布标题
        return [(d, t) for d, t in items if d >= 1 and t != "画布 1"]
    return [(1, ln.strip()) for ln in io.open(path, encoding="utf-8").read().splitlines() if ln.strip()]


def bracket_spans(text):
    """返回所有『』区间 [(start, end)]，end 为闭区间下标。"""
    spans, stack = [], []
    for i, ch in enumerate(text):
        if ch == "『":
            stack.append(i)
        elif ch == "』":
            if stack:
                spans.append((stack.pop(), i))
    return spans


def inside_spans(idx, spans):
    return any(s <= idx <= e for s, e in spans)


def is_data_context(text, i, kw):
    """判断该命中是否处于「测试数据」语境，而非界面标签。

    典型数据语境（不算遗漏）：
    - `导入文件=覆盖度查询导入.xlsx`（等号键值对，数据描述）
    - `覆盖度查询-tingting_yu-20260921-001`（连字符拼成的任务名/文件名）
    """
    end = i + len(kw)
    if (end < len(text) and text[end] == "=") or (i > 0 and text[i - 1] == "="):
        return True
    if end < len(text) and text[end] in "._-":
        return True
    return False


def lint(path, keywords=None, strict=False, show_all=False):
    items = read_titles(path)
    kws = keywords if keywords is not None else DEFAULT_KEYWORDS

    errors, warns, strong, hints, frags = [], [], [], [], []

    for depth, text in items:
        n_open, n_close = text.count("『"), text.count("』")
        if n_open != n_close:
            errors.append(("『』不成对（%d 个『 / %d 个』）" % (n_open, n_close), text))
        # L1/L2 是场景/分类名，不是界面文字引用，不允许带『』
        if depth <= 2 and (n_open or n_close):
            errors.append(("L%d 层级名不需要『』（场景/分类名不框）" % depth, text))
        spans = bracket_spans(text)
        if any("『" in text[s + 1:e] for s, e in spans):
            errors.append(("『』嵌套", text))
        for q in BAD_QUOTES:
            if q in text:
                warns.append(("误用引号 %s" % q, text))
                break

        # 主规则：未包裹的枚举值列表
        for m in ENUM_RUN_RE.finditer(text):
            if not inside_spans(m.start(), spans):
                strong.append(("枚举值列表未包裹：%s" % m.group(0), text))

        # 主规则：碎片化包裹（并列关键字应合并为一对『』）
        for m in FRAG_RE.finditer(text):
            frags.append(("碎片化包裹：%s" % m.group(0), text))

        # 参考：命中界面词但未包裹
        for kw in kws:
            start = 0
            while True:
                i = text.find(kw, start)
                if i < 0:
                    break
                if not inside_spans(i, spans) and not is_data_context(text, i, kw):
                    hints.append((kw, text))
                start = i + len(kw)

    # ---------------- 输出 ----------------
    print("检查文件：%s" % os.path.basename(path))
    print("节点数：%d    枚举值：%d 个    界面词表：%d 个" % (len(items), len(ENUM_VALUES), len(kws)))
    print("-" * 66)

    if errors:
        print("[ERROR] 『』格式问题 %d 处" % len(errors))
        for msg, t in errors:
            print("   - %s\n     %s" % (msg, t))

    if strong:
        print("[ERROR] 枚举值列表未包裹『』 %d 处" % len(strong))
        for msg, t in strong:
            print("   - %s\n     %s" % (msg, t))

    if frags:
        print("[ERROR] 碎片化包裹（并列关键字应合并为一对『』）%d 处" % len(frags))
        for msg, t in frags:
            print("   - %s\n     %s" % (msg, t))
        print("   修复：python merge_brackets.py <文件.xmind>")

    if warns:
        print("[WARN] 引号使用异常 %d 处" % len(warns))
        for msg, t in warns[:MAX_HINT_DETAIL]:
            print("   - %s | %s" % (msg, t))

    if hints:
        from collections import Counter
        c = Counter(kw for kw, _ in hints)
        summary = "、".join("%s×%d" % (k, v) for k, v in c.most_common())
        print("[HINT] 命中界面词但未包裹 %d 处（含描述性用法，需人工判断）" % len(hints))
        print("   词频：%s" % summary)
        limit = len(hints) if show_all else MAX_HINT_DETAIL
        for kw, t in hints[:limit]:
            print("   - 未包裹：%s | %s" % (kw, t))
        if len(hints) > limit:
            print("   ... 另有 %d 条，用 --all 查看" % (len(hints) - limit))

    if not (errors or strong or frags or warns or hints):
        print("OK: 『』格式正确，枚举值均已包裹，无碎片化包裹，未发现疑似遗漏")

    print("-" * 66)
    print("ERROR=%d（格式+枚举+碎片化）  WARN=%d  HINT=%d"
          % (len(errors) + len(strong) + len(frags), len(warns), len(hints)))
    bad = len(errors) + len(strong) + len(frags)
    if strict:
        bad += len(warns) + len(hints)
    return 1 if bad else 0


def load_keywords(path):
    if not os.path.exists(path):
        print("关键词文件不存在：%s" % path)
        return None
    lines = io.open(path, encoding="utf-8").read().splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = argv[1]
    strict = "--strict" in argv
    show_all = "--all" in argv
    kws = None
    if "--keywords" in argv:
        i = argv.index("--keywords")
        if i + 1 >= len(argv):
            print("--keywords 需要一个文件路径")
            return 2
        kws = load_keywords(argv[i + 1])
        if kws is None:
            return 2
        if not kws:
            print("关键词文件为空，回退到内置词表")
            kws = None
    if not os.path.exists(path):
        print("文件不存在：%s" % path)
        return 2
    return lint(path, keywords=kws, strict=strict, show_all=show_all)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
