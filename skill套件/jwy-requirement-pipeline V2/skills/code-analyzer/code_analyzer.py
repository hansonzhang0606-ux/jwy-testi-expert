"""Compatibility facade for the unified multi-stack code analysis engine."""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional, Sequence

from business_extractor import extract_business_logic


def analyze_code(
    repo_path: str,
    branch: str,
    baseline: str = "origin/master",
    selected_files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Canonical public entry; engine selection stays inside business_extractor."""
    return extract_business_logic(repo_path, branch, baseline, selected_files=selected_files)


class CodeAnalyzer:
    """Backward-compatible class adapter with no independent parsing path."""

    def __init__(self, repo_dir=None):
        self.repo_dir = repo_dir or os.getcwd()

    def _run_git(self, args: Sequence[str]):
        """Retained for callers that use the safe Git helper directly."""
        if isinstance(args, (str, bytes)):
            raise TypeError("Git arguments must be a sequence, not a shell command string")
        command = ["git", "-C", os.fspath(self.repo_dir), *[str(arg) for arg in args]]
        try:
            result = subprocess.run(
                command,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            return result.returncode, result.stdout
        except Exception as exc:
            return -1, str(exc)

    def analyze_branch(
        self,
        branch_name: str,
        baseline: str = "origin/master",
        selected_files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Delegate to the unified AST/SQL/config-aware engine and retain legacy aliases."""
        result = analyze_code(self.repo_dir, branch_name, baseline, selected_files)
        file_changes = result.get("file_changes", {})
        files = [{"status": status, "path": path} for path, status in file_changes.items()]
        result.update(
            branch=branch_name,
            files=files,
            controllers=[item["path"] for item in files if "controller" in item["path"].casefold()],
            services=[item["path"] for item in files if "service" in item["path"].casefold()],
            daos=[item["path"] for item in files if any(token in item["path"].casefold() for token in ("mapper", "dao", "repository"))],
            entities=[item["path"] for item in files if any(token in item["path"].casefold() for token in ("entity", "dto", "vo"))],
            sqls=result.get("sql_analysis", []),
            apis=result.get("api_endpoints", []),
            risks=result.get("analysis_warnings", []),
        )
        return result
