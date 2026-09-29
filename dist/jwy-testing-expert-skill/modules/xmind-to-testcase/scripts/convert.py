# -*- coding: utf-8 -*-
"""
xmind-to-testcase 参考实现：基于团队 DMP 模板生成 Excel。

支持两种 XMind 格式：
  A) XMind Zen  -> content.json（节点 children.attached；测试点/预期结果 或 叶子节点）
  B) 经典 XMind -> content.xml（urn:xmind:xmap:xmlns:content:2.0；
                    L1=模块 / L2=子模块 / L3=条件 / L4=数据 / L5=预期）
Step3-选项1(xmind-testcase) 产出经典格式，本实现优先兼容。

关键约束（来自 SKILL.md）：
- 生成的 Excel 必须基于团队 DMP 模板文件。
- 模板「前 4 行」原样保留（字体/颜色/填充/对齐/边框）。
- 仅从第 5 行起写入数据，通过「第 3 行」英文列名建立 col_map 按名映射。
- 固定值：team/product/modulePath={部署配置}，manager={部署配置}，autoState=否，source 留空；
  name 自动加「验证」前缀。

内嵌资源（其他测试人员无需 GitHub 即可复用）：
- 本 Skill 的 assets/dmp_template.xlsx 为团队 DMP 模板默认回退。
- 经典 XMind 的独立转换器亦可单独调用 assets/convert_jwy.py。

用法：
  python convert.py --xmind <file.xmind> --template <可选> \
        --case-group "..." --version "V..." --manager "..." --output <out.xlsx>
未提供 --template 时按序查找：输出目录的 excel模板.xlsx / 模板 - 副本.xlsx / 本 Skill assets/dmp_template.xlsx。
"""
import argparse, json, os, zipfile, glob
import xml.etree.ElementTree as ET
from openpyxl import load_workbook
from openpyxl.styles import Alignment

NS = "{urn:xmind:xmap:xmlns:content:2.0}"

# ---------- 1. 解析 XMind ----------
def _parse_zen(path):
    """XMind Zen (content.json)。返回 list[{module, scenario, tp, er}]"""
    z = zipfile.ZipFile(path)
    data = json.loads(z.read("content.json"))
    root = data[0]["rootTopic"]
    recs = []
    def walk(n, path=None):
        if path is None:
            path = []
        title = n.get("title", "")
        cur = path + [title]
        ch = n.get("children", {}).get("attached", [])
        if len(ch) == 2 and ch[0].get("title", "").startswith("测试点") and ch[1].get("title", "").startswith("预期结果"):
            tp = ch[0]["title"][len("测试点："):].strip()
            er = ch[1]["title"][len("预期结果："):].strip()
            recs.append({"module": " / ".join(path), "scenario": title, "tp": tp, "er": er})
            return
        if not ch:
            recs.append({"module": " / ".join(path[:-1]), "scenario": title, "tp": title, "er": "（按需求描述预期）"})
            return
        for k in ch:
            walk(k, cur)
    walk(root)
    return recs


def _title(e):
    t = e.find(f"{NS}title")
    return t.text if t is not None else ""


def _kids(e):
    ch = e.find(f"{NS}children")
    if ch is None:
        return []
    ts = ch.find(f"{NS}topics")
    if ts is None:
        return []
    return ts.findall(f"{NS}topic")


def _parse_classic(path):
    """经典 XMind (content.xml)。结构：
    L1=模块, L2=子模块, L3=条件(scenario), L4=数据(tp), L5=预期(er)。
    「需求疑问点(待确认)」分支为说明性叶子，整体跳过，不产用例。"""
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("content.xml").decode("utf-8"))
    sheet = root.find(f"{NS}sheet")
    rt = sheet.find(f"{NS}topic")
    recs = []
    def walk(e, depth, mod_path):
        tg = _title(e)
        if depth == 1 and tg == "需求疑问点(待确认)":
            return
        ks = _kids(e)
        if depth == 3:
            data = _title(ks[0]) if len(ks) >= 1 else ""
            expect = _title(_kids(ks[0])[0]) if (len(ks) >= 1 and _kids(ks[0])) else ""
            recs.append({"module": " / ".join(mod_path), "scenario": tg, "tp": data, "er": expect})
            return
        for c in ks:
            walk(c, depth + 1, mod_path + ([tg] if depth <= 2 else []))
    for l1 in _kids(rt):
        walk(l1, 1, [])
    return recs


