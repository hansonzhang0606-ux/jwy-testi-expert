# 泾渭云测试专家套件

本仓库维护泾渭云测试需求流水线的共享核心，以及两个可独立部署的发布包：

- `dist/jingweiyun-testing-expert`：WorkBuddy 单 Agent 专家包
- `dist/jwy-testing-expert-skill`：VS Code 纯 Skill 包
- `packages/jwy-requirement-pipeline-core`：共享源码核心

流水线按 `step1`～`step5` 调度需求确认、代码分析、需求脑图、DMP 用例和 Confluence 归档，并使用状态文件记录进度。运行时配置（数据库、Confluence、产物目录）仅从本机读取，不随仓库分发。

## 构建与验证

```powershell
python tools/build_packages.py
python -m unittest discover -s tests -v
```

构建结果和 SHA-256 清单写入 `dist/MANIFEST.sha256`。
