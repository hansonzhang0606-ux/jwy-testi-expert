# xmind-to-testcase

将 XMind 需求文档转换为 Excel 测试用例文件。

---

## 内嵌资源（其他测试人员无需 GitHub 即可复用）

本 Skill 已将团队 DMP 模板与经典 XMind 转换器**内嵌**于专家包，避免依赖外部仓库分发：

| 资源 | 路径（相对 `skills/`） | 作用 |
|------|----------------------|------|
| 团队 DMP 模板 | `assets/dmp_template.xlsx` | 14 列标准模板，前 4 行样式权威来源 |
| 经典 XMind 转换器 | `assets/convert_jwy.py` | 独立脚本，专门处理经典 XMind（`content.xml`，Step3-选项1 产出） |

**模板查找顺序**（`scripts/convert.py` 的 `find_template`）：
1. 输出目录的 `excel模板.xlsx`
2. 输出目录的 `模板 - 副本.xlsx`
3. **本 Skill 内嵌 `assets/dmp_template.xlsx`**（兜底，确保任何测试人员在空白目录也能跑通）
4. 输出目录任意 `*.xlsx`

> 分发专家包时，上述 `assets/` 目录会随包一起复制；其他测试人员首次使用 Step4 时，即使本地无模板，也会自动回退到内嵌模板，无需从 GitHub 拉取。

**支持的 XMind 格式**（升级后的 `scripts/convert.py`）：
- XMind Zen：`content.json`（测试点/预期结果 节点对，或通用叶子节点）
- 经典 XMind：`content.xml`（L1 模块 / L2 子模块 / L3 条件 / L4 数据 / L5 预期；「需求疑问点(待确认)」分支自动跳过）

> 历史说明：原 `scripts/convert.py` 仅支持 XMind Zen，无法解析 Step3-选项1 产出的经典 XMind（表现为 `RuntimeError: 仅支持 XMind Zen`）。现已内置经典格式解析，可直接复用。

---

## 元数据

- **名称**: xmind-to-testcase
- **版本**: 1.8.1
- **作者**: WorkBuddy
- **描述**: 读取 XMind 需求脑图文件，解析需求结构，生成符合 DMP 模板格式的 Excel 测试用例文件。以模板列名为唯一权威来源（第 3 行为列名行，第 5 行起为数据行），按列名映射写入，绝不修改或新增列名。

## 触发条件

当用户提出以下需求时触发：
- "把 XMind 转成 Excel 用例"
- "XMind 转测试用例"
- "根据 XMind 生成 Excel 用例"
- "将 xmind 转化为 excel 用例"

---

## 核心原则：基于团队 DMP 模板生成，前 4 行原样保留

**生成的 Excel 必须基于团队提供的 DMP 模板文件（如 `excel模板.xlsx` / `模板 - 副本.xlsx`），不得自行重建表头。模板文件是唯一权威来源：**

1. **加载模板** — 用 `openpyxl.load_workbook(模板路径)` 打开模板；模板固定 14 列，第 1-4 行为表头区。
2. **前 4 行冻结保留（含字体/颜色/填充）** — 第 1 行标题、第 2 行使用说明、第 3 行英文列名、第 4 行灰色中文说明（含 `*` 必录标记）。**字体、颜色、填充、对齐、边框全部原样保留，绝不重建或覆盖任何单元格。** 只要 `load_workbook` 后仅写入数据行（第 5 行起），openpyxl 会自动保留这些样式。
3. **按名映射** — 从模板「第 3 行」读取英文列名建立 `列名 → 列索引` 映射；所有数据写入通过列名定位，绝不使用硬编码列号。
4. **不增不改** — 不新增列、不重命名列、不删除列、不调整列顺序、不改动第 1-4 行。
5. **数据从第 5 行起写** — 若模板自带示例数据行（如第 5 行示例），生成时先清空第 5 行及之后的内容，再从第 5 行写入正式用例。

---

## DMP 模板标准结构

DMP 模板固定为 **14 列**，结构如下：

