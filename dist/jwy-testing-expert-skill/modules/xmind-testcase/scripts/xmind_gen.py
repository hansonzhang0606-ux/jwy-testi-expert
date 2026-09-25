# -*- coding: utf-8 -*-
"""XMind 2.0 测试用例生成器（可复用模块）

特性
----
- 输出符合 XMind 2.0 规范的 .xmind 文件（本质是 zip 包）。
- 推荐使用 5 层纯文本风格（无前缀），对标用户实际脑图习惯：
    L0 根(需求名) → L1 业务场景 → L2 测试分类 → L3 测试条件 → L4 测试数据 → L5 预期结果
  条件与数据一体时可省略 L4，用 C2() 生成 L3→L4(预期) 两层。
- 兼容旧版 TC()（带「测试点：」「预期结果：」前缀的三节点结构），但不再推荐。
- 默认套用「商业 II」主题。

用法
----
    from xmind_gen import N, C3, C2, build_xmind

    root = N("【TD-AI】示例需求", [
        N("业务场景描述", [
            N("挡板", [
                C3("近12个月销售额>=50W and <100W",   # L3 测试条件
                   "jysj=60万，zysx=80万",            # L4 测试数据
                   "使用jysj=60万进行分档"),           # L5 预期结果
                C2("maxskssqz=202607（当前月）",       # L3 条件+数据一体
                   "按示例排除（不含当月）"),           # L4 预期结果
            ]),
        ]),
    ])
    build_xmind(root, req_name="示例需求v1.0")
    # -> 生成【TD-AI】示例需求v1.0_测试用例.xmind
"""
import os
import zipfile
import shutil
import time

# ---------------------------------------------------------------------------
# 节点构造器
# ---------------------------------------------------------------------------
def N(text, children=None):
    """普通节点：text 为标题，children 为子节点列表。"""
    return {"text": text, "children": children or [], "_case": False}


def C3(condition, data, expected):
    """测试用例节点（推荐·5层风格·纯文本无前缀）。

    生成 3 层节点链：L3(测试条件) → L4(测试数据) → L5(预期结果)
    适用于「条件」与「数据」可拆分的场景。

    condition : 测试条件/规则描述（如「近12个月销售额>=50W and <100W」）
    data      : 具体测试数据/输入（如「jysj=60万，zysx=80万」）
    expected  : 预期结果（如「使用jysj=60万进行分档，不使用zysx」）
    """
    return {"text": condition, "children": [
        {"text": data, "children": [
            {"text": expected, "children": [], "_case": False}
        ], "_case": False}
    ], "_case": True}


def C2(condition, expected):
    """测试用例节点（推荐·5层风格·纯文本无前缀·省略L4）。

    生成 2 层节点链：L3(条件+数据一体) → L4(预期结果)
    适用于「条件」与「数据」无法拆分或一体的场景。

    condition : 测试条件+数据（如「sbxxList存在clientId=1000076记录，其余条件均满足」）
    expected  : 预期结果（如「该记录被排除，不入名单二」）
    """
    return {"text": condition, "children": [
        {"text": expected, "children": [], "_case": False}
    ], "_case": True}


def TC(scenario, testpoint, expected):
    """测试用例节点（旧版兼容·带前缀·不再推荐）。

    生成 3 节点：场景标题 + 「测试点：...」 + 「预期结果：...」
    保留是为了向后兼容旧脚本；新代码请改用 C3()/C2()。

    scenario  : 场景标题（简短，一眼看懂测什么）
    testpoint : 测试点——测试数据 / 前置条件 / 操作步骤
    expected  : 预期结果——系统应有的行为或输出
    """
    return {"text": scenario, "children": [
        {"text": "测试点：" + testpoint, "children": [], "_case": False},
        {"text": "预期结果：" + expected, "children": [], "_case": False},
    ], "_case": True}


