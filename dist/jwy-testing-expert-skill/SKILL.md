---
name: jwy-testing-expert-skill
description: |
  泾渭云需求测试全流程 Skill，覆盖需求确认、代码分析、脑图用例、DMP 转换、Confluence/weknora 归档和节省工时追踪。
  当用户提及 step1 至 step5、需求确认、代码分析、测试脑图、DMP 用例、归档、上传知识库、同步 weknora、查看工时统计时必须使用。
---

# 泾渭云测试专家 Skill

每次进入步骤前，先读 `prompts/pipeline.md`；再按其中映射读取 `modules/<能力>/SKILL.md`。
所有产物必须落在用户指定的绝对输出目录，并用 `scripts/pipeline_state.py` 维护状态。

完成 P1/P2/P3-1~3/P4/P5 任一实际步骤后，必须先完成 `time-tracking/prompts/time_tracking.md` 定义的工时采集，才可进入下一步。仅补录当前状态文件中已完成的追踪步骤。

工时按「提交即同步（A）+ 提示词回补（B）」自动进入 MySQL `agent_time_tracking` 表，无需等待定时任务；录错时用 `void_time_record.py` 软作废（或联系管理员执行 DELETE）。

## 用户故事信息（工时入库前置，强制）

工时入库要求用户故事**两部分齐全**：`<PRJ 编号>-<故事名称>`，例 `PRJ-00884552-【泾渭云20260915】修改泾渭云使用中台数据库账号`。

- 需求开始时先确认这两部分，P1~P5 全程复用同一串；
- 测试人员**只给一部分**（只给 PRJ 编号 / 只给故事名称）时，**追问补齐再推进**，不得臆造 PRJ 编号；
- 脚本层硬校验：缺任一部分时 `record_time_saved.py` / `secure_record_time_saved.py` **拒绝记录**（退出码 2）并返回补齐提示，`--allow-partial-user-story` 仅供排障/历史补录。

> 详细规则见 `prompts/pipeline.md`「用户故事信息」与 `time-tracking/prompts/time_tracking.md`「用户故事完整性」。

## weknora 知识库归档（xmind-to-weknora 技能）

本专家已合并 `xmind-to-weknora` 技能，负责把**终稿 xmind 用例**转 Markdown 并归档到团队 weknora 知识库。完整说明见 `../xmind-to-weknora/SKILL.md` 与 `../xmind-to-weknora/references/expert_integration.md`。

> **双归档定位（不冲突）**：step5 归档到 Confluence 的文档是**给人看**的（团队 wiki、季度页/需求子页）；归档到 weknora 的内容是**给 AI 读**的（向量化知识库、供后续智能检索与复用）。二者目标读者不同、互不替代，故 weknora 作为**新增**归档目的地与现有 Confluence 归档**并存互补**。

### 泾渭云默认匹配（内置，无需配置）

| 业务线 | 空间（空间ID） | 目标知识库 | 知识库ID |
| --- | --- | --- | --- |
| 泾渭云 JWY | 数据业务线（10003） | 泾渭云_测试_测试用例 | 4b61aa94-2478-49e2-84c9-4847b309871c |

> 映射内置在 `../xmind-to-weknora/assets/preset_kb_mapping.json`，测试人员**无需配任何 json**；连接器只需配 `url` + `Authorization`。

### 钩子 A：生成 xmind 用例之后（提醒）

**触发条件：step3 脑图（三选一）任一方式都会产出 `.xmind` 文件——但凡生成 xmind 即触发本钩子**（选项1 测试脑图 / 选项2 接口脑图 / 选项3 DMP 用例脑图，三者最终都落 `.xmind`）。在 step3 任一项生成 xmind 用例的步骤末尾追加：

> 生成 xmind 用例后，调用 xmind-to-weknora 技能「提醒模式」：询问测试人员是否立即上传到 weknora 知识库。
> - 回答「是」：进入执行模式（解析 → 自动匹配 → 确认卡 → 上传）
> - 回答「否」：用 `../xmind-to-weknora/scripts/sync_state.py mark --status pending` 标记 pending，并在后续每个必做步骤收尾时再次提醒

### 钩子 B：每个必做步骤收尾（检查）

在每个必须执行的步骤结束前追加：

> 步骤收尾检查：执行 `../xmind-to-weknora/scripts/sync_state.py check --key "<用户故事>|<文档类型>"`
> - 退出码 10/12（pending/无记录）→ 输出提醒：「⚠️ 该需求的 xmind 用例尚未同步到 weknora 知识库（目标：泾渭云_测试_测试用例）。终版确定后请说『上传知识库』，我会转成 Markdown 并归档。」
> - 退出码 11（skipped）→ 提醒一次即可，不再重复追问
> - 退出码 0（uploaded）→ 不打扰；但仍需看 `tag_reminder` / `untagged_total`，非空则提醒人工打标

### 触发词

当用户说「上传知识库」「同步 weknora」「归档用例」「用例入库」「批量上传」「上传到知识库了吗」「检查同步状态」时，调用 xmind-to-weknora 技能。

### 硬性规则（继承技能定义，务必遵守）

1. **每次上传前必须展示确认卡**（业务线+对应专家/空间名称+weknora空间ID/知识库名+知识库ID/文档类型/weknora 标签/文档标题/来源文件/新建或更新），得到明确「确认」后才上传；沉默或答非所问视为未确认。
2. **测试人员唯一要配的是 MCP 连接器**（`url` + `Authorization`），不要让测试人员生成或修改任何 json。
3. **遇到映射里没有的知识库必须停下来问**，禁止凭相似名称猜测；先确认是否新增库及归属业务线，登记复核后再上传。
4. **标签走方案 C**：上传后必提醒人工在网页端勾选（MCP 无标签参数），并用 `../xmind-to-weknora/scripts/sync_state.py mark --tag-status` 追踪到闭环。
