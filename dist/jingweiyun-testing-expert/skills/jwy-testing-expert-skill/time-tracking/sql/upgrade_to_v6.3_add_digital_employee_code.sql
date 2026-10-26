-- 时间节省追踪 Skill 升级脚本：新增 digital_employee_code 列
-- 管理员审核后，在已选定的目标数据库连接中手动执行。
-- 本脚本只新增「数字员工编号」列，不修改旧字段、索引、唯一键或历史数据。
-- 列已存在则跳过（幂等）。

SET @dec_column_exists = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'agent_time_tracking'
      AND COLUMN_NAME = 'digital_employee_code'
);

SET @dec_upgrade_sql = IF(
    @dec_column_exists = 0,
    'ALTER TABLE `agent_time_tracking` ADD COLUMN `digital_employee_code` VARCHAR(32) NULL COMMENT ''实际使用的数字员工/Skill套件编号'' AFTER `biz_line_code`',
    'SELECT ''digital_employee_code column already exists'' AS message'
);

PREPARE dec_upgrade_statement FROM @dec_upgrade_sql;
EXECUTE dec_upgrade_statement;
DEALLOCATE PREPARE dec_upgrade_statement;

SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'agent_time_tracking'
  AND COLUMN_NAME = 'digital_employee_code';
