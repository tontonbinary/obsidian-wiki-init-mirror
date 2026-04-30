#!/usr/bin/env python3
"""
compile.py — Compile raw/ files to wiki/ pages.

Usage:
    python3 compile.py <vault-path> <raw-file-path> [options]

This script helps Agent compile raw files to wiki. It:
1. Reads the raw file and extracts key concepts
2. Suggests wiki pages to create/update
3. Generates frontmatter-compatible markdown

Note: Actual content generation requires LLM reasoning,
so this script prepares the structure and leaves content
for Agent to fill or use with LLM.
"""
from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from vault_utils import parse_frontmatter, relative_to_vault, strip_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile raw file to wiki")
    parser.add_argument("vault", type=Path, help="Path to vault")
    parser.add_argument("raw_file", type=Path, help="Path to raw file (relative to vault)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    parser.add_argument("--output-dir", type=str, default=None, help="Target wiki subdirectory")
    args = parser.parse_args()

    vault: Path = args.vault
    raw_path = vault / args.raw_file if not args.raw_file.is_absolute() else args.raw_file
    
    if not raw_path.exists():
        print(f"Error: Raw file not found: {raw_path}")
        return 1

    # Read raw file
    content = raw_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(raw_path)
    
    # ★ FIX: Source must point to ORIGINAL source, not raw file
    raw_source = fm.get("source", "")
    if raw_source and raw_source != str(args.raw_file):
        # raw file has an original source (e.g., memory/MEMORY.md)
        wiki_source = raw_source
    else:
        # raw file IS the original source (no parent source)
        wiki_source = str(args.raw_file)
    
    # Extract concepts (simple heuristic)
    plain = strip_markdown(content)
    words = plain.split()
    
    # Find potential wiki page titles (capitalized phrases or quoted terms)
    import re
    candidates = set()
    
    # Chinese terms: 2-10 char phrases that appear multiple times
    for i in range(len(words)):
        for length in range(2, min(6, len(words) - i + 1)):
            phrase = "".join(words[i:i+length])
            if len(phrase) >= 4 and plain.count(phrase) >= 2:
                candidates.add(phrase[:30])
    
    # English capitalized terms
    for match in re.finditer(r'\b[A-Z][a-zA-Z]{2,}\b', content):
        candidates.add(match.group())
    
    # Generate compile plan
    plan = {
        "source": wiki_source,  # Points to original source, NOT raw file
        "raw_source": str(args.raw_file),  # Raw file used as intermediate
        "source_type": fm.get("type", "unknown"),
        "suggested_category": _suggest_category(fm, args.output_dir),
        "key_concepts": sorted(list(candidates))[:10],
        "frontmatter": {
            "type": "concept",
            "created": _today(),
            "updated": _today(),
            # ★ wiki source points to ORIGINAL source (e.g., memory/MEMORY.md)
            # NOT the raw file path (which is just intermediate processing)
            "source": wiki_source,
            "raw_source": str(args.raw_file),  # For traceability
        },
        "actions": [
            "1. Review key_concepts and decide which need wiki pages",
            "2. Create/update wiki pages in suggested_category",
            "3. Add wikilinks between related pages",
            "4. Update raw file frontmatter: compiled_1st or compiled_2nd",
        ],
    }
    
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        # Save plan for Agent review
        plan_file = vault / ".compile-plan.json"
        plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Compile plan saved to: {plan_file}")
        print("\nAgent should:")
        print("1. Review the plan")
        print("2. Create/update wiki pages")
        print("3. Update raw file frontmatter")
    
    return 0


def _suggest_category(fm: dict[str, Any], override: str | None) -> str:
    """Suggest wiki/ subdirectory based on raw file metadata.
    
    NOTE: This is just a suggestion. Agent must make final decision
    based on SCHEMA.md classification rules.
    """
    if override:
        return override
    
    type_map = {
        "article": "知识概念",
        "document": "知识概念", 
        "transcript": "环境与社会关系",
        "environment": "环境与社会关系",
        "diary": "方法论",
    }
    return type_map.get(fm.get("type", ""), "知识概念")


def _today() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


if __name__ == "__main__":
    sys.exit(main())
