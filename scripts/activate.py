#!/usr/bin/env python3
"""
obsidian-wiki-init activate: Register vault's OBHeartbeat scan to agent's HEARTBEAT.md

Usage: python3 activate.py <vault-path> [agent-name]
Example: python3 activate.py "/Volumes/Binary HD/obsidian/TS" TS

If agent-name is not provided, infers from vault directory name.
"""
import os
import sys
import re
from pathlib import Path


def find_agent_workspace(vault_path: str, agent_name: str = None) -> str:
    """Find agent workspace directory."""
    vault_path = os.path.expanduser(vault_path)
    vault_path = os.path.expandvars(vault_path)
    
    # If agent_name provided, direct path
    if agent_name:
        workspace = os.path.expanduser(f"~/.openclaw/workspaces/{agent_name}/workspace")
        if os.path.exists(workspace):
            return workspace
        raise FileNotFoundError(f"Agent workspace not found: {workspace}")
    
    # Infer from vault directory name
    vault_name = os.path.basename(os.path.normpath(vault_path))
    workspace = os.path.expanduser(f"~/.openclaw/workspaces/{vault_name}/workspace")
    if os.path.exists(workspace):
        return workspace
    
    # Try common agent names (scan workspaces directory)
    workspaces_dir = os.path.expanduser("~/.openclaw/workspaces")
    if os.path.exists(workspaces_dir):
        for entry in os.listdir(workspaces_dir):
            entry_path = os.path.join(workspaces_dir, entry)
            if os.path.isdir(entry_path):
                # Check if vault path is mentioned in any file
                for root, dirs, files in os.walk(entry_path):
                    for f in files:
                        if f.endswith('.md') or f.endswith('.json'):
                            try:
                                with open(os.path.join(root, f), 'r', encoding='utf-8') as fh:
                                    content = fh.read()
                                    if vault_path in content or vault_name in content:
                                        return os.path.join(entry_path, "workspace")
                            except:
                                continue
                    break  # Only check top level
    
    raise FileNotFoundError(
        f"Could not find agent workspace for vault: {vault_path}\n"
        f"Please provide agent-name explicitly."
    )


