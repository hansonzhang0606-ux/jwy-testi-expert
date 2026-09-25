---
name: upload-to-confluence
description: "将本地文件作为附件上传到 Confluence 页面，并使用符合团队标准格式的样式化附件链接更新页面正文。当用户提供 Confluence 页面 URL 和一个或多个文件时使用，或者当用户仅提供文件/目录名称，期望代理自动定位目标 Confluence 页面和本地文件时使用。"
agent_created: true
---

# 上传文件到 Confluence

## 使用时机

支持两种输入方式：

1. **直接模式**：用户提供 Confluence 页面 URL 和一个或多个绝对文件路径。
2. **自动定位模式**：用户仅提供文件名或目录名（例如 `【泾渭云20260609】20260609 鹰眼报告-V1.6-界面优化需求`）。代理必须在 2026 泾渭云目录下找到匹配的 Confluence 页面，并定位对应的本地文件夹。

目标：将文件作为附件上传到正确的 Confluence 页面，并更新页面正文，使附件以样式化链接的形式展示。

## 核心规则（季度页 + 自动建需求子页）—— 流水线 step5 必读

> **关键约定**：在本流水线（jwy-requirement-pipeline）的 step5 中，用户传入的「页面 id」**始终是季度页的 id**（如 Q3=97124877），**不是**具体要求子页。
>
> 因此**严禁**把附件直接上传到季度页本身。标准动作是：
> 1. 根据本次待上传文件的「需求命名」，**自动在该季度页下创建（或复用）一个需求子页**；
> 2. 把需求文件作为附件上传到这个**子页**；
> 3. 用样式化 `<ac:link>` 更新**子页**正文（季度页正文保持原样，不被改动）。

### 需求子页标题推导（「需求命名」）

- 收集本次所有**已重命名**的待上传文件名（已带用户指定的前缀，如 `【余萍】【TD-AI】`）。
- 推导步骤（参考脚本 `scripts/create_subpage_and_upload.py` 的 `derive_title`）：
  1. **先去掉用户前缀**（`【余萍】【TD-AI】`）。
  2. 再去掉每个文件名各自前置的 `【…】` 标签（如 `【泾渭云20260728】`），对「去标签后的剩余部分」求**多个字符串的最长公共前缀**（逐字符串比较，非仅取 min/max），并清掉已知后缀（`_需求确认` / `_分析报告` / `_测试用例` / `_测试分析` / `_含疑问点` 等）与扩展名，得到需求核心名。
  3. 若所有带标签的文件都含**同一个**前置 `【…】` 标签，则把它补回标题 —— 解决「部分文件缺日期标签（如 .xmind 没带 `【泾渭云YYYYMMDD】`，但 .docx 带了）」导致公共前缀塌缩成空的问题。
- 示例：
  - 全部一致：`…【泾渭云20260804】纳税H5增加登录身份提示_需求确认.docx` 与 `…【泾渭云20260804】纳税H5增加登录身份提示.xmind` → `【余萍】【TD-AI】【泾渭云20260804】纳税H5增加登录身份提示`。
  - 标签不一致：`【余萍】【TD-AI】【泾渭云20260728】NS004限制taxCode必填.docx` 与 `【余萍】【TD-AI】NS004限制taxCode必填_测试分析.xmind` → 从 .docx 补回一致的 `【泾渭云20260728】` 标签 → `【余萍】【TD-AI】【泾渭云20260728】NS004限制taxCode必填`。

### 幂等：先查后建

- 用 CQL 搜索 `space={季度页space.key} AND title="{推导标题}" AND type=page`，并检查其祖先链是否包含传入的季度页 id。
- 已存在 → 复用该子页 id；不存在 → `POST /rest/api/content` 新建，body 中 `ancestors=[{季度页id}]`，`space.key` 取自季度页 GET 结果。

## 自动定位模式

当用户**没有**提供完整的 Confluence URL 或完整文件路径时使用此模式。

### 1. 确定当前季度

使用当前系统日期：
- 1月–3月 → Q1
- 4月–6月 → Q2
- 7月–9月 → Q3
- 10月–12月 → Q4

### 2. 查找 Confluence 目标页面

从 2026 泾渭云目录页面开始：`https://finkms.kingdee.com/pages/viewpage.action?pageId=97124871`

使用 `confluence_get_page_children` 列出季度子页面：
- Q1: `97124873`
- Q2: `97124875`
- Q3: `97124877`
- Q4: `97124879`

搜索顺序：
1. 当前季度
2. 上一季度
3. 下一季度
4. 其余季度

对于每个季度，获取其子页面并筛选以 `【张登山】` 开头的标题。

