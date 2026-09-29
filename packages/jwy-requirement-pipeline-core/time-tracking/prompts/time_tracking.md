# 泾渭云工时追踪规则 v6.2-JWY（提交即同步 + 提示词回补兜底）

## 零、会话启动（强制）：MySQL 配置闭环

泾渭云业务线确定后、进入任何工时采集之前，**必须先完成本机 MySQL 配置检查**（每台机器只需成功一次）：

1. 检查本机配置是否存在：`~/.workbuddy/data/time-tracking/泾渭云/mysql_config.json`
2. **不存在 → AI 必须立即执行**（是"自动执行并校验"，不是"提示用户自己去执行"）：
   python scripts/init_mysql_config.py --biz-line 泾渭云 --template --no-interactive --quiet
   执行后**校验两个文件确已落地**：`mysql_config.json`（全空模板）与同目录 `mysql_config.notes.md`（逐字段填写说明）。未落地不得继续。
3. 落地后告知测试人员：按同目录 `mysql_config.notes.md` 填写全部字段（不清楚的找管理员获取），填好后回复「已填好」即可继续。
   **严禁在对话中索要数据库密码**，也不要让测试人员把凭据贴进对话或提交到 Git。
4. 配置已存在则跳过，不重复生成；配置存在但字段为空时，提示其按 notes 补全后再继续。

> `mysql_config.json` 是**本机文件**、不随专家包分发。因此其他测试人员首次使用本专家时，会自动获得空模板 + 字段说明，**只需填一次**，无需手动开 CMD，也无需管理员逐台配置。

仅对流水线状态中实际完成的 P1、P2、P3-1/P3-2/P3-3、P4、P5 采集工时。完成产物后必须先独立生成 AI 预估、收集测试人员反馈并调用记录脚本，确认保存前禁止展示下一步。

## 记录与同步（融合方案 A+B）

【A·提交即同步】每一步完成并二次确认后，调用：
  python scripts/secure_record_time_saved.py \\
    --employee "姓名" --user-story "PRJ-xxxxxxx" --step "需求确认" --step-code "P1" \\
    --hours 4.0 --biz-line 泾渭云 \\
    [--remark ...] [--agent-start-time ...] [--agent-end-time ...] \\
    [--agent-duration-minutes ...] [--ai-estimated-time-saved-hours ...]
该脚本会在本地 records.jsonl 落盘成功后立即把本次及此前所有本地记录同步到 MySQL 的 agent_time_tracking 表（内部调用 sync_to_mysql.py），无需等待定时任务；同步失败仅告警、不阻断本地落盘。

【B·提示词回补兜底】若某次记录只落到本地而未进 MySQL（如：提交即同步时 MySQL 不可用/未初始化、此前误用纯 record_time_saved.py、或人员忘了触发），由本提示词驱动 AI 在以下时机回补：
  - 会话开始：检查本机 records.jsonl 是否已有未同步记录；
  - 用户提及“同步工时 / 核对工时 / 工时没进库”等；
  - 某步骤提交即同步返回告警时。
回补命令（幂等，可重复执行，不影响已存在记录）：
  python scripts/sync_to_mysql.py --biz-line 泾渭云
  # 试运行先看不写：python scripts/sync_to_mysql.py --biz-line 泾渭云 --dry-run

【可选安全网】如需额外定时兜底（与效贷 Lite 体验一致），可注册本机任务计划：
  python scripts/register_sync_tasks.py --biz-line 泾渭云
（每日 09:00/12:00/18:00 自动同步；核心保障仍是 A 提交即同步 + B 提示词回补，注册与否不影响数据入库。）

【录错/误记录的处理】优先联系数据库管理员执行 DELETE 物理删除。若同步账号暂无 DELETE 权限，可用软作废作为临时/审计手段：
  python scripts/void_time_record.py --biz-line 泾渭云 --id <数据库主键> --reason "原因"      # 最精确
  python scripts/void_time_record.py --biz-line 泾渭云 --employee "姓名" --user-story "PRJ-xxxxxxx" --step-code "P4"
  # 先预览：加 --dry-run
作用：该行工时字段归零（time_saved_hours/time_saved_pd/total_hours=0）+ remark 打 `[作废]` 前缀 + 写入本机作废名单 `voided.json`；后续同步会跳过其 record_key，**不会被重新写回**。统计汇总按 SUM 计算时该行贡献为 0，等同删除。

## 采集口径

“采纳”取该步骤参考范围中间值；两次未提供实际值则记录中间值并备注“用户未反馈，采用参考中间值”。
跨步骤补录只认 `.jwy_pipeline_state.json` 中 `tracking.eligible` 的 P 标识集合，不得补录本次未执行的可选步骤或未选择的 Step3 分支；需与已记录集合做差集时，可调用 skill 根目录下的 `scripts/jwy_tracking.py`（相对 time-tracking 目录为 `../scripts/jwy_tracking.py`）的 `missing_tracking_ids(state, recorded_ids)` —— 该模块是辅助库而非命令行脚本，不能直接执行。

## 身份与凭据

身份验证查询 MySQL `agent_team_roster`，仅允许 `JWY` 精确匹配成员；数据库配置须在本机填写，不得在对话或发布包中收集、输出或保存凭据。
若本机尚未初始化 MySQL 配置，按「零、会话启动」节**自动执行** `python scripts/init_mysql_config.py --biz-line 泾渭云 --template --no-interactive --quiet` 并校验产物落地，由测试人员按 `mysql_config.notes.md` 填写或找管理员获取，AI 不在对话中索要密码。
