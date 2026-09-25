# -*- coding: utf-8 -*-
"""『』碎片化包裹合并工具（用户要求，2026-09-20）

问题
----
并列关键字被逐个套括号，读起来割裂：

    『任务名称』/『导入文件』/『数据源』(所选值)/『总税号数』
    『任务名称』、『导入 Excel』、『数据源』

要求
----
并列时**只写一对『』**，开头一个『、结尾一个』，内部以 / 分隔：

    『任务名称/导入文件/数据源(所选值)/总税号数』
    『任务名称/导入 Excel/数据源』

处理规则
--------
- 括号注释（`数据源(所选值)`、`创建人(中文)`）跟随所属词，保留在『』内部
- `、` 并列统一改写为 `/`（全图风格一致）
- 两个『』之间的文字不是分隔符（`分别选`、`点击…后`）→ **不合并**，语义不同
- `『覆盖度查询』『执行中』`（无分隔符，分属不同字段）→ **不合并**

用法
----
    python merge_brackets.py 脑图.xmind                    # 原地修复（改前自动备份）
    python merge_brackets.py 脑图.xmind -o 新脑图.xmind     # 另存
    python merge_brackets.py 脑图.xmind --dry-run          # 只报告，不写文件

退出码：0 = 成功（含无变化）；2 = 用法/文件错误
"""
import argparse
import io
import os
import re
import shutil
import sys
import zipfile

# 括号注释（如 `(所选值)`），出现在词后或分隔符前
NOTE = r"(?:[(（][^『』()（）<>]*[)）])?"
ITEM = r"『[^『』<>]*』"
# 并列 run：ITEM，之后至少一个「(注释)? 分隔符 (注释)? ITEM」
RUN_RE = re.compile(ITEM + r"(?:" + NOTE + r"\s*(?:/|、)\s*" + NOTE + ITEM + r")+")

ITEM_RE = re.compile(r"『([^『』<>]*)』")
SEP_RE = re.compile(r"』(.*?)『", re.S)
LEAD_NOTE_RE = re.compile(r"^\s*([(（][^()（）]*[)）])")


def merge_run(run):
    """把『A』/『B』(x)/『C』合并成『A/B(x)/C』。"""
    items = ITEM_RE.findall(run)
    if len(items) < 2:
        return run
    seps = SEP_RE.findall(run)
    out = "『" + items[0]
    for i, sep in enumerate(seps):
        m = LEAD_NOTE_RE.match(sep)
        if m:
            out += m.group(1)
        out += "/" + items[i + 1]
    return out + "』"


def merge_text(text):
    """对单行文本执行合并，返回 (新文本, 是否变化)。"""
    prev = None
    cur = text
    while prev != cur:
        prev = cur
        cur = RUN_RE.sub(lambda m: merge_run(m.group(0)), cur)
    return cur, cur != text


def process_xml(content):
    """对整个 content.xml 做合并（只动 <title> 内的文本）。

    字符类排除 `<`/`>`，正则不会跨越标签边界，因此可安全地在原始 XML 上操作，
    其余字节（样式、id、时间戳）保持原样。
    """
    matches = []

    def repl(m):
        new = merge_run(m.group(0))
        if new != m.group(0):
            matches.append((m.group(0), new))
        return new

    return RUN_RE.sub(repl, content), matches


def fix_xmind(path, out_path=None, dry_run=False):
    if not zipfile.is_zipfile(path):
        print("不是有效的 .xmind（zip）文件：%s" % path)
        return 2
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        content = z.read("content.xml").decode("utf-8")
        others = {n: z.read(n) for n in names if n != "content.xml"}

    new_content, matches = process_xml(content)

    print("文件：%s" % os.path.basename(path))
    print("-" * 66)
    if not matches:
        print("OK: 未发现碎片化包裹，无需合并")
        return 0

    print("合并 %d 处：\n" % len(matches))
    for old, new in matches:
        print("  - %s" % old)
        print("    %s\n" % new)

    if dry_run:
        print("（--dry-run，未写入文件）")
        return 0

    target = out_path or path
    if target == path:
        bak = path + ".bak"
        shutil.copy2(path, bak)
        print("已备份原文件：%s" % os.path.basename(bak))

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.xml", new_content.encode("utf-8"))
        for n, data in others.items():
            zf.writestr(n, data)
    print("已写入：%s" % target)
    return 0


def fix_text_file(path, out_path=None, dry_run=False):
    lines = io.open(path, encoding="utf-8").read().splitlines()
    changed = []
    out = []
    for ln in lines:
        new, ok = merge_text(ln)
        out.append(new)
        if ok:
            changed.append((ln, new))
    print("文件：%s" % os.path.basename(path))
    print("-" * 66)
    if not changed:
        print("OK: 未发现碎片化包裹")
        return 0
    for old, new in changed:
        print("  - %s\n    %s" % (old, new))
    if dry_run:
        print("（--dry-run，未写入文件）")
        return 0
    target = out_path or path
    io.open(target, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("已写入：%s" % target)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="合并『』碎片化包裹（并列关键字只写一对『』）")
    ap.add_argument("path", help=".xmind 文件或纯文本文件（每行一个节点）")
    ap.add_argument("-o", "--output", default=None, help="输出路径，默认原地修复")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写文件")
    args = ap.parse_args(argv)

    if not os.path.exists(args.path):
        print("文件不存在：%s" % args.path)
        return 2
    if args.path.lower().endswith(".xmind") or zipfile.is_zipfile(args.path):
        return fix_xmind(args.path, args.output, args.dry_run)
    return fix_text_file(args.path, args.output, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