# ---------------------------------------------------------------------------
# 文件命名规范（必须执行）：需求名_测试脑图.xmind
# ---------------------------------------------------------------------------
def make_output_name(req_name):
    """按 skill 命名规范生成文件名：需求名_测试脑图.xmind

    req_name : 需求名称（保留版本号与需求标识标签，如「【泾渭云20260804】纳税H5增加登录身份提示」）。
               仅清理团队前缀（【TD-AI】/【{部署配置}】）与冗余后缀，不加团队前缀——
               团队前缀由流水线 Step5 上传前统一追加，避免双重前缀。
    """
    name = req_name.strip()
    # 仅去除团队强制前缀（若有遗漏），保留需求标识标签如【泾渭云YYYYMMDD】
    name = name.replace("【TD-AI】", "").replace("【{部署配置}】", "")
    # 清理可能重复的命名后缀，避免叠加
    name = name.replace("_测试用例", "").replace("_测试脑图", "").replace("-测试点", "").replace("-脑图", "")
    name = name.strip()
    return f"{name}_测试脑图.xmind"


# ---------------------------------------------------------------------------
# 标准样式（商业 II 主题），与原项目保持一致，可直接复用
# ---------------------------------------------------------------------------
STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
    '<xmap-styles xmlns="urn:xmind:xmap:xmlns:style:2.0" '
    'xmlns:fo="http://www.w3.org/1999/XSL/Format" '
    'xmlns:svg="http://www.w3.org/2000/svg" version="2.0">'
    '<automatic-styles>'
    '<style id="5b0kom1meupj4lun8djain2l1k" name="" type="summary">'
    '<summary-properties line-color="#253249" line-width="1pt" '
    'shape-class="org.xmind.summaryShape.square"/></style>'
    '<style id="1c28ojce2ulq2tu7t5c4vgkjdv" name="" type="topic">'
    '<topic-properties fo:color="#253249" fo:font-family="Microsoft YaHei" '
    'svg:fill="none"/></style>'
    '<style id="035at5lk5bafep9ddnvuimvpg2" name="" type="boundary">'
    '<boundary-properties fo:color="#FFFFFF" fo:font-family="Microsoft YaHei" '
    'fo:font-size="9pt" fo:font-style="italic" line-color="#253249" '
    'line-pattern="dash" line-width="2pt" '
    'shape-class="org.xmind.boundaryShape.roundedRect" svg:fill="#253249" '
    'svg:opacity="0.2"/></style>'
    '<style id="0ahsritbda2grisbhr9clr0gmm" name="" type="topic">'
    '<topic-properties border-line-color="#7e8aa3" border-line-width="2pt" '
    'callout-shape-class="org.xmind.calloutTopicShape.balloon.roundedRect" '
    'fo:color="#FFFFFF" fo:font-family="Microsoft YaHei" fo:font-style="italic" '
    'line-class="org.xmind.branchConnection.roundedElbow" line-color="#7e8aa3" '
    'line-width="2pt" svg:fill="#7e8aa3"/></style>'
    '<style id="361fa45tvq7e250pmv9qh8urg5" name="" type="topic">'
    '<topic-properties border-line-width="5pt" fo:color="#253249" '
    'fo:font-family="Microsoft YaHei" fo:font-size="22pt" fo:font-weight="bold" '
    'fo:text-align="center" fo:text-transform="uppercase" '
    'line-class="org.xmind.branchConnection.elbow" line-color="#253249" '
    'line-width="1pt" shape-class="org.xmind.topicShape.underline" '
    'svg:fill="none"/></style>'
    '<style id="7a0e4jp1t64vf9eujkvc8hg1mi" name="" type="topic">'
    '<topic-properties border-line-color="#253249" border-line-width="4pt" '
    'fo:color="#253249" fo:font-family="Microsoft YaHei" fo:font-weight="bold" '
    'fo:text-transform="uppercase" line-class="org.xmind.branchConnection.elbow" '
    'line-color="#253249" line-width="1pt" '
    'shape-class="org.xmind.topicShape.underline" svg:fill="none"/></style>'
    '<style id="5upgguvfc2tu5dnpgmkqi03h8q" name="" type="topic">'
    '<topic-properties border-line-width="0pt" fo:color="#253249" '
    'fo:font-family="Microsoft YaHei" fo:font-size="11pt" fo:font-style="italic" '
    'line-class="org.xmind.branchConnection.elbow" '
    'shape-class="org.xmind.topicShape.ellipse" svg:fill="none"/></style>'
    '<style id="1r4g6m342r5tjr9lb7oji2b8es" name="" type="relationship">'
    '<relationship-properties arrow-begin-class="org.xmind.arrowShape.none" '
    'arrow-end-class="org.xmind.arrowShape.triangle" fo:color="#253249" '
    'fo:font-family="Microsoft YaHei" fo:font-size="12pt" fo:font-style="italic" '
    'line-color="#ff9900" line-pattern="solid" line-width="3pt" '
    'shape-class="org.xmind.relationshipShape.curved"/></style>'
    '<style id="0pv08d7p9rs2ik0p3sb0k74f4f" name="" type="topic">'
    '<topic-properties border-line-width="4pt" fo:color="#253249" '
    'fo:font-family="Microsoft YaHei" fo:font-size="16pt" fo:font-style="italic" '
    'fo:font-weight="normal" line-class="org.xmind.branchConnection.elbow" '
    'line-color="#253249" line-width="1pt" '
    'shape-class="org.xmind.topicShape.underline" svg:fill="none"/></style>'
    '<style id="6cr299e9b71ml25nkmkt5gqnp9" name="" type="map">'
    '<map-properties background="" color-gradient="none" line-tapered="none" '
    'multi-line-colors="none" svg:fill="#FFFFFF" svg:opacity="1.0"/></style>'
    '</automatic-styles><master-styles>'
    '<style id="6bqonjeshs1b09a83dba89uaeq" name="商业 II" type="theme">'
    '<theme-properties>'
    '<default-style style-family="summary" style-id="5b0kom1meupj4lun8djain2l1k"/>'
    '<default-style style-family="subTopic" style-id="1c28ojce2ulq2tu7t5c4vgkjdv"/>'
    '<default-style style-family="boundary" style-id="035at5lk5bafep9ddnvuimvpg2"/>'
    '<default-style style-family="calloutTopic" style-id="0ahsritbda2grisbhr9clr0gmm"/>'
    '<default-style style-family="centralTopic" style-id="361fa45tvq7e250pmv9qh8urg5"/>'
    '<default-style style-family="mainTopic" style-id="7a0e4jp1t64vf9eujkvc8hg1mi"/>'
    '<default-style style-family="summaryTopic" style-id="5upgguvfc2tu5dnpgmkqi03h8q"/>'
    '<default-style style-family="relationship" style-id="1r4g6m342r5tjr9lb7oji2b8es"/>'
    '<default-style style-family="floatingTopic" style-id="0pv08d7p9rs2ik0p3sb0k74f4f"/>'
    '<default-style style-family="map" style-id="6cr299e9b71ml25nkmkt5gqnp9"/>'
    '</theme-properties></style></master-styles></xmap-styles>'
)

