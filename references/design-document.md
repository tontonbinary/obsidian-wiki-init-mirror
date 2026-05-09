# obsidian-wiki-init 完整设计方案

> 创建时间：2026-04-20
> 供 Mautoer 参考实现
> 来源：小娴与 Binary 的讨论
> 
> **⚠️ 更新说明**：2026-04-22 已完成最终设计讨论。
> **最终设计契约见**：`~/.openclaw/skills/obsidian-wiki-init/OBheartbeat.json`
> **使用规范见**：`~/.openclaw/skills/obsidian-wiki-init/SKILL.md`
> **本文件为历史参考，最终设计以上述两份文件为准。**

---

## 一、背景：Mauto 记忆体系 + LLM Wiki 的关系

### 1.1 Mauto 记忆体系

Mauto 是 Agent 的记忆管理系统，三层架构：

```
L0（session JSONL）
  ↓ Mauto 蒸馏
L1（每日结构化记忆，7类标签，重要性评分）
  ↓ Auto-Dream 梦境周期
L3（MEMORY.md + tag index）
  ↓ 懒加载触发
Agent context（按需加载）
  ↓
L4（SOUL.md 身份与价值观）
```

### 1.2 LLM Wiki 的角色

LLM Wiki 不是"贡献内容给 L3"，而是"L3 帮助检索的外部知识库"。

```
Agent 当前 context
  ↓ 触发标签/场景
L3（MEMORY.md + tag index）→ 快速定位要调用的知识
  ↓
LLM Wiki wiki/（实体页/概念页/对比页）→ 返回实际内容
```

**核心原则：记忆减负，不是记忆积累**
- 懒加载 = 不用不加载
- 标签检索 = 按需触发
- 强化高频 = 越用越容易召回
- 忘却低频 = 不常用就沉没

### 1.3 obsidian-wiki-init 的定位

- **目的**：为 Agent 创建一个可编译、可检索的 Wiki 知识库
- **不是**：给人类使用的笔记工具
- **存储什么**：稳定信息（世界知识/周期性规律/环境认知）
- **不存储什么**：瞬时状态/当前进度（这些放 MEMORY.md）

---

## 二、存储原则

| 信息类型 | 存储位置 | 特点 | 处理方式 |
|---------|---------|------|---------|
| 世界知识 | Obsidian wiki | 稳定，长期不变 | compile 后持久存在 |
| 周期性规律 | Obsidian wiki | 稳定，但需定期更新 | lint 检查时效 |
| 环境认知 | Obsidian wiki | 相对稳定，缓慢变化 | compile + lint |
| 库存/项目进度 | MEMORY.md / memory | 动态，时效性强 | 时效过后 auto-dream 忘却 |
| 临时状态/会话信息 | L0 / L1 | 一次性的 | 直接遗忘 |

**判断标准：**
- ✅ "YLT 客户默认折扣是 8 折" → 稳定规则 → Wiki
- ❌ "棠绶 YLT-001 当前库存是 120 件" → 瞬时状态 → memory/

---

## 三、近期实现（obsidian-wiki-init）

### 3.1 目标

创建一个 LLM Wiki 结构的 Obsidian vault，包含：
- 正确的目录结构
- SCHEMA.md 编译规则
- compile 命令（可选）
- lint 检查清单

### 3.2 目录结构

```
vault-name/
├── SCHEMA.md              # 编译规则（你和 AI 的契约）
├── index.md               # 总导航
├── log.md               # 操作日志（每次 compile 追加）
├── raw/                   # 原始材料（只读）
│   ├── articles/          # 文章/公众号/博客
│   ├── documents/         # 文档/手册
│   ├── transcripts/       # 聊天记录/会议记录
│   └── environment/       # 环境认知原始材料
├── wiki/                  # LLM 编译后的知识网络
│   ├── 项目/              # 项目设计、决策
│   ├── 工具/              # 工具配置
│   ├── 实体信息/          # 人/客户具体信息
│   ├── 知识概念/          # 概念、定义
│   ├── 方法论/            # 方法
│   ├── 规则纪律/          # 规则、制度
│   ├── 参考与对比/        # A vs B、参考对比
│   └── 环境与社会关系/    # 环境认知（团队配置、昵称映射）
└── outputs/              # 最终产物
```

