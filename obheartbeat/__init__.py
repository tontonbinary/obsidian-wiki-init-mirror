#!/usr/bin/env python3
"""
obheartbeat - Obsidian Wiki Heartbeat Scanner

为 obsidian-wiki-init skill 提供自动化扫描入口。

使用方法:
    python3 -m obheartbeat scan <vault_path> [--json]
    python3 -m obheartbeat lint <vault_path> [--json]  
    python3 -m obheartbeat check <vault_path> [--check <check_id>] [--json]
"""
import sys
import os
import json
import argparse
from typing import Any, Optional, Dict, List, Union
from pathlib import Path
from datetime import datetime, timezone

# 确保能导入 scripts 目录下的模块
SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from vault_utils import relative_to_vault, get_markdown_files, extract_wikilinks, update_indexed_by
    from check_scanner import run_all_checks
    from wiki_lint import run_lint
    from index_generator import generate_missing_indexes
    from lint_state import (
        load_lint_state,
        save_lint_state,
        ensure_issue,
        prune_fixed_issues,
        get_active_issues,
        make_issue_id_custom,
    )
except ImportError as e:
    print(f"[ERROR] 无法导入 obheartbeat 模块: {e}", file=sys.stderr)
    sys.exit(1)


# 5 个外部扫描位置
EXTERNAL_SOURCES = [
    "shared/board/",
    "shared/SharedMemory/",
]


def _get_external_paths(home: Path) -> list[Path]:
    """获取 5 个外部扫描路径。"""
    claw = home / ".openclaw"
    paths = []
    
    # shared 目录
    for src in EXTERNAL_SOURCES:
        p = claw / src
        if p.exists():
            paths.append(p)
    
    # workspace 下的 memory 文件
    workspaces = claw / "workspaces"
    if workspaces.exists():
        for agent_dir in workspaces.iterdir():
            memory_dir = agent_dir / "workspace" / "memory"
            for fname in ["MEMORY.md", "TOOLS.md", "USER.md"]:
                f = memory_dir / fname
                if f.exists():
                    paths.append(f)
    
    return paths


def _scan_external_for_indexed_by(vault: Path, scanner_name: str = "obheartbeat", purpose: str = "定期维护扫描") -> dict:
    """
    扫描 5 个外部位置，更新被引用 wiki 页面的 indexed_by。
    
    Returns:
        dict: 扫描结果（updated count, etc）
    """
    home = Path.home()
    external_paths = _get_external_paths(home)
    
    updated = 0
    errors = 0
    scanned_files = 0
    
    # 建立 wiki 页面名称到路径的映射
    wiki_files = {}
    for mf in get_markdown_files(vault):
        # 使用文件名（不含路径）作为 key
        name = mf.stem  # filename without .md
        wiki_files[name.lower()] = mf
    
    # 扫描每个外部文件
    for ext_path in external_paths:
        if ext_path.is_file():
            files_to_scan = [ext_path]
        else:
            files_to_scan = get_markdown_files(ext_path)
        
        for ext_file in files_to_scan:
            scanned_files += 1
            try:
                content = ext_file.read_text(encoding="utf-8")
                wikilinks = extract_wikilinks(content)
                
                # 更新每个被引用的 wiki 页面
                for link in wikilinks:
                    link_lower = link.lower()
                    if link_lower in wiki_files:
                        if update_indexed_by(wiki_files[link_lower], scanner_name, purpose):
                            updated += 1
            except Exception:
                errors += 1
    
    return {
        "scanned_files": scanned_files,
        "updated_pages": updated,
        "errors": errors,
    }


def scan_vault(vault_path: str, workspace_path: str = None, check_id: str = None) -> Dict:
    """
    扫描 vault，返回完整报告。
    
    Args:
        vault_path: Vault 路径
        workspace_path: Agent workspace 路径（用于 memory_to_wiki_extract）
        check_id: 仅运行指定 check（None 则运行所有）
    
    Returns:
        dict: 扫描结果
    """
    from datetime import datetime, timezone
    
    vault = Path(vault_path).expanduser()
    if not vault.exists():
        return {"status": "error", "message": f"Vault 不存在: {vault}"}
    
    workspace: Optional[Path] = Path(workspace_path).expanduser() if workspace_path else None
    
    # Run checks
    if check_id:
        check_results = [_run_single_check(check_id, vault, workspace)]
        if check_results[0] is None:
            return {"status": "error", "message": f"未知 check: {check_id}"}
    else:
        check_results = run_all_checks(vault, workspace)
    
    # Run lint
    lint_result = run_lint(vault)
    lint_result = _process_lint_state(vault, lint_result)
    
    # Auto-fix missing indexes
    auto_fixed = generate_missing_indexes(vault)
    if auto_fixed:
        lint_result.setdefault("auto_fixed", []).extend(auto_fixed)
    
    # 扫描外部位置，更新 indexed_by
    indexed_by_result = _scan_external_for_indexed_by(vault)
    
    # Build notifications
    notifications = _build_notifications(check_results, lint_result)
    
    return {
        "vault": str(vault),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "ok",
        "checks": [r for r in check_results if r.get("count", 0) > 0],
        "lint": lint_result,
        "indexed_by": indexed_by_result,
        "notifications": notifications,
    }