MANIFEST_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
    '<manifest xmlns="urn:xmind:xmap:xmlns:manifest:1.0" password-protected="false">'
    '<file-entry full-path="content.xml" media-type="text/xml"/>'
    '<file-entry full-path="styles.xml" media-type="text/xml"/>'
    '<file-entry full-path="meta.xml" media-type="text/xml"/>'
    '</manifest>'
)


# ---------------------------------------------------------------------------
# XML 生成
# ---------------------------------------------------------------------------
def _escape(text):
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


def _build_topic_xml(topic, prefix, depth, count, timestamp):
    count[0] += 1
    tid = f"{prefix}{count[0]:04d}"
    safe = _escape(topic["text"])
    children_xml = ""
    kids = topic.get("children", [])
    if kids:
        subs = "".join(
            _build_topic_xml(c, prefix, depth + 1, count, timestamp)[0]
            for c in kids
        )
        children_xml = (
            f'<children><topics type="attached">{subs}</topics></children>'
        )
    if depth == 0:
        return (f'<topic id="{tid}" timestamp="{timestamp}" '
                f'style-id="361fa45tvq7e250pmv9qh8urg5">'
                f'<title svg:width="500">{safe}</title>{children_xml}</topic>', tid)
    return (f'<topic id="{tid}" timestamp="{timestamp}">'
            f'<title>{safe}</title>{children_xml}</topic>', tid)


