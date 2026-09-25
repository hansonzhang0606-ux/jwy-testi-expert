"""Build installable WorkBuddy and VS Code releases from the shared core."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


WORKBUDDY_NAME = "jingweiyun-testing-expert"
VSCODE_NAME = "jwy-testing-expert-skill"
FORBIDDEN_TEXT = ("余萍", "张登山", "金蝶征信", "D:\\工作\\泾渭云\\2026")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _sanitize_text_files(root: Path) -> None:
    for path in root.rglob("*"):
        if path.suffix.lower() not in {".md", ".py", ".yaml", ".json", ".bat"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for forbidden in FORBIDDEN_TEXT:
            text = text.replace(forbidden, "{部署配置}")
        path.write_text(text, encoding="utf-8")


def _copy_core(core: Path, destination: Path) -> None:
    shutil.copytree(core, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    nested_skills = destination / "skills"
    if nested_skills.exists():
        nested_skills.rename(destination / "modules")
    _sanitize_text_files(destination)
    _write(destination / "SKILL.md", """---
name: jwy-testing-expert-skill
description: |
  泾渭云需求测试全流程 Skill，覆盖需求确认、代码分析、脑图用例、DMP 转换、Confluence 归档和节省工时追踪。
  当用户提及 step1 至 step5、需求确认、代码分析、测试脑图、DMP 用例、归档或查看工时统计时必须使用。
---

# 泾渭云测试专家 Skill

每次进入步骤前，先读 `prompts/pipeline.md`；再按其中映射读取 `modules/<能力>/SKILL.md`。
所有产物必须落在用户指定的绝对输出目录，并用 `scripts/pipeline_state.py` 维护状态。

完成 P1/P2/P3-1~3/P4/P5 任一实际步骤后，必须先完成 `time-tracking/prompts/time_tracking.md` 定义的工时采集，才可进入下一步。仅补录当前状态文件中已完成的追踪步骤。
""")
    _write(destination / "prompts" / "pipeline.md", """# 泾渭云五步编排

1. Step1：需求确认，调用 `modules/requirement-analysis-docx/`。
2. Step2：代码分析，可选，调用 `modules/code-analyzer/`。
3. Step3：必须选择一项：选项1 测试脑图、选项2 接口脑图、选项3 DMP 用例脑图。
4. Step4：仅 Step3-选项1/2 后允许，调用 `modules/xmind-to-testcase/`。
5. Step5：可选 Confluence 归档；配置缺失、匹配不唯一或无权限时停止并说明原因。

每步完成后执行 `scripts/pipeline_state.py record`。工时适配只读取状态中 `tracking.eligible` 的 P 标识，禁止将未执行的可选步骤或未选择的 Step3 分支判为漏记。
""")
    _write_jwy_tracking_configuration(destination)


def _write_jwy_tracking_configuration(destination: Path) -> None:
    _write(destination / "time-tracking" / "config" / "time_tracking_config.yaml", """default_biz_line: "泾渭云"
storage_mode: "mysql"
local_storage:
  dir: "time-tracking/{biz_line}"
  records_file: "records.jsonl"
  report_file: "time_analytics_{biz_line}.html"
  csv_file: "time_analytics_{biz_line}.csv"
mysql:
  default_host: ""
  default_port: 3306
  default_user: ""
  default_database: ""
  default_table: "agent_time_tracking"
reference_times:
  - step_code: "P1"
    step_name: "需求确认"
    min_hours: 2
    max_hours: 4
  - step_code: "P2"
    step_name: "代码分析"
    min_hours: 2
    max_hours: 5
  - step_code: "P3-1"
    step_name: "测试脑图生成"
    min_hours: 3
    max_hours: 5
  - step_code: "P3-2"
    step_name: "接口脑图生成"
    min_hours: 3
    max_hours: 6
  - step_code: "P3-3"
    step_name: "DMP用例脑图生成"
    min_hours: 4
    max_hours: 8
  - step_code: "P4"
    step_name: "DMP Excel转换"
    min_hours: 2
    max_hours: 4
  - step_code: "P5"
    step_name: "Confluence归档"
    min_hours: 0.5
    max_hours: 1
rules:
  mandatory: true
  allow_skip: false
  require_confirmation: true
  adopt_reference_value: "midpoint"
  no_feedback_after_retries: "midpoint"
  no_feedback_remark: "用户未反馈，采用参考中间值"
  max_feedback_retries: 2
""")
    _write(destination / "time-tracking" / "prompts" / "time_tracking.md", """# 泾渭云工时追踪规则 v6.2-JWY

仅对流水线状态中实际完成的 P1、P2、P3-1/P3-2/P3-3、P4、P5 采集工时。完成产物后必须先独立生成 AI 预估、收集测试人员反馈并调用记录脚本，确认保存前禁止展示下一步。