def parse_xmind(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    if "content.json" in names:
        return _parse_zen(path)
    if "content.xml" in names:
        return _parse_classic(path)
    raise RuntimeError("XMind 文件须含 content.json(XMind Zen) 或 content.xml(经典 XMind)")


# ---------- 2. 用例级别 ----------
def case_level(scenario):
    if any(t in scenario for t in ["异常", "错误", "失败", "无效", "为空", "缺失"]):
        return "P1"
    if any(t in scenario for t in ["边界", "临界", "最大", "最小", "重复", "超长"]):
        return "P2"
    return "P0"


def pre_cond(module):
    return "1. 测试环境已部署\n2. 相关依赖服务正常运行\n3. 测试账号与测试数据就绪"


# ---------- 2.1 步骤化 input / output（每条用例至少 3 个步骤） ----------
def _split_items(text):
    if not text:
        return []
    text = str(text).replace("；", ";").replace("\n", ";")
    items = [t.strip(" 。.；;") for t in text.split(";")]
    return [t for t in items if t]


def build_io(scenario, tp, er):
    tp_items = _split_items(tp)
    er_items = _split_items(er)
    inp_steps, out_steps = [], []
    # 第 1 步：进入页面 / 准备数据（通用）
    inp_steps.append("进入对应功能页面，准备测试账号与测试数据")
    out_steps.append("页面正常加载，无报错，测试数据就绪")
    # 中间步：来自测试点 / 预期结果，一一对应
    n = max(len(tp_items), len(er_items))
    for i in range(n):
        t = tp_items[i] if i < len(tp_items) else "复核上述操作"
        e = er_items[i] if i < len(er_items) else "系统返回符合预期"
        inp_steps.append("执行操作：%s" % t)
        out_steps.append("预期结果：%s" % e)
    # 末步：通用检查（保证至少 3 步）
    inp_steps.append("检查系统响应、页面展示与数据落库结果")
    out_steps.append("系统与页面展示与预期一致，数据正确落库")
    while len(inp_steps) < 3:
        inp_steps.append("执行测试用例步骤并观察结果")
        out_steps.append("结果符合预期")
    inp = "\n".join("%d. %s" % (i + 1, s) for i, s in enumerate(inp_steps))
    out = "\n".join("%d. %s" % (i + 1, s) for i, s in enumerate(out_steps))
    return inp, out


# ---------- 3. 主流程 ----------
def convert(xmind, template, output, case_group, version, manager):
    recs = parse_xmind(xmind)
    wb = load_workbook(template)          # 保留全部样式（含前4行字体/颜色/填充）
    ws = wb.active

    # 从「第 3 行」建立 列名->列索引 映射（绝不硬编码列号）
    col_map = {}
    for c in range(1, ws.max_column + 1):
        k = ws.cell(row=3, column=c).value
        if k and str(k).strip():
            col_map[str(k).strip()] = c

    # 清空第 5 行及之后的旧数据（含模板自带示例行），但不动前 4 行
    for r in range(5, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(row=r, column=c).value = None

    data_start = 5
    for i, r in enumerate(recs):
        row = data_start + i
        inp, out = build_io(r["scenario"], r["tp"], r["er"])
        tc = {
            "team": "{部署配置}",
            "caseGroup": case_group,
            "name": "验证" + r["scenario"],
            "preCondition": pre_cond(r["module"]),
            "input": inp,
            "output": out,
            "product": "{部署配置}",
            "modulePath": "{部署配置}",
            "version": version,
            "caseType": "功能测试",
            "source": "",
            "caseLevel": case_level(r["scenario"]),
            "manager": manager,
            "autoState": "否",
        }
        for col_name, val in tc.items():
            if col_name in col_map:
                ws.cell(row=row, column=col_map[col_name], value=val)
        for cn in ("preCondition", "input", "output"):
            if cn in col_map:
                ws.cell(row=row, column=col_map[cn]).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[row].height = 120

    wb.save(output)
    return len(recs)


def find_template(xmind_path):
    """模板查找顺序：
    1) 输出目录 excel模板.xlsx
    2) 输出目录 模板 - 副本.xlsx
    3) 本 Skill 内嵌 assets/dmp_template.xlsx（无需 GitHub）
    4) 输出目录任意 *.xlsx
    """
    xdir = os.path.dirname(os.path.abspath(xmind_path))
    for name in ("excel模板.xlsx", "模板 - 副本.xlsx"):
        p = os.path.join(xdir, name)
        if os.path.exists(p):
            return p
    here = os.path.dirname(os.path.abspath(__file__))
    # scripts/ -> xmind-to-testcase/ -> modules/ -> jwy-testing-expert-skill/assets/
    embedded = os.path.normpath(os.path.join(here, "..", "..", "..", "assets", "dmp_template.xlsx"))
    if os.path.exists(embedded):
        return embedded
    cands = glob.glob(os.path.join(xdir, "*.xlsx"))
    return cands[0] if cands else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--xmind", required=True)
    ap.add_argument("--template", default=None)
    ap.add_argument("--output", default=None)
    ap.add_argument("--case-group", default="")
    ap.add_argument("--version", default="")
    ap.add_argument("--manager", default="{部署配置}")
    args = ap.parse_args()

    template = args.template or find_template(args.xmind)
    if not template or not os.path.exists(template):
        raise SystemExit("未找到团队 DMP 模板，请提供 --template")
    if args.output is None:
        base = os.path.splitext(os.path.basename(args.xmind))[0]
        args.output = os.path.join(os.path.dirname(os.path.abspath(args.xmind)), base + "_测试用例.xlsx")

    n = convert(args.xmind, template, args.output, args.case_group, args.version, args.manager)
    print(f"已生成 {n} 条用例 -> {args.output}")
    print(f"模板: {template}（前4行样式已原样保留）")
