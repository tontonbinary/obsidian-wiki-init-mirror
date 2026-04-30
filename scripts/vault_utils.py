#!/usr/bin/env python3
"""
vault_utils.py - General utilities for Obsidian Wiki Vault scanning.

Provides:
  - Frontmatter parsing (with python-frontmatter or yaml fallback)
  - Wikilink extraction
  - Markdown file discovery
  - Date helpers
  - Markdown stripping
"""
from __future__ import annotations

import re
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a Markdown file.

    Tries python-frontmatter first, falls back to a simple regex + yaml
    implementation so the script works even when the optional dependency is
    missing.
    """
    try:
        import frontmatter  # type: ignore
        post = frontmatter.load(str(path))
        # frontmatter returns ordered dicts – cast to plain dict
        return dict(post.metadata) if post.metadata else {}
    except Exception:
        return _parse_frontmatter_fallback(path)


def _parse_frontmatter_fallback(path: Path) -> dict[str, Any]:
    """Fallback frontmatter parser using regex + yaml.safe_load."""
    text = _safe_read_text(path)
    if not text:
        return {}

    # Obsidian / Jekyll style frontmatter: ---\n...\n---
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}

    yaml_text = m.group(1)
    try:
        import yaml
        data = yaml.safe_load(yaml_text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_frontmatter(path: Path, metadata: dict[str, Any], content: str) -> None:
    """Write YAML frontmatter and content back to a Markdown file."""
    import yaml
    
    # Build frontmatter string
    fm_lines = ["---"]
    fm_lines.append(yaml.dump(metadata, allow_unicode=True, default_flow_style=False, sort_keys=False).strip())
    fm_lines.append("---")
    
    frontmatter_text = "\n".join(fm_lines)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter_text)
        f.write("\n")
        f.write(content)


def update_indexed_by(path: Path, scanner_name: str, purpose: str) -> bool:
    """
    Add indexed_by entry to a wiki page's frontmatter if not already present.
    
    Args:
        path: Path to the .md file
        scanner_name: Name of the scanner (e.g., "obheartbeat")
        purpose: Purpose string (e.g., "定期维护扫描")
    
    Returns:
        True if updated, False if already present or error
    """
    try:
        text = _safe_read_text(path)
        fm = parse_frontmatter(path)
        
        entry = f"{scanner_name}（{purpose}）"
        
        # Initialize indexed_by if not present
        if "indexed_by" not in fm:
            fm["indexed_by"] = []
        
        # Check if entry already exists
        if entry in fm["indexed_by"]:
            return False
        
        fm["indexed_by"].append(entry)
        
        # Reconstruct content (after frontmatter)
        content = text
        m = re.match(r'^---\s*\n.*?\n---\s*\n', text, re.DOTALL)
        if m:
            content = text[m.end():]
        
        write_frontmatter(path, fm, content)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Wikilink extraction
# ---------------------------------------------------------------------------

_WIKILINK_RE = re.compile(r'\[\[([^\]]+)\]\]')
_WIKILINK_RE_ALIASES = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')


def extract_wikilinks(content: str) -> list[str]:
    """Extract all [[wikilink]] targets from markdown content.

    Handles aliases: [[Target|Display]] → returns 'Target'.
    """
    links: list[str] = []
    for match in _WIKILINK_RE_ALIASES.finditer(content):
        target = match.group(1).strip()
        # Strip anchor (#heading)
        if '#' in target:
            target = target.split('#')[0]
        # Strip block reference (^blockid)
        if '^' in target:
            target = target.split('^')[0]
        if target:
            links.append(target)
    return links


# ---------------------------------------------------------------------------
# Markdown file discovery
# ---------------------------------------------------------------------------

def get_markdown_files(directory: Path, recursive: bool = True) -> list[Path]:
    """Return all .md files under *directory*, skipping hidden files and .DS_Store."""
    if not directory.exists():
        return []

    pattern = "**/*.md" if recursive else "*.md"
    files = [
        p for p in directory.glob(pattern)
        if p.is_file()
        and not p.name.startswith('.')
        and p.name != '.DS_Store'
        and not _is_gitignored(p)
    ]
    return sorted(files)


def _is_gitignored(path: Path) -> bool:
    """Naive gitignore check – walks up to find .gitignore and matches patterns."""
    gitignore = _find_gitignore(path)
    if not gitignore:
        return False

    try:
        patterns = [
            line.strip()
            for line in gitignore.read_text(encoding='utf-8').splitlines()
            if line.strip() and not line.strip().startswith('#')
        ]
    except Exception:
        return False

    rel = path.relative_to(gitignore.parent)
    rel_str = str(rel).replace(os.sep, '/')
    for pat in patterns:
        # Very naive matching – covers most common cases
        if pat.endswith('/'):
            # Directory ignore
            dir_pat = pat.rstrip('/')
            if dir_pat in rel_str.split('/'):
                return True
        elif '*' in pat:
            # Glob pattern – extremely simplified
            if _simple_glob_match(rel_str, pat):
                return True
        else:
            if pat == rel_str or rel_str.endswith('/' + pat):
                return True
    return False


def _find_gitignore(path: Path) -> Path | None:
    """Find the nearest .gitignore walking upward from *path*."""
    current = path if path.is_dir() else path.parent
    while current != current.parent:
        gi = current / '.gitignore'
        if gi.exists():
            return gi
        current = current.parent
    return None


def _simple_glob_match(text: str, pattern: str) -> bool:
    """Very simplified glob matching for gitignore-style patterns."""
    # Convert glob to regex-ish
    regex = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
    regex = f'^{regex}$'
    try:
        return bool(re.search(regex, text))
    except re.error:
        return False


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def days_since(date_str: str | None) -> int | None:
    """Return the number of days between *date_str* (YYYY-MM-DD) and today."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(str(date_str).strip(), '%Y-%m-%d').replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except (ValueError, TypeError):
        return None


