#!/usr/bin/env python3
"""
check_scanner.py — 7 OBHeartbeat checks for raw/ and wiki/ scanning.

Each check returns a dict:
    {
        "id": str,
        "type": "maintenance" | "discussion",
        "count": int,
        "items": list[dict],
        "message": str,
        "action": "notify_agent" | "extract_to_raw" | "report",
    }
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from vault_utils import (
    parse_frontmatter,
    get_markdown_files,
    days_since,
    parse_date,
    relative_to_vault,
)


def run_all_checks(vault: Path, workspace: Path | None = None) -> list[dict[str, Any]]:
    """Run every check and return a list of results."""
    return [
        check_batch_compile_folder(vault),
        check_batch_compile_7days(vault),
        check_scheduled_pending(vault),
        check_optional_recompile(vault),
        check_undiscussed_raw(vault),
        check_memory_to_wiki_extract(vault, workspace),
        check_wiki_lint(vault),
    ]


# ---------------------------------------------------------------------------
# Check 1: batch_compile_folder
# ---------------------------------------------------------------------------

def check_batch_compile_folder(vault: Path) -> dict[str, Any]:
    """同一文件夹内 never_compiled ≥3 条。"""
    raw_dir = vault / "raw"
    if not raw_dir.exists():
        return _empty_result("batch_compile_folder", "maintenance")

    folder_counts: dict[str, list[Path]] = {}
    for path in get_markdown_files(raw_dir):
        fm = parse_frontmatter(path)
        if fm.get("never_compiled") is True:
            folder = path.parent.name
            folder_counts.setdefault(folder, []).append(path)

    triggered = {f: files for f, files in folder_counts.items() if len(files) >= 3}
    if not triggered:
        return _empty_result("batch_compile_folder", "maintenance")

    items = []
    for folder, files in triggered.items():
        items.append({
            "folder": f"raw/{folder}",
            "count": len(files),
            "files": [relative_to_vault(p, vault) for p in files],
        })

    total = sum(len(files) for files in triggered.values())
    return {
        "id": "batch_compile_folder",
        "type": "maintenance",
        "count": total,
        "items": items,
        "message": f"有 {total} 个从未编译的 raw 文件分布在 {len(triggered)} 个文件夹中（≥3条/文件夹），请 Agent 编译到 wiki",
        "action": "notify_agent",
    }


# ---------------------------------------------------------------------------
# Check 2: batch_compile_7days
# ---------------------------------------------------------------------------

def check_batch_compile_7days(vault: Path) -> dict[str, Any]:
    """从未编译且 recorded ≥7 天。"""
    raw_dir = vault / "raw"
    if not raw_dir.exists():
        return _empty_result("batch_compile_7days", "maintenance")

    files: list[Path] = []
    for path in get_markdown_files(raw_dir):
        fm = parse_frontmatter(path)
        if fm.get("never_compiled") is True:
            recorded = parse_date(fm.get("recorded"))
            if recorded and days_since(recorded) is not None and days_since(recorded) >= 7:
                files.append(path)

    if not files:
        return _empty_result("batch_compile_7days", "maintenance")

    return {
        "id": "batch_compile_7days",
        "type": "maintenance",
        "count": len(files),
        "items": [{"file": relative_to_vault(p, vault), "recorded": parse_date(parse_frontmatter(p).get("recorded"))} for p in files],
        "message": f"有 {len(files)} 个从未编译的 raw 文件已超过 7 天，请 Agent 编译到 wiki",
        "action": "notify_agent",
    }


# ---------------------------------------------------------------------------
# Check 3: scheduled_pending
# ---------------------------------------------------------------------------

def check_scheduled_pending(vault: Path) -> dict[str, Any]:
    """scheduled ≤ today 且 discussed_1st 为空。"""
    raw_dir = vault / "raw"
    if not raw_dir.exists():
        return _empty_result("scheduled_pending", "discussion")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    files: list[tuple[Path, dict[str, Any]]] = []

    for path in get_markdown_files(raw_dir):
        fm = parse_frontmatter(path)
        scheduled = parse_date(fm.get("scheduled"))
        discussed = parse_date(fm.get("discussed_1st"))
        if scheduled and scheduled <= today and not discussed:
            files.append((path, fm))

    if not files:
        return _empty_result("scheduled_pending", "discussion")

    items = []
    for path, fm in files:
        items.append({
            "file": relative_to_vault(path, vault),
            "scheduled": parse_date(fm.get("scheduled")),
            "scheduled_note": fm.get("scheduled_note", ""),
        })

    return {
        "id": "scheduled_pending",
        "type": "discussion",
        "count": len(files),
        "items": items,
        "message": f"有 {len(files)} 个预定讨论的 raw 文件未讨论，请判断：项目已完成→主动找用户讨论；项目未完成→更新 scheduled",
        "action": "notify_agent",
    }


# ---------------------------------------------------------------------------
# Check 4: optional_recompile
# ---------------------------------------------------------------------------

def check_optional_recompile(vault: Path) -> dict[str, Any]:
    """compiled_1st 存在但 compiled_2nd 为空，且 stop_compiling != true。"""
    raw_dir = vault / "raw"
    if not raw_dir.exists():
        return _empty_result("optional_recompile", "discussion")

    files: list[Path] = []
    for path in get_markdown_files(raw_dir):
        fm = parse_frontmatter(path)
        c1 = parse_date(fm.get("compiled_1st"))
        c2 = parse_date(fm.get("compiled_2nd"))
        stop = fm.get("stop_compiling")
        if c1 and not c2 and stop is not True:
            files.append(path)

    if not files:
        return _empty_result("optional_recompile", "discussion")

    return {
        "id": "optional_recompile",
        "type": "discussion",
        "count": len(files),
        "items": [{"file": relative_to_vault(p, vault), "compiled_1st": parse_date(parse_frontmatter(p).get("compiled_1st"))} for p in files],
        "message": f"有 {len(files)} 个文件可以第二次编译，Agent 可自行判断是否有价值",
        "action": "notify_agent",
    }


# ---------------------------------------------------------------------------
# Check 5: undiscussed_raw
# ---------------------------------------------------------------------------

def check_undiscussed_raw(vault: Path) -> dict[str, Any]:
    """discussed_1st 为空、scheduled 为空、stop_compiling != true。
    排除 batch_compile_folder / batch_compile_7days 的文件。"""
    raw_dir = vault / "raw"
    if not raw_dir.exists():
        return _empty_result("undiscussed_raw", "discussion")

    # Collect files that would be caught by batch checks
    batch_files = set()
    for path in get_markdown_files(raw_dir):
        fm = parse_frontmatter(path)
        if fm.get("never_compiled") is True:
            batch_files.add(str(path.resolve()))

    files: list[Path] = []
    for path in get_markdown_files(raw_dir):
        if str(path.resolve()) in batch_files:
            continue
        fm = parse_frontmatter(path)
        discussed = parse_date(fm.get("discussed_1st"))
        scheduled = parse_date(fm.get("scheduled"))
        stop = fm.get("stop_compiling")
        if not discussed and not scheduled and stop is not True:
            files.append(path)

    if not files:
        return _empty_result("undiscussed_raw", "discussion")

    return {
        "id": "undiscussed_raw",
        "type": "discussion",
        "count": len(files),
        "items": [{"file": relative_to_vault(p, vault)} for p in files],
        "message": f"有 {len(files)} 个 raw 文件从未讨论且未被预约，建议找时间讨论",
        "action": "notify_agent",
    }


# ---------------------------------------------------------------------------
# Check 6: memory_to_wiki_extract
# ---------------------------------------------------------------------------

def check_memory_to_wiki_extract(vault: Path, workspace: Path | None = None) -> dict[str, Any]:
    """简化实现：检查 workspace/memory/MEMORY.md 行数和体积。"""
    if workspace is None:
        # Guess workspace from vault path (vault is usually /Volumes/Binary HD/obsidian/{AgentName})
        # Try to find a matching workspace under ~/.openclaw/workspaces/
        agent_name = vault.name
        ws = Path.home() / ".openclaw" / "workspaces" / agent_name / "workspace"
        if not ws.exists():
            ws = Path.home() / ".openclaw" / "workspaces" / agent_name.lower() / "workspace"
        if ws.exists():
            workspace = ws

    memory_path = (workspace / "MEMORY.md") if workspace else None
    if not memory_path or not memory_path.exists():
        return _empty_result("memory_to_wiki_extract", "maintenance")

    try:
        lines = memory_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return _empty_result("memory_to_wiki_extract", "maintenance")

    line_count = len(lines)
    # Heuristic: if MEMORY.md > 350 lines, suggest extraction
    if line_count <= 350:
        return _empty_result("memory_to_wiki_extract", "maintenance")

    return {
        "id": "memory_to_wiki_extract",
        "type": "maintenance",
        "count": 1,
        "items": [{"memory_path": str(memory_path), "lines": line_count}],
        "message": f"MEMORY.md 已达 {line_count} 行，建议将稳定知识提取到 wiki",
        "action": "extract_to_raw",
    }


# ---------------------------------------------------------------------------
# Check 7: wiki_lint
# ---------------------------------------------------------------------------

def check_wiki_lint(vault: Path) -> dict[str, Any]:
    """Delegate to wiki_lint.py; if it doesn't exist yet, return empty."""
    try:
        from wiki_lint import run_lint
        lint_result = run_lint(vault)
        return {
            "id": "wiki_lint",
            "type": "maintenance",
            "count": lint_result.get("total_issues", 0),
            "items": lint_result.get("issues", []),
            "message": lint_result.get("message", "Wiki 健康检查完成"),
            "action": "report",
        }
    except ImportError:
        return _empty_result("wiki_lint", "maintenance")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_result(check_id: str, check_type: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "type": check_type,
        "count": 0,
        "items": [],
        "message": "",
        "action": "notify_agent",
    }
