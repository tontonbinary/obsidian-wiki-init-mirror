#!/usr/bin/env python3
"""
index_generator.py — Auto-generate _index.md for wiki/ subdirectories.

Scans wiki/ subdirectories; if _index.md is missing, creates one with
rich content including descriptions and status markers.
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from vault_utils import get_markdown_files, relative_to_vault, parse_frontmatter, strip_markdown


def generate_missing_indexes(vault: Path) -> list[dict[str, str]]:
    """Scan wiki/ subdirectories and auto-generate missing _index.md files.

    Returns a list of {path, action} dicts for each generated index.
    """
    wiki_dir = vault / "wiki"
    if not wiki_dir.exists():
        return []

    results: list[dict[str, str]] = []
    for subdir in wiki_dir.iterdir():
        if not subdir.is_dir():
            continue
        index_file = subdir / "_index.md"
        if index_file.exists():
            continue

        try:
            _generate_index(subdir, vault)
            results.append({
                "path": relative_to_vault(index_file, vault),
                "action": "created",
            })
        except Exception as e:
            print(f"Error generating index for {subdir}: {e}", file=sys.stderr)

    return results


def _has_deferred_tag(tags: list[str] | None) -> bool:
    """Check if frontmatter tags contain deferred learning markers."""
    if not tags:
        return False
    deferred = {"#待学习", "#待搜索", "#TODO", "待学习", "待搜索"}
    return any(str(t).strip() in deferred for t in tags)


def _has_permanent_exemption(tags: list[str] | None) -> bool:
    """Check if page is permanently exempted from deferred reminders."""
    if not tags:
        return False
    exempt = {"#永久空缺", "永久空缺"}
    return any(str(t).strip() in exempt for t in tags)


def _generate_index(subdir: Path, vault: Path) -> None:
    """Generate rich _index.md content for a wiki/ subdirectory."""
    index_file = subdir / "_index.md"
    folder_name = subdir.name

    lines = [f"# {folder_name} 索引", ""]
    lines.append(f"## 概述")
    lines.append(f"本目录包含 **{folder_name}** 相关的知识页面。")
    lines.append("")

    # Collect pages with metadata
    pages: list[tuple[str, str, str, list[str]]] = []  # (name, first_line, status, tags)
    for md in sorted(subdir.glob("*.md")):
        if md.name == "_index.md":
            continue
        name = md.stem
        content = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(md)

        # Extract first non-empty line as description
        desc = ""
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("---"):
                desc = line[:80]
                break

        # Check status
        tags = fm.get("tags", [])
        status = ""
        if _has_deferred_tag(tags):
            status = "⏳ 待学习"
        elif _has_permanent_exemption(tags):
            status = "✅ 永久空缺"
        elif len(strip_markdown(content)) < 50:
            status = "⚠️ 空页面"

        pages.append((name, desc, status, tags))

    if not pages:
        lines.append("*暂无页面*")
    else:
        # Group by status
        normal_pages = [p for p in pages if not p[2]]
        status_pages = [p for p in pages if p[2]]

        if normal_pages:
            lines.append("## 页面列表")
            lines.append("")
            for name, desc, status, tags in normal_pages:
                if desc:
                    lines.append(f"- [[{name}]] — {desc}")
                else:
                    lines.append(f"- [[{name}]]")
            lines.append("")

        if status_pages:
            lines.append("## 状态标记")
            lines.append("")
            for name, desc, status, tags in status_pages:
                lines.append(f"- [[{name}]] — {status}")
            lines.append("")

    lines.append("---")
    lines.append(f"*自动生成于 {datetime.now(timezone.utc).strftime('%Y-%m-%d')}*")

    index_file.write_text("\n".join(lines), encoding="utf-8")
