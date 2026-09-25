"""
XMind 脑图生成脚本 - 需求接口维度分析

从入参（字段清单+正常场景+异常场景）、出参（字段映射+正常场景+异常场景）、扣费、接口文档4个维度生成 XMind 脑图文件。
直接构建兼容新版 XMind 的 zip 格式（content.json + metadata.json + manifest.json）。

脑图结构：
    根节点 = 年份（如 "2026"），全部右侧展开
    二级节点 = 需求名称（如 "【20260604】新增自研司法库产品 - 查询限制高消费信息"）
    三级及以下 = 四维度分析内容

使用方法：
    python gen_xmind.py

注意：
    - ID 必须是完整 UUID 格式
    - 根节点 class = "attached topic"，需设置 structureClass = "org-chart" 确保全部右侧展开
    - 二级节点（需求名称）class = "attached"
    - 其他子节点 class = "attached"
    - zip 包必须包含三个文件：content.json + metadata.json + manifest.json
    - 入参/出参的具体字段值从需求文档提取，不硬编码
"""

import json
import zipfile
import uuid


def new_id():
    """生成 UUID 格式的节点 ID"""
    return str(uuid.uuid4())


def make_topic(title, children=None, is_root=False, structure_class=None):
    """构建 XMind 主题节点

    Args:
        title: 节点标题
        children: 子节点列表（可选）
        is_root: 是否为根节点（根节点 class 为 "attached topic"）
        structure_class: 节点布局类型（可选），如 "org-chart" 使全部右侧展开

    Returns:
        dict: XMind 主题节点对象
    """
    t = {
        "id": new_id(),
        "class": "attached topic" if is_root else "attached",
        "title": title,
        "titleUnedited": False,
    }
    if structure_class:
        t["structureClass"] = structure_class
    if children:
        t["children"] = {"attached": children}
    return t


def build_content(root_topic, sheet_title="需求分析"):
    """构建 XMind content.json 数据结构

    Args:
        root_topic: 根节点对象
        sheet_title: 画布标题

    Returns:
        tuple: (content.json 数据列表, sheet_id)
    """
    sheet_id = new_id()
    content = [{
        "id": sheet_id,
        "class": "sheet",
        "title": sheet_title,
        "rootTopic": root_topic,
        "relationships": [],
        "extensions": [],
        "topicPositioning": "fixed",
        "topicOverlapping": "overlap",
    }]
    return content, sheet_id


def build_metadata(sheet_id):
    """构建 XMind metadata.json 数据结构

    Args:
        sheet_id: 画布 ID

    Returns:
        dict: metadata.json 数据对象
    """
    return {
        "modifier": "WorkBuddy 1.0",
        "dataStructureVersion": "1",
        "layoutEngineVersion": "2",
        "activeSheetId": sheet_id
    }


def build_manifest():
    """构建 XMind manifest.json 数据结构

    Returns:
        dict: manifest.json 数据对象
    """
    return {
        "file-entries": {
            "content.json": {},
            "metadata.json": {}
        }
    }


def write_xmind(content, metadata, manifest, output_path):
    """写入 XMind zip 文件

    Args:
        content: content.json 数据
        metadata: metadata.json 数据
        manifest: manifest.json 数据
        output_path: 输出文件路径

    Returns:
        str: 生成的文件路径
    """
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.json", json.dumps(content, ensure_ascii=False, indent=2))
        zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False))
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))

    return output_path


# ============================================================
# 需求接口维度分析脑图构建函数
# ============================================================

