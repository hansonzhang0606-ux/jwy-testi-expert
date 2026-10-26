# 泾渭云测试专家 v1.2.1

WorkBuddy 专家包。将整个目录交由专家包管理器校验、注册和打包。数据库与 Confluence 凭据仅在本机配置，不随包分发。

> **v1.2.1 变更**：工时入库自动写入数字员工编号 `digital_employee_code`（泾渭云=DE-025）到 `agent_time_tracking`，并新增升级 SQL（`upgrade_to_v6.3_add_digital_employee_code.sql`）与按注册表回填逻辑，确保每个工时记录都归属到正确的数字员工。
> **v1.2.0 变更**：工时入库前置「用户故事完整性」校验——`<PRJ 编号>-<故事名称>` 两部分缺一不可。测试人员只提供其中一部分时，专家会提示补齐；工时记录脚本对半截信息直接拒绝（退出码 2），避免 `agent_time_tracking` 出现 `user_story` 不完整、`user_story_code` 为空的脏数据。
