# Compile 操作流程

> Agent 执行 raw → wiki 编译时的完整 step-by-step 流程。
> 执行 compile 前必须先阅读 `wiki-index-format.md` 了解索引格式规范。
> 本文档是 SKILL.md 的执行层补充。

---

## 编译决策树（来源：OBheartbeat.json）

```
Step 1: 这是禁止性规则吗？
  → 是 → 规则纪律/
  → 否 → Step 2

Step 2: 这有明确起止和阶段性成果吗？
  → 是 → 项目/
  → 否 → Step 3

Step 3: 这是具体存在的人/物吗？
  → 是 → 实体信息/
  → 否 → Step 4

Step 4: 这是 A vs B 或需要对比才能理解的吗？
  → 是 → 参考与对比/
  → 否 → 再问：这个内容对谁最重要？
    → 对我(Agent) → 工具/
    → 对团队/环境 → 环境与社会关系/
    → 通用定义 → 知识概念/
    → 踩坑经验 → 方法论/
```

**核心原则：**
- 不能仅凭关键词判断：有"规范"二字不一定规则纪律/
- 看本质而非看标签：问"这个内容描述的是什么"
- 规则纪律是"禁止性规则"（违反有负面后果），API限制是"事实性约束"→ 方法论/

---

## 完整编译流程（6 步）

### Step 0：读取引用文档

**必须先读：**
- `references/wiki-index-format.md` — 索引格式规范
- `{vault}/SCHEMA.md` — 该 vault 的分类规则

---

### Step 1：读取来源文件

读取待编译的 raw 文件，提取：
- frontmatter（source、type、recorded、confidence 等）
- body 内容
- 关键实体、概念、关系

---

### Step 2：判断目标分类

根据编译决策树判断放到哪个 wiki/ 子目录。

**特殊情况：**
- 涉及多个分类 → 优先放最具体的那个
- 边界模糊 → 放"最像"的那个，之后 lint 会发现
- 完全不确定 → 放知识概念/，让后续讨论修正

---

### Step 3：生成/更新 wiki 页面

**新建页面：**
```markdown
---
type: {concept|entity|method|rule|...}
sources: [{source}]
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [#标签]
---

# 页面标题

## 内容...
```

**更新已有页面：**
- 在现有内容基础上整合，不覆盖
- 冲突内容标记为 `⚠️待验证`，不删除旧内容
- 添加来源标注：`^[filename.md]`

---

### Step 4：更新索引

**更新根目录 index.md：**
1. 在对应分类下添加/更新页面条目
2. 按修改时间重新排序
3. 补充 metadata 行

**更新分类 _index.md：**
1. 在页面列表中添加/更新条目
2. 按修改时间重新排序
3. 补充 metadata 行

---

### Step 5：更新 raw 文件 frontmatter

编译完成后更新 raw 文件的 frontmatter：

```yaml
compiled_1st: YYYY-MM-DD   # 首次编译时间
```

**不立即填 compiled_2nd**，由 Agent 判断是否需要第二次编译。

---

### Step 6：更新 lint-state（如有）

如果是 lint 驱动的 compile（orphan_pages、broken_links 等），修复后更新：
```json
{
  "id": "{page}",
  "state": "fixed",
  "fixed_at": "YYYY-MM-DD"
}
```

---

## 流程检查清单

compile 完成后，确认以下全部完成：

- [ ] Step 0 — 读了 wiki-index-format.md 和 SCHEMA.md
- [ ] Step 1 — 读取了 raw 文件内容
- [ ] Step 2 — 确认了目标分类
- [ ] Step 3 — wiki 页面已创建/更新
- [ ] Step 4 — index.md 和 _index.md 已更新
- [ ] Step 5 — raw 文件的 compiled_1st 已填
- [ ] Step 6 — lint-state 已更新（如有）

---

## 特殊情况处理

### 情况 1：多个来源同时编译

多个 raw 属于同一实体/主题时：
1. 先读取所有来源，提取共享概念
2. 一次性生成一个 wiki 页面（不拆分）
3. sources 字段列出所有来源

### 情况 2：新来源推翻旧 wiki 内容

- 不删除旧内容，标记为过时
- 添加新内容，注明覆盖原因
- 格式：`> ⚠️ 以下内容已于 YYYY-MM-DD 修正：...`

### 情况 3：悬空链接

| 情况 | 处理 |
|------|------|
| 有来源/有内容 | 创建目标 MD + 填内容 |
| 无来源/待补充 | 创建空 MD + 标记 #待学习 |

---

## 禁止事项

- ❌ 编译后立即删除 raw 文件（最少保留 7 天）
- ❌ 编译后不更新 index
- ❌ 不读 wiki-index-format.md 就更新 index
- ❌ 强制覆盖已有内容（只能合并或标记冲突）