| 列索引 | 列名（英文 key） | 中文说明 | 数据行写入规则 |
|--------|-----------------|----------|---------------|
| 0 | `team` | *项目组 | **固定值**："金蝶征信" |
| 1 | `caseGroup` | *功能路径（用例分组），层级之间用"-"间隔 | XMind 路径中"功能测试"一级节点前的路径，层级用 "-" 分隔，不含测试类型后缀 |
| 2 | `name` | *功能点（用例名称） | 叶子节点标题，**自动添加"验证"前缀** |
| 3 | `preCondition` | 功能说明（前置条件） | 从 XMind 节点备注提取，多条用 `\n` 换行 |
| 4 | `input` | input（步骤描述），多个步骤的请在单元格内换行输入。 | 测试操作步骤，**每条用例该列至少 3 个编号步骤**，步骤与 output 一一对应，编号后用 `\n` 换行 |
| 5 | `output` | output（预期结果），多个结果的请在单元格内换行输入。 | 预期结果，**每条用例该列至少 3 个编号步骤**，与 input 一一对应，编号后用 `\n` 换行 |
| 6 | `product` | *产品 | **固定值**："金蝶征信" |
| 7 | `modulePath` | *模块路径，层级之间用"-"间隔 | **固定值**："金蝶征信" |
| 8 | `version` | 适用版本（产品版本） | 从 XMind 根节点日期推断，如 `V2026.7.16` |
| 9 | `caseType` | *用例类型 | 从 XMind 一级节点推断：功能测试/集成测试/性能测试/安全测试 |
| 10 | `source` | 来源 | **保持空值，不填写** |
| 11 | `caseLevel` | 用例级别 | 根据场景类型填写：P0（核心流程）/ P1（重要分支）/ P2（边缘场景） |
| 12 | `manager` | *责任人，重名的请输入工号 | **固定值**："余萍" |
| 13 | `autoState` | 已实现自动化 | **默认值**："否" |

**模板行结构**（固定不可改）：
- 第 1 行（index 0）：标题 `用例管理 # dmp_testcase`
- 第 2 行（index 1）：使用说明（字段录入要求等）
- 第 3 行（index 2）：列名（英文 key，如上表）
- 第 4 行（index 3）：列中文说明
- 第 5 行起（index 4+）：数据行

---

## 执行步骤

### 第一步：解析 XMind 文件

使用 Python 的 zipfile 和 json 模块读取 XMind 文件内容：

```python
import zipfile, json

def parse_xmind(xmind_path):
    z = zipfile.ZipFile(xmind_path)
    c = json.loads(z.read('content.json'))
    root = c[0]['rootTopic']

    def walk(node, path=None):
        if path is None:
            path = []
        title = node.get('title', '')
        current_path = path + [title]
        notes = node.get('notes', {}).get('plain', {}).get('content', '')
        children = node.get('children', {}).get('attached', [])

        if not children:
            # 叶子节点 → 生成一条用例
            return [{'path': current_path, 'title': title, 'notes': notes}]

        results = []
        for child in children:
            results.extend(walk(child, current_path))
        return results

    return walk(root)
```

提取需求的关键信息：
- 需求名称/编号（从根节点路径）
- 功能模块
- 处理逻辑（存量/增量）
- 预警机制
- 码表映射
- 接口信息
- 性能要求
- 异常场景

### 第二步：加载团队模板并建立列名映射（保留前 4 行样式）

**核心：用 `load_workbook` 加载团队 DMP 模板文件（默认 `excel模板.xlsx` 或 `模板 - 副本.xlsx`，优先从输出目录读取；缺失则向用户索取），从模板第 3 行读取列名建立映射；前 4 行样式由 openpyxl 自动保留，绝不修改。**

```python
import openpyxl

def load_template_mapping(excel_path):
    """从模板读取列名 → 列索引映射"""
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active  # 或 wb[wb.sheetnames[0]]

    # 第 3 行（index 2）是列名行
    col_map = {}
    for col_idx in range(1, ws.max_column + 1):
        name = ws.cell(row=3, column=col_idx).value
        if name and str(name).strip():
            col_map[str(name).strip()] = col_idx

    # 数据起始行 = 第 5 行（index 4）
    data_start_row = 5

    return wb, ws, col_map, data_start_row
```

