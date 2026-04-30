#!/usr/bin/env python3
"""
raw_index.py — 生成 raw/ 目录状态索引

按编译状态分类显示 raw 文件：
- 已完成：已编译且不需要再讨论
- 未编译待讨论：从未编译且未讨论
- 预约讨论：已预约讨论时间
- 需再次讨论：已讨论但需要再次讨论

同时生成 raw/_index.md 文件。

Usage:
    python3 raw_index.py <vault-path> [--json]
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import sys

def parse_frontmatter(path: Path) -> dict:
    """简单解析 frontmatter"""
    try:
        content = path.read_text(encoding='utf-8')
        if not content.startswith('---'):
            return {}
        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}
        fm_text = parts[1]
        fm = {}
        for line in fm_text.strip().split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                fm[key.strip()] = val.strip()
        return fm
    except Exception:
        return {}

def days_ago(date_str: str) -> int:
    """计算日期距离今天的天数"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - date).days
    except Exception:
        return -1

def classify_file(path: Path, fm: dict) -> dict:
    """根据 frontmatter 分类文件"""
    has_compiled = 'compiled_1st' in fm and fm['compiled_1st']
    never_compiled = fm.get('never_compiled', '').lower() == 'true'
    has_scheduled = 'scheduled' in fm and fm['scheduled']
    has_discussed_1st = 'discussed_1st' in fm and fm['discussed_1st']
    has_discussed_2nd = 'discussed_2nd' in fm and fm['discussed_2nd']
    
    if has_compiled:
        compiled_days = days_ago(fm['compiled_1st'])
        if compiled_days >= 7:
            status = "过期待清理"
        else:
            status = "已完成"
    elif has_scheduled:
        status = "预约讨论"
    elif never_compiled and not has_discussed_1st:
        status = "未编译待讨论"
    elif has_discussed_1st and not has_discussed_2nd:
        status = "需再次讨论"
    else:
        status = "待分类"
    
    return {
        "file": path.name,
        "status": status,
        "compiled_1st": fm.get('compiled_1st', ''),
        "never_compiled": never_compiled,
        "scheduled": fm.get('scheduled', ''),
        "discussed_1st": fm.get('discussed_1st', ''),
        "discussed_2nd": fm.get('discussed_2nd', ''),
        "confidence": fm.get('confidence', ''),
    }

def generate_index(vault: Path) -> dict:
    """生成 raw 目录索引"""
    raw_dir = vault / "raw"
    if not raw_dir.exists():
        return {"error": "raw/ 目录不存在"}
    
    result = {
        "generated": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "vault": str(vault),
        "status": {
            "已完成": [],
            "未编译待讨论": [],
            "预约讨论": [],
            "需再次讨论": [],
        }
    }
    
    for subdir in sorted(raw_dir.iterdir()):
        if subdir.is_dir():
            for path in sorted(subdir.glob("*.md")):
                fm = parse_frontmatter(path)
                info = classify_file(path, fm)
                info["path"] = str(path.relative_to(vault))
                status = info["status"]
                if status in result["status"]:
                    result["status"][status].append(info)
    
    # 合并"已编译"和"过期待清理"到"已完成"
    all_done = result["status"].get("已完成", []) + result["status"].get("过期待清理", [])
    result["status"]["已完成"] = all_done
    for k in ["已编译", "过期待清理"]:
        if k in result["status"]:
            del result["status"][k]
    
    return result

def print_and_save(data: dict):
    """打印文本格式报告并写入 raw/_index.md"""
    vault = Path(data['vault'])
    raw_index_path = vault / "raw" / "_index.md"
    
    status_labels = {
        "已完成": "✅ 已完成",
        "未编译待讨论": "⏳ 未编译待讨论",
        "预约讨论": "📅 预约讨论",
        "需再次讨论": "🔄 需再次讨论",
    }
    
    output = []
    output.append("---")
    output.append("title: Raw 目录索引")
    output.append(f"description: 按状态分类显示 raw 文件，生成时间：{data['generated']}")
    output.append("---")
    output.append("")
    output.append("# Raw 目录索引")
    output.append("")
    output.append(f"生成时间：{data['generated']}")
    output.append("")
    
    for status, files in data["status"].items():
        label = status_labels.get(status, status)
        output.append(f"## {label} ({len(files)} 个)")
        output.append("")
        for f in files:
            meta = []
            if f['compiled_1st']:
                meta.append(f"编译:{f['compiled_1st']}")
            if f['confidence']:
                meta.append(f"自信度:{f['confidence']}")
            if f['scheduled']:
                meta.append(f"预约:{f['scheduled']}")
            meta_str = f" ({', '.join(meta)})" if meta else ""
            output.append(f"- {f['file']}{meta_str}")
        output.append("")
    
    # 打印
    print('\n'.join(output))
    
    # 写入
    raw_index_path.write_text('\n'.join(output), encoding='utf-8')
    print(f"\n已写入: {raw_index_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="生成 raw 目录索引")
    parser.add_argument("vault", type=Path, help="Vault 路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()
    
    data = generate_index(args.vault)
    
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_and_save(data)

if __name__ == "__main__":
    main()
