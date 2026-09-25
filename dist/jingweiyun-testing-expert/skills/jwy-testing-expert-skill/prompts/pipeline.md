# 泾渭云五步编排

1. Step1：需求确认，调用 `modules/requirement-analysis-docx/`。
2. Step2：代码分析，可选，调用 `modules/code-analyzer/`。
3. Step3：必须选择一项：选项1 测试脑图、选项2 接口脑图、选项3 DMP 用例脑图。
4. Step4：仅 Step3-选项1/2 后允许，调用 `modules/xmind-to-testcase/`。
5. Step5：可选 Confluence 归档；配置缺失、匹配不唯一或无权限时停止并说明原因。

每步完成后执行 `scripts/pipeline_state.py record`。工时适配只读取状态中 `tracking.eligible` 的 P 标识，禁止将未执行的可选步骤或未选择的 Step3 分支判为漏记。
