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
        if path.suffix.lower() not in {".md", ".py", ".yaml", ".json", ".bat", ".ps1"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for forbidden in FORBIDDEN_TEXT:
            text = text.replace(forbidden, "{部署配置}")
        path.write_text(text, encoding="utf-8")


def _copy_core(core: Path, destination: Path) -> None:
    """把 core 包复制到目标目录，并把 skills/ 重命名为 modules/（VS Code skill 约定）。"""
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(core, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    nested_skills = destination / "skills"
    if nested_skills.exists():
        nested_skills.rename(destination / "modules")
    _sanitize_text_files(destination)


def _write_workbuddy_files(package: Path, core: Path, packaging: Path) -> None:
    """写入 WorkBuddy 专家包特有的元数据文件，并从 core/assets 还原头像。"""
    _write(package / ".codebuddy-plugin" / "plugin.json",
           json.dumps(json.loads((packaging / "plugin.json").read_text(encoding="utf-8")),
                      ensure_ascii=False, indent=2) + "\n")
    _write(package / "agents" / "jingweiyun-testing-expert.md",
           (packaging / "agent.md").read_text(encoding="utf-8"))
    _write(package / "README.md",
           (core / "README.md").read_text(encoding="utf-8"))
    _write(package / "install.ps1",
           (core / "install.ps1").read_text(encoding="utf-8"))

    avatars = package / "avatars"
    avatars.mkdir(parents=True, exist_ok=True)
    avatar_source = core / "assets" / "expert.png"
    if avatar_source.exists():
        shutil.copy2(avatar_source, avatars / "expert.png")


def _manifest(output: Path) -> None:
    rows = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.sha256":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append(f"{digest}  {path.relative_to(output).as_posix()}")
    _write(output / "MANIFEST.sha256", "\n".join(rows) + "\n")


def build_packages(core: Path, output: Path, packaging: Path | None = None) -> dict:
    if packaging is None:
        packaging = core.parents[1] / "tools" / "packaging"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    vscode = output / VSCODE_NAME
    workbuddy = output / WORKBUDDY_NAME

    # VS Code pure skill
    _copy_core(core, vscode)
    shutil.copy2(packaging / "skill_entry.md", vscode / "SKILL.md")

    # WorkBuddy expert package: skill 嵌入 + expert metadata
    skill_destination = workbuddy / "skills" / VSCODE_NAME
    _copy_core(core, skill_destination)
    shutil.copy2(packaging / "skill_entry.md", skill_destination / "SKILL.md")
    _write_workbuddy_files(workbuddy, core, packaging)

    _manifest(output)
    return {"workbuddy": str(workbuddy), "vscode": str(vscode)}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = build_packages(
        root / "packages" / "jwy-requirement-pipeline-core",
        root / "dist",
        root / "tools" / "packaging",
    )
    print(json.dumps(result, ensure_ascii=False))