def parse_date(date_val: Any) -> str | None:
    """Normalise a frontmatter date value to YYYY-MM-DD string."""
    if not date_val:
        return None
    # Handle datetime.datetime (includes datetime.date via inheritance check)
    if hasattr(date_val, 'strftime'):
        return date_val.strftime('%Y-%m-%d')
    if isinstance(date_val, str):
        s = date_val.strip()
        # Take only the date part if it includes time
        if 'T' in s:
            s = s.split('T')[0]
        if ' ' in s:
            s = s.split(' ')[0]
        return s if len(s) == 10 and s[4] == '-' and s[7] == '-' else None
    return None


# ---------------------------------------------------------------------------
# Markdown stripping
# ---------------------------------------------------------------------------

def strip_markdown(content: str) -> str:
    """Remove markdown syntax, leaving plain text."""
    text = content

    # Remove frontmatter
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '\n', text, flags=re.DOTALL)

    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', ' ', text)
    text = re.sub(r'`[^`]+`', ' ', text)

    # Remove links – keep link text
    text = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1', text)   # images
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)    # normal links
    text = re.sub(r'\[([^\]]+)\]\[[^\]]*\]', r'\1', text)   # ref links

    # Remove wikilinks – keep target name
    text = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', text)

    # Remove headings markers
    text = re.sub(r'^#{1,6}\s+', ' ', text, flags=re.MULTILINE)

    # Remove emphasis
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    text = re.sub(r'~~([^~]+)~~', r'\1', text)

    # Remove blockquotes
    text = re.sub(r'^>\s?', ' ', text, flags=re.MULTILINE)

    # Remove list markers
    text = re.sub(r'^[\s]*[-*+]\s+', ' ', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', ' ', text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r'^[\s]*[-=*_]{3,}[\s]*$', ' ', text, flags=re.MULTILINE)

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def _safe_read_text(path: Path) -> str:
    """Safely read text from a file, returning empty string on any error."""
    try:
        return path.read_text(encoding='utf-8')
    except Exception:
        return ''


def relative_to_vault(path: Path, vault: Path) -> str:
    """Return *path* relative to *vault* as a POSIX-style string."""
    try:
        return str(path.relative_to(vault)).replace(os.sep, '/')
    except ValueError:
        return str(path).replace(os.sep, '/')