### 3.3 文件夹归属（默认分类）

| 文件夹 | 存放内容 | 示例 |
|--------|---------|------|
| 项目/ | 项目设计、决策 | `ChatERP.md`、`Mauto设计.md` |
| 工具/ | 工具配置 | `feishu_doc.md` |
| 实体信息/ | 人/客户信息 | `允林棠.md`、`尤维琦.md` |
| 知识概念/ | 概念、定义 | `LLM-Wiki定位.md` |
| 方法论/ | 方法、流程、最佳实践 | `API使用实践.md` |
| 规则纪律/ | 规则、制度 | `术语定义.md`、`Workspace整洁规范.md` |
| 参考与对比/ | A vs B | `飞书-vs-企微.md` |
| 环境与社会关系/ | 环境认知 | `团队配置.md` |

**文件命名**：直接用内容名称，不用前缀。

### 3.4 分类判断标准

**核心问题**：这个内容应该放哪个文件夹？

| 判断问题 | 答案 → 文件夹 |
|---------|---------------|
| 这是"怎么做"的方法吗？ | 方法论/ |
| 这是"禁止做什么"的规则吗？ | 规则纪律/ |
| 这是工具的配置/踩坑吗？ | 工具/ |
| 这是具体人/客户的信息吗？ | 实体信息/ |
| 这是项目的设计/决策吗？ | 项目/ |
| 这是抽象的概念/定义吗？ | 知识概念/ |
| 这是A和B的比较吗？ | 参考与对比/ |
| 这是环境/团队/角色相关吗？ | 环境与社会关系/ |

**分类的思考链**：
```
这个内容是...
  → 一个方法/最佳实践？     → 方法论/
  → 一个禁止清单/规则？     → 规则纪律/
  → 一个工具的使用限制？     → 工具/
  → 一个具体的人/客户？     → 实体信息/
  → 一个项目的决策？        → 项目/
  → 一个概念/定义？         → 知识概念/
  → 一个对比分析？          → 参考与对比/
  → 一个环境/团队配置？     → 环境与社会关系/
```

### 3.5 分类决策案例

**案例1：飞书多维表API使用实践**
- 错误理解：这是"规则"，所以放规则纪律/
- 正确理解：
  - 不是"禁止做什么"的清单
  - 而是"在限制下怎么工作"的实践智慧
  - 包含踩坑后的解决方案（如用batch_create替代batch_update）
- **结论**：放方法论/，文件名改为"API使用实践"

**案例2：Agent团队协作配置**
- 思考：这是关于团队的配置（有哪些Agent、如何沟通）
- **结论**：放环境与社会关系/

**案例3：ChatERP关键设计决策**
- 思考：这是项目"ChatERP"的设计决策
- **结论**：放项目/

**案例4：飞书多维表ERP环境配置**
- 思考：这是工具"飞书多维表"的配置
- **结论**：放项目/（因为是ERP项目使用的工具配置）

### 3.6 标记规则

| 标记 | 含义 |
|------|------|
| 无标记 | 确定的知识 |
| ⚠️ 待验证 | 不确定，需要找方法/求证 |
| ❌ 已验证为错误 | 纠正后的记录 |

### 3.7 SCHEMA.md 模板

