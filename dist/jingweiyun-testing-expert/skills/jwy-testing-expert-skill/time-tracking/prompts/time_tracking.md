# 泾渭云工时追踪规则 v6.2-JWY（提交即同步 + 提示词回补兜底）

仅对流水线状态中实际完成的 P1、P2、P3-1/P3-2/P3-3、P4、P5 采集工时。完成产物后必须先独立生成 AI 预估、收集测试人员反馈并调用记录脚本，确认保存前禁止展示下一步。

## 记录与同步（融合方案 A+B）

【A·提交即同步】每一步完成并二次确认后，调用：
  python scripts/secure_record_time_saved.py \
    --employee "姓名" --user-story "PRJ-xxxxxxx" --step "需求确认" --step-code "P1" \
    --hours 4.0 --biz-line 泾渭云 \
    [--remark ...] [--agent-start-time ...] [--agent-end-time ...] \
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

## 采集口径
“采纳”取该步骤参考范围中间值；两次未提供实际值则记录中间值并备注“用户未反馈，采用参考中间值”。跨步骤补录只使用 `scripts/jwy_tracking.py` 从 `.jwy_pipeline_state.json` 计算的 eligible 集合，不得补录本次未执行的可选步骤或未选择的 Step3 分支。

## 身份与凭据
身份验证查询 MySQL `agent_team_roster`，仅允许 `JWY` 精确匹配成员；数据库配置须在本机填写，不得在对话或发布包中收集、输出或保存凭据。
若本机尚未初始化 MySQL 配置，AI 应提示运行 `python scripts/init_mysql_config.py --biz-line 泾渭云 --template`（生成空模板 + 备注说明），由测试人员按备注填写或找管理员获取，AI 不在对话中索要密码。