def build_req_analysis_xmind(
    year,
    req_title,
    # --- 入参 ---
    auth_params,
    biz_params,
    param_limits,
    input_normal_scenarios,
    input_abnormal_scenarios,
    # --- 出参 ---
    output_fields,
    output_normal_scenarios,
    output_abnormal_scenarios,
    # --- 扣费 ---
    billing_datasource,
    billing_product,
    # --- 接口文档 ---
    api_url,
    sort_logic,
    query_scenarios,
    req_background,
    output_path,
):
    """构建需求接口维度分析 XMind 脑图

    脑图结构：根节点=年份（全部右侧展开），二级节点=需求名称，三级及以下=四维度分析内容。
    入参/出参维度的核心是正常场景+异常场景分析，具体字段值从需求文档提取。

    Args:
        year: 年份根节点，如 "2026"
        req_title: 需求名称二级节点，如 "【20260604】新增自研司法库产品 - 查询限制高消费信息"

        # 入参
        auth_params: 认证参数列表，每个元素为 (name, required, type, desc)
        biz_params: 业务参数列表，每个元素为 (name, required, type, desc, extra_note)
            extra_note: 补充说明（如"与pname必填一项"），为空字符串则无补充
        param_limits: 入参限制列表，每个元素为 (param_name, limit_rules_list)
        input_normal_scenarios: 入参正常场景列表，每个元素为 (scenario_desc, expected_result)
        input_abnormal_scenarios: 入参异常场景列表，每个元素为 (scenario_desc, expected_result)

        # 出参
        output_fields: 出参字段列表，每个元素为 (field_name, desc, db_field, db_desc)
            db_field: 数据库字段名（如 sf_xgl.name），为空字符串则无映射
            db_desc: 字段中文说明，如有勘误需在此标注
        output_normal_scenarios: 出参正常场景列表，每个元素为 (scenario_desc, expected_result)
        output_abnormal_scenarios: 出参异常场景列表，每个元素为 (scenario_desc, expected_result)

        # 扣费
        billing_datasource: 数据源产品信息 dict，如 {"名称": "...", "产品": "...", "成本": "..."}
        billing_product: 产品信息 dict，如 {"名称": "...", "数据源产品": "...", "扣费方式": "..."}

        # 接口文档
        api_url: 接口地址
        sort_logic: 排序逻辑列表，每个元素为 (level_desc, field, direction)
        query_scenarios: 查询场景列表，每个元素为 (scenario_name, steps_list)
        req_background: 需求背景 dict，如 {"现有问题": "...", "解决目标": "..."}

        output_path: 输出文件路径

    Returns:
        str: 生成的 XMind 文件路径
    """

    # ========== 一、接口入参 ==========
    # 字段清单 - 认证参数
    auth_children = [make_topic(f"{p[0]} | {p[1]} | {p[2]} | {p[3]}") for p in auth_params]

    # 字段清单 - 业务参数
    biz_children = []
    for p in biz_params:
        topic = make_topic(f"{p[0]} | {p[1]} | {p[2]} | {p[3]}")
        if p[4]:
            topic["children"] = {"attached": [make_topic(p[4])]}
        biz_children.append(topic)

    # 字段清单 - 入参限制
    limit_children = [make_topic(f"{l[0]}限制", [make_topic(r) for r in l[1]]) for l in param_limits]

    # 正常场景
    input_normal_children = [
        make_topic(s[0], [make_topic(s[1])]) for s in input_normal_scenarios
    ]

    # 异常场景
    input_abnormal_children = [
        make_topic(s[0], [make_topic(s[1])]) for s in input_abnormal_scenarios
    ]

    input_topic = make_topic("一、接口入参", [
        make_topic("字段清单", [
            make_topic("认证参数", auth_children),
            make_topic("业务参数", biz_children),
            make_topic("入参限制", limit_children),
        ]),
        make_topic("正常场景", input_normal_children),
        make_topic("异常场景", input_abnormal_children),
    ])

    # ========== 二、接口出参 ==========
    # 字段映射 - items 字段列表
    items_children = []
    for f in output_fields:
        if f[2]:  # 有数据库映射的字段
            items_children.append(make_topic(f"{f[0]} → {f[2]} | {f[3]}"))
        else:
            items_children.append(make_topic(f"{f[0]} | {f[1]}"))

    # 正常场景
    output_normal_children = [
        make_topic(s[0], [make_topic(s[1])]) for s in output_normal_scenarios
    ]

    # 异常场景
    output_abnormal_children = [
        make_topic(s[0], [make_topic(s[1])]) for s in output_abnormal_scenarios
    ]

    output_topic = make_topic("二、接口出参", [
        make_topic("字段映射", [
            make_topic("status | 提交响应码"),
            make_topic("msg | 结果描述"),
            make_topic("data.result", [
                make_topic("解密后的参数"),
                make_topic("total | 总数"),
                make_topic("items | 结果列表", items_children),
            ]),
        ]),
        make_topic("正常场景", output_normal_children),
        make_topic("异常场景", output_abnormal_children),
    ])

    # ========== 三、扣费 ==========
    billing_topic = make_topic("三、扣费", [
        make_topic("数据源产品", [
            make_topic(f"数据源名称 | {billing_datasource['名称']}"),
            make_topic(f"数据源产品 | {billing_datasource['产品']}"),
            make_topic(f"成本 | {billing_datasource['成本']}"),
        ]),
        make_topic("产品", [
            make_topic(f"产品名称 | {billing_product['名称']}"),
            make_topic(f"数据源产品 | {billing_product['数据源产品']}"),
            make_topic(f"扣费方式 | {billing_product['扣费方式']}"),
        ]),
    ])

    # ========== 四、接口文档 ==========
    sort_children = [make_topic(f"{s[0]} | {s[1]} | {s[2]}") for s in sort_logic]
    scenario_children = [make_topic(s[0], [make_topic(step) for step in s[1]]) for s in query_scenarios]
    bg_children = [make_topic(f"{k} | {v}") for k, v in req_background.items()]

    doc_topic = make_topic("四、接口文档", [
        make_topic("接口地址", [make_topic(api_url)]),
        make_topic("排序逻辑", sort_children),
        make_topic("查询逻辑", scenario_children),
        make_topic("需求背景", bg_children),
    ])

    # ========== 二级节点：需求名称 ==========
    req_topic = make_topic(req_title, [
        input_topic, output_topic, billing_topic, doc_topic
    ])

    # ========== 根节点：年份，全部右侧展开 ==========
    root_topic = make_topic(year, [req_topic], is_root=True, structure_class="org-chart")

    # 构建并写入文件
    content, sheet_id = build_content(root_topic)
    metadata = build_metadata(sheet_id)
    manifest = build_manifest()

    return write_xmind(content, metadata, manifest, output_path)