将用户输入与页面标题中的**需求部分**（`【张登山】【TD-AI】` 之后的部分）进行匹配。需求部分的格式通常为 `【泾渭云YYYYMMDD】...`。

可接受的输入格式：
- `【泾渭云20260609】20260609 鹰眼报告-V1.6-界面优化需求`
- `20260609 鹰眼报告-V1.6-界面优化需求`
- `鹰眼报告-V1.6-界面优化需求`

匹配策略：
- 精确子串匹配为最佳。
- 如果提供的字符串与标题匹配但有少量字符差异，视为模糊匹配。
- **如果模糊匹配不完全精确，暂停并询问用户**："找到疑似匹配页面《XXX》，与你提供的名称有差异，是否继续上传？"
- 如果匹配到多个页面，优先选择 `泾渭云YYYYMMDD` 日期与用户输入日期最接近或相等的那一个。

匹配成功后，提取页面 ID 和 URL，这就是上传目标。

### 3. 查找本地文件夹

基础根目录：`D:\工作\泾渭云\2026\`

追加季度文件夹名称：
- Q1 → `第一季度`
- Q2 → `第二季度`
- Q3 → `第三季度`
- Q4 → `第四季度`

使用与 Confluence 搜索相同的顺序。

在季度文件夹内，找到名称与需求部分匹配的目录（格式通常为 `【泾渭云YYYYMMDD】...`）。本地文件夹名称通常等于 Confluence 页面标题去掉 `【张登山】【TD-AI】` 前缀后的部分。

如果找到文件夹，列出其中的文件。如果未找到，按照相同顺序回退到相邻季度。

### 4. 待上传文件

如果用户提供了单个文件名，则只上传匹配文件夹中的该文件。

如果用户提供了目录名或没有指定文件名，则上传匹配文件夹中的所有文件。

典型文件：
- `【泾渭云YYYYMMDD】... .md` → 纯链接
- `【泾渭云YYYYMMDD】... _分析报告.docx` → 纯链接
- `【泾渭云YYYYMMDD】... _测试用例.xlsx` → 自定义显示文本（文件名已包含 `_测试用例`）
- `【泾渭云YYYYMMDD】... _测试用例.xmind` → 自定义显示文本

## 直接模式（流水线 step5 主路径：传入的 id = 季度页）

用户传入「页面 id」（= 季度页 id，如 97124877）和本地文件路径（或目录）。**标准动作：在该季度页下自动建需求子页，再上传到子页。**

执行序列：

1. **确定季度页**：从传入 id 用 `GET /rest/api/content/{id}?expand=space` 拿到 `space.key`（如 `KJBQT`）。该 id 即子页的父（`ancestors`）。
2. **收集待上传文件**：若给的是目录，取其中所有 `.docx/.xmind/.xlsx/.md` 等需求文件；若给的是具体文件，取这些文件。**先按用户指定前缀重命名**（如 `【余萍】【TD-AI】`）。
3. **推导需求子页标题**：见上文「需求子页标题推导」。
4. **幂等查建子页**：按上文「幂等：先查后建」复用或新建子页，得到 `sub_page_id`。
5. **上传附件**：`POST /rest/api/content/{sub_page_id}/child/attachment`，把每个文件作为附件上传（MCP 工具失败则走 REST 回退）。
6. **更新子页正文**：`GET` 子页当前正文（`expand=body.storage`）→ 在其后**追加** `<ac:link>` 块（见下方格式）→ `PUT` 该子页，`version.number` +1，`content_format: storage`。**不要改动季度页正文。**
7. **报告结果**：子页 URL（`.../pages/viewpage.action?pageId={sub_page_id}`）、附件数量、每个附件下载链接，以及任何错误。

> 若用户**显式**要求「直接上传到给定 id 的页面、不建子页」（非流水线场景），才跳过第 3–4 步，直接把附件传到该 id。流水线 step5 一律走子页流程。

## 上传和更新工作流程

在确定了目标 `pageId`（季度页）和本地文件后：

1. **建/复需求子页**：见「核心规则」与「直接模式」第 3–4 步，得到 `sub_page_id`。后续所有上传与正文更新都作用于 `sub_page_id`，**不是**传入的季度页 id。
2. **上传附件**：首先使用 `confluence_upload_attachment`（目标是 `sub_page_id`）。如果失败，回退到 Confluence REST API（`POST /rest/api/content/{sub_page_id}/child/attachment`），使用 `mcp.json` 中的 Basic Auth 凭据。
3. **读取子页当前正文**：使用 `confluence_get_page`（`convert_to_markdown: false`，目标是 `sub_page_id`）。
4. **构建 `<ac:link>` 块**（Confluence 存储格式）：
   - `.md` 和其他文档使用纯链接：
     ```xml
     <ac:link><ri:attachment ri:filename="FILENAME"></ri:attachment></ac:link>
     ```
   - 测试用例文件使用自定义文本：
     ```xml
     <ac:link><ri:attachment ri:filename="FILENAME"></ri:attachment><ac:plain-text-link-body><![CDATA[DISPLAY_TEXT]]></ac:plain-text-link-body></ac:link>
     ```
   - **重要提示**：如果文件名包含 `&`（与符号），在 `ri:filename` 属性中将其转义为 `&amp;`。例如，`工商&司法` 变为 `工商&amp;司法`。`<![CDATA[...]]>` 内容无需转义。
5. **更新子页正文**：使用 `confluence_update_page`（`content_format: "storage"`，目标是 `sub_page_id`）。将新的段落追加到现有内容中，保留原有布局。
6. **报告结果**：子页 URL、文件数量、每个文件的附件 ID/下载 URL，以及任何错误。

## REST API 回退方案

如果 MCP 工具（`confluence_upload_attachment` / `confluence_get_page` / `confluence_update_page`）调用失败（本环境常见：连接器实例 host 配置为占位符 `confluence.your-company.com`，且 `file_path` 仅允许其 sandbox 目录 → 报 path traversal），改用 Confluence REST API。

**凭据来源**：从用户本地 `~/.workbuddy/mcp.json` 的 `mcpServers.Confluence.env` 读取 `CONFLUENCE_URL` / `CONFLUENCE_USERNAME` / `CONFLUENCE_API_TOKEN`（真实 host 为 `https://finkms.kingdee.com`，账号如 `yu_ping`）。**脚本中不要硬编码凭据，也不要在任何输出中暴露 token**；用 `base64` 拼 Basic Auth。

