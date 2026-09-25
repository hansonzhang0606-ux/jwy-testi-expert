---
name: generate-xmind-cases
version: 1.5.0
description: |
  根据测试方案或需求文档生成 XMind 格式的测试用例文件（.xmind）。支持两种模式：①迭代用例模式（PLM需求，含PRJ编号、集成测试）；②回归测试模式（泾渭云H5/RPA等业务，按年月组织，无PRJ层级）。每条用例严格按4列结构编排：用例名称（含优先级图标）→ 前置条件 → 操作步骤 → 预期结果。

  ⚠️ 强制约束（禁止 AI 擅自决策）：
  1. 执行到每一阶段时，AI 必须完整阅读该阶段相关的 md 文档或脚本内容
  2. 严格按照流程执行，不可跳过任何步骤
  3. 每个阶段开始前，AI 必须先阅读对应文档：
     - 步骤②需求评审 → 阅读 prompts/requirement_review.md
     - 步骤④生成测试点 → 阅读 prompts/testpoint_generate.md
     - 步骤⑥生成用例 → 阅读 prompts/testcase_refine.md
     - 步骤⑦入库 → 阅读 prompts/knowledge_base_archive.md
  4. 禁止凭记忆或推断执行，必须以文档内容为准

  ⛔ 禁止 AI 擅自做决定（强制按流程规范执行）：
  - ⛔ 禁止假设已读取：不假设前置步骤已完成，必须实际执行每步读取操作
  - ⛔ 禁止简化 Todo：Todo 清单必须完整，不可省略强制检查项（⭐标记项）
  - ⛔ 禁止跳过步骤：强制项（⭐）不可跳过，必须逐项执行并标记状态
  - ⛔ 禁止自行判断：AI 不可自行判断「不重要」「已完成」「无需执行」，按流程规范执行
  - ⛔ 禁止假设状态：标记「已完成」前必须实际执行该操作，不可凭记忆标记
  - ⛔ 禁止修改文件路径：路径字符串原样复制使用，禁止添加/删除空格、符号等

  ⚠️ 进入任何主步骤时，第一步必须追加子流程 Todo（规划动作），禁止先执行操作再追加
install_method: upload
---

# 生成 XMind 测试用例

## 全局约束

- **产品线固定为"金蝶征信"**：无论模式A还是模式B，产品线/系统名称一律使用"金蝶征信"，不需要用户传入或确认。
- 模式B回归测试中，`build_xmind_regression()` 已内置产品线名称，调用时无需传 `product_name` 参数。

## 触发条件

当用户提出以下需求时使用本 Skill：
- 要求生成 XMind 格式的迭代用例 / 回归测试用例
- 提供测试方案或需求文档，要求转化为 XMind 用例
- 要求按迭代版本或年月组织测试用例
- 提到"迭代用例"、"XMind 用例"、"回归用例"、"回归测试"关键词

## 模式选择

根据输入内容自动判断使用哪种模式：

| 模式 | 适用场景 | 识别特征 |
|------|---------|---------|
| **模式A：迭代用例** | PLM产品需求迭代 | 有PRJ编号、按版本号组织、需要集成测试 |
| **模式B：回归测试** | 泾渭云业务回归（H5采集、RPA、银税等） | 按年月组织、产品线固定为"金蝶征信"、无PRJ编号 |

---

## 模式A：迭代用例

### 节点层级结构

