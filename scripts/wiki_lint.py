#!/usr/bin/env python3
"""
wiki_lint.py — Lint scanner for wiki/ directory.

Checks:
  1. Schema pending (SCHEMA.md still has 🟡 待填充 marker)
  2. Orphan pages (no incoming wikilinks)
  3. Broken links (wikilink target doesn't exist)
  4. Empty pages (< 50 chars of content)
  5. Stale content (updated/created > 90 days ago)
  6. Missing _index.md in wiki/ subdirectories
  7. Missing cross-references (mentioned concept without [[wikilink]])
  8. Deferred expired (#待学习 pages > 30 days old)

Auto-fix rules (from OBheartbeat.json):
  - missing_index → auto-generate _index.md
  - orphan_count > 3 → agent_review
  - broken_link_count > 5 → agent_review
  - empty_count > 2 → agent_review
  - stale_count > 0 → human_confirm (no auto-fix)
  - schema_pending_count > 0 → agent_review (must discuss with user)
"""
from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from vault_utils import (
    parse_frontmatter,
    get_markdown_files,
    extract_wikilinks,
    strip_markdown,
    days_since,
    parse_date,
    relative_to_vault,
)


# ---------------------------------------------------------------------------
# Lint runner
# ---------------------------------------------------------------------------

def run_lint(vault: Path) -> dict[str, Any]:
    """Run all lint checks and return a structured report."""
    wiki_dir = vault / "wiki"
    if not wiki_dir.exists():
        return {
            "total_issues": 0,
            "orphan_count": 0,
            "broken_link_count": 0,
            "empty_count": 0,
            "stale_count": 0,
            "missing_index_count": 0,
            "missing_ref_count": 0,
            "deferred_expired_count": 0,
            "schema_pending_count": 0,
            "issues": [],
            "auto_fixed": [],
            "agent_review": [],
            "message": "wiki/ 目录不存在，跳过 lint 检查",
        }

    all_md = get_markdown_files(wiki_dir)
    if not all_md:
        return {
            "total_issues": 0,
            "orphan_count": 0,
            "broken_link_count": 0,
            "empty_count": 0,
            "stale_count": 0,
            "missing_index_count": 0,
            "missing_ref_count": 0,
            "deferred_expired_count": 0,
            "schema_pending_count": 0,
            "issues": [],
            "auto_fixed": [],
            "agent_review": [],
            "message": "wiki/ 下无 Markdown 文件",
        }

    # Build page title index for missing cross-reference detection
    page_titles: dict[str, tuple[str, str]] = {}  # lower_title -> (title, rel_path)
    for path in all_md:
        if path.name == "_index.md":
            continue
        rel = relative_to_vault(path, vault)
        title = path.stem
        page_titles[title.lower()] = (title, rel)

    # ★ NEW: Check SCHEMA.md pending status
    schema_pending_issues: list[dict[str, Any]] = []
    schema_path = vault / "SCHEMA.md"
    if schema_path.exists():
        schema_content = schema_path.read_text(encoding="utf-8")
        if "🟡 待填充" in schema_content:
            schema_pending_issues.append({
                "type": "schema_pending",
                "path": "SCHEMA.md",
                "note": "SCHEMA.md 仍带 🟡 待填充 标记，Agent 必须完成与用户的 schema 讨论",
            })

    # Collect all wikilink targets (for orphan detection)
    all_targets: set[str] = set()
    link_sources: dict[str, list[str]] = {}  # target_rel -> [source_rel, ...]
    broken_links: list[dict[str, Any]] = []
    empty_pages: list[dict[str, Any]] = []
    stale_pages: list[dict[str, Any]] = []
    # Track plain text per page for cross-reference detection
    page_plain_texts: dict[str, str] = {}  # rel_path -> plain_text
    page_wikilinks: dict[str, list[str]] = {}  # rel_path -> [target, ...]

    for path in all_md:
        rel = relative_to_vault(path, vault)
        content = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(path)

        # 1. Collect wikilinks for orphan / broken detection
        links = extract_wikilinks(content)
        page_wikilinks[rel] = links
        for target in links:
            # Resolve target to a relative path under wiki/
            target_path = _resolve_wikilink(target, wiki_dir)
            target_rel = relative_to_vault(target_path, vault) if target_path else f"wiki/{target}.md"
            all_targets.add(target_rel)
            link_sources.setdefault(target_rel, []).append(rel)

            # Broken link check
            if target_path is None or not target_path.exists():
                # Skip if source has #待学习 / #待搜索 / #TODO tags in frontmatter
                tags = fm.get("tags", [])
                if not _has_deferred_tag(tags):
                    broken_links.append({
                        "type": "broken_link",
                        "source": rel,
                        "target": target_rel,
                        "target_name": target,
                    })

        # Store plain text for cross-reference detection (skip _index.md)
        if path.name != "_index.md":
            plain = strip_markdown(content)
            page_plain_texts[rel] = plain

            # 3. Empty page check
            # Skip pages with deferred tags (intentionally empty placeholders)
            # and pages without frontmatter (junk empty pages)
            has_frontmatter = content.strip().startswith("---")
            has_deferred = _has_deferred_tag(fm.get("tags", []))
            if len(plain) < 50 and has_frontmatter and not has_deferred:
                empty_pages.append({
                    "type": "empty_page",
                    "path": rel,
                    "char_count": len(plain),
                })

        # 4. Stale content check
        updated = parse_date(fm.get("updated"))
        created = parse_date(fm.get("created"))
        check_date = updated or created
        if check_date:
            ds = days_since(check_date)
            if ds is not None and ds > 90:
                stale_pages.append({
                    "type": "stale_content",
                    "path": rel,
                    "last_updated": check_date,
                    "days_since": ds,
                })

    # 1. Orphan pages (no incoming wikilinks, skip _index.md)
    orphan_pages: list[dict[str, Any]] = []
    for path in all_md:
        rel = relative_to_vault(path, vault)
        if path.name == "_index.md":
            continue
        if rel not in link_sources:
            orphan_pages.append({
                "type": "orphan_page",
                "path": rel,
            })

    # 5. Missing _index.md in subdirectories
    missing_index: list[dict[str, Any]] = []
    auto_fixed: list[dict[str, Any]] = []
    for subdir in wiki_dir.iterdir():
        if subdir.is_dir():
            index_file = subdir / "_index.md"
            if not index_file.exists():
                # Auto-generate
                rel = relative_to_vault(index_file, vault)
                missing_index.append({
                    "type": "missing_index",
                    "path": rel,
                })
                try:
                    _generate_index_md(subdir, vault)
                    auto_fixed.append({
                        "type": "missing_index",
                        "path": rel,
                    })
                except Exception:
                    pass

    # 6. Missing cross-references
    missing_refs = _check_missing_cross_references(
        page_titles, page_plain_texts, page_wikilinks, vault
    )

    # 7. Deferred pages that have exceeded 30 days
    deferred_expired = _check_deferred_expired(all_md, vault)

    # ★ NEW: Check missing source frontmatter in wiki pages
    missing_source_issues = _check_missing_source(all_md, vault)

    # Check raw/ confidence for compile readiness
    ready_to_compile, need_discussion = _check_raw_confidence(vault)

    # Aggregate
    issues = orphan_pages + broken_links + empty_pages + stale_pages + missing_index + missing_refs + deferred_expired + schema_pending_issues + missing_source_issues
    orphan_count = len(orphan_pages)
    broken_link_count = len(broken_links)
    empty_count = len(empty_pages)
    stale_count = len(stale_pages)
    missing_index_count = len(missing_index)
    missing_ref_count = len(missing_refs)
    deferred_expired_count = len(deferred_expired)
    schema_pending_count = len(schema_pending_issues)
    missing_source_count = len(missing_source_issues)
    ready_count = len(ready_to_compile)
    low_confidence_count = len(need_discussion)

    # Auto-fix rules from OBheartbeat.json
    agent_review: list[dict[str, Any]] = []
    if ready_count > 0:
        agent_review.append({
            "type": "ready_to_compile",
            "count": ready_count,
            "note": "confidence ≥80 且未编译，建议编译到 wiki",
        })
    if low_confidence_count > 0:
        agent_review.append({
            "type": "low_confidence_review",
            "count": low_confidence_count,
            "note": "confidence <80，需要讨论验证",
        })
    if schema_pending_count > 0:
        agent_review.append({
            "type": "schema_pending_review",
            "count": schema_pending_count,
            "note": "SCHEMA.md 未完成讨论，Agent 必须与用户讨论 5 个问题并填充",
        })
    if orphan_count > 3:
        agent_review.append({
            "type": "orphan_review",
            "count": orphan_count,
            "note": "Agent 排查孤儿页原因",
        })
    if broken_link_count > 5:
        agent_review.append({
            "type": "broken_link_review",
            "count": broken_link_count,
            "note": "Agent 排查悬空链接",
        })
    if empty_count > 2:
        agent_review.append({
            "type": "empty_review",
            "count": empty_count,
            "note": "Agent 确认是否删除空页面",
        })
    if stale_count > 0:
        agent_review.append({
            "type": "stale_confirm",
            "count": stale_count,
            "note": "过时内容必须人工确认，不可自动删除",
        })
    if missing_ref_count > 0:
        agent_review.append({
            "type": "missing_ref_review",
            "count": missing_ref_count,
            "note": "Agent 确认是否添加交叉引用",
        })
    if deferred_expired_count > 0:
        agent_review.append({
            "type": "deferred_expired_review",
            "count": deferred_expired_count,
            "note": "Agent 补充内容或改为 #永久空缺",
        })
    if missing_source_count > 0:
        agent_review.append({
            "type": "missing_source_review",
            "count": missing_source_count,
            "note": "wiki 页面必须添加 source frontmatter 指向 raw 来源",
        })

    return {
        "total_issues": len(issues),
        "orphan_count": orphan_count,
        "broken_link_count": broken_link_count,
        "empty_count": empty_count,
        "stale_count": stale_count,
        "missing_index_count": missing_index_count,
        "missing_ref_count": missing_ref_count,
        "deferred_expired_count": deferred_expired_count,
        "ready_count": ready_count,
        "low_confidence_count": low_confidence_count,
        "schema_pending_count": schema_pending_count,
        "missing_source_count": missing_source_count,
        "ready_to_compile": ready_to_compile,
        "need_discussion": need_discussion,
        "issues": issues,
        "auto_fixed": auto_fixed,
        "agent_review": agent_review,
        "message": (
            f"Wiki 检查完成：{orphan_count} 个孤儿页，{broken_link_count} 个悬空链接，"
            f"{empty_count} 个空页面，{stale_count} 个过时内容，"
            f"{missing_index_count} 个缺失索引，{missing_ref_count} 个缺失交叉引用，"
            f"{deferred_expired_count} 个待学习已过期，"
            f"{schema_pending_count} 个 SCHEMA.md 待填充，"
            f"{ready_count} 个待编译（confidence ≥80），"
            f"{low_confidence_count} 个需讨论（confidence <80），"
            f"{missing_source_count} 个缺失 source，"

        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_wikilink(target: str, wiki_dir: Path) -> Path | None:
    """Resolve a wikilink target to an actual file path under wiki/."""
    # Try exact path first
    candidate = wiki_dir / f"{target}.md"
    if candidate.exists():
        return candidate

    # Try without .md extension (target might already include it)
    if target.endswith(".md"):
        candidate = wiki_dir / target
        if candidate.exists():
            return candidate

    # Try walking all subdirectories
    for subdir in wiki_dir.rglob("*.md"):
        if subdir.stem == target or subdir.name == f"{target}.md":
            return subdir

    return None


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


def _generate_index_md(subdir: Path, vault: Path) -> None:
    """Auto-generate _index.md for a wiki/ subdirectory with summaries."""
    index_file = subdir / "_index.md"
    folder_name = subdir.name
    
    lines = [f"# {folder_name} 目录索引", ""]
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
    lines.append("*自动生成于 " + datetime.now(timezone.utc).strftime("%Y-%m-%d") + "*")
    
    index_file.write_text("\n".join(lines), encoding="utf-8")


def _check_missing_cross_references(
    page_titles: dict[str, tuple[str, str]],
    page_plain_texts: dict[str, str],
    page_wikilinks: dict[str, list[str]],
    vault: Path,
) -> list[dict[str, Any]]:
    """Find pages that mention a concept but don't link to it.

    Strategy:
      1. For each page, get its plain text (markdown stripped).
      2. For each OTHER page title, search for the title in the plain text.
      3. If found but not already wikilinked → report missing cross-reference.
      4. Use word-boundary matching to reduce false positives.
    """
    missing: list[dict[str, Any]] = []
    reported: set[tuple[str, str]] = set()  # (source_rel, target_lower)

    for source_rel, plain in page_plain_texts.items():
        # Skip deferred pages
        source_path = vault / source_rel
        fm = parse_frontmatter(source_path)
        tags = fm.get("tags", [])
        if _has_deferred_tag(tags):
            continue

        # Get existing wikilinks for this page
        existing_links = {t.lower() for t in page_wikilinks.get(source_rel, [])}

        for lower_title, (title, target_rel) in page_titles.items():
            # Skip self-reference
            if target_rel == source_rel:
                continue
            # Skip if already linked
            if lower_title in existing_links:
                continue
            # Skip if already reported for this source
            if (source_rel, lower_title) in reported:
                continue
            # Skip very short titles (likely false positive)
            if len(title) < 2:
                continue

            # Search for title in plain text with word boundaries
            # Use regex: title surrounded by non-word chars or string boundaries
            pattern = r'(?<![\w\u4e00-\u9fff])' + re.escape(title) + r'(?![\w\u4e00-\u9fff])'
            if re.search(pattern, plain):
                missing.append({
                    "type": "missing_cross_reference",
                    "source": source_rel,
                    "target": target_rel,
                    "target_name": title,
                })
                reported.add((source_rel, lower_title))

    return missing


def _check_deferred_expired(all_md: list[Path], vault: Path) -> list[dict[str, Any]]:
    """Find pages with deferred tags (#待学习 etc.) that have exceeded 30 days.

    Rules:
      - Page has #待学习 / #待搜索 / #TODO tag
      - Page does NOT have #永久空缺 tag
      - updated/created date is > 30 days ago
      → Report as deferred_expired
    """
    expired: list[dict[str, Any]] = []
    for path in all_md:
        if path.name == "_index.md":
            continue
        fm = parse_frontmatter(path)
        tags = fm.get("tags", [])

        # Skip if not deferred
        if not _has_deferred_tag(tags):
            continue
        # Skip if permanently exempted
        if _has_permanent_exemption(tags):
            continue

        # Check date
        updated = parse_date(fm.get("updated"))
        created = parse_date(fm.get("created"))
        check_date = updated or created
        if not check_date:
            # No date available - use file mtime as fallback
            try:
                mtime = path.stat().st_mtime
                from datetime import datetime
                check_date = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
            except Exception:
                continue

        ds = days_since(check_date)
        if ds is not None and ds > 30:
            rel = relative_to_vault(path, vault)
            expired.append({
                "type": "deferred_expired",
                "path": rel,
                "tag": next((t for t in tags if str(t).strip() in {"#待学习", "#待搜索", "#TODO", "待学习", "待搜索"}), "#待学习"),
                "days_since": ds,
                "note": "30 天前标记为待学习，请补充内容或改为 #永久空缺",
            })

    return expired

def _check_raw_confidence(vault: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Check raw/ files for confidence levels.
    
    Returns:
        (ready_to_compile, need_discussion) - two lists of file dicts
    """
    raw_dir = vault / "raw"
    ready_to_compile: list[dict[str, Any]] = []
    need_discussion: list[dict[str, Any]] = []
    
    if not raw_dir.exists():
        return ready_to_compile, need_discussion
    
    for path in get_markdown_files(raw_dir):
        fm = parse_frontmatter(path)
        conf = fm.get("confidence")
        never_compiled = fm.get("never_compiled", True)
        
        # Only process never_compiled files for compile check
        if never_compiled and conf is not None:
            conf_int = int(conf) if str(conf).isdigit() else 0
            rel = relative_to_vault(path, vault)
            entry = {"path": rel, "confidence": conf_int}
            
            if conf_int >= 80:
                ready_to_compile.append(entry)
            else:
                entry["discussed_1st"] = fm.get("discussed_1st", "")
                need_discussion.append(entry)
    
    return ready_to_compile, need_discussion


def _check_missing_source(all_md: list[Path], vault: Path) -> list[dict[str, Any]]:
    """Check wiki pages that are missing source frontmatter.

    wiki/ 页面应该有 source 字段指向 raw 来源。
    如果缺失，报告为 missing_source。
    """
    missing: list[dict[str, Any]] = []
    for path in all_md:
        if path.name == "_index.md":
            continue
        fm = parse_frontmatter(path)
        source = fm.get("source")
        if not source:
            rel = relative_to_vault(path, vault)
            missing.append({
                "type": "missing_source",
                "path": rel,
                "note": "wiki 页面缺少 source frontmatter，必须指向 raw 来源",
            })
    return missing

