# ⚠️ 已废弃 - 请勿参考
# Obsidian Vault 标准结构

> 每个 Agent 的知识库应遵循以下标准结构，确保跨 Agent 协作和知识沉淀的一致性。
> 此体系为 **M1/M2/M3 三层编译** 的一部分，详见 `three-layer-compilation.md`。

---

## 目录结构

```
vault-name/
├── INDEX.md              # 知识库总览
├── CLAUDE.md             # AI 协作指南
├── raw/                  # M1：原始数据（永久保留，只增不减）
│   ├── chat-logs/       # 聊天记录原始文本
│   └── orders/           # 订单/出货记录原始文件
├── wiki/                 # M2：结构化笔记（从 M1 提炼）
│   ├── concepts/         # 概念/术语/业务规则
│   ├── customers/       # 客户信息
│   ├── products/        # 产品信息
│   ├── warehouse/       # 仓库信息
│   └── people/          # 人员信息
└── outputs/             # M3：最终产物（报告/摘要/可交付结论）
```

---

## 各目录说明

### raw/（M1）— 原始数据
- **chat-logs/**：从 IM 软件导出的原始聊天记录
- **orders/**：订单 Excel、截图等未处理数据
- **性质**：只增不减，永不删除

### wiki/（M2）— 结构化笔记
- **concepts/**：概念定义、行业术语、业务规则
- **customers/**：客户信息、联系人、历史订单、偏好
- **products/**：产品信息、款号、面料、库存状态
- **warehouse/**：仓库信息、入库出库记录、库存台账
- **people/**：内部人员信息、职责分工

### outputs/（M3）— 最终产物
- **reports/**：分析报告
- **summaries/**：汇总摘要
- **deliverables/**：可交付产物

---

## 命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 客户笔记 | `C-{简称}.md` | `C-允林棠.md` |
| 产品笔记 | `P-{款号}.md` | `P-TY261WA22.md` |
| 仓库笔记 | `WH-{名称}.md` | `WH-总部仓库.md` |
| 人员笔记 | `AD-{姓名}.md` | `AD-尤维琦.md` |
| 概念笔记 | `{概念名}.md` | `订货会规则.md` |

---

## 笔记 frontmatter 模板

```yaml
---
type: customer | product | warehouse | person | concept
created: YYYY-MM-DD
updated: YYYY-MM-DD
aliases:
  - 别名1
  - 别名2
tags:
  - #客户/批发
  - #地区/浙江
links:
  - [[C-另一客户]]
  - [[P-产品款号]]
---

# 标题

## 基本信息

## M1 来源记录

## 变更历史

## 关联笔记
```

---

## 双向链接使用场景

1. **客户笔记** → 关联负责的 AD、产品、常用仓库
2. **产品笔记** → 关联常订客户、所属仓库
3. **仓库笔记** → 关联常供货客户
4. **人员笔记** → 关联负责的客户