```
迭代用例 (根节点, structureClass: org.xmind.ui.logic.right)
└── {版本号} (如 R20260416版本)
    └── {功能模块} (如 工艺批量变更)
        └── {PRJ编号}【{模块}】{需求标题}
            ├── 功能测试
            │   ├── {版本号}                    [symbol-pin]    ← 图钉图标
            │   ├── {PRJ编号}                   [symbol-comment] ← 评论图标
            │   └── PLM云-{所属菜单}             [star-red]      ← 红星图标
            │       └── 功能测试
            │           └── {用例名称}           [priority-N]    ← 优先级图标
            │               └── {前置条件}
            │                   ├── {操作步骤1}
            │                   │   └── {预期结果1}
            │                   └── {操作步骤N}
            │                       └── {预期结果N}
            └── 集成测试 (必须有)
                ├── {版本号},集成测试             [symbol-pin]
                ├── {PRJ编号}                   [symbol-comment]
                └── PLM云-{所属菜单}             [star-red]
                    └── 功能测试
                        └── {用例名称}           [priority-1]
                            └── {前置条件}
                                ├── {操作步骤1}
                                │   └── {预期结果1}
                                └── {操作步骤N}
                                    └── {预期结果N}
```

### 图标标记（模式A）

| markerId | 用途 | 放置位置 |
|----------|------|----------|
| `symbol-pin` | 标记版本号 | 功能测试/集成测试下第1个子节点 |
| `symbol-comment` | 标记 PRJ 编号 | 功能测试/集成测试下第2个子节点 |
| `star-red` | 标记所属菜单模块 | 功能测试/集成测试下第3个子节点 |
| `priority-1` | 高优先级（核心流程、集成测试必须） | 用例名称节点 |
| `priority-2` | 普通优先级（界面校验、字段验证） | 用例名称节点 |

### 集成测试要求（模式A）

**每个 PRJ 必须包含集成测试用例，且优先级必须为 `priority-1`：**

| 要求 | 说明 |
|------|------|
| 必须存在 | 每个 PRJ 节点下必须有"集成测试"分支 |
| 优先级 | 所有集成测试用例必须使用 `priority-1` |
| 覆盖范围 | 验证该 PRJ 核心功能的端到端流程 |
| 数量 | 根据功能复杂度，1-3条为宜 |

---

## 模式B：回归测试

### 节点层级结构

参考文件：`金蝶征信_张小增【泾渭云20260319】RPA银税一键授权回归测试 - 安徽.xmind`

```
{年份} (根节点，如 2026，无 structureClass)
└── {年月} (如 202604)
    └── 【泾渭云YYYYMMDD】{需求标题} - {省份/区域}
        └── 金蝶征信（固定产品线）    [star-red]
            ├── 功能测试
            │   └── {用例名称}               [priority-2]
            │       └── {前置条件}
            │           ├── {操作步骤1}
            │           │   └── {预期结果1}
            │           ├── {操作步骤2}
            │           │   └── {预期结果2}
            │           └── {操作步骤N}
            │               └── {预期结果N}
            └── 需求疑问点                     ← 普通分支，无图标（可选，有疑问点时添加）
                ├── 疑问点1：{描述}【建议确认方：XX】
                ├── 疑问点2：{描述}【建议确认方：XX】
                └── 疑问点N：{描述}【建议确认方：XX】
```

### 图标标记（模式B）

| markerId | 用途 | 放置位置 |
|----------|------|----------|
| `star-red` | 标记产品线（固定为"金蝶征信"） | 产品线节点 |
| `priority-2` | 所有功能用例（默认） | 用例名称节点 |

### 模式B特点

- **无 PRJ 编号层级**，直接按需求标题 → 金蝶征信（固定产品线）→ 功能测试 → 用例组织
- **无集成测试分支**，所有用例统一放在"功能测试"下
- **所有用例使用 `priority-2`**（除非明确要求核心流程使用 priority-1）
- **禁止使用 `tag-green` 等任何步骤级标记**，所有步骤节点保持统一样式，不添加任何 marker
- **根节点为年份**（如 2026），不是"迭代用例"
- **sheet.title** 为文件的完整标题（如"【张小增】【泾渭云20260319】...需求"）

---

## 产物命名（流水线 Step3-选项3）

生成的 XMind 落到「指定目录」，文件名必须为 `需求名_DMP用例.xmind`：