# ============================================================
# 示例：根据需求文档内容填充参数（可直接修改运行）
# ============================================================

if __name__ == "__main__":
    # 以下参数值均从需求文档提取，不同需求需替换为对应内容
    result = build_req_analysis_xmind(
        year="2026",
        req_title="【20260604】新增自研司法库产品 - 查询限制高消费信息",

        # --- 入参（从需求文档提取） ---
        auth_params=[
            ("client_id", "必填", "String", "id"),
            ("client_secret", "必填", "String", "secret"),
        ],
        biz_params=[
            ("ename", "非必填", "String", "企业名称", "与pname必填一项"),
            ("pname", "非必填", "String", "人员名称", "与ename必填一项"),
        ],
        param_limits=[
            ("pname", ["长度2到20个字符之间", "只能包含中文、点（·）"]),
            ("ename", ["默认规则"]),
            ("组合限制", ["ename与pname必填一项，不能同时为空"]),
        ],
        # 入参正常场景：根据需求文档查询逻辑分支推衍
        input_normal_scenarios=[
            ("仅传pname合法值（2-20字符，中文和点）", "正常返回该人员的限消信息列表"),
            ("仅传ename合法值（企业名称）", "正常返回该企业相关的限消信息列表"),
            ("同时传ename+pname合法值", "返回企业+人员交集的限消信息（结果C）"),
        ],
        # 入参异常场景：根据入参限制规则推衍
        input_abnormal_scenarios=[
            ("pname为空（ename也为空）", "参数校验失败：ename与pname必填一项"),
            ("pname超长（>20字符）", "参数校验失败：长度超限"),
            ("pname超短（<2字符）", "参数校验失败：长度不足"),
            ("pname含非法字符（英文/数字/特殊符号）", "参数校验失败：只能包含中文和点"),
            ("ename与pname同时为空", "参数校验失败：必填一项"),
            ("client_id/client_secret错误", "认证失败：无效凭证"),
        ],

        # --- 出参（从需求文档提取） ---
        output_fields=[
            ("name", "限制高消费人", "sf_xgl.name", "限制高消费人"),
            ("companyName", "限消人企业", "sf_xgl.company_info", "限消人企业"),
            ("sex", "性别", "sf_xgl.sex", "性别"),
            ("releaseDate", "限制令发布日期（原文档描述错误，实为发布日期而非立案日期）", "sf_xgl.publish_date", "限制令发布日期"),
            ("caseNo", "案号", "sf_xgl.case_code", "案号"),
            ("filingDate", "立案时间（原文档描述错误，实为立案时间而非发布日期）", "sf_xgl.lian_date", "立案时间"),
            ("court", "执行法院", "sf_xgl.court_name", "执行法院"),
            ("executionApplicant", "申请执行人", "sf_xgl.all_applicant", "申请执行人"),
            ("caseReason", "案由", "sf_xgl.action_cause", "案由"),
            ("content", "限消正文", "sf_xgl.content", "限消正文"),
            ("tag", "是否历史(1-是 0-否)", "sf_xgl.is_history", "是否历史"),
        ],
        # 出参正常场景
        output_normal_scenarios=[
            ("查询成功，有匹配数据", "返回完整items字段列表，total > 0"),
            ("多条限消记录", "items为列表，包含多条记录，按publish_date和id倒序排列"),
            ("无匹配数据", "total = 0，items为空列表"),
        ],
        # 出参异常场景
        output_abnormal_scenarios=[
            ("认证失败", "status=错误码，msg=认证失败/无效凭证"),
            ("参数校验失败", "status=错误码，msg=参数错误描述"),
            ("内部服务异常", "status=错误码，msg=服务异常/数据库查询失败"),
        ],

        # --- 扣费（从需求文档表格提取） ---
        billing_datasource={"名称": "自研工商库（已存在）", "产品": "司法库_查询限制高消费信息", "成本": "一口价，查询扣费 0.01元/次"},
        billing_product={"名称": "司法库_查询限制高消费信息", "数据源产品": "司法库_查询限制高消费信息", "扣费方式": "一口价 查询扣费"},

        # --- 接口文档（从需求文档提取） ---
        api_url="/verify/restricted/consumer",
        sort_logic=[
            ("组合倒序排序", "", ""),
            ("一级排序", "publish_date", "倒序"),
            ("二级排序", "id", "倒序"),
        ],
        query_scenarios=[
            ("场景1：企业查询(仅ename)", [
                "1. 查company_base表，筛选use_flag in ('0','1','2','3')，company_name=入参ename → 得company_id",
                "2. 根据company_id查mongodb sf_xgl表，筛选use_flag in ('0','1','2','3')",
                "3. 匹配接口输出字段进行输出",
            ]),
            ("场景2：个人查询(仅pname)", [
                "1. 根据pname查sf_xgl表，筛选use_flag in ('0','1','2','3')",
                "2. 匹配接口输出字段进行输出",
            ]),
            ("场景3：企业+个人查询(ename+pname)", [
                "1. 查company_base表得company_id",
                "2. 用company_id查sf_xgl得结果A",
                "3. 用pname查sf_xgl得结果B",
                "4. 取A∩B得结果C（需与现有接口逻辑保持一致）",
                "5. 匹配接口输出字段进行输出",
            ]),
        ],
        req_background={"现有问题": "当前查询限制高消费信息接口均为外部数据源", "解决目标": "新增自研司法库数据源产品，实现降本"},

        output_path=r"D:\需求\2026\【20260604】新增自研司法库产品-查询限制高消费信息.xmind",
    )

    print(f"XMind文件已生成：{result}")
