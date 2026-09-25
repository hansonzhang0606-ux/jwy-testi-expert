# 各步骤契约明细（references/steps.md）

本文件是 `SKILL.md` 的配套速查表。每一步都给出了：**绑定子 skill（内嵌于 `skills/`）**、**触发关键字**、**提取参数**、**产物**、**依赖**。编排逻辑以 `SKILL.md` 为准，本表用于核对参数与输出。

---

## 全局参数

| 参数 | 含义 | 是否必填 | 说明 |
|------|------|---------|------|
| 指定目录 / 输出目录 | 产物落盘的绝对路径 | ✅ 必填 | 所有 step 产物与状态文件 `.jwy_pipeline_state.json` 都在这里 |
| 需求文档 | docx / md / 图片 / 文字 | 视步骤 | requiremnt-analysis / 各脑图步骤的输入 |

---

## Step 1：需求确认

| 项 | 内容 |
|----|------|
| 绑定（内嵌） | `skills/requirement-analysis-docx/` |
| 触发关键字 | `step1` / `分析确认需求` / `需求确认` / `需求分析` / `requirement analysis` |
| 提取参数 | 需求文档（docx/md 文件或文字/截图） |
| 产物 | `需求名_需求确认.docx`（结构化需求分析 DOCX / 需求确认清单） |
| 依赖 | 无 |

> 仅当消息中**不含**仓库路径/开发分支/对比基线/重点关注时，只跑 Step 1。

---

## Step 2：代码分析（非必选，与 Step1 联动）

| 项 | 内容 |
|----|------|
| 绑定（内嵌） | `skills/code-analyzer/` |
| 触发关键字 | `step2` / `代码分析` / `code analyze` / `分析变更` / `实现分析` |
| 提取参数 | 仓库路径、开发分支（目标分支）、对比基线（基线分支）、重点关注 |
| 产物 | `需求名_代码分析.docx`（代码分析总结：技术栈覆盖、业务规则、调用链、SQL/数据流、配置值、测试关注点） |
| 依赖 | 与 Step1 一起触发（消息同时含「需求确认 + 仓库路径类参数」） |

> 当消息同时具备「需求文档 + 仓库路径/开发分支/对比基线/重点关注」时，编排同时调度内嵌的 `skills/requirement-analysis-docx/`（`step1`）与 `skills/code-analyzer/`（`step2`）。

---

## Step 3：需求分析生成脑图（三选一）

三项互斥，按用户选择的「选项」调度对应 skill。输入优先复用 `step1` / `step2` 产物，其次使用用户直接提供的文档。

### 选项1：非转dmp版脑图设计

| 项 | 内容 |
|----|------|
| 绑定（内嵌） | `skills/xmind-testcase/` |
| 触发关键字 | `step3-选项1` / `生成测试脑图` / `测试点脑图` / `xmind testcase` / `非转dmp` |
| 提取参数 | 需求文档/截图/PRD（或复用 step1/step2 产物） |
| 产物 | `.xmind` 非转dmp测试脑图（5 层纯文本风格，强制 UI 展示效果覆盖），命名 `需求名_测试脑图.xmind` |
| 后续 | **可走 Step 4**（转 DMP） |

### 选项2：产品接口维度脑图设计

| 项 | 内容 |
|----|------|
| 绑定（内嵌） | `skills/req-analysis-xmind/` |
| 触发关键字 | `step3-选项2` / `接口维度分析` / `入参出参` / `扣费分析` / `req analysis xmind` / `定制化产品` |
| 提取参数 | 需求文档（DOCX/图片/文字）（或复用 step1/step2 产物） |
| 产物 | `.xmind` 接口分析脑图（入参/出参/扣费/接口文档四维度），命名 `需求名_接口脑图.xmind` |
| 后续 | **可走 Step 4**（转 DMP） |

### 选项3：直接导入dmp版脑图设计

| 项 | 内容 |
|----|------|
| 绑定（内嵌） | `skills/generate-xmind-cases/` |
| 触发关键字 | `step3-选项3` / `迭代用例` / `回归测试` / `generate xmind cases` / `转dmp` / `DMP 用例` / `PRJ` |
| 提取参数 | 测试方案（XMind/Markdown）+ 需求文档（必须提供）；模式A=迭代（含PRJ），模式B=回归（按年月） |
| 产物 | `.xmind` DMP 兼容用例脑图，命名 `需求名_DMP用例.xmind` |
| 后续 | **无 Step 4**（已直接生成 DMP 格式，直接进入 Step 5 归档） |

> 依赖约束：只有走了 **选项1 或 选项2** 才能继续输入 Step 4；走了选项3 则提示「step3-选项3 无step4」。

---

## Step 4：脑图转 Excel 导入 DMP（选项1、2 专属）

| 项 | 内容 |
|----|------|
| 绑定（内嵌） | `skills/xmind-to-testcase/` |
| 触发关键字 | `step4` / `xmind转excel` / `脑图转dmp` / `XMind 转用例` / `导入DMP` / `xmind to testcase` |
| 提取参数 | 文档（Step3 生成的 `.xmind`）；可选 DMP 模板路径；列填充提示：`功能路径列`(caseGroup)、`适用版本列`(version)、`责任人列`(manager) |
| 产物 | DMP 格式 Excel 测试用例 `.xlsx`（14 列模板），命名 `需求名_测试用例.xlsx` |
| 依赖 | 必须先完成 Step3-选项1 或 选项2（否则拒绝并提示） |

> 列映射规则由内嵌的 `skills/xmind-to-testcase/` 按模板列名自动完成；manager 默认「余萍」，team/product/modulePath 默认「金蝶征信」，version 从脑图根节点日期推断。用户提供的「功能路径/适用版本/责任人」作为覆盖提示传入。

---

## Step 5：文档归类上传 Confluence（非必选）

| 项 | 内容 |
|----|------|
| 绑定（内嵌） | `skills/upload-to-confluence/` |
| 触发关键字 | `step5` / `上传confluence` / `归档` / `文档上传` / `upload confluence` / `归类上传` |
| 提取参数 | 目录（待上传文件所在目录）、文件清单（.docx / .xmind / .xlsx 等）、命名规则、上传目录 id（Confluence 页面 pageId） |
| 产物 | Confluence 页面附件链接（按团队标准 `<ac:link>` 格式更新页面正文） |
| 依赖 | 无（但通常承接前面所有步骤的产物） |

> 直接模式：用户已给出 pageId + 文件，编排直接调用内嵌的 `skills/upload-to-confluence/` 的上传/更新流程；上传前按「命名」规则规整文件名。