```python
import json, os, base64, requests
cfg = json.load(open(os.path.expanduser(r"~/.workbuddy/mcp.json"), encoding="utf-8"))["mcpServers"]["Confluence"]["env"]
base = cfg["CONFLUENCE_URL"].rstrip("/"); user = cfg["CONFLUENCE_USERNAME"]; token = cfg["CONFLUENCE_API_TOKEN"]
auth = base64.b64encode(f"{user}:{token}".encode()).decode()
H = {"Authorization": f"Basic {auth}", "Accept": "application/json"}
A = {"Authorization": f"Basic {auth}", "X-Atlassian-Token": "no-check"}
# 1) 取季度页 space.key
space_key = requests.get(f"{base}/rest/api/content/{QUARTER_ID}", params={"expand":"space"}, headers=H, verify=False).json()["space"]["key"]
# 2) 查/建需求子页（见核心规则），得到 sub_page_id
# 3) 上传附件到子页
with open(file_path, "rb") as f:
    requests.post(f"{base}/rest/api/content/{sub_page_id}/child/attachment", headers=A, files={"file": (filename, f)}, verify=False)
# 4) 读取子页正文 -> 追加 ac:link -> PUT（version+1, representation=storage）
```

用户倾向于将临时脚本保留在工作空间中，不需要删除。

## 参考脚本（可直接调用）

`scripts/create_subpage_and_upload.py` 已封装上述「季度页 → 自动建/复需求子页 → 上传并更新正文」全流程，单列命令即可完成 step5：

```bash
python scripts/create_subpage_and_upload.py \
    --quarter-id 97124877 \
    --dir "D:/需求/2026/8.27" \
    --prefix "【余萍】【TD-AI】"
```

参数：`--quarter-id`（季度页 id，必填）、`--dir`（取目录内需求文件）或 `--files`（显式文件）、`--prefix`（重命名前缀，可选）。脚本会自动加前缀、按最长公共前缀推导子页标题、幂等查建子页、上传附件并追加 `<ac:link>` 正文；凭据从 `~/.workbuddy/mcp.json` 读取。

## 命名规则

- 上传时保留原始文件名。
- 对于已以 `_测试用例.xlsx` 或 `_测试用例.xmind` 结尾的测试用例文件，使用原始文件名作为显示文本。
- 对于 `.md` 和分析报告，使用纯链接。

## 注意事项

- **季度页正文永不被改动**：step5 传入的 id 是季度页，所有附件与正文更新都作用于自动创建/复用的**需求子页**，季度页保持原样。
- 先用 CQL 查重、再建子页（幂等），避免同一需求重复建子页。
- 更新前务必先读取子页当前内容。
- 更新时使用 `content_format: "storage"`；markdown 格式无法保留 `<ac:link>` 宏。
- 如果文件在其他程序中打开，请用户关闭后重试。
- 凭据全程从 `mcp.json` 读取，绝不硬编码或暴露 token。