- `需求名`：从需求文档标题 / 输入文件名提取，去掉团队前缀（`【余萍】`、`【TD-AI】`），保留需求标识标签（如 `【泾渭云YYYYMMDD】`）。
- 示例：需求 `【余萍】【TD-AI】【泾渭云20260804】纳税H5增加登录身份提示` → `【泾渭云20260804】纳税H5增加登录身份提示_DMP用例.xmind`。

## 用例4列格式（两种模式通用）

每条测试用例由4个层级组成，第3-4层可以重复多组：

| 层级 | 内容 | 说明 |
|------|------|------|
| 第1层 | 用例名称 | 带 `priority-1` 或 `priority-2` 图标标记 |
| 第2层 | 前置条件 | 描述执行前必须满足的系统状态和数据准备 |
| 第3层 | 操作步骤 | 描述具体的用户操作动作，**可以有多个步骤并列** |
| 第4层 | 预期结果 | 描述操作后可验证的具体行为，**每个步骤必须对应一个预期结果** |

### 关键规则：步骤与预期结果一一对应

一条用例允许包含多个操作步骤，但**每一个操作步骤节点下必须且只能有一个预期结果节点**。

单步骤结构：
```
用例名称 [priority-N]
└── 前置条件
    └── 操作步骤
        └── 预期结果
```

多步骤结构（推荐，覆盖更完整）：
```
用例名称 [priority-N]
└── 前置条件
    ├── 操作步骤1
    │   └── 预期结果1
    ├── 操作步骤2
    │   └── 预期结果2
    └── 操作步骤N
        └── 预期结果N
```

---

## XMind 文件结构

XMind 文件本质是 ZIP 压缩包，至少包含以下文件：

```
*.xmind (ZIP)
├── content.json      # 思维导图节点数据（核心）
├── metadata.json     # 元数据
├── manifest.json     # 文件清单
└── content.xml       # 兼容旧版（可选）
```

## JSON 节点格式

每个节点的 JSON 结构：

```json
{
  "id": "UUID或24位唯一ID",
  "class": "topic",
  "title": "节点标题",
  "markers": [{"markerId": "star-red"}],
  "children": {
    "attached": [ /* 子节点数组 */ ]
  }
}
```

**模式A根节点**额外字段：`"structureClass": "org.xmind.ui.logic.right"`

**模式B根节点**：无 `structureClass`，title为年份（如"2026"）

---

## Python 生成脚本模板