def _run_single_check(check_id: str, vault: Path, workspace: Optional[Path]) -> Optional[Dict]:
    """运行单个 check。"""
    # Import here to avoid circular import
    from check_scanner import (
        check_batch_compile_folder,
        check_batch_compile_7days,
        check_scheduled_pending,
        check_optional_recompile,
        check_undiscussed_raw,
        check_memory_to_wiki_extract,
        check_wiki_lint,
    )
    
    check_map = {
        "batch_compile_folder": check_batch_compile_folder,
        "batch_compile_7days": check_batch_compile_7days,
        "scheduled_pending": check_scheduled_pending,
        "optional_recompile": check_optional_recompile,
        "undiscussed_raw": check_undiscussed_raw,
        "memory_to_wiki_extract": lambda v, w: check_memory_to_wiki_extract(w),
        "wiki_lint": lambda v, w: check_wiki_lint(v),
    }
    
    func = check_map.get(check_id)
    if not func:
        return None
    
    if check_id == "memory_to_wiki_extract":
        return func(vault, workspace)
    elif check_id == "wiki_lint":
        return func(vault, workspace)
    else:
        return func(vault)


def _process_lint_state(vault: Path, lint_result: Dict) -> Dict:
    """处理 lint 状态。"""
    state = load_lint_state(vault)
    
    # Track new issues
    for issue in lint_result.get("issues", []):
        issue_id = issue.get("id")
        if issue_id:
            ensure_issue(state, issue_id, issue)
    
    # Prune fixed issues
    current_ids = {i.get("id") for i in lint_result.get("issues", []) if i.get("id")}
    prune_fixed_issues(vault, state, current_ids)
    
    # Save state
    save_lint_state(vault, state)
    
    # Filter to active issues only
    active = get_active_issues(state)
    lint_result["issues"] = active
    lint_result["issue_count"] = len(active)
    
    return lint_result


def _build_notifications(check_results: List[Dict], lint_result: Dict) -> List[Dict]:
    """构建通知列表（按类型限制数量）。"""
    MAX_PER_TYPE = 2
    
    maintenance_items = []
    discussion_items = []
    
    for check in check_results:
        if check.get("count", 0) == 0:
            continue
        
        notif = {
            "id": check.get("id"),
            "type": check.get("type"),
            "message": check.get("message"),
            "count": check.get("count"),
        }
        
        if check.get("type") == "maintenance":
            maintenance_items.append(notif)
        else:
            discussion_items.append(notif)
    
    # Add lint issues as maintenance
    lint_issues = lint_result.get("issues", [])
    if lint_issues:
        lint_notif = {
            "id": "wiki_lint",
            "type": "maintenance",
            "message": f"Wiki 检查完成：{len(lint_issues)} 个活跃问题",
            "count": len(lint_issues),
            "details": lint_issues[:3],  # 最多3个详情
        }
        maintenance_items.append(lint_notif)
    
    # Limit per type
    notifications = maintenance_items[:MAX_PER_TYPE] + discussion_items[:MAX_PER_TYPE]
    
    return notifications


def heartbeat_activate(vault_path: str = None, workspace_path: str = None) -> dict:
    """
    首次激活时调用：将 obheartbeat 注册到当前 agent 的 HEARTBEAT.md
    
    Args:
        vault_path: Vault 路径（可选，默认从已知路径推断）
        workspace_path: Agent workspace 路径（必填）
    
    Returns:
        操作结果 dict
    """
    # workspace_path 是必填的
    workspace = Path(workspace_path).expanduser() if workspace_path else None
    if not workspace:
        return {
            "success": False,
            "error": "workspace_path 是必填参数"
        }
    
    heartbeat_file = workspace / "HEARTBEAT.md"
    
    if not heartbeat_file.exists():
        return {
            "success": False,
            "error": f"HEARTBEAT.md 不存在: {heartbeat_file}"
        }
    
    # 生成 heartbeat 命令
    if vault_path:
        vault = Path(vault_path)
    else:
        # 从 vault_utils 推断
        vault = Path("/Volumes/Binary HD/obsidian/Xiaoxian")
    
    heartbeat_cmd = f"PYTHONPATH=~/.openclaw/skills/obsidian-wiki-init python3 -m obheartbeat scan \"{vault}\" --json"
    
    # 检查是否已存在
    content = heartbeat_file.read_text(encoding="utf-8")
    if "obheartbeat" in content:
        return {
            "success": True,
            "message": "obheartbeat 已存在于 HEARTBEAT.md，无需重复添加",
            "file": str(heartbeat_file)
        }
    
    # 追加到 HEARTBEAT.md
    new_entry = f"\n## obsidian-wiki-init (OBHeartbeat)\n{heartbeat_cmd}\n"
    
    with open(heartbeat_file, "a", encoding="utf-8") as f:
        f.write(new_entry)
    
    return {
        "success": True,
        "message": "已添加 obheartbeat 到 HEARTBEAT.md",
        "command": heartbeat_cmd,
        "file": str(heartbeat_file)
    }


