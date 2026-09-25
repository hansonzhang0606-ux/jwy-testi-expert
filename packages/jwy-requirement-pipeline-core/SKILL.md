---
name: jwy-requirement-pipeline
description: |
  泾渭云需求全流程「组合编排」Skill 套件。按 step 关键字把「需求文档 → 需求确认 → 代码分析 → 需求脑图 → DMP 用例 → Confluence 归档」整条链路自动调度到 7 个子 skill，并把产物统一落到用户指定的目录。

  触发关键字：
  - step1 / 分析确认需求 / 需求确认 / 需求分析 → 调度 requirement-analysis-docx
  - step2 / 代码分析 / code analyze / 分析变更 → 调度 code-analyzer
  - step3 / 需求分析生成脑图 / 生成脑图 → 按选项调度 xmind-testcase（选项1）/ req-analysis-xmind（选项2）/ generate-xmind-cases（选项3）
  - step4 / xmind转excel / 脑图转dmp / 导入DMP → 调度 xmind-to-testcase（仅选项1/2 后可）
  - step5 / 上传confluence / 归档 / 归类上传 → 调度 upload-to-confluence

  当用户消息包含上述任一 step 关键字 + 指定目录（输出目录）时，进入本编排。

  本 skill 为**自包含**套件：已将全部 7 个子 skill 内嵌于本 skill 根目录下的 `skills/` 子目录（每个含独立 SKILL.md / scripts / references），团队只需安装这一个总 skill 即可，无需再单独安装任何子 skill。
---

# 泾渭云需求全流程编排（组合编排 Skill）

## 一、定位

把一次需求评审到归档的工作流，拆成 5 个可独立触发的步骤，每一步自动调度对应的子 skill，产物统一落到**指定目录**，并用状态文件记录链路进度与依赖关系。

```
需求文档 → [Step1 需求确认] ┐
          → [Step2 代码分析] ┴─→ [Step3 需求脑图(三选一)] ─→(选项1/2)→ [Step4 转DMP] → [Step5 归档]
                                                            └─(选项3)────────────────→ [Step5 归档]
```

## 二、触发与基本约定

- 用户消息包含 `step1`~`step5` 任一关键字，或对应的中文触发词（见 `references/steps.md`），即进入本编排。
- **每个 step 都必须带「指定目录 / 输出目录」**（绝对路径）。所有产物与该步骤状态文件 `.jwy_pipeline_state.json` 都落在此目录。
- 调度子 skill **一律使用本 skill 内嵌的版本**：先 `Read` 本 skill 根目录下 `skills/<子skill名>/SKILL.md`，再按其指令执行（运行其中的 `scripts/` 脚本、参考 `references/`）。**不要**用 Skill 工具去加载外部的、同名子 skill——团队其他成员很可能没有单独安装它们，本套件必须自包含可运行。子 skill SKILL.md 中凡是写 `scripts/xxx` 或 `references/yyy` 的相对路径，实际执行时一律解析为「本 skill 根目录/skills/<子skill名>/scripts/xxx」（或 references），即相对于该子 skill 自身目录。不要重写子 skill 的内部逻辑，只负责解析参数、喂入、回收产物。
- 跨步骤状态与 step4 依赖校验，统一用 `scripts/pipeline_state.py`（标准库，无依赖）。

## 三、路由表：判断用户要跑哪一步

先识别消息中的 **step 关键字** 与 **参数**，再决定调度哪些子 skill：

