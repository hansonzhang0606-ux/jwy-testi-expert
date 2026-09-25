# DOCX Input Schema

The generator accepts JSON with these top-level fields. Missing optional arrays are allowed and render as empty sections only if useful.

```json
{
  "title": "NS011 查询是否有记录挡板需求分析",
  "metadata": "v1.4 / 2026-07-09 新增    接口：NS011",
  "conclusion": ["one-line summary", "major uncertainty", "recommended next step"],
  "rule_overview": [{"clientId":"1000076", "metric":"销项票 / 进项票 / 应税销售收入", "period":"近 12 个月", "threshold":"50 万", "condition":"任一指标 > 50 万"}],
  "priority_items": [{"priority":"P0", "question":"...", "impact":"...", "confirmation":"待填写"}],
  "detailed_questions": ["..."],
  "ambiguities": [{"term":"近 12 个月", "issue":"起止时间不明确", "suggestion":"..."}],
  "acceptance_criteria": [{"id":"AC01", "scenario":"...", "expected":"..."}],
  "risks": [{"level":"高", "risk":"时间口径不清晰", "description":"..."}],
  "recommendation": ["..."]
}
```

Priority confirmation items support an optional `confirmation` field. The DOCX generator renders it as a manual follow-up field and defaults missing values to `待填写`.

Keep cell text concise. If a cell needs multiple sentences, split it into multiple rows or move detail to a question list.
