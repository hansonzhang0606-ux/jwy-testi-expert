# -*- coding: utf-8 -*-
"""
xmind-to-testcase 参考实现：基于团队 DMP 模板生成 Excel。

关键约束（来自 SKILL.md）：
- 生成的 Excel 必须基于团队 DMP 模板文件（默认 excel模板.xlsx / 模板 - 副本.xlsx）。
- 模板「前 4 行」（标题/说明/英文列名/灰色中文说明）原样保留，
  包括字体、颜色、填充、对齐、边框——绝不重建或覆盖。
- 仅从第 5 行起写入数据，通过「第 3 行」英文列名建立 col_map 按名映射。
- 固定值：team/product/modulePath=金蝶征信，manager=余萍，autoState=否，source 留空；
  name 自动加「验证」前缀。

用法：
  python convert.py --xmind <file.xmind> --template <excel模板.xlsx> \
        --case-group "..." --version "V..." --manager "余萍" --output <out.xlsx>
"""
import argparse, json, os, zipfile, glob
from openpyxl import load_workbook
from openpyxl.styles import Alignment

# ---------- 1. 解析 XMind ----------
def parse_xmind(path):
    """优先 content.json（XMind Zen），回退 content.xml。
    支持两种结构：
      A) 测试点/预期结果 节点对（本流水线产出）
      B) 通用叶子节点（需求文档脑图）
    返回 list[{module, scenario, tp, er}]"""
    z = zipfile.ZipFile(path)
    names = z.namelist()
    if "content.json" in names:
        data = json.loads(z.read("content.json"))
        root = data[0]["rootTopic"]
        recs = []
        def walk(n, path=None):
            if path is None: path = []
            title = n.get("title", "")
            cur = path + [title]
            ch = n.get("children", {}).get("attached", [])
            if len(ch) == 2 and ch[0].get("title", "").startswith("测试点") and ch[1].get("title", "").startswith("预期结果"):
                tp = ch[0]["title"][len("测试点："):].strip()
                er = ch[1]["title"][len("预期结果："):].strip()
                recs.append({"module": " / ".join(path), "scenario": title, "tp": tp, "er": er})
                return
            if not ch:  # 叶子节点 -> 单条用例
                recs.append({"module": " / ".join(path[:-1]), "scenario": title,
                             "tp": title, "er": "（按需求描述预期）"})
                return
            for k in ch:
                walk(k, cur)
        walk(root)
        return recs
    raise RuntimeError("仅支持 XMind Zen (content.json) 格式")

# ---------- 2. 用例级别 ----------
def case_level(scenario):
    if any(t in scenario for t in ["解析-空格", "解析-大小写", "解析-去重", "解析-异常值"]):
        return "P2"
    if any(t in scenario for t in ["不展示-其他clientId", "命中-ALL大小写", "命中-ALL与具体取并集",
                                    "范围-其他H5", "范围-Web端", "配置-热生效", "回归-存量客户"]):
        return "P1"
    return "P0"

def pre_cond(module):
    if "五、配置生效与回归" in module:
        return "1. 字典配置中心支持热更新，无需重启/重新部署\n2. 存在已配置 clientId 的存量客户\n3. 纳税H5 登录页可正常访问"
    if "一、字典配置" in module:
        return "1. 字典 LOGIN_ROLE_TIPS_CLIENTIDS 已按用例配置\n2. 纳税H5 登录页可正常访问\n3. 相应 clientId 的测试账号可登录"
    if "二、页面范围隔离" in module:
        return "1. 字典已配置命中 clientId\n2. 纳税H5 登录页与对照页面（其他 H5 / Web 端）均可访问\n3. 测试账号可登录"
    return "1. 测试环境已部署\n2. 相关依赖服务正常运行"

# ---------- 2.1 步骤化 input / output（每条用例至少 3 个步骤） ----------
def _split_items(text):
    """将测试点 / 预期结果文本拆分为多个步骤项（按换行 / 分号 / 句号切分，过滤空项）。"""
    if not text:
        return []
    text = str(text).replace("；", ";").replace("\n", ";")
    items = [t.strip(" 。.；;") for t in text.split(";")]
    return [t for t in items if t]

def build_io(scenario, tp, er):
    """构造 input（操作步骤）与 output（预期结果）。

    规则：两条列均**至少 3 个编号步骤**且步数一致（一一对应）。
    优先使用 XMind 测试点 / 预期结果文本作为中间步骤，
    不足 3 步时用规范的通用步骤补全至 3 步。
    """
    tp_items = _split_items(tp)
    er_items = _split_items(er)

    inp_steps, out_steps = [], []

    # 第 1 步：进入页面 / 准备数据（通用）
    inp_steps.append("进入对应功能页面，准备测试账号与测试数据")
    out_steps.append("页面正常加载，无报错，测试数据就绪")

    # 中间步：来自测试点 / 预期结果，一一对应
    n = max(len(tp_items), len(er_items))
    for i in range(n):
        t = tp_items[i] if i < len(tp_items) else "复核上述操作（第%d次）" % (i + 1)
        e = er_items[i] if i < len(er_items) else "系统返回符合预期"
        inp_steps.append("执行操作：%s" % t)
        out_steps.append("预期结果：%s" % e)

    # 末步：通用检查（保证至少 3 步）
    inp_steps.append("检查系统响应、页面展示与数据落库结果")
    out_steps.append("系统与页面展示与预期一致，数据正确落库")

    # 极端情况（tp / er 均空）兜底补齐到 3 步
    while len(inp_steps) < 3:
        inp_steps.append("执行测试用例步骤并观察结果")
        out_steps.append("结果符合预期")

    # 编号
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
            "team": "金蝶征信",
            "caseGroup": case_group,
            "name": "验证" + r["scenario"],
            "preCondition": pre_cond(r["module"]),
            "input": inp,
            "output": out,
            "product": "金蝶征信",
            "modulePath": "金蝶征信",
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

def find_template(xmind_dir):
    for name in ("excel模板.xlsx", "模板 - 副本.xlsx"):
        p = os.path.join(xmind_dir, name)
        if os.path.exists(p):
            return p
    cands = glob.glob(os.path.join(xmind_dir, "*.xlsx"))
    return cands[0] if cands else None

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--xmind", required=True)
    ap.add_argument("--template", default=None)
    ap.add_argument("--output", default=None)
    ap.add_argument("--case-group", default="")
    ap.add_argument("--version", default="")
    ap.add_argument("--manager", default="余萍")
    args = ap.parse_args()

    xdir = os.path.dirname(os.path.abspath(args.xmind))
    template = args.template or find_template(xdir)
    if not template or not os.path.exists(template):
        raise SystemExit("未找到团队 DMP 模板（excel模板.xlsx / 模板 - 副本.xlsx），请提供 --template")
    if args.output is None:
        base = os.path.splitext(os.path.basename(args.xmind))[0]
        args.output = os.path.join(xdir, base + "_测试用例.xlsx")

    n = convert(args.xmind, template, args.output, args.case_group, args.version, args.manager)
    print(f"已生成 {n} 条用例 -> {args.output}")
    print(f"模板: {template}（前4行样式已原样保留）")