| 用户输入特征 | 执行的 step | 调度的子 skill |
|-------------|------------|---------------|
| 含 `step1` 或「分析确认需求/需求确认」+ 需求文档（**无**仓库/分支/基线） | Step 1 | `requirement-analysis-docx` |
| 含 `step1,step2` 或同时具备「需求确认 + 仓库路径/开发分支/对比基线/重点关注」 | Step 1 + Step 2 | `requirement-analysis-docx` + `code-analyzer` |
| 含 `step3-选项1`（或「生成测试脑图/测试点脑图/非转dmp」）+「需求分析生成脑图」 | Step 3 选项1（非转dmp版脑图设计） | `xmind-testcase` |
| 含 `step3-选项2`（或「接口维度分析/入参出参/扣费分析/定制化产品」）+「需求分析生成脑图」 | Step 3 选项2（产品接口维度脑图设计） | `req-analysis-xmind` |
| 含 `step3-选项3`（或「迭代用例/回归测试/转dmp/DMP 用例/PRJ」）+「需求分析生成脑图」+ 提供文档 | Step 3 选项3（直接导入dmp版脑图设计） | `generate-xmind-cases` |
| 含 `step4`（或「xmind转excel/脑图转dmp/导入DMP」） | Step 4 | `xmind-to-testcase` |
| 含 `step5`（或「上传confluence/归档/归类上传」） | Step 5 | `upload-to-confluence` |

> 若用户只说「需求分析生成脑图」但没指明选项，停下来向用户确认走选项1 / 选项2 / 选项3（三者产物不同、后续链路也不同）。

## 四、参数解析规则（每一步要提取什么）

- **指定目录 / 输出目录**：必填。从消息中的「目录」「输出到」「落地到」「指定目录」等后提取绝对路径。找不到则追问用户。
- **需求文档**：docx / md / 图片 / 文字；Step1、Step3 各选项的输入。
- **Step2 联动参数**：仓库路径、开发分支（目标分支）、对比基线（基线分支）、重点关注（分析侧重）。
- **Step3 输入来源**：优先复用状态文件中 `step1`/`step2` 的产物（调用 `products --step step3-inputs` 获取）；若用户额外提供了文档，则直接用用户给的。
- **Step4 输入**：Step3 生成的 `.xmind` + 可选 DMP 模板路径 + 列填充提示（功能路径列=caseGroup / 适用版本列=version / 责任人列=manager）。
- **Step5 输入**：待上传目录、文件清单（.docx/.xmind/.xlsx 等）、命名规则、上传目录 id（Confluence 页面 pageId）。

## 五、标准执行流程（每个 step 通用）

1. **解析**：从用户消息提取 step 关键字与全部参数，确认「指定目录」存在。
2. **初始化状态**：`python scripts/pipeline_state.py init --output-dir <指定目录>`（幂等，已存在则读取）。
3. **依赖校验（仅 Step4）**：
   ```bash
   python scripts/pipeline_state.py check --output-dir <指定目录> --step step4
   ```
   - `allowed=true` → 继续。
   - `allowed=false` → **停止**，把 `reason` 原样告知用户（典型为「step3-选项3 无step4」或「请先完成 step3 选项1/2」），不再调度。
4. **调度子 skill**：按「第十节·调用规范」`Read` 本 skill 内嵌的 `skills/<子skill名>/SKILL.md` 并执行，把解析出的参数作为该子 skill 的输入传入；输出目录统一指向「指定目录」。
5. **回收产物**：子 skill 完成后，罗列「指定目录」中本次新增的文件（或取子 skill 报告的产物路径），调用：
   ```bash
   python scripts/pipeline_state.py record --output-dir <指定目录> --step <stepId> --products "<产物1>;<产物2>"
   ```
   stepId 取值：`step1` / `step2` / `step3-1` / `step3-2` / `step3-3` / `step4` / `step5`。
6. **汇报**：给出本步产物路径、状态文件位置、以及下一步建议（尤其提示 Step4 是否可用）。

## 六、依赖约束（重要，务必执行）

- **Step4 仅允许在 Step3-选项1 或 Step3-选项2 完成后执行。**
- Step3-选项3（generate-xmind-cases）已直接产出 DMP 兼容格式，**没有 Step4**；若用户走到选项3 后再输入 step4，必须提示「step3-选项3 无step4」，并建议直接走 step5 归档。
- 该约束由 `pipeline_state.py check --step step4` 自动判定（依据状态文件中的 `last_step3`）。