```python
import json, zipfile, uuid

def gen_id():
    return str(uuid.uuid4()).replace('-', '')[:24]

def t(title, children=None, markers=None):
    """创建主题节点"""
    topic = {"id": gen_id(), "class": "topic", "title": title}
    if markers:
        topic["markers"] = [{"markerId": m} for m in markers]
    if children:
        topic["children"] = {"attached": children}
    return topic

def case(name, pre, steps_expects, priority="priority-2"):
    """创建用例: 用例名称 → 前置条件 → [步骤→预期结果, ...]
    steps_expects: [(step, expect), ...] 列表
    注意：步骤节点不添加任何 marker（禁止使用 tag-green）
    """
    if isinstance(steps_expects, tuple):
        steps_expects = [steps_expects]
    step_nodes = [t(s, [t(e)]) for s, e in steps_expects]
    return t(name, [t(pre, step_nodes)], [priority])


# ===== 模式A：迭代用例 =====

def build_prj_iterative(prj_id, prj_title, version, menu, func_cases, integ_cases=None):
    """构建完整 PRJ 节点（迭代用例模式）"""
    func_test = t("功能测试", [
        t(version, markers=["symbol-pin"]),
        t(prj_id, markers=["symbol-comment"]),
        t(f"PLM云-{menu}", [t("功能测试", func_cases)], ["star-red"]),
    ])
    children = [func_test]
    if integ_cases:
        integ_test = t("集成测试", [
            t(f"{version},集成测试", markers=["symbol-pin"]),
            t(prj_id, markers=["symbol-comment"]),
            t(f"PLM云-{menu}", [t("功能测试", integ_cases)], ["star-red"]),
        ])
        children.append(integ_test)
    return t(f"{prj_id}【{prj_title}】", children)

def build_xmind_iterative(version, module, prj_nodes):
    """组装迭代用例整棵树"""
    ver_node = t(version, [t(module, prj_nodes)])
    ver_node["customWidth"] = 168
    ver_node["position"] = {"x": 268.89, "y": 0}
    sheet = {
        "id": gen_id(),
        "class": "sheet",
        "rootTopic": {
            "id": gen_id(),
            "class": "topic",
            "title": "迭代用例",
            "structureClass": "org.xmind.ui.logic.right",
            "children": {"attached": [ver_node]}
        }
    }
    return [sheet]


# ===== 模式B：回归测试 =====

def build_xmind_regression(year, yearmonth, req_title, cases, questions_node=None, sheet_title=None):
    """
    组装回归测试整棵树（产品线固定为"金蝶征信"，无需传入）
    :param year: 根节点年份，如 "2026"
    :param yearmonth: 年月节点，如 "202604"
    :param req_title: 需求标题，如 "【泾渭云20260319】RPA银税一键授权回归测试 - 安徽"
    :param cases: 功能测试用例节点列表
    :param questions_node: 需求疑问点分支节点（普通文本节点，非用例格式，无图标），挂在产品线下功能测试同级
    :param sheet_title: sheet标题（可选，默认用 req_title）
    """
    product_children = [t("功能测试", cases)]
    if questions_node:
        product_children.append(questions_node)
    product_node = t("金蝶征信", product_children, ["star-red"])
    req_node = t(req_title, [product_node])
    month_node = t(yearmonth, [req_node])
    root = {
        "id": gen_id(),
        "class": "topic",
        "title": year,
        "children": {"attached": [month_node]}
    }
    sheet = {
        "id": gen_id(),
        "class": "sheet",
        "title": sheet_title or req_title,
        "rootTopic": root
    }
    # 注意：回归测试模式根节点无 structureClass
    return [sheet]


# ===== 通用写入 =====

def write_xmind(content, output_path):
    """
    将 sheets 写入 .xmind 文件
    :param content: sheet 列表（数组），如 [sheet1, sheet2, ...]
                   ⚠️ 必须是数组本身，切勿包装成 {"sheets": [...]}，否则 XMind 软件无法打开
    :param output_path: 输出 .xmind 文件路径
    """
    metadata = json.dumps({"creator": {"name": "Xmind", "version": "24.04"}})
    manifest = json.dumps({"file-entries": {"content.json": {}, "metadata.json": {}}})
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('content.json', json.dumps(content, ensure_ascii=False, indent=2))
        zf.writestr('metadata.json', metadata)
        zf.writestr('manifest.json', manifest)


# ===== 调用示例 =====
# sheets = build_xmind_regression(year="2026", yearmonth="202604", req_title="...", cases=[...])
# write_xmind(sheets, "output.xmind")   # ✅ 直接传 sheets 数组
# write_xmind({"sheets": sheets}, ...)  # ❌ 错误：会导致文件损坏
```

---

## 编写规范

### 用例名称
- **模式A格式**：`{操作类型}-{操作入口}-{具体场景}`
  - 示例：`批量新增-点击【新增】打开父项选择界面-界面展示与校验`
- **模式B格式**：`{流程描述}，{关键参数}`（与业务流程一一对应）
  - 示例：`不需要二次短验授权成功流程，tasktype=1`
  - 示例：`不需要二次短验，仅银税授权（tasktype=1）跳转到授权失败页`
- 用例名称必须包含**从哪个入口操作并进入**的完整描述

### 前置条件
- 明确系统状态，如"支持银税授权"、"已创建ECN，启用工艺批量更改"
- 明确数据准备，如"多个工序下挂接同一消耗物料"
- 明确配置要求，如"将授权税区添加到临时关闭字典：SILVER_TAX_SHUT_DOWN_AREA"