“采纳”取该步骤参考范围中间值；两次未提供实际值则记录中间值并备注“用户未反馈，采用参考中间值”。跨步骤补录只使用 `scripts/jwy_tracking.py` 从 `.jwy_pipeline_state.json` 计算的 eligible 集合，不得补录本次未执行的可选步骤或未选择的 Step3 分支。

身份验证查询 MySQL `agent_team_roster`，仅允许 `JWY` 精确匹配成员；数据库配置须在本机填写，不得在对话或发布包中收集、输出或保存凭据。
""")


def _workbuddy_plugin() -> dict:
    return {
        "name": WORKBUDDY_NAME,
        "version": "1.0.0",
        "description": "Jingweiyun testing expert for the requirement-to-testcase pipeline with measurable time savings.",
        "author": {"name": "Quality Management Team", "email": "qa@kingdee.com"},
        "agents": ["./agents/jingweiyun-testing-expert.md"],
        "skills": ["./skills/jwy-testing-expert-skill"],
        "expertType": "agent",
        "agentName": "jingweiyun-testing-expert",
        "displayName": {"en": "Jingweiyun Testing Expert", "zh": "泾渭云测试专家"},
        "profession": {"en": "Jingweiyun Functional Testing Expert", "zh": "泾渭云功能测试专家"},
        "displayDescription": {"en": "[v1.0.0] Jingweiyun requirement-to-testcase workflow with time-saving tracking.", "zh": "【v1.0.0】覆盖需求确认、代码分析、脑图用例、DMP转换和归档，并以强制工时追踪量化泾渭云测试效能。"},
        "avatar": "avatars/expert.png",
        "categoryId": "10-ProjectQuality",
        "defaultInitPrompt": {"zh": "开始泾渭云需求测试流程", "en": "Start the Jingweiyun testing workflow"},
        "plugin": WORKBUDDY_NAME,
        "tags": [{"en": "Requirement Testing", "zh": "需求测试"}, {"en": "Testcase Generation", "zh": "用例生成"}, {"en": "Time Savings", "zh": "工时追踪"}],
        "quickPrompts": [{"en": "Start the Jingweiyun testing workflow", "zh": "开始泾渭云需求测试流程"}, {"en": "Analyze a Jingweiyun code change", "zh": "执行泾渭云代码分析"}, {"en": "Show time-saving statistics", "zh": "查看泾渭云工时统计"}],
    }


def _write_workbuddy_files(package: Path) -> None:
    _write(package / ".codebuddy-plugin" / "plugin.json", json.dumps(_workbuddy_plugin(), ensure_ascii=False, indent=2) + "\n")
    _write(package / "agents" / "jingweiyun-testing-expert.md", """---
name: jingweiyun-testing-expert
description: Activates for Jingweiyun requirement analysis, code analysis, testcase generation, DMP conversion, Confluence archival, or time-saving tracking.
displayName:
  en: "Jingweiyun Testing Expert"
  zh: "泾渭云测试专家"
profession:
  en: "Jingweiyun Functional Testing Expert"
  zh: "泾渭云功能测试专家"
maxTurns: 100
---

# 泾渭云测试专家

会话开始先按内嵌时间追踪规则检查本机 MySQL 配置，再实时查询 `agent_team_roster`。仅接受具备 `JWY` 业务线权限的姓名精确匹配；不得展示名单、不得提供 fallback。

每个步骤前必须阅读 Skill 指定的 prompt。完成实际执行的 P1、P2、P3-1/2/3、P4、P5 后，立即采集并确认节省工时，完成记录前禁止展示下一步。Step4 仅在 Step3-选项1或2完成后执行。所有输出使用中文，明确区分事实、推断、建议和待确认项。
""")
    _write(package / "avatars" / ".gitkeep", "")
    _write(package / "README.md", "# 泾渭云测试专家 v1.0.0\n\nWorkBuddy 专家包。将整个目录交由专家包管理器校验、注册和打包。数据库与 Confluence 凭据仅在本机配置，不随包分发。\n")


def _manifest(output: Path) -> None:
    rows = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.sha256":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append(f"{digest}  {path.relative_to(output).as_posix()}")
    _write(output / "MANIFEST.sha256", "\n".join(rows) + "\n")


def build_packages(core: Path, output: Path) -> dict:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    vscode = output / VSCODE_NAME
    workbuddy = output / WORKBUDDY_NAME
    _copy_core(core, vscode)
    skill_destination = workbuddy / "skills" / VSCODE_NAME
    _copy_core(core, skill_destination)
    _write_workbuddy_files(workbuddy)
    _manifest(output)
    return {"workbuddy": str(workbuddy), "vscode": str(vscode)}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = build_packages(root / "packages" / "jwy-requirement-pipeline-core", root / "dist")
    print(json.dumps(result, ensure_ascii=False))