## 七、状态脚本用法

```bash
# 初始化 / 读取状态（幂等）
python scripts/pipeline_state.py init --output-dir D:\需求\2026\7.16

# 记录某步产物（更新状态文件）
python scripts/pipeline_state.py record --output-dir D:\需求\2026\7.16 --step step3-1 --products "D:\需求\2026\7.16\【泾渭云20260716】xxx_测试脑图.xmind"

# 校验 step4 依赖（退出码 0=允许，3=拒绝；stdout 含 allowed/reason）
python scripts/pipeline_state.py check --output-dir D:\需求\2026\7.16 --step step4

# 取 step3 可复用的 step1/step2 产物路径
python scripts/pipeline_state.py products --output-dir D:\需求\2026\7.16 --step step3-inputs

# 查看完整状态
python scripts/pipeline_state.py status --output-dir D:\需求\2026\7.16
```

> 脚本使用托管的 Python 运行（如 `C:\Users\<用户名>\.workbuddy\binaries\python\versions\3.13.12\python.exe scripts/pipeline_state.py ...`）。

## 八、产物命名规范（统一，必须执行）

所有产物统一落盘到用户「指定目录」，并**统一以「需求名_步骤」命名**，便于团队辨识与 step5 归档。

**需求名定义**：从需求文档标题或输入文件名提取的需求主体名称，**去掉团队强制前缀**（`【余萍】`、`【TD-AI】` 等），**保留需求自身标识标签**（如 `【泾渭云YYYYMMDD】`）。示例：`【余萍】【TD-AI】【泾渭云20260804】纳税H5增加登录身份提示` → 需求名 = `【泾渭云20260804】纳税H5增加登录身份提示`。

**各步骤产物命名表**：

| step | 子 skill | 产物 | 命名格式（落盘到指定目录） |
|------|----------|------|---------------------------|
| Step1 | requirement-analysis-docx | 需求确认 DOCX | `需求名_需求确认.docx` |
| Step2 | code-analyzer | 代码分析文档 | `需求名_代码分析.docx` |
| Step3-选项1 | xmind-testcase | 非转dmp脑图 | `需求名_测试脑图.xmind` |
| Step3-选项2 | req-analysis-xmind | 产品接口维度脑图 | `需求名_接口脑图.xmind` |
| Step3-选项3 | generate-xmind-cases | 直接导入dmp脑图 | `需求名_DMP用例.xmind` |
| Step4 | xmind-to-testcase | DMP 测试用例 Excel | `需求名_测试用例.xlsx` |
| Step5 | upload-to-confluence | 子页 + 附件 | 子页标题 = 团队前缀 + 需求名；附件沿用上表命名（Step5 上传前再追加用户前缀如 `【余萍】【TD-AI】`） |

**要点**：
- 各子 skill 的 SKILL.md 已写入上述命名约束，调度时由子 skill 生成对应文件名，编排层不擅自改名。
- 团队前缀（`【余萍】`、`【TD-AI】`）**只在 Step5 上传前追加**（由 `upload-to-confluence` 的 `--prefix` 规整），Step1~Step4 落盘的文件不带前缀。
- Step5 归档时若用户提供「上传目录 id」（Confluence pageId），走 `upload-to-confluence` 的**直接模式**（pageId + 文件），按团队标准 `<ac:link>` 格式更新**子页**正文。

## 九、完整链路示例

**场景：接口分析链路（选项2 路径）**
```
用户: step1,step2 需求确认 文档:D:\需求\2026\7.16\接口需求.docx
      仓库路径:D:\workspace\jwy-product 开发分支:feature/xxx 对比基线:main 重点关注:扣费逻辑
      → 调度 requirement-analysis-docx + code-analyzer，产物落到 D:\需求\2026\7.16

用户: step3-选项2 需求分析生成脑图
      → 复用 step1/step2 产物，调度 req-analysis-xmind，产出 .xmind

用户: step4 文档:D:\需求\2026\7.16\xxx.xmind 责任人列:余萍
      → check 通过（last_step3=选项2），调度 xmind-to-testcase，产出 .xlsx

用户: step5 目录:D:\需求\2026\7.16 上传目录id:97124875 命名:按团队规范
      → 调度 upload-to-confluence，上传并.append 页面正文
```