### 操作步骤
- 每个步骤描述一个操作动作
- **前端操作步骤**：如"进入H5采集页面URL"、"输入测试企业四要素"、"点击获取验证码"
- **后台验证步骤**：如"查看采集记录表jwy_tax.t_tax_declare_apply_record"
- 步骤之间并列挂在前置条件下
- **禁止使用 `tag-green` 等任何步骤级标记**，所有步骤节点（含DB验证步骤）保持统一样式，不添加任何 marker

### 预期结果
- 描述可验证的具体行为
- 前端：如"四要素通过，勾选授权协议跳转到登录页"
- 后台DB：如"对应taskid的状态为未登录003"
- **每个操作步骤必须且只能对应一个预期结果**

### 用例合并原则（模式A）

**相同界面的多个校验点应合并为一条用例，以多个步骤-预期结果形式描述：**

| 场景 | 合并前（多条用例） | 合并后（单条用例多步骤） |
|------|------------------|------------------------|
| 父项选择界面 | 过滤显示、置灰、选择显示、类型校验... | 界面展示与校验（6个步骤） |
| 返回明细界面 | 字段显示、版本规则、数量编辑、F7选择... | 字段显示与编辑（6个步骤） |
| 保存校验 | 必填校验、类型校验、状态校验、重复校验... | 各类校验场景（8个步骤） |

### 流程覆盖原则（模式B）

**回归测试用例应覆盖完整业务流程，包含：**

| 覆盖维度 | 示例 |
|---------|------|
| 正向主流程 | 不需要二次短验授权成功流程（各tasktype） |
| 异常/降级流程 | 银税授权关闭时降级走RPA |
| 需要二次短验流程 | 二次短验成功/失败 |
| 登录方式变体 | 账密登录 / 扫码登录 |
| 后台状态验证 | DB表状态、通知表、mongo数据 |

---

## 工作流程

### 模式A（迭代用例）
1. **读取输入**：读取测试方案（XMind/Markdown）和需求文档
2. **提取 PRJ 清单**：确认 PRJ 编号、需求标题、所属模块和菜单
3. **按 PRJ 编排用例**：每个 PRJ 拆分为功能测试和集成测试
4. **合并相同界面用例**：将同一界面的多个校验点合并为单条用例的多步骤
5. **逐条编写4列用例**：用例名称 → 前置条件 → 步骤 → 预期结果
6. **补充集成测试**：确保每个 PRJ 都有集成测试用例（priority-1）
7. **生成 XMind**：调用 `build_xmind_iterative()` 生成 .xmind 文件
8. **验证输出**：解压检查节点结构和总数，确认集成测试完整性

### 模式B（回归测试）
1. **读取输入**：读取测试方案或需求文档，确认需求编号、省份/区域
2. **确认树结构参数**：年份、年月、需求标题（含泾渭云编号），产品线固定为"金蝶征信"无需确认
3. **梳理测试场景**：按 tasktype / 流程类型 / 异常场景组织用例
4. **逐条编写4列用例**：用例名称 → 前置条件 → 步骤（含DB验证）→ 预期结果
5. **生成 XMind**：调用 `build_xmind_regression()` 生成 .xmind 文件
6. **验证输出**：解压检查节点层级（根→年月→需求→产品线→功能测试→用例）
7. **疑问点处理**：识别需求疑问点后，在产品线下功能测试同级创建"需求疑问点"分支（普通文本节点，非用例格式，无优先级图标），同时回复用户时以表格形式呈现

---

## 完整示例

详见 [example.md](example.md)，包含完整的 JSON 结构和 Python 代码示例。

---

## 需求疑问点模块

**适用场景**：在整理任何需求用例时，若发现需求描述存在歧义、缺失或不明确之处，必须识别并输出疑问点清单，供开发/产品确认后再补充用例。

### 何时输出疑问点

满足以下任意条件，必须提出疑问点：

