#!/usr/bin/env python3
"""
obsidian-wiki-init: Create a new Obsidian vault with LLM Wiki-inspired structure

Usage: python3 init_vault.py <vault-name> <vault-path>
Example: python3 init_vault.py Matuoer "/Volumes/Binary HD/obsidian/Matuoer"

⚠️ IMPORTANT: Before running, Agent MUST discuss SCHEMA.md with user.
See schema-discussion-guide.md for the discussion flow.
"""
import os
import sys
import json
from datetime import datetime

# Import activate for auto-registration
try:
    from activate import activate
except ImportError:
    # Fallback: try importing from same directory
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from activate import activate
    except ImportError:
        activate = None


LINT_STATE_DEFAULT = {"issues": [], "version": "1.0"}


def init_lint_state(vault_path: str) -> None:
    """Create the initial .lint-state.json in the vault root."""
    state_path = os.path.join(vault_path, ".lint-state.json")
    if not os.path.exists(state_path):
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(LINT_STATE_DEFAULT, f, indent=2, ensure_ascii=False)


def create_vault(vault_name: str, vault_path: str) -> dict:
    """Create a new Obsidian vault with LLM Wiki standard structure (Chinese categories)."""
    
    vault_path = os.path.expanduser(vault_path)
    vault_path = os.path.expandvars(vault_path)
    
    result = {
        "success": False,
        "vault_name": vault_name,
        "vault_path": vault_path,
        "created_dirs": [],
        "created_files": [],
        "errors": []
    }
    
    try:
        # Create main directories (Chinese naming per SKILL.md)
        dirs = [
            vault_path,
            os.path.join(vault_path, "raw"),
            os.path.join(vault_path, "raw", "文章"),
            os.path.join(vault_path, "raw", "文档"),
            os.path.join(vault_path, "raw", "对话"),
            os.path.join(vault_path, "raw", "环境认知"),
            os.path.join(vault_path, "raw", "日记"),
            os.path.join(vault_path, "wiki"),
            os.path.join(vault_path, "wiki", "项目"),
            os.path.join(vault_path, "wiki", "工具"),
            os.path.join(vault_path, "wiki", "实体信息"),
            os.path.join(vault_path, "wiki", "知识概念"),
            os.path.join(vault_path, "wiki", "方法论"),
            os.path.join(vault_path, "wiki", "规则纪律"),
            os.path.join(vault_path, "wiki", "参考与对比"),
            os.path.join(vault_path, "wiki", "环境与社会关系"),
            os.path.join(vault_path, "outputs"),
        ]
        
        for d in dirs:
            os.makedirs(d, exist_ok=True)
            result["created_dirs"].append(d)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # SCHEMA.md — Compile rules contract (REQUIRED)
        schema_path = os.path.join(vault_path, "SCHEMA.md")
        with open(schema_path, "w", encoding="utf-8") as f:
            f.write(f"""# SCHEMA.md — Wiki 编译规则

> ⚠️ 本文件由 Agent 与用户讨论后生成，是 Wiki 的"宪法"
> 生成时间：{today}
> 状态：🟡 讨论中 — 边讨论边填入，每项确认后立即更新，完成后改为 ✅

---

## 1. Vault 定位

- **使用者**：_____（Agent 名 / 项目名）
- **定位**：_____
- **知识边界**：
  - ✅ 记录：_____
  - ❌ 不记录：_____

## 2. raw/ 分类约定

| 文件夹 | 用途 | 示例 |
|--------|------|------|
| 文章/ | 公众号、博客、RSS | 来源-标题摘要.md |
| 文档/ | PDF、手册、飞书文档 | 文档类型-标题摘要.md |
| 对话/ | 邮件、会议、IM 记录 | 对话对象-主题.md |
| 环境认知/ | 工具配置、团队关系 | 类型-内容摘要.md |
| 日记/ | 工作日志、踩坑记录、MEMORY.md 迁移 | YYYY-MM-DD-类型.md |
| 代码/ | 代码片段、CLI 命令 | （可选） |

## 3. 来源处理规则

> ⚠️ 核心原则：所有内容必须经过 raw 再编译到 wiki，禁止跳过 raw 直接按记忆写入

### 自信度评估

| 自信度 | 处理方式 |
|--------|---------|
| ≥80% | 直接记录/编译到 wiki |
| <80% | 需要找到原文验证后再编译 |

### 各来源类型处理

**文章 / 文档：**

| 情况 | 处理 |
|------|------|
| 记录时已同步讨论 | 存链接 + 直接编译到 wiki |
| 预定讨论时间 | 存链接 + 标记 scheduled + Heartbeat 提醒 |
| 未讨论（或讨论到一半） | 存链接 + Heartbeat 定期检索，提醒 |
| 搁置/无响应 | Agent 自主读取→编译 |
| 中间态文档 | 存链接/路径 + 摘要 + 时间戳 |

**对话：**

| 情况 | 处理 |
|------|------|
| 用户主动暂存 | 记录/编译 |
| 暂存 + 预定讨论时间 | frontmatter + scheduled + Heartbeat 提醒 |

**环境认知：**

| 情况 | 处理 |
|------|------|
| 用户确认 或 自信度≥80% | 直接记录/编译 |
| 自信度<80% | 参考文章处理 |

**日记：**

| 情况 | 处理 |
|------|------|
| 用户确认 或 自信度≥80% | 直接记录/编译 |
| 自信度<80% | 需要讨论验证 |
| MEMORY.md 内容迁移 | 一律先到 raw/，经过来源处理才能进 wiki |

**MEMORY.md 体积维护：**
- 当 MEMORY.md 超过 350 行时，建议迁移到 wiki/
- 稳定知识（定义/规则纪律/术语）→ wiki/知识概念/ 或 wiki/规则纪律/
- 工具配置 → wiki/工具/
- 项目信息 → wiki/项目/
- 方法流程 → wiki/方法论/
- 对比分析 → wiki/参考与对比/

---

## 4. Raw 保留规则

- **最少保留 7 天** — raw 文件编译后不可立即删除
- **删除条件**：必须同时满足：
  - 文件存在超过 7 天
  - 已在 wiki 中有对应页面（frontmatter 有 source）
  - MEMORY.md 已更新反向检索标记

---

## 5. wiki/ 分类约定

### 文件夹和用途

| 文件夹 | 用途 | 判断问题 |
|--------|------|---------|
| 项目/ | 项目设计、决策 | 这是某个项目的设计吗？ |
| 工具/ | 工具配置、踩坑记录 | 这是工具的使用方法或限制吗？ |
| 实体信息/ | 人/客户具体信息 | 这是某个具体的人或客户吗？ |
| 知识概念/ | 概念、定义 | 这是抽象的道理或定义吗？ |
| 方法论/ | 方法、流程、最佳实践 | 这是"怎么做"的经验吗？ |
| 规则纪律/ | 规则、标准 | 这是做事的标准吗？ |
| 参考与对比/ | A vs B、参考对比 | 这是两个东西的对比吗？ |
| 环境与社会关系/ | 环境认知、团队配置 | 这是团队/环境相关的吗？ |

### 页面格式模板

**项目页（wiki/项目/*.md）**

```yaml
---
type: project
name: 项目名
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags:
  - "#项目"
---

# 项目名

## 概述
（项目做什么）

## 规则纪律/标准
（项目相关的规则、标准、踩坑记录）

## Open Threads
（进行中的任务）

## 相关记录（编译时自动维护）
> 以下记录由 Agent 编译时自动追加，记录与该项目相关的新发现

| 时间 | 来源 | 内容摘要 | 关联决策 |
|------|------|---------|---------|
| YYYY-MM-DD | [[raw/文章/xxx]] | 关键发现摘要 | 追加到本页 |

## 关联页面
- [[wiki/工具/相关工具]]
- [[wiki/知识概念/相关概念]]
```

**工具页（wiki/工具/*.md）**

```yaml
---
type: tool
name: 工具名
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags:
  - "#工具"
---

# 工具名

## 概述
（工具用途）

## 配置/踩坑记录
## 使用场景

## 相关记录（编译时自动维护）
> 以下记录由 Agent 编译时自动追加

| 时间 | 来源 | 内容摘要 | 关联决策 |
|------|------|---------|---------|
| YYYY-MM-DD | [[raw/文章/xxx]] | 关键发现摘要 | 追加到本页 |

## 关联页面
- [[wiki/项目/使用该工具的项目]]
- [[wiki/方法论/相关方法]]
```

**实体信息页（wiki/实体信息/*.md）**

```yaml
---
type: entity
subtype: person | tool | project | customer
created: YYYY-MM-DD
updated: YYYY-MM-DD
aliases: [别名1, 别名2]
tags:
  - "#实体"
---

# 实体名称

## 基本信息
## 环境认知
## 关联记录
## 变更历史

## 相关记录（编译时自动维护）
> 以下记录由 Agent 编译时自动追加

| 时间 | 来源 | 内容摘要 | 关联决策 |
|------|------|---------|---------|
| YYYY-MM-DD | [[raw/对话/xxx]] | 关键发现摘要 | 追加到本页 |

## 关联页面
- [[wiki/项目/相关项目]]
- [[wiki/知识概念/相关概念]]
```

**概念页（wiki/知识概念/*.md）**

```yaml
---
type: concept
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags:
  - "#概念"
---

# 概念名

## 定义
## 适用范围
## 相关概念

## 相关记录（编译时自动维护）
> 以下记录由 Agent 编译时自动追加

| 时间 | 来源 | 内容摘要 | 关联决策 |
|------|------|---------|---------|
| YYYY-MM-DD | [[raw/文章/xxx]] | 关键发现摘要 | 追加到本页 |

## 关联页面
- [[wiki/项目/应用该概念的项目]]
- [[wiki/知识概念/相关概念]]
```

**方法页（wiki/方法论/*.md）**

```yaml
---
type: method
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags:
  - "#方法论"
---

# 方法名

## 概述
## 步骤
## 适用场景
## 踩坑记录

## 相关记录（编译时自动维护）
> 以下记录由 Agent 编译时自动追加

| 时间 | 来源 | 内容摘要 | 关联决策 |
|------|------|---------|---------|
| YYYY-MM-DD | [[raw/文章/xxx]] | 关键发现摘要 | 追加到本页 |

## 关联页面
- [[wiki/项目/使用该方法的项目]]
- [[wiki/工具/相关工具]]
```

**规则页（wiki/规则纪律/*.md）**

```yaml
---
type: rule
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags:
  - "#规则纪律"
---

# 规则名

## 规则内容
## 适用范围
## 例外情况
## 变更历史

## 相关记录（编译时自动维护）
> 以下记录由 Agent 编译时自动追加

| 时间 | 来源 | 内容摘要 | 关联决策 |
|------|------|---------|---------|
| YYYY-MM-DD | [[raw/对话/xxx]] | 决策依据 | 追加到本页 |

## 关联页面
- [[wiki/项目/适用该规则的项目]]
- [[wiki/知识概念/相关概念]]
```

**对比页（wiki/参考与对比/*.md）**

```yaml
---
type: comparison
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags:
  - "#对比"
---

# A vs B

## 共同点
## 差异点
## 适用场景
## 决策建议

## 相关记录（编译时自动维护）
> 以下记录由 Agent 编译时自动追加

| 时间 | 来源 | 内容摘要 | 关联决策 |
|------|------|---------|---------|
| YYYY-MM-DD | [[raw/文章/xxx]] | 关键发现摘要 | 追加到本页 |

## 关联页面
- [[wiki/参考与对比/其他对比]]
- [[wiki/知识概念/相关概念]]
```

---

## 6. 编译触发规则

| 条件 | 说明 |
|------|------|
| 同一文件夹 ≥3 条未编译 | raw/ 攒够了才提醒 |
| 单条 ≥7 天未编译 | 太久没动就提醒 |
| MEMORY.md > 350 行 | 记忆太满，建议迁移到 wiki |

### 编译流程（Karpathy 模式）

1. raw/ 新文件进入 → Agent 读取内容
2. 提取关键实体/概念
3. 搜索现有 wiki 页面（grep / index.md）
4. **关联判断**：Agent 手动判断新内容与现有 wiki 页面的关联关系
   - 关联到已有页面 → 在「相关记录」中追加一行，并更新页面内容
   - 无关联 → 创建新页面（按模板）
5. **记录关联决策**：在 `log.md` 中记录关联决策和用户评价（如有）
6. 新内容与旧页面冲突 → 标记矛盾，不覆盖，等待用户确认
7. 编译完成 → 更新 index.md + log.md

---

## 7. 关联与追加策略

### 关联判断流程

```
新 raw 内容
  ↓
提取关键实体/概念
  ↓
搜索现有 wiki 页面（grep / index.md）
  ↓
有匹配页面？
  ├─ 是 → 在「相关记录」追加来源，更新页面内容
  └─ 否 → 创建新页面（按模板）
```

### 关联决策记录格式（log.md）

```markdown
| 时间 | 操作 | 来源 | 目标页面 | 关联决策 | 用户评价 | 冲突标记 |
|------|------|------|---------|---------|---------|---------|
| YYYY-MM-DD | 关联 | [[raw/文章/xxx]] | [[wiki/项目/ChatERP]] | 追加到「相关记录」；更新「概述」段落；标记 #待验证 | Binary：同意 | 新内容与旧页面「技术选型」段落矛盾，已标记 ⚠️ |
```

**字段说明**：

| 字段 | 说明 | 示例 |
|------|------|------|
| 时间 | 编译时间 | 2026-05-09 |
| 操作 | 关联/创建/更新/合并 | 关联 |
| 来源 | raw 文件路径 | [[raw/文章/xxx]] |
| 目标页面 | wiki 页面路径 | [[wiki/项目/ChatERP]] |
| 关联决策 | 具体更新内容 | 追加到「相关记录」；更新「概述」段落；标记 #待验证 |
| 用户评价 | Binary 的反馈 | Binary：同意 / 不同意：应放到 [[wiki/工具/xxx]] |
| 冲突标记 | 新内容与旧内容的矛盾 | 新内容与旧页面「技术选型」段落矛盾，已标记 ⚠️ |

### 用户评价收集

- 编译完成后，Agent 主动询问用户："已将 [[raw/xxx]] 关联到 [[wiki/xxx]]，判断是否准确？"
- 用户评价记录到 log.md 的「用户评价」列
- **评价类型**：
  - ✅ 同意 — 关联准确，无需调整
  - ⚠️ 部分同意 — 大体正确，但有细节需要调整（如"应补充到 [[wiki/工具/xxx]]"）
  - ❌ 不同意 — 关联错误，需要重新判断（如"应放到 [[wiki/概念/xxx]] 而非项目"）
- 定期（每月）回顾关联决策记录，统计各类型评价比例
- 针对 ❌ 和 ⚠️ 评价，分析误判模式，总结优化建议
- 经验总结编入 SCHEMA.md，实现 Agent 自我进化

### 自我进化流程

```
每月回顾 log.md
  ↓
统计评价类型比例（同意/部分同意/不同意）
  ↓
分析 ❌ 和 ⚠️ 评价的共性模式
  ↓
总结优化建议（如"XX 类型内容应优先关联到 YY 页面"）
  ↓
与用户讨论确认
  ↓
更新 SCHEMA.md「关联规则进化记录」
  ↓
下次编译时应用新规则
```

**进化记录位置**：在 SCHEMA.md 末尾添加「关联规则进化记录」章节，记录每次更新的规则和经验。

| 标记 | 含义 |
|------|------|
| ⚠️ 待验证 | 不确定，需要找方法/求证 |
| ❌ 已验证为错误 | 纠正后的记录 |

---

## 8. 标记规则

| 标记 | 含义 |
|------|------|
| ⚠️ 待验证 | 不确定，需要找方法/求证 |
| ❌ 已验证为错误 | 纠正后的记录 |

---

## 9. raw frontmatter 模板

```yaml
---
source: https://...          # 原文链接/路径
type: article | document | transcript | environment | diary | code
recorded: YYYY-MM-DD       # 记录时间
confidence: 80             # 自信度 0-100，≥80 可直接编译
discussed_1st: YYYY-MM-DD  # 首次讨论（自信度<80 时必填）
discussed_2nd:              # 再次讨论（可为空）
scheduled: YYYY-MM-DD     # 预定讨论时间（可为空）
compiled_1st: YYYY-MM-DD   # 第一次被编译时间（可为空）
compiled_2nd:               # 第二次被编译时间（可为空）
never_compiled: true       # 从未编译标注
tags:
  - "#标签"
---
```

---

## 10. Heartbeat 职责

1. **检索未讨论的 raw** → 提醒用户讨论
2. **检查 scheduled 字段** → 预定时间到了提醒
3. **检查自信度** → 自信度<80 时提醒用户验证
4. **触发 compile** → 达到编译条件时提醒
5. **用户评价回顾** → 每月回顾关联决策记录，总结经验

**Heartbeat 提示词应包含：**
- 自信度数值（如"自信度 65%，建议验证"）
- 首次讨论时间（如"discussed_1st 为空，请讨论"）
- 关联决策统计（如"本月关联准确率 80%，主要误判：XX 类型内容"）

---

## 11. lint 检查清单

| 检查项 | 说明 |
|--------|------|
| 矛盾内容 | 新观点推翻旧观点但旧页面未更新 |
| 过时内容 | 判断已不适用但仍在 wiki |
| 孤儿页 | 没有任何 wikilink 引用的页面 |
| 格式一致性 | frontmatter 是否符合规范 |
| 悬空链接 | wikilink 指向不存在的目标文件 |
| **关联完整性** | 「相关记录」中的来源是否都已编译到 wiki |
| **用户评价回顾** | 近期关联决策是否有用户反馈，是否需要调整策略 |

---

## 12. 悬空链接处理

| 情况 | 处理 | 标签 |
|------|------|------|
| 有来源/有内容 | 创建目标 MD，填入内容 | 无特殊标签 |
| 无来源/待补充 | 创建空 MD + 标记待补充 | #待学习 / #待搜索 / #TODO |

**Workflow：**
```
发现相关概念 [[新概念]]
  ↓
有来源？
  ├─ 有 → 立即创建目标 MD + 填内容
  └─ 无 → 创建空 MD + 标记 #待学习
        ↓
  后续发现相关来源 → 补充内容 + 移除标签
```

---

## 13. 关联规则进化记录

> 本章节记录 Agent 关联决策经验的进化过程，每次更新需标注时间和触发原因。

### 进化流程

```
每月回顾 log.md
  ↓
统计评价类型比例（同意/部分同意/不同意）
  ↓
分析 ❌ 和 ⚠️ 评价的共性模式
  ↓
总结优化建议（如"XX 类型内容应优先关联到 YY 页面"）
  ↓
与用户讨论确认
  ↓
更新本章节
  ↓
下次编译时应用新规则
```

### 进化记录格式

```markdown
### YYYY-MM-DD 更新

**触发原因**：月度回顾 / 用户反馈 / 新类型内容出现

**发现问题**：
- XX 类型内容常被误判关联到 YY 页面
- ZZ 类型内容遗漏关联到 WW 页面

**优化规则**：
- XX 类型内容 → 优先关联到 [[wiki/概念/XX概念]]
- ZZ 类型内容 → 必须关联到 [[wiki/工具/ZZ工具]]

**验证结果**：
- 更新后关联准确率从 X% 提升到 Y%
```

---

> 📌 每项讨论确认后立即填入，完成后状态改为 ✅
""")
        result["created_files"].append(schema_path)
        
        
        # index.md — Main navigation
        index_path = os.path.join(vault_path, "index.md")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(f"""---
title: {vault_name} 知识库
description: {vault_name} 的 LLM Wiki 结构化知识库
---

# 🏠 {vault_name} Wiki 总览

> 外部知识库，存储稳定信息（世界知识/周期性规律/环境认知）
> 瞬时状态放 MEMORY.md，时效后 auto-dream 忘却

## 📂 目录索引

### raw/ — 原始材料（只读）
- 文章/ — 公众号、博客、RSS
- 文档/ — PDF、手册、资料
- 对话/ — 聊天记录、会议记录
- 环境认知/ — 工具配置、角色关系
- 日记/ — 工作日志

### wiki/ — 编译后的知识网络
- [[项目/_index|项目/]] — 项目设计、决策
- [[工具/_index|工具/]] — 工具配置
- [[实体信息/_index|实体信息/]] — 人/客户信息
- [[知识概念/_index|知识概念/]] — 概念、定义
- [[方法论/_index|方法论/]] — 方法、流程
- [[规则纪律/_index|规则纪律/]] — 规则、制度
- [[参考与对比/_index|参考与对比/]] — A vs B
- [[环境与社会关系/_index|环境与社会关系/]] — 团队配置

## 📌 最近更新

- {today}：初始化知识库（SCHEMA.md 待讨论填充）

---

*由 OBHeartbeat 自动更新*
""")
        result["created_files"].append(index_path)
        
        # log.md — Operation log
        log_path = os.path.join(vault_path, "log.md")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"""# 操作日志

记录 Wiki 的 compile、lint 和其他维护操作。

---

| 时间 | 操作 | 详情 |
|------|------|------|
| {today} | Vault 初始化 | 创建目录结构和初始文件，SCHEMA.md 待讨论填充 |

*由 OBHeartbeat 自动更新*
""")
        result["created_files"].append(log_path)
        
        # .obsidian/ — Obsidian core plugin configurations
        obsidian_dir = os.path.join(vault_path, ".obsidian")
        os.makedirs(obsidian_dir, exist_ok=True)
        result["created_dirs"].append(obsidian_dir)

        core_plugins = {
            "backlink": True,
            "note-composer": True,
            "outgoing-link": True,
            "tag-pane": True,
            "outline": True,
            "workspaces": True,
            "file-recovery": True,
            "canvas": False,
            "daily-notes": False,
            "zk-prefixer": False,
            "templates": False,
            "markdown-importer": False,
            "publish": False,
            "sync": False,
            "bookmarks": True,
            "quick-switcher": True,
            "command-palette": True,
            "slash-commands": True,
            "search": True,
            "graph-view": True,
            "page-preview": True,
            "word-count": True,
            "web-viewer": True,
            "audio-recorder": True,
            "slides": True,
            "random-note": True,
            "file-explorer": True,
            "bases": True
        }
        core_plugins_path = os.path.join(obsidian_dir, "core-plugins.json")
        with open(core_plugins_path, "w", encoding="utf-8") as f:
            json.dump(core_plugins, f, indent=2, ensure_ascii=False)
        result["created_files"].append(core_plugins_path)

        note_composer = {
            "askBeforeMerging": False,
            "dontAskAgain": True,
            "extractBehavior": "link"
        }
        note_composer_path = os.path.join(obsidian_dir, "note-composer.json")
        with open(note_composer_path, "w", encoding="utf-8") as f:
            json.dump(note_composer, f, indent=2, ensure_ascii=False)
        result["created_files"].append(note_composer_path)

        app_config = {
            "newFileLocation": "folder",
            "newFileFolderPath": "raw",
            "attachmentFolderPath": "outputs",
            "useMarkdownLinks": False,
            "useWikiLinks": True
        }
        app_config_path = os.path.join(obsidian_dir, "app.json")
        with open(app_config_path, "w", encoding="utf-8") as f:
            json.dump(app_config, f, indent=2, ensure_ascii=False)
        result["created_files"].append(app_config_path)

        # README.md — Quick reference (replaces old CLAUDE.md)
        readme_path = os.path.join(vault_path, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"""# {vault_name} 知识库 — 快速参考

## 目录结构

```
{vault_name}/
├── SCHEMA.md      # 编译规则（核心契约，Agent 与用户讨论后填充）
├── index.md       # 总导航
├── log.md         # 操作日志
├── raw/           # 原始材料（只读）
│   ├── 文章/      # 公众号、博客
│   ├── 文档/      # PDF、手册
│   ├── 对话/      # 聊天记录
│   ├── 环境认知/  # 工具配置、角色关系
│   └── 日记/      # 工作日志
├── wiki/          # 编译后的知识网络
│   ├── 项目/          # 项目设计、决策
│   ├── 工具/          # 工具配置
│   ├── 实体信息/      # 人/客户信息
│   ├── 知识概念/      # 概念、定义
│   ├── 方法论/        # 方法、流程
│   ├── 规则纪律/      # 规则、制度
│   ├── 参考与对比/    # A vs B
│   └── 环境与社会关系/ # 团队配置
└── outputs/       # 最终产物（报告/摘要）
```

## 命名规范

- 文件直接用内容名称，**不用前缀**
- 示例：`允林棠.md`、`API使用实践.md`

## 核心规则

1. **先记录，后整理** — 有价值的内容先写 raw/，后续编译
2. **好答案归档** — 讨论产生的好答案 → wiki/知识概念/
3. **compile 必须由 Agent 执行** — 脚本只扫描，不自动编译
4. **SCHEMA.md 是契约** — 创建前必须讨论，创建后按需更新

## 分类速查

| 内容 | 放哪 |
|------|------|
| "怎么做"的方法 | 方法论/ |
| "禁止做什么"的规则 | 规则纪律/ |
| 工具配置/踩坑 | 工具/ |
| 具体人/客户信息 | 实体信息/ |
| 项目设计/决策 | 项目/ |
| 抽象概念/定义 | 知识概念/ |
| A vs B 对比 | 参考与对比/ |
| 团队/环境配置 | 环境与社会关系/ |

---

*生成时间：{today}*
""")
        result["created_files"].append(readme_path)
        
        result["success"] = True
        
    except Exception as e:
        result["errors"].append(str(e))
    
    return result