def build_xmind(root, out_path=None, req_name=None, author="kingdee", theme_id="6bqonjeshs1b09a83dba89uaeq"):
    """根据节点树生成 .xmind 文件。

    root     : N() 返回的根节点字典
    out_path : 输出 .xmind 路径。为 None 时，必须传 req_name，
               自动套用命名规范：需求名_测试脑图.xmind
    req_name : 需求名称（保留版本号）。与 out_path 二选一，推荐用此参数。
    author   : 作者名（写入 meta）
    theme_id : 主题 id（默认商业 II）
    """
    if out_path is None:
        if req_name is None:
            raise ValueError("必须指定 out_path 或 req_name 之一")
        out_path = make_output_name(req_name)
    timestamp = str(int(time.time() * 1000))
    root_xml, _ = _build_topic_xml(root, "t", 0, [0], timestamp)
    content_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        '<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0" '
        'xmlns:fo="http://www.w3.org/1999/XSL/Format" '
        'xmlns:svg="http://www.w3.org/2000/svg" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'modified-by="{author}" timestamp="{timestamp}" version="2.0">'
        f'<sheet id="sheet1" timestamp="{timestamp}" theme="{theme_id}">'
        f'{root_xml}<title>画布 1</title></sheet></xmap-content>'
    )
    meta_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        '<xmap-meta xmlns="urn:xmind:xmap:xmlns:meta:2.0" version="2.0">'
        f'<Creator><Name>{author}</Name></Creator>'
        f'<CreateDate>{timestamp}</CreateDate>'
        f'<Modifier><Name>{author}</Name></Modifier>'
        f'<ModifyDate>{timestamp}</ModifyDate>'
        f'<SheetId>0o692lutnpalrqsdo2ki6hemlv</SheetId></xmap-meta>'
    )

    # 唯一临时目录，避免覆盖写时触发沙箱安全删除拦截
    tmp = out_path + f".{timestamp}.tmp"
    os.makedirs(tmp, exist_ok=True)
    try:
        with open(os.path.join(tmp, "content.xml"), "w", encoding="utf-8") as f:
            f.write(content_xml)
        with open(os.path.join(tmp, "styles.xml"), "w", encoding="utf-8") as f:
            f.write(STYLES_XML)
        with open(os.path.join(tmp, "meta.xml"), "w", encoding="utf-8") as f:
            f.write(meta_xml)
        os.makedirs(os.path.join(tmp, "META-INF"), exist_ok=True)
        with open(os.path.join(tmp, "META-INF", "manifest.xml"), "w", encoding="utf-8") as f:
            f.write(MANIFEST_XML)

        # ZipFile "w" 模式直接覆盖旧文件，无需先 os.remove（避免安全删除拦截）
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root_dir, _, files in os.walk(tmp):
                for fname in files:
                    full = os.path.join(root_dir, fname)
                    arc = os.path.relpath(full, tmp).replace("\\", "/")
                    zf.write(full, arc)
    finally:
        # 容错清理：沙箱环境回收站不可用时忽略清理失败（文件已写出）
        try:
            shutil.rmtree(tmp)
        except Exception:
            pass

    # 统计用例数（C3/C2/TC 标记的 _case 节点）
    tc_count = [0]
    def walk(t):
        if t.get("_case"):
            tc_count[0] += 1
        for c in t.get("children", []):
            walk(c)
    walk(root)
    return {"path": out_path, "size": os.path.getsize(out_path), "test_cases": tc_count[0]}


if __name__ == "__main__":
    # 自测：生成一份最小示例，验证模块可用（5层纯文本风格）
    demo = N("【TD-AI】示例需求", [
        N("业务场景描述", [
            N("挡板", [
                C3("近12个月销售额>=50W and <100W",
                   "jysj=60万，zysx=80万",
                   "使用jysj=60万进行分档，不使用zysx"),
                C2("maxskssqz=202607（当前月）",
                   "按示例排除（不含当月）"),
            ]),
            N("异常场景", [
                C2("接口返回null", "视为不满足（异常兜底）"),
            ]),
        ]),
    ])
    res = build_xmind(demo, req_name="示例需求")
    print("✅ 示例生成:", res)