| 触发条件 | 示例 |
|---------|------|
| 需求未说明异常时的返回格式/错误码 | 重试失败时返回什么HTTP状态码或业务错误？ |
| 超时参数可配置但未说明配置方式 | 配置项在哪里修改？支持热更新吗？ |
| 重试逻辑的触发条件边界不清晰 | HTTP 5xx、网络断开等是否也触发重试？ |
| 需求涉及第三方/外部系统，无法直接测试 | 如何模拟连接超时？是否有Mock环境？ |
| 日志/监控要求未说明 | 重试日志写到哪里？格式是什么？ |
| 需求影响范围未明确 | 该重试策略只针对OCR，还是所有中胜接口？ |
| 业务异常与技术异常处理方式是否相同 | OCR返回失败识别结果（200但内容为空）是否重试？ |

### 疑问点输出格式

疑问点需要**双重输出**：

1. **XMind用例文件内**：在产品线下、功能测试同级创建"需求疑问点"分支节点，每条疑问点作为普通文本子节点（**不使用用例4列格式，不带 priority 图标**），文本中包含疑问描述及建议确认方。

2. **回复用户时**：将疑问点以表格形式呈现，便于快速浏览：

```markdown
## 需求疑问点

| # | 疑问描述 | 影响的用例 | 建议确认方 |
|---|---------|-----------|-----------|
| 1 | XXX不明确 | 用例X、用例Y | 开发/产品 |
| 2 | YYY未说明 | 用例Z | 开发 |
```

### 疑问点在XMind中的结构示例

疑问点**不是用例**，不遵循4列格式，不带优先级图标，仅作为说明性文本节点：

```
金蝶征信                             [star-red]
├── 功能测试
│   └── {用例名称}                  [priority-2]
│       └── ...（4列用例结构）
└── 需求疑问点                       ← 普通分支节点，无图标
    ├── 疑问点1：{疑问描述}【建议确认方：XX】    ← 普通文本节点，无图标
    ├── 疑问点2：{疑问描述}【建议确认方：XX】
    └── 疑问点3：{疑问描述}【建议确认方：XX】
```

**关键规则**：
- 疑问点节点挂在**产品线下、功能测试同级**，不混入用例列表
- 疑问点文本节点**不带任何 marker/图标**（尤其不用 priority-2）
- 疑问点**不拆分为前置条件/步骤/预期**，整体作为一段说明文本
- 文本末尾标注`【建议确认方：XX】`

### 本需求（中胜OCR重试策略）疑问点示例

以下是针对「中胜营业执照OCR识别增加重试策略」整理的疑问点，作为参考示例：

| # | 疑问描述 | 影响的用例 | 建议确认方 |
|---|---------|-----------|-----------|
| 1 | **重试失败后的返回内容**：两次均失败时，业务层返回什么错误码或提示信息？前端如何展示？ | 用例3、用例5 | 开发/产品 |
| 2 | **连接超时时间3秒是否可配置**：需求说"Read Timeout 20秒支持配置"，但连接超时3秒未提及是否可配置 | 用例10（可配置验证） | 开发 |
| 3 | **HTTP 5xx 等服务端错误是否触发重试**：需求仅说"读取超时"和"连接异常"，5xx/4xx等HTTP错误码是否也需要重试？ | 用例9（非超时异常） | 开发/产品 |
| 4 | **重试链接生成机制**：需求背景提到"每次请求都生成新链接"，重试时是重新生成新链接还是复用原链接？ | 用例11 | 开发 |
| 5 | **测试环境模拟方案**：连接超时/读取超时如何在测试环境模拟？是否有Mock服务或专用测试配置？ | 全部超时相关用例 | 开发/测试环境负责人 |
| 6 | **影响范围**：重试策略是仅针对营业执照OCR识别，还是所有调用中胜接口的场景均生效？ | 影响范围测试 | 开发/产品 |
| 7 | **重试日志规范**：重试日志输出到哪个日志文件？日志中需要包含哪些字段（如请求ID、重试次数、耗时）？ | 用例7（重试次数上限验证） | 开发 |