def register_with_obsidian_cli(vault_path: str) -> dict:
    """Register vault with obsidian-cli by adding to obsidian.json."""
    import subprocess
    import uuid
    
    result = {"success": False, "output": "", "error": ""}
    
    try:
        # Check if obsidian-cli is installed
        check = subprocess.run(["which", "obsidian-cli"], capture_output=True, text=True)
        if check.returncode != 0:
            result["error"] = "obsidian-cli not installed. Run: brew install yakitrak/yakitrak/obsidian-cli"
            return result
        
        # Read obsidian.json
        obsidian_json_path = os.path.expanduser("~/Library/Application Support/obsidian/obsidian.json")
        if not os.path.exists(obsidian_json_path):
            result["error"] = "obsidian.json not found. Open Obsidian app first."
            return result
        
        with open(obsidian_json_path, "r", encoding="utf-8") as f:
            obsidian_config = json.load(f)
        
        # Check if vault already registered
        vault_name = os.path.basename(os.path.normpath(vault_path))
        for vault_id, vault_info in obsidian_config.get("vaults", {}).items():
            if vault_info.get("path") == vault_path:
                result["success"] = True
                result["output"] = f"Vault already registered: {vault_name}"
                return result
        
        # Add new vault
        new_vault_id = uuid.uuid4().hex[:12]
        obsidian_config["vaults"][new_vault_id] = {
            "path": vault_path,
            "ts": int(os.path.getmtime(vault_path)) * 1000 if os.path.exists(vault_path) else 0,
            "open": True
        }
        
        # Close other vaults (set open=false)
        for vid in obsidian_config["vaults"]:
            if vid != new_vault_id:
                obsidian_config["vaults"][vid]["open"] = False
        
        with open(obsidian_json_path, "w", encoding="utf-8") as f:
            json.dump(obsidian_config, f, indent=4, ensure_ascii=False)
        
        result["success"] = True
        result["output"] = f"Registered new vault: {vault_name} at {vault_path}"
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 init_vault.py <vault-name> <vault-path>")
        print("Example: python3 init_vault.py Matuoer '/Volumes/Binary HD/obsidian/Matuoer'")
        sys.exit(1)
    
    vault_name = sys.argv[1]
    vault_path = sys.argv[2]
    
    print(f"[obsidian-wiki-init] Creating vault '{vault_name}' at {vault_path}")
    
    # Create vault structure
    create_result = create_vault(vault_name, vault_path)
    
    if not create_result["success"]:
        print(f"[ERROR] Failed to create vault: {create_result['errors']}")
        sys.exit(1)
    
    print(f"[OK] Created {len(create_result['created_dirs'])} directories")
    print(f"[OK] Created {len(create_result['created_files'])} files:")
    for f in create_result["created_files"]:
        print(f"       - {f}")
    
    # Register with obsidian-cli
    print(f"\n[obsidian-wiki-init] Registering with obsidian-cli...")
    reg_result = register_with_obsidian_cli(vault_path)
    
    if reg_result["success"]:
        print(f"[OK] Vault registered with obsidian-cli")
    else:
        if reg_result["error"]:
            print(f"[WARN] Could not register with obsidian-cli: {reg_result['error']}")
            print(f"[INFO] You can register manually: obsidian-cli set-vault '{vault_path}'")
        else:
            print(f"[OK] Vault registered")
    
    # Initialize lint-state tracking
    init_lint_state(vault_path)

    # Auto-activate: register OBHeartbeat to agent's HEARTBEAT.md
    print(f"\n[obsidian-wiki-init] Activating vault...")
    if activate:
        try:
            act_result = activate(vault_path)
            if act_result.get("success"):
                print(f"[OK] Vault activated")
                print(f"   Workspace: {act_result.get('agent_workspace', 'N/A')}")
                print(f"   HEARTBEAT.md: {'Updated' if act_result.get('heartbeat_updated') else 'No change'}")
                for msg in act_result.get("messages", []):
                    print(f"   > {msg}")
            else:
                print(f"[WARN] Could not auto-activate vault:")
                for msg in act_result.get("messages", []):
                    print(f"   > {msg}")
                print(f"[INFO] You can activate manually: python3 {os.path.join(os.path.dirname(__file__), 'activate.py')} '{vault_path}'")
        except Exception as e:
            print(f"[WARN] Auto-activation failed: {e}")
            print(f"[INFO] You can activate manually: python3 {os.path.join(os.path.dirname(__file__), 'activate.py')} '{vault_path}'")
    else:
        print(f"[WARN] activate.py not found, skipping auto-activation")
        print(f"[INFO] You can activate manually: python3 {os.path.join(os.path.dirname(__file__), 'activate.py')} '{vault_path}'")

    print(f"\n✅ Vault '{vault_name}' created successfully!")
    print(f"   Path: {vault_path}")
    print(f"\n⚠️  IMPORTANT: SCHEMA.md is a TEMPLATE — Agent MUST discuss with user before filling it.")
    print(f"   See: ~/.openclaw/skills/obsidian-wiki-init/references/schema-discussion-guide.md")
    print(f"\nNext steps:")
    print(f"  1. Agent discusses SCHEMA.md with user (5 questions)")
    print(f"  2. Fill in SCHEMA.md based on discussion")
    print(f"  3. Add raw data to raw/文章/ or raw/对话/")
    print(f"  4. Create wiki notes in wiki/实体信息/, wiki/知识概念/, etc.")
    print(f"  5. Use obsidian-cli search-content '<query>' to search")


if __name__ == "__main__":
    main()