### 第三步：提取 XMind 路径信息

从 XMind 脑图路径中提取关键字段：

```python
def extract_path_info(leaf_path):
    """
    leaf_path 示例：
    ['2026', '202606', '20260630', '【泾渭云20260630】行政处罚接口优化', '功能测试', '企业查询', 'keyword精确匹配存在的企业']
    """
    # 找到测试类型节点位置
    test_types = ['功能测试', '集成测试', '性能测试', '安全测试', '异常场景', '边界场景']
    test_type_idx = None
    test_type = '功能测试'

    for i, node in enumerate(leaf_path):
        if node in test_types:
            test_type_idx = i
            test_type = node
            break

    # caseGroup：测试类型节点之前的路径，用 "-" 分隔
    if test_type_idx is not None:
        case_group = '-'.join(leaf_path[:test_type_idx])
    else:
        case_group = '-'.join(leaf_path[:-1])

    # name：叶子节点标题（最后一个元素）
    name = leaf_path[-1]

    # version：从路径中提取日期
    version = 'V2026.7.16'  # 默认，可从根节点日期推断

    return case_group, name, test_type, version
```

### 第四步：生成测试用例

根据 XMind 解析的需求内容，设计测试用例。

**用例设计原则**：
1. **input 列与 output 列每条用例至少 3 个编号步骤**（步骤之间用 `\n` 换行），且两步数一致、一一对应。
2. 步骤优先取自 XMind 的「测试点 / 预期结果」文本；若不足 3 步，用规范的通用步骤（进入页面/准备数据 → 执行操作 → 检查响应与落库）补全至 3 步。
3. 覆盖正常场景、异常场景、边界场景
4. 从 XMind 叶子节点提取用例，非叶子节点不生成用例

**字段填充规则**：

```python
def build_test_case(leaf_info, case_group, test_type, version):
    """
    构建一条测试用例数据，返回 dict，key 为列名
    """
    name = f"验证{leaf_info['title']}"

    # 根据场景类型设置 caseLevel
    path_str = '-'.join(leaf_info['path'])
    if '异常' in path_str or '错误' in path_str:
        case_level = 'P1'
    elif '边界' in path_str:
        case_level = 'P2'
    else:
        case_level = 'P0'

    pre_condition = leaf_info.get('notes', '')
    if not pre_condition:
        pre_condition = (
            "1. 测试环境已部署\n"
            "2. 数据源连接正常\n"
            "3. 相关依赖服务正常运行"
        )

    return {
        'team': '金蝶征信',
        'caseGroup': case_group,
        'name': name,
        'preCondition': pre_condition,
        'input': (
            "1. 确认测试环境正常，相关服务可用\n"
            "2. 准备测试数据及参数\n"
            "3. 发送请求/执行操作\n"
            "4. 检查响应结果"
        ),
        'output': (
            "1. 测试环境运行正常\n"
            "2. 参数准备完成，格式符合规范\n"
            "3. 请求正常执行，返回预期响应\n"
            "4. 结果符合预期"
        ),
        'product': '金蝶征信',
        'modulePath': '金蝶征信',
        'version': version,
        'caseType': test_type,
        'source': '',  # 保持空值
        'caseLevel': case_level,
        'manager': '余萍',
        'autoState': '否',
    }
```

### 第五步：按列名写入 Excel

**核心：通过 `col_map` 映射按列名写入，不依赖列号。**

```python
from openpyxl.styles import Alignment
from copy import copy

def write_test_cases(ws, col_map, data_start_row, test_cases):
    """按列名映射写入测试用例数据"""
    for i, tc in enumerate(test_cases):
        row = data_start_row + i

        # 从模板的数据行（如果已存在）复制样式
        # 否则设置默认样式
        template_row = data_start_row  # 使用第一行数据行作为样式参考

        for col_name, value in tc.items():
            if col_name not in col_map:
                continue  # 跳过模板中不存在的列
            col_idx = col_map[col_name]
            cell = ws.cell(row=row, column=col_idx)
            if value is not None:
                cell.value = value

        # 设置需要自动换行的列
        wrap_cols = ['preCondition', 'input', 'output']
        for cn in wrap_cols:
            if cn in col_map:
                cell = ws.cell(row=row, column=col_map[cn])
                cell.alignment = Alignment(wrap_text=True, vertical='top')

        ws.row_dimensions[row].height = 150
```

