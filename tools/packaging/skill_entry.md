---
name: jwy-testing-expert-skill
description: |
  泾渭云需求测试全流程 Skill，覆盖需求确认、代码分析、脑图用例、DMP 转换、Confluence 归档和节省工时追踪。
  当用户提及 step1 至 step5、需求确认、代码分析、测试脑图、DMP 用例、归档或查看工时统计时必须使用。
---

# 泾渭云测试专家 Skill

每次进入步骤前，先读 `prompts/pipeline.md`；再按其中映射读取 `modules/<能力>/SKILL.md`。
所有产物必须落在用户指定的绝对输出目录，并用 `scripts/pipeline_state.py` 维护状态。

完成 P1/P2/P3-1~3/P4/P5 任一实际步骤后，必须先完成 `time-tracking/prompts/time_tracking.md` 定义的工时采集，才可进入下一步。仅补录当前状态文件中已完成的追踪步骤。

工时按「提交即同步（A）+ 提示词回补（B）」自动进入 MySQL `agent_time_tracking` 表，无需等待定时任务；录错时用 `void_time_record.py` 软作废（或联系管理员执行 DELETE）。
