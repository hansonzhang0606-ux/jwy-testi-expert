---
name: requirement-analysis-docx
description: Analyze business or product requirements and generate a consistent, easy-to-scan DOCX requirement analysis report. Use when the user asks to analyze a requirement, review requirement ambiguity, identify questions, vague points, risks, acceptance criteria, or asks to output the analysis as a Word/docx file with a reusable template.
---

# Requirement Analysis DOCX

## Overview

Use this skill to turn a raw requirement into a structured requirement-analysis report and, when requested, generate a consistent Word document. The default output is a concise review artifact for product, business, development, and QA alignment.

## Workflow

1. Read the raw requirement and restate the business intent in plain language.
2. Extract explicit rules, actors, identifiers, thresholds, dates, interfaces, states, and outputs.
3. Analyze the requirement using the checklist in `references/analysis-framework.md`.
4. Organize findings into this fixed structure:
   - One-page conclusion
   - Rule overview
   - Priority confirmation items, with a reserved 确认结论 column for manual confirmation result
   - Detailed questions
   - Ambiguities and clarification suggestions
   - Acceptance criteria suggestions
   - Risk notes
   - Final recommendation
5. If the user asks for DOCX, build the document with `scripts/build_requirement_analysis_docx.py` instead of improvising a new layout.
6. Keep the DOCX layout consistent with `assets/requirement-analysis-template.docx`: first page for scanability, later pages for details.

## Output Rules

- Lead with the highest-value uncertainties, especially P0 items that block development or test design.
- Use tables for comparable items and short rows; use numbered lists only for detailed questions.
- In the priority confirmation table, always leave one fillable manual confirmation column: 确认结论. If no confirmed value is available, render 待填写.
- Preserve exact requirement terms such as interface names, client IDs, thresholds, dates, field names, and status names.
- Treat words such as “近”, “自动”, “默认”, “支持”, “有记录”, “及时”, “可配置”, “异常”, and “按规则” as ambiguity triggers.
- Mark equal-to-threshold cases explicitly when the requirement says “大于” or “小于”.
- Call out whether non-mentioned users, clients, statuses, historical data, exceptions, and failures are affected.

## 产物命名（流水线 Step1）

生成的 DOCX 落到「指定目录」，文件名必须为 `需求名_需求确认.docx`：

- `需求名`：从需求文档标题 / 输入文件名提取，去掉团队前缀（`【{部署配置}】`、`【TD-AI】`），保留需求标识标签（如 `【泾渭云YYYYMMDD】`）。
- 示例：需求 `【{部署配置}】【TD-AI】【泾渭云20260804】纳税H5增加登录身份提示` → `【泾渭云20260804】纳税H5增加登录身份提示_需求确认.docx`。

## DOCX Generation

Prepare a JSON file with the schema described in `references/docx-input-schema.md`, then run:

```bash
python scripts/build_requirement_analysis_docx.py input.json --output output.docx
```

Use the bundled Python from the workspace dependency loader when available. If DOCX rendering tools are available, render and inspect the document before delivery; otherwise, at least open it structurally with `python-docx` and report that visual rendering was not completed.

## Template Consistency

The DOCX must keep these layout decisions:

- Title and metadata at top.
- First-page blue conclusion callout.
- Rule overview table immediately after the conclusion.
- Yellow priority confirmation table before detailed analysis, with a reserved 确认结论 column for follow-up alignment.
- Detailed sections after a page break.
- Green acceptance criteria table and red risk table.
- Same Chinese section names unless the user requests another language.