def read_heartbeat(workspace: str) -> str:
    """Read HEARTBEAT.md content."""
    hb_path = os.path.join(workspace, "HEARTBEAT.md")
    if os.path.exists(hb_path):
        with open(hb_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def write_heartbeat(workspace: str, content: str) -> None:
    """Write HEARTBEAT.md content."""
    hb_path = os.path.join(workspace, "HEARTBEAT.md")
    with open(hb_path, "w", encoding="utf-8") as f:
        f.write(content)


def has_obheartbeat_entry(content: str, vault_path: str) -> bool:
    """Check if OBHeartbeat entry for this vault already exists."""
    # Check for vault path in content
    return vault_path in content


def add_obheartbeat_entry(content: str, vault_path: str) -> str:
    """Add OBHeartbeat scan entry to HEARTBEAT.md content."""
    vault_path = os.path.expanduser(vault_path)
    vault_path = os.path.expandvars(vault_path)
    
    entry = f"""\n## OBHeartbeat (obsidian-wiki-init)
# 扫描知识库：检查 raw/ 待编译文件、wiki/ 健康状态
PYTHONPATH=~/.openclaw/skills/obsidian-wiki-init python3 -m obheartbeat scan "{vault_path}" --json
"""
    
    # Check if content already has OBHeartbeat section
    if "## OBHeartbeat" in content:
        # Append to existing section (before any other section or at end)
        lines = content.split('\n')
        result = []
        inserted = False
        
        for i, line in enumerate(lines):
            result.append(line)
            if line.strip() == "## OBHeartbeat (obsidian-wiki-init)" and not inserted:
                # Skip existing lines in this section until next section or end
                j = i + 1
                while j < len(lines) and not lines[j].startswith('#') and lines[j].strip():
                    if vault_path not in lines[j]:
                        result.append(lines[j])
                    j += 1
                # Add our entry
                result.append(f"# 扫描知识库：检查 raw/ 待编译文件、wiki/ 健康状态")
                result.append(f'PYTHONPATH=~/.openclaw/skills/obsidian-wiki-init python3 -m obheartbeat scan "{vault_path}" --json')
                result.append("")
                inserted = True
                # Continue from where we left off
                while j < len(lines):
                    result.append(lines[j])
                    j += 1
                break
        
        if inserted:
            return '\n'.join(result)
        else:
            return content + entry
    else:
        # Add at end
        if content and not content.endswith('\n'):
            content += '\n'
        return content + entry


def update_agents_md(workspace: str, vault_path: str) -> bool:
    """Update AGENTS.md with wiki vault reference if not already present."""
    agents_path = os.path.join(workspace, "AGENTS.md")
    if not os.path.exists(agents_path):
        return False
    
    with open(agents_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check if already has wiki reference
    if vault_path in content or "Wiki Vault" in content or "wiki" in content.lower():
        return False  # Already referenced
    
    # Add wiki reference section
    wiki_section = f"""\n## Wiki Vault

**Vault 路径**: `{vault_path}`
- 外部知识库，存储稳定信息（世界知识/周期性规律/环境认知）
- 瞬时状态放 MEMORY.md，时效后 auto-dream 忘却
- OBHeartbeat 自动扫描维护
"""
    
    content = content + wiki_section
    with open(agents_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return True


def activate(vault_path: str, agent_name: str = None) -> dict:
    """Activate vault: register OBHeartbeat to agent's HEARTBEAT.md."""
    result = {
        "success": False,
        "vault_path": vault_path,
        "agent_workspace": None,
        "heartbeat_updated": False,
        "agents_md_updated": False,
        "messages": []
    }
    
    try:
        # Find agent workspace
        workspace = find_agent_workspace(vault_path, agent_name)
        result["agent_workspace"] = workspace
        
        # Read current HEARTBEAT.md
        content = read_heartbeat(workspace)
        
        # Check if already registered
        if has_obheartbeat_entry(content, vault_path):
            result["messages"].append(f"OBHeartbeat already registered for {vault_path}")
            result["heartbeat_updated"] = True
            result["success"] = True
            return result
        
        # Add OBHeartbeat entry
        new_content = add_obheartbeat_entry(content, vault_path)
        write_heartbeat(workspace, new_content)
        result["heartbeat_updated"] = True
        result["messages"].append(f"Added OBHeartbeat scan to HEARTBEAT.md")
        
        # Update AGENTS.md
        agents_updated = update_agents_md(workspace, vault_path)
        result["agents_md_updated"] = agents_updated
        if agents_updated:
            result["messages"].append(f"Added Wiki Vault reference to AGENTS.md")
        
        result["success"] = True
        
    except FileNotFoundError as e:
        result["messages"].append(str(e))
    except Exception as e:
        result["messages"].append(f"Error: {e}")
    
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 activate.py <vault-path> [agent-name]")
        print("Example: python3 activate.py '/Volumes/Binary HD/obsidian/TS' TS")
        sys.exit(1)
    
    vault_path = sys.argv[1]
    agent_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"[obsidian-wiki-init] Activating vault: {vault_path}")
    
    result = activate(vault_path, agent_name)
    
    if result["success"]:
        print(f"[OK] Activated successfully")
        print(f"   Workspace: {result['agent_workspace']}")
        print(f"   HEARTBEAT.md: {'Updated' if result['heartbeat_updated'] else 'No change'}")
        print(f"   AGENTS.md: {'Updated' if result['agents_md_updated'] else 'No change'}")
        for msg in result["messages"]:
            print(f"   > {msg}")
    else:
        print(f"[ERROR] Activation failed:")
        for msg in result["messages"]:
            print(f"   > {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