### 第六步：保存文件

```python
output_path = excel_path  # 或用户指定路径
wb.save(output_path)
print(f"用例已保存到: {output_path}")
```

---

## 关键要点

1. **模板列名是唯一权威来源** — 绝不硬编码列号，始终从模板读取列名
2. **按名映射写入** — 所有数据通过 `col_map[列名]` 定位列位置
3. **不增不改不删** — 不新增列、不修改列名、不删除列、不调整模板结构
4. **保留模板原样** — 第 1-4 行（标题/说明/英文列名/灰色中文说明）的字体、颜色、填充、对齐、边框原封不动；仅从第 5 行起写入数据
5. **多行文本** — step 和预期结果使用 `\n` 换行，设置 `wrap_text=True`
6. **行高设置** — 根据内容多少设置合适的行高（建议 120-150）
7. **从叶子节点提取** — 只从 XMind 叶子节点生成用例，非叶子节点不生成
8. **name 自动加"验证"前缀** — 如叶子节点标题为"score 匹配"，则 name 为"验证score 匹配"
9. **source 列保持空值** — 不填任何内容
10. **固定值字段**：team="金蝶征信"，product="金蝶征信"，modulePath="金蝶征信"，manager="余萍"

## 用例覆盖维度

- 正常流程（单条/批量）
- 异常流程（无映射/空值/无效参数）
- 预警验证（触发条件/内容格式）
- 性能测试（大数据量/响应时间）
- 兼容性（多接口复用）

## 产物命名（流水线 Step4）

生成的 Excel 落到「指定目录」，文件名必须为 `需求名_测试用例.xlsx`：

- `需求名`：从需求文档标题 / 输入文件名（或 Step3 脑图根节点）提取，去掉团队前缀（`【余萍】`、`【TD-AI】`），保留需求标识标签（如 `【泾渭云YYYYMMDD】`）。
- 示例：`【泾渭云20260630】行政处罚信息（不分页）接口输出逻辑优化_测试用例.xlsx`。
- 团队前缀（`【余萍】`、`【TD-AI】`）**不在此步加**，仅在流水线 Step5 上传前追加。

## 路径规范

**默认保存路径格式**：`D:\需求\2026\月.日\文件名.xlsx`

用户使用的目录命名规则为 `月.日`（如 `7.16`、`6.4`）。

**功能路径（XMind 脑图根节点层级）命名规则**：`年份-年月-年月日-文件名`
- `caseGroup` 使用 `-` 分隔层级，不使用 `/`

当用户未指定输出路径时，默认保存到 `D:\需求\2026\<最新日期>\`。

## 示例

**用户输入**：
> 把 D:\需求\2026\7.16\【泾渭云20260630】行政处罚信息（不分页）接口输出逻辑优化.xmind 转成 Excel 用例

**执行过程**：
1. 读取 XMind 文件，解析需求结构（测试点/预期结果节点或叶子节点）
2. 用 `load_workbook` 加载团队 DMP 模板（`excel模板.xlsx` / `模板 - 副本.xlsx`），建立列名映射；**前 4 行（含字体、灰色填充颜色）原样保留**
3. 从节点生成测试用例（正常/边界/异常场景）
4. 按列名映射写入第 5 行起的数据，固定值字段自动填充
5. 保存并打开文件；校验第 1-4 行与模板完全一致

**输出结果**：
- 文件：`D:\需求\2026\7.16\【泾渭云20260630】行政处罚信息（不分页）接口输出逻辑优化_测试用例.xlsx`
- 每条用例 input / output 至少 3 个编号步骤，一一对应
- 所有 14 列按模板列名正确映射；第 1-4 行与团队模板逐字逐样式一致

> **参考脚本**：`scripts/convert.py` 已内置「加载模板 + 仅写第 5 行起 + 保留前 4 行字体/颜色/填充」的实现，可直接复用以保证本约束不被破坏。