def main():
    parser = argparse.ArgumentParser(
        description="OBheartbeat - Obsidian Wiki Vault Scanner"
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # activate 命令（首次激活时调用）
    activate_parser = subparsers.add_parser("activate", help="首次激活时注册 obheartbeat 到 HEARTBEAT.md")
    activate_parser.add_argument("--vault", help="Vault 路径")
    activate_parser.add_argument("--workspace", help="Agent workspace 路径（必填）")
    activate_parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    # scan 命令
    scan_parser = subparsers.add_parser("scan", help="完整扫描 vault")
    scan_parser.add_argument("vault_path", help="Vault 路径")
    scan_parser.add_argument("--workspace", help="Agent workspace 路径")
    scan_parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    # lint 命令
    lint_parser = subparsers.add_parser("lint", help="仅执行 wiki lint")
    lint_parser.add_argument("vault_path", help="Vault 路径")
    lint_parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    # check 命令
    check_parser = subparsers.add_parser("check", help="仅执行 raw/ checks")
    check_parser.add_argument("vault_path", help="Vault 路径")
    check_parser.add_argument("--check-id", help="仅运行指定 check")
    check_parser.add_argument("--workspace", help="Agent workspace 路径")
    check_parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # activate 命令不需要 vault_path 但需要 workspace
    if args.command == "activate":
        vault_path = None
        workspace = os.path.expanduser(args.workspace) if hasattr(args, 'workspace') and args.workspace else None
    elif args.command:
        vault_path = os.path.expanduser(args.vault_path)
        workspace = os.path.expanduser(args.workspace) if hasattr(args, 'workspace') and args.workspace else None
        
        if not os.path.exists(vault_path):
            error = {"status": "error", "message": f"Vault 路径不存在: {vault_path}"}
            print(json.dumps(error, ensure_ascii=False) if args.json else f"[ERROR] {error['message']}")
            sys.exit(1)
    else:
        vault_path = None
        workspace = None
    
    try:
        if args.command == "activate":
            result = heartbeat_activate(
                vault_path=args.vault if hasattr(args, 'vault') else None,
                workspace_path=args.workspace if hasattr(args, 'workspace') else None
            )
        elif args.command == "scan":
            result = scan_vault(vault_path, workspace)
        elif args.command == "lint":
            from wiki_lint import run_lint
            lint_result = run_lint(Path(vault_path))
            result = {
                "vault": vault_path,
                "status": "ok",
                "lint": lint_result,
            }
        elif args.command == "check":
            from check_scanner import run_all_checks
            check_results = run_all_checks(Path(vault_path), Path(workspace) if workspace else None)
            result = {
                "vault": vault_path,
                "status": "ok",
                "checks": [r for r in check_results if r.get("count", 0) > 0],
            }
        
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_human_readable(result)
            
    except Exception as e:
        error = {"status": "error", "message": str(e)}
        print(json.dumps(error, ensure_ascii=False) if args.json else f"[ERROR] {e}")
        sys.exit(1)


def _print_human_readable(result: Dict):
    """以人类可读的格式输出结果"""
    print(f"\n{'='*60}")
    print(f"OBheartbeat 扫描报告")
    print(f"{'='*60}")
    print(f"Vault: {result.get('vault', 'N/A')}")
    print(f"时间: {result.get('timestamp', 'N/A')}")
    print(f"状态: {result.get('status', 'unknown')}")
    
    checks = result.get("checks", [])
    if not checks:
        print("\n✅ 未发现需要处理的问题")
    else:
        print(f"\n发现 {len(checks)} 项检查:\n")
        
        for check in checks:
            check_id = check.get("id", "unknown")
            check_type = check.get("type", "unknown")
            count = check.get("count", 0)
            message = check.get("message", "")
            
            icon = "🔧" if check_type == "maintenance" else "💬"
            print(f"{icon} [{check_id}] ({check_type})")
            print(f"   数量: {count}")
            print(f"   说明: {message}")
            
            items = check.get("items", [])
            if items:
                print(f"   详情:")
                for item in items[:5]:
                    if isinstance(item, dict):
                        if "file" in item:
                            print(f"     - {item.get('file', 'N/A')}")
                        elif "folder" in item:
                            print(f"     - {item.get('folder', 'N/A')}: {item.get('count', 0)} 个文件")
                        else:
                            print(f"     - {item}")
                    else:
                        print(f"     - {item}")
                if len(items) > 5:
                    print(f"     ... 还有 {len(items) - 5} 项")
            print()
    
    # 显示 lint 结果
    lint = result.get("lint", {})
    if lint and lint.get("issues"):
        issues = lint["issues"]
        print(f"\n🔍 Wiki Lint: {len(issues)} 个问题")
        for issue in issues[:3]:
            print(f"   - [{issue.get('type', 'unknown')}] {issue.get('description', '')}")
        if len(issues) > 3:
            print(f"   ... 还有 {len(issues) - 3} 个问题")
    
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