**场景：完整 DMP 链路（选项3 路径，无 step4）**
```
用户: step1 需求确认 文档:D:\需求\2026\7.16\需求.docx
用户: step3-选项3 需求分析生成脑图 PRJ:PRJ-2026-xxx 版本:R20260416
      → 调度 generate-xmind-cases，产出 DMP 兼容 .xmind
用户: step4 ...
      → check 拒绝，提示「step3-选项3 无step4」，建议直接 step5
用户: step5 目录:... 上传目录id:... 
      → 调度 upload-to-confluence 归档
```

## 十、内嵌子 skill 索引与调用规范（自包含）

本套件已把 7 个子 skill **完整内嵌**于本 skill 根目录下的 `skills/` 子目录，每个子 skill 都是独立可执行的单元（含自己的 SKILL.md / scripts / references）。

| 子 skill（内嵌路径） | 用途 |
|----------|------|
| `skills/requirement-analysis-docx/` | 需求确认 DOCX |
| `skills/code-analyzer/` | 代码变更分析 |
| `skills/xmind-testcase/` | 非转dmp版脑图设计 |
| `skills/req-analysis-xmind/` | 产品接口维度脑图设计 |
| `skills/generate-xmind-cases/` | 直接导入dmp版脑图设计 |
| `skills/xmind-to-testcase/` | XMind → Excel DMP |
| `skills/upload-to-confluence/` | Confluence 归档 |

### 调用规范（重要）

1. **本 skill 的根目录** = 本 `SKILL.md` 所在目录（安装到任意位置都成立，不写死绝对路径）。
2. 需要调度某子 skill 时：
   - 用 `Read` 工具读取 `skills/<子skill名>/SKILL.md`；
   - 严格按其 SKILL.md 的指示执行（包括运行 `scripts/` 下的脚本、参考 `references/`）；
   - 子 skill 中凡是出现 `scripts/xxx` 或 `references/yyy` 的相对路径，一律解析为「本 skill 根目录/skills/<子skill名>/scripts/xxx」（或 references），即相对于该子 skill 自身目录。
3. **不要**使用 `Skill` 工具去加载外部的、同名子 skill。本套件必须自包含：团队其他成员即便没有单独安装那些子 skill，也能通过本总 skill 完整跑通流程。
4. 子 skill 内部的示例路径（如 `D:\需求\2026`、仓库路径 `D:\JavaWorkSpace\jwy3`）仅为演示，运行时由编排层传入真实参数覆盖，请勿直接照搬。

### 团队部署与依赖说明

- **安装**：将本 `jwy-requirement-pipeline` 整个目录放入 `~/.workbuddy/skills/`（或团队共享 skill 目录）即可，无需再安装上述任何子 skill。
- **Python 运行时**：子 skill 脚本使用托管的 Python（如 `C:\Users\<用户名>\.workbuddy\binaries\python\versions\3.13.12\python.exe`）。如团队运行环境不同，请改用其本机 Python 3.11+。
- **Confluence 凭据**：`upload-to-confluence` 子 skill 从其脚本中读取 `~/.workbuddy/mcp.json` 的 `mcpServers.Confluence.env`（CONFLUENCE_URL / CONFLUENCE_USERNAME / CONFLUENCE_API_TOKEN）。每个成员需在本机配置自己的 Confluence 连接器凭据；未配置时该子 skill 会报错提示。
- **状态脚本**：本 skill 的 `scripts/pipeline_state.py`（标准库，无第三方依赖）用于跨步骤状态与 step4 依赖校验，路径解析同上为「本 skill 根目录/scripts/」。

> 详细每步参数/产物/关键字见 `references/steps.md`。
