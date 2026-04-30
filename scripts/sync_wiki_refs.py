#!/usr/bin/env python3
"""
Sync wiki page references from external files (MEMORY.md, TOOLS.md, USER.md, etc.)
Updates wiki page frontmatter with `referenced_by` field.
"""
from pathlib import Path
from typing import Any
import re

from vault_utils import parse_frontmatter, write_frontmatter, relative_to_vault

# Files to scan for wiki references
EXTERNAL_REF_SOURCES = [
    # Board
    "~/.openclaw/shared/board/**/*.md",
    # Shared memory
    "~/.openclaw/shared/SharedMemory/**/*.md",
    # Agent workspace memory files
    "~/.openclaw/workspaces/*/workspace/memory/MEMORY.md",
    "~/.openclaw/workspaces/*/workspace/memory/TOOLS.md",
    "~/.openclaw/workspaces/*/workspace/memory/USER.md",
]


def _resolve_glob(pattern: str) -> list[Path]:
    """Resolve glob pattern, expanding ~."""
    expanded = Path(pattern).expanduser()
    if '**' in pattern:
        return list(expanded.parent.rglob(expanded.name))
    elif '*' in pattern:
        return list(expanded.parent.glob(expanded.name))
    elif expanded.exists():
        return [expanded]
    return []


def _extract_wikilinks(text: str) -> list[str]:
    """Extract wikilink targets like [[page name]]."""
    pattern = r'\[\[([^\]]+)\]\]'
    return re.findall(pattern, text)


def _safe_read_text(path: Path) -> str:
    """Read text file, return empty string on error."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _update_referenced_by(wiki_page: Path, vault: Path, source_files: list[str]) -> bool:
    """Update the referenced_by field in a wiki page's frontmatter.
    
    Returns True if updated, False if no change needed.
    """
    fm = parse_frontmatter(wiki_page)
    existing = fm.get("referenced_by", [])
    if isinstance(existing, str):
        existing = [existing]
    
    # Convert to set for comparison
    existing_set = set(existing)
    new_set = set(source_files)
    
    if existing_set == new_set:
        return False
    
    # Update frontmatter
    fm["referenced_by"] = sorted(list(new_set))
    fm["updated"] = "2026-04-26"  # Could use actual date
    
    # Read content after frontmatter
    text = _safe_read_text(wiki_page)
    m = re.match(r'^---\s*\n.*?\n---\s*\n', text, re.DOTALL)
    if m:
        content = text[m.end():]
    else:
        content = text
    
    write_frontmatter(wiki_page, fm, content)
    return True


def sync_wiki_references(vault: Path) -> dict[str, Any]:
    """Scan external files for wiki references and update wiki page frontmatter.
    
    Returns:
        {"updated": int, "unchanged": int, "errors": list}
    """
    wiki_dir = vault / "wiki"
    if not wiki_dir.exists():
        return {"updated": 0, "unchanged": 0, "errors": ["wiki/ 目录不存在"]}
    
    # Build map: wiki page name (without .md) -> list of source files referencing it
    wiki_refs: dict[str, list[str]] = {}
    errors: list[str] = []
    
    # Scan external files
    scanned_files = 0
    for pattern in EXTERNAL_REF_SOURCES:
        for source_file in _resolve_glob(pattern):
            scanned_files += 1
            text = _safe_read_text(source_file)
            if not text:
                continue
            
            wikilinks = _extract_wikilinks(text)
            if not wikilinks:
                continue
            
            source_label = f"{source_file.name}"
            
            for link in wikilinks:
                # Normalize link: remove aliases [[page|alias]] -> page
                page_name = link.split("|")[0].strip()
                if not page_name:
                    continue
                
                if page_name not in wiki_refs:
                    wiki_refs[page_name] = []
                if source_label not in wiki_refs[page_name]:
                    wiki_refs[page_name].append(source_label)
    
    # Update wiki pages
    updated = 0
    unchanged = 0
    
    for wiki_page in wiki_dir.rglob("*.md"):
        if wiki_page.name == "_index.md":
            continue
        
        # Get page name (without .md)
        page_name = wiki_page.stem
        source_files = wiki_refs.get(page_name, [])
        
        if not source_files:
            # No external references found for this page
            # Check if it has referenced_by that should be cleared
            fm = parse_frontmatter(wiki_page)
            if "referenced_by" in fm:
                del fm["referenced_by"]
                text = _safe_read_text(wiki_page)
                m = re.match(r'^---\s*\n.*?\n---\s*\n', text, re.DOTALL)
                content = text[m.end():] if m else text
                write_frontmatter(wiki_page, fm, content)
                updated += 1
            continue
        
        if _update_referenced_by(wiki_page, vault, source_files):
            updated += 1
        else:
            unchanged += 1
    
    return {
        "updated": updated,
        "unchanged": unchanged,
        "scanned_files": scanned_files,
        "errors": errors,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        vault = Path(sys.argv[1])
    else:
        vault = Path("/Volumes/Binary HD/obsidian/Mautoer")
    
    result = sync_wiki_references(vault)
    print(f"同步完成：更新 {result['updated']} 个，未变更 {result['unchanged']} 个")
    print(f"扫描外部文件：{result['scanned_files']} 个")
    if result['errors']:
        print(f"错误：{result['errors']}")