```markdown
# SCHEMA.md — Wiki 编译规则

## 页面格式规范

### entity（实体页）
```yaml
---
type: entity
subtype: customer | product | person | tool | project
created: YYYY-MM-DD
updated: YYYY-MM-DD
aliases: [别名1, 别名2]
tags: [#标签1, #标签2]
---

# 实体名称

## 基本信息
- 字段1: 值

## 环境认知（昵称/代号/角色）
## 关联记录
## 变更历史
```

### concept（概念页）
```yaml
---
type: concept
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [#标签]
---

# 概念名

## 定义
## 适用范围
## 相关概念
```

### comparison（对比页）
```yaml
---
type: comparison
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [#对比]
---

# A vs B

## 共同点
## 差异点
## 适用场景
## 决策建议
```

## raw 文件格式

### frontmatter 时间戳格式

```yaml
---
source: https://...          # 原文链接/路径
type: article | document | transcript | environment | diary
recorded: YYYY-MM-DD       # 记录时间
discussed_1st: YYYY-MM-DD # 首次讨论（可为空）
discussed_2nd:             # 再次讨论（可为空）
scheduled: YYYY-MM-DD     # 预定讨论时间（可为空）
compiled_1st: YYYY-MM-DD  # 第一次被编译时间（可为空）
compiled_2nd:              # 第二次被编译时间（可为空）
never_compiled: true      # 从未编译标注（脚本扫描用）
stop_compiling: true       # 停止编译（user/agent 认为无再次编译价值）
tags: [#标签1, #标签2]
---
```

### body 内容

- 去除杂质（网页噪音等）
- 保持干净内容

### 脚本扫描条件

| 检测条件 | 含义 |
|---------|------|
| `never_compiled: true` | 从未编译，需要处理 |
| `stop_compiling: true` | 停止编译，跳过 |
| `compiled_1st` 存在但 `compiled_2nd` 为空 | 可选第二次编译，由 Agent 判断 |
| `scheduled <= today` 且 `discussed_1st` 为空 | 预定讨论但未讨论 |

## 编译触发规则

1. raw/ 新文件进入 → LLM 读取内容 → 判断实体类型
2. 同一实体 raw 累积 ≥3 条 或 时间跨度 ≥7 天 → 触发 compile
3. 新内容与旧页面冲突 → 标记矛盾，不覆盖，等待人工确认
4. 编译完成 → 更新 index.md + log.md

## lint 检查清单

- [ ] 矛盾内容：新观点推翻旧观点但旧页面未更新
- [ ] 过时内容：判断已不适用但仍在 wiki
- [ ] 孤儿页：没有任何 wikilink 引用的页面
- [ ] 格式一致性：frontmatter 是否符合规范
- [ ] 悬空链接：wikilink 指向不存在的目标文件

### 悬空链接的处理

当 Agent 创建 wikilink `[[新概念]]` 时：

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
        ↓n后续发现相关来源 → 补充内容 + 移除标签
```

### 3.8 init 脚本要创建的文件

1. **目录**：所有上述目录
2. **SCHEMA.md**：编译规则模板
3. **index.md**：总导航模板
4. **log.md**：操作日志初始页

---

## 四、远期实现（待规划）

### 4.1 compile 命令

触发 LLM 从 raw/ 读取内容，生成/更新 wiki/ 页面。

```
输入：raw/ 下新增的文件
过程：LLM 读取 → 按 SCHEMA 生成 wiki/ 页面
输出：更新 index.md + log.md
```

### 4.2 lint 机制

定期检查矛盾/过时/孤儿页。

### 4.3 与 L3 的闭环

编译后的 wiki 页面更新 tag index，支持懒加载检索。

---

## 五、相关文档

- **SKILL.md**: `~/.openclaw/skills/obsidian-wiki-init/SKILL.md`（使用规范，已同步最终设计）
- **OBheartbeat.json**: `~/.openclaw/skills/obsidian-wiki-init/OBheartbeat.json`（扫描配置，最终设计契约）
- Mauto 设计: `/Volumes/Binary HD/claw/mission/Xiaoxian/研究/mauto-importance-design.md`

---

## 六、注意事项

1. 这是给 Agent 用的知识库，不是给人类
2. 存储稳定信息，不存储瞬时状态
3. 参考 karpathy 的 LLM Wiki 模式，但适配我们自己的体系
4. 命名和格式保持一致，方便 LLM 检索和理解
5. **最终设计以上面两份文件（SKILL.md + OBheartbeat.json）为准**

---

## 附录：Obsidian 核心插件配置历史

> 2026-05-09 小娴与 Binary 逐一讨论确认
> 配置已固化到 `init_vault.py`，创建 vault 时自动生效

### 讨论结论

**Agent 相关插件**：
- canvas 关闭（空间布局 Agent 无法解析）
- daily-notes 关闭（与 Memory L1 独立，避免混乱）
- zk-prefixer 关闭（Agent 直接写文件）
- templates 关闭（Agent 直接生成内容）
- markdown-importer 关闭（一次性工具，需要时手动开启）
- publish 关闭（Agent 不涉及发布）
- sync 关闭（使用 iCloud/本地存储）
- note-composer 开启，`askBeforeMerging: false`，`extractBehavior: "link"`
- tag-pane/outline/backlink/outgoing-link/workspaces/file-recovery 保持开启
- bases 开启（资源占用低，未来可能有用）

**note-composer 配置理由**：
- `extractBehavior: "link"` — 链接到新笔记优于插入存放，原文干净语义清晰，Agent 处理时上下文更少
- `askBeforeMerging: false` — 避免交互阻塞

**纯 UI 层插件**：不影响 Agent，人类自行决定开/关

### 配置文件位置

- `core-plugins.json` — 插件开关
- `note-composer.json` — 合并提示/Extract 行为
- `app.json` — 链接格式、新文件位置、附件路径

---

## 七、核心运作原则

### 7.1 先记录，后整理

> 重要原则：不要等完全理解才开始记。
> Agent 在工作/讨论中感知到有价值的内容 → 立即写入 raw/
> 后续 LLM 编译/提炼/结构化

**INGEST 的来源不只是文件：**

| 来源 | 形式 |
|------|------|
| 文档/文章 | 文件丢到 raw/ |
| 对话讨论 | 会话中提取有价值的内容 |
| 工作发现 | Agent 实时写入 |
| 用户反馈 | 纠正 → 规则 |

> 核心就是：Agent 在工作中持续感知和提取有价值的内容，不管来源是什么。

### 7.2 好答案归档

> 重要原则：好的回答不应该只在 chat 里消失。
> 讨论/查询产生的好答案 → 归档到 wiki/知识概念/

**QUERY 工作流：**
1. 问问题
2. LLM 回答
3. 判断答案是否有价值
4. 有价值 → 归档到知识概念/ → 变成 wiki 的一部分

> 这样探索的结果和知识一样会 compounding（复利积累）。

### 7.3 设计原则总结

| 原则 | 说明 |
|------|------|
| 先记录，后整理 | 有价值的内容先写，后续编译 |
| 好答案归档 | 不是只在 chat 里回复，要存 wiki |
| 不只是文件 | 对话、工作、讨论都是来源 |

---

## 八、业务表结构（TS 场景）

> ⚠️ **待后期完善** — 当前设计不成熟，暂不纳入实现范围

### 核心原则

| 内容 | 存哪 | 原因 |
|------|------|------|
| 表结构/字段 | Wiki | 稳定 |
| 具体数据 | 多维表/Memory | 动态 |

### 示例


---

> **以下为历史讨论内容，最终设计以 OBheartbeat.json 为准**

## 九、周期检查机制（heartbeat 历史方案）

> 最终方案见：`~/.openclaw/skills/obsidian-wiki-init/OBheartbeat.json`

### 9.1 检查项（历史参考）

| 检查项 | 触发条件 | 行为 |
|--------|---------|------|
| raw 未讨论内容 | raw/ 中存在 `discussed_1st` 为空的文件 | 提醒用户查看 |
| scheduled 到期 | raw/ 中 `scheduled` 字段 ≤ 今天 | 提醒用户讨论 |
| MEMORY.md 体积 | MEMORY.md 行数超过阈值（建议 350 行） | 建议迁移到 wiki |
| Wiki 健康检查 | wiki/ 中孤儿页、悬空链接、过时内容 | 报告问题 |

### 9.2 heartbeat.json 建议格式（历史参考）

> 已废弃，最终版本见 OBheartbeat.json

---

## 十、compile 脚本设计（已废弃）

> **⚠️ 本章节内容已被最终决策取代**
> 
> **最终决策**：compile 必须由 Agent 执行，不能脚本自动处理。
> - 原因：涉及语义理解、多类别分类和知识网络维护，需要 Agent 的推理能力
> - 脚本只负责扫描发现和提醒（见 OBheartbeat.json）
> - compile_pipeline 见 SKILL.md

---

## 十一、lint 检查实施（与 OBheartbeat 同步）

> 最终设计见：`~/.openclaw/skills/obsidian-wiki-init/OBheartbeat.json`
> 
> 以下为历史讨论中的伪代码参考，已同步到 OBheartbeat.json 的 `lint_state` 和 `auto_fix`：

### 11.1 检查项（历史参考，已同步）

| 检查项 | 检测方法 | 处理方式 |
|--------|---------|---------|
| 孤儿页 | 扫描 wiki/ 所有文件，统计入链/出链 | 报告无引用的页面 |
| 悬空链接 | 正则匹配 `[[链接]]`，检查目标是否存在 | 报告不存在的链接目标 |
| 过时内容 | 比较 `updated` 字段与当前日期 | 超过 90 天未更新的页面提醒 |
| 格式一致性 | 检查 frontmatter 完整性 | 报告缺失字段 |

### 11.2 触发周期（历史参考，已同步）

**建议**：Heartbeat 每次统一检查，轻量扫描。

### 11.3 伪代码示例（参考实现）

```python
def lint_vault(vault_path):
    # 1. 扫描所有 wiki/ 文件
    # 2. 构建链接图谱（入链/出链）
    # 3. 检测孤儿页（入链=0）
    # 4. 检测悬空链接（目标不存在）
    # 5. 检测过时内容（updated > 90天）
    # 6. 生成报告
    return report
```

> 以上伪代码的完整实现和状态追踪机制已同步到 OBheartbeat.json 的 `lint_state` 和 `auto_fix` 字段。

---

> 以上为小娴与 Binary 截至 2026-04-21 的历史讨论成果。**最终设计以 OBheartbeat.json 为准**。Mautoer 实现时请结合完整资料自主设计。

---

## 附录：Obsidian 核心插件配置历史

> 2026-05-09 小娴与 Binary 逐一讨论确认
> 配置已固化到 `init_vault.py`，创建 vault 时自动生效

### 讨论结论

**Agent 相关插件**：
- canvas 关闭（空间布局 Agent 无法解析）
- daily-notes 关闭（与 Memory L1 独立，避免混乱）
- zk-prefixer 关闭（Agent 直接写文件）
- templates 关闭（Agent 直接生成内容）
- markdown-importer 关闭（一次性工具，需要时手动开启）
- publish 关闭（Agent 不涉及发布）
- sync 关闭（使用 iCloud/本地存储）
- note-composer 开启，`askBeforeMerging: false`，`extractBehavior: "link"`
- tag-pane/outline/backlink/outgoing-link/workspaces/file-recovery 保持开启
- bases 开启（资源占用低，未来可能有用）

**note-composer 配置理由**：
- `extractBehavior: "link"` — 链接到新笔记优于插入存放，原文干净语义清晰，Agent 处理时上下文更少
- `askBeforeMerging: false` — 避免交互阻塞

**纯 UI 层插件**：不影响 Agent，人类自行决定开/关

### 配置文件位置

- `core-plugins.json` — 插件开关
- `note-composer.json` — 合并提示/Extract 行为
- `app.json` — 链接格式、新文件位置、附件路径
