# 三层编译规则（Obsidian Vault · M1/M2/M3）

> 注：此体系与 Mauto 的 L1/L2/L3 记忆层级对应，vault 采用 M1/M2/M3 命名。
> - **Mauto L1/L2/L3** = Agent 会话记忆（经验、偏好、规则）
> - **Vault M1/M2/M3** = Agent 业务知识（客户、产品、仓库等实体信息）

---

## 三层定义

| 层级 | 目录 | 内容 | 性质 |
|------|------|------|------|
| **M1** | `raw/` | 原始数据（聊天记录/截图/文件/订单） | 只增不减，永不删除 |
| **M2** | `wiki/` | 从 raw 提炼的结构化笔记（客户/产品/概念/人员） | 增量更新 |
| **M3** | `outputs/` | 最终产物（报告/摘要/可交付结论） | 代谢产物 |

---

## 执行机制

### M1 写入（实时 · Agent 主动）

Agent 在执行核心工作时遇到新知识，**立即写入 `raw/`**：

- 新的客户需求或偏好
- 产品规格/库存变化
- 业务规则或决策
- 人员变动信息

> **脚本无法替代**：因为脚本不知道「哪里有新知识」——只有 Agent 在工作中才能感知到什么是重要的。

**命名格式**：
```
raw/chat-logs/{YYYY-MM-DD}-{对话摘要}.txt
raw/orders/{YYYY-MM-DD}-{单号}.xlsx
raw/screenshots/{YYYY-MM-DD}-{描述}.png
```

### M2 提炼（定时 · Agent 执行）

- **每日 heartbeat 时**执行
- 从 `raw/` 读取 M1 内容，**用 LLM 语义理解**提炼到 `wiki/`
- 触发条件：同一实体 M1 记录 ≥ 3 条，或时间跨度超过 7 天

### M3 提炼（按需 · Agent 执行）

- 特定项目周期结束时（季度、订货会结束后）
- 跨 M2 笔记综合分析，用 LLM 生成报告或摘要
- 输出到 `outputs/reports/` 或 `outputs/summaries/`

---

## frontmatter 规范

```yaml
---
type: customer | product | warehouse | person | concept
created: YYYY-MM-DD    # 首次创建
updated: YYYY-MM-DD    # 每次 M1→M2 提炼后更新
aliases:
  - 别名1
  - 别名2
tags:
  - #实体类型/分类
links:
  - [[关联笔记]]
---

# 标题

## 基本信息

## M1 来源记录

## 变更历史
```

---

## 禁忌

1. **禁止从 `raw/` 删除内容**（M1 永久保留）
2. **禁止跳过 M1 直接写 M2**（实时记录是提炼的原材料）
3. **M2 笔记禁止覆盖，只可追加或更新**
4. **wikilink 变更必须同步更新所有相关笔记**
