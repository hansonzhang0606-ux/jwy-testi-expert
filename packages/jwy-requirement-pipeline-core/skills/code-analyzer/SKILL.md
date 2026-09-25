---
name: code-analyzer
description: 分析 Java/MyBatis、Python、SQL/存储过程及混合技术栈变更，提取实现证据、语法级业务规则、SQL/数据流、调用链、配置值、异常处理、覆盖缺口和测试关注点。适用于中文企业项目的业务逻辑分析、需求实现验证、影响分析与测试设计。
---

# 代码分析器

使用本技能检查源码，并产出有代码证据支撑且明确披露覆盖边界的实现分析。

## 工作流程

1. 调用方统一使用 `business_extractor.extract_business_logic()`；兼容旧调用时使用 `code_analyzer.analyze_code()`。引擎选择和降级由内部完成，调用方不得直接选择正则或 tree-sitter 路径。
2. 确认仓库、目标分支、基线和本次实际变更文件。
3. 先形成逐文件 technology_coverage 清单。每个文件必须标记为 analyzed、partial、recognized_unanalyzed、unsupported、unreadable 或 not_applicable；禁止静默跳过。
4. 按技术栈选择证据提取：
   - Java：调用链与业务规则；关键 if、throw、validate/check 优先使用 tree-sitter Java。
   - Python：使用标准库 AST 提取分支、raise、断言、校验调用和路由入口。
   - MyBatis XML、SQL、DDL 和 Oracle 存储过程文件：提取表、连接、过滤、聚合及数据流；结果标记为部分覆盖。
   - properties/YAML：提取配置值。
   - JavaScript、TypeScript、Vue、Kotlin、Groovy、Scala：当前只识别并报告缺口，不得推断其内部逻辑。
5. Java tree-sitter 依赖不可用或解析失败时，必须记录 fallback_reason，并使用“注释/字符串屏蔽 + 括号配平”的结构化降级解析。不得把降级结果宣称为完整 AST 分析。
6. 用 rg、Get-Content 和源码定位核验关键结论。若存在 .codegraph/codegraph.db，仅将其作为索引，最终证据仍回到源码。
7. 将每项行为、风险和覆盖缺口映射到可验证的测试关注点；覆盖不完整时降低影响结论置信度。

## 随附脚本

- business_extractor.py：唯一权威分析入口，汇总各技术栈证据、测试提示和覆盖报告。
- code_analyzer.py：兼容门面，仅委托给权威入口，不维护独立正则分析路径。
- syntax_analyzer.py：内部语法引擎，提供 Java tree-sitter/结构化降级与 Python AST；业务调用方不直接依赖。
- technology_inventory.py：文件技术栈识别与覆盖汇总。
- sql_analyzer.py：Mapper XML、SQL 和存储过程的结构化分析。
- call_chain_analyzer.py：Java 方法、入口注解和调用关系。
- business_rule_extractor.py：Java 分支、显式抛错、校验、异常处理和日志规则。
- config_extractor.py：@Value、常量、cron、properties 和 YAML。
- flow_diagram_generator.py：文本版数据流或业务流程图。

## 产物命名（流水线 Step2）

代码分析结果落到「指定目录」，文件名必须为 `需求名_代码分析.docx`（或 `.md`）：

- `需求名`：从需求文档标题 / 输入文件名提取，去掉团队前缀（`【余萍】`、`【TD-AI】`），保留需求标识标签（如 `【泾渭云YYYYMMDD】`）。
- 示例：需求 `【余萍】【TD-AI】【泾渭云20260804】纳税H5增加登录身份提示` → `【泾渭云20260804】纳税H5增加登录身份提示_代码分析.docx`。

## 约束

- 脚本输出是候选证据，不代替源码验证。
- 所有结论需锚定到文件路径以及方法、行号、SQL、表名或配置键。
- 调用 Git 时使用参数列表和 `shell=False`；不得拼接 `cd && git ...` 或把仓库路径插入 shell 字符串。
- 需求与实现不一致时同时引用两侧证据。
- 除非用户明确要求修改目标代码，不要改动被分析的业务仓库。
