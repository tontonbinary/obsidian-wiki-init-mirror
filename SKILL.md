---
name: obsidian-wiki-init
description: |
  Create a new Obsidian vault with LLM Wiki-inspired structure for Agent knowledge management.
  Triggers when:
  - User says "帮我建一个知识库"、"创建 Obsidian vault"、"初始化知识库"
  - An agent needs to set up its own knowledge base
  - Onboarding a new Agent that needs a wiki knowledge base

  Formerly known as "obsidian-vault-init", upgraded with LLM Wiki principles.

variables:
  SKILL_DIR: ~/.openclaw/skills/obsidian-wiki-init
---

# Wiki Vault Init

为 Agent 创建标准化的 LLM Wiki 结构知识库。

## 核心定位

**Wiki Vault 是 Agent 的外部知识库，不是 Agent 的记忆。**

- 存储：稳定信息（世界知识/周期性规律/环境认知）
- 不存储：瞬时状态，项目当前进度（这些放 MEMORY.md，时效后 auto-dream 忘却）

## ⚠️ 强制流程

### 讨论时必须按完整流程执行

**⚠️ 禁止只讨论不执行。讨论过程中要按流程运行脚本。**

完整流程见 `schema-discussion-guide.md`，核心步骤：

1. **讨论前**：告知用户讨论时长
2. **讨论 Q1-Q2 后**：立即运行 `init_vault.py` 创建基础目录
3. **讨论过程中**：可以运行 `activate.py` 注册 heartbeat
4. **讨论中边讨论边填**：每项确认后立即填入 SCHEMA.md（不要等全部讨论完再填）

**示例：**

> "Q1 和 Q2 讨论完了，我现在运行 init_vault.py 创建 vault 目录。"
> ```bash
> python3 $SKILL_DIR/scripts/init_vault.py Mautoer "/Volumes/Binary HD/obsidian/Mautoer"
> ```

---

### Wiki 编译规则

1. **必须写 source frontmatter** — 编译 raw → wiki 时，必须写 `source: <原始文件路径>`
2. **Raw 最少保留 7 天** — 编译后不可立即删除 raw 文件
3. **违规后果** — 漏写 source 或提前删除 raw 会被 Lint 检测并报错
4. **compile 前必须读** — 执行 compile 前必须先读：
   - `references/wiki-index-format.md` — 索引格式规范
   - `references/compile-pipeline.md` — 完整编译流程

### ⚠️ MEMORY.md 不适合提取到 Wiki 的内容

以下内容**留在 MEMORY.md**，不提取到 Obsidian wiki：

| 内容类型 | 原因 | 示例 |
|---------|------|------|
| **高频使用的工具配置** | 几乎每天用，需要快速访问 | 飞书 API Token、GitHub 凭据、MiniMax Key |
| **当前会话状态** | 瞬时信息，时效性强 | 当前任务进度、pending queue |
| **用户偏好设置** | 随时可能变更 | 工作风格、沟通偏好 |
| **可通过脚本获取的信息** | 不需要记忆，有脚本即可 | clean_session 路径、版本号 |

**判断标准：**
- 这条信息是**高频使用**的吗？（每天用几次）
- 这条信息是**当前状态**吗？（随时变化）
- 这条信息是**工具配置**吗？（坏了查官方文档就好）

→ 以上情况 → **留在 MEMORY.md，不提取**

**适合提取到 wiki 的：**
- 设计决策（项目规则、架构选择）
- 踩坑记录（已验证的错误）
- 稳定知识（不常变）
- 人/客户信息（具体存在）

### 📌 什么时候应该从 MEMORY.md 提取到 Wiki

**触发条件（满足任一即应考虑提取）：**

| 触发条件 | 说明 |
|---------|------|
| **MEMORY.md 超过 350 行** | 记忆太满，建议迁移稳定信息到 wiki |
| **设计决策已确认** | 项目规则、架构选择等稳定信息 |
| **踩坑已验证修复** | 错误已修复，记录下来避免再踩 |
| **用户主动提供资料** | 用户发来的文章/文档需要整理 |
| **讨论中确认的规则** | 逐条讨论后确认的决策 |

**提取流程：**
1. 判断是否值得提取（不是高频使用/不是当前状态）
2. **复写到 raw/日记/**（MEMORY.md 原内容保留，加标注）
3. 与用户讨论确认（discussed_1st）
4. **编译到 wiki**（MEMORY.md 原内容替换为检索指针）

### 📌 来源与 Wiki 的同步规则

**⚠️ 以下来源文件必须遵守操作规则：**

| 路径 | 用途 |
|------|------|
| `~/.openclaw/shared/board/` | board 公告 |
| `~/.openclaw/shared/SharedMemory/` | 共享 memory |
| `~/.openclaw/workspaces/<agent>/workspace/memory/MEMORY.md` | Agent 长期记忆 |
| `~/.openclaw/workspaces/<agent>/workspace/memory/TOOLS.md` | 工具配置 |
| `~/.openclaw/workspaces/<agent>/workspace/memory/USER.md` | 用户信息 |

**操作规则：**

**复写到 raw 时（未编译到 wiki）：**
- 来源文件**原内容保留**，不删除
- 加标注：`→ raw/<类型>/xxx.md`（根据内容类型选择 raw/ 下的文件夹）
- 退回时：**去掉标注**，原内容不变

**编译到 wiki 时（已完成）：**
- 来源文件原内容**替换为检索指针**
- 格式：`详见 [[wiki/xxx.md]]`
- **同时保留 wikilink 作为检索入口**

**raw/ 分类参考：**
- `raw/日记/` — MEMORY.md 迁移内容（工作日志、决策、踩坑）
- `raw/环境认知/` — TOOLS.md 内容（工具配置、环境设置）
- `raw/实体信息/` — USER.md 内容（用户信息、联系人）

---

### 第一步：检查 vault SCHEMA.md

**任何操作前，Agent 必须先读 vault 的 SCHEMA.md：**

```bash
cat {vault}/SCHEMA.md
```

### 第二步：根据情况处理

| 情况 | Agent 动作 |
|------|---------|
| SCHEMA.md 存在且已完成（✅） | 按其规则操作 |
| SCHEMA.md 存在但未完成（🟡） | 继续完成讨论 |
| SCHEMA.md 不存在 | **读取 schema-discussion-guide.md，按 Q1-Q5 完整讨论流程创建** |

---

## 使用方式

### 初始化 Vault

```bash
python3 $SKILL_DIR/scripts/init_vault.py <vault-name> <vault-path>
```

### 激活 Heartbeat

```bash
python3 $SKILL_DIR/scripts/activate.py <vault-path> [agent-name]
```

### OBHeartbeat 扫描

```bash
# 完整扫描（checks + lint）
python3 -m obheartbeat scan <vault-path> [--json]

# 仅执行 wiki lint
python3 -m obheartbeat lint <vault-path> [--json]

# 仅执行 raw/ checks
python3 -m obheartbeat check <vault-path> [--check-id <check_id>] [--json]
```

---

## ⚠️ 操作规程

### 批量重构前手动触发快照备份

**规则**：Agent 执行批量笔记重构前，**必须**手动触发一次 File Recovery 快照备份。

**原因**：
- 批量操作（移动、合并、重命名笔记）风险高，一旦出错影响面广
- File Recovery 是"后悔药"机制，有快照才能回滚
- 符合"不可逆操作前先备份"的责任心原则

**操作方式**：
- Obsidian 自动快照间隔为 5 分钟（默认值）
- 批量重构前，Agent 可通过操作确保最新状态已被快照捕获
- 或等待一个快照周期（5分钟）后再执行批量操作

**记录位置**：此规则属于 skill 使用者须知，记在 skill.md（本文档）而非 SCHEMA.md。

---

## vault SCHEMA.md

vault 的 SCHEMA.md 是该 vault 的"宪法"，包含：
- Vault 定位和知识边界
- raw/ 和 wiki/ 的具体分类
- 命名规范
- 编译触发规则（与默认的差异）
- 页面格式模板
- frontmatter 格式

### SCHEMA.md 操作场景

| 场景 | 操作方式 |
|------|---------|
| **首次创建 SCHEMA** | 读取 schema-discussion-guide.md，按 Q1-Q5 完整讨论流程执行（15-45 分钟） |
| **后续小调整**（加分类、调规则等） | 直接修改 SCHEMA.md，不需要重读讨论指南 |
| **SCHEMA 存在但未完成**（🟡） | 继续完成讨论，按进度接着走 |

> ⚠️ schema-discussion-guide.md 的完整流程（讨论 Q1-Q5、init_vault.py、activate.py）**仅限首次创建 SCHEMA 时使用**。后续调整无需重复讨论。

---

## AGENTS.md 约定

使用本 skill 的 Agent 需要在生产时更新自己的 AGENTS.md，添加以下约定：

### 收到 OBHeartbeat 通知后的标准动作

| 通知类型 | Agent 动作 |
|---------|---------|
| **batch_compile_folder** | 创建/更新 wiki 页面 |
| **batch_compile_7days** | 创建/更新 wiki 页面 |
| **scheduled_pending** | 判断项目是否完成，决定讨论或延期 |
| **optional_recompile** | 判断是否有价值 |
| **undiscussed_raw** | 找用户讨论 |
| **memory_to_wiki_extract** | 从 MEMORY.md 提取到 wiki |
| **low_confidence** | 验证不确定的内容（confidence <80） |
| **missing_source** | 为 wiki 页面补充 source frontmatter |
| **ready_to_compile** | 确认无误后编译 confidence ≥80 的 raw |
| **wiki_lint** | 修复孤儿页、悬空链接、空页面、过时内容 |

---

## 相关文档

| 文档 | 作用 |
|------|------|
| schema-discussion-guide.md | **SCHEMA.md 讨论指南（含完整流程）** |
| OBheartbeat.json | 7项P0检查完整定义 |
| design-document.md | 完整设计方案 |

---

## Obsidian 核心插件配置标准

> ⚠️ **本配置已固化到 `init_vault.py`** — 创建 vault 时自动生效，无需手动配置。
> 2026-05-09 小娴与 Binary 逐一讨论确认。

创建 vault 时，`init_vault.py` 会自动写入 `.obsidian/` 配置。以下是 Agent 相关插件的开/关规则：

### Agent 必须关注的插件（已固化到 init_vault.py）

| 插件 | 状态 | 原因 |
|------|------|------|
| backlink | ✅ 开启 | 双链核心，Agent 解析入链 |
| outgoing-link | ✅ 开启 | 双链核心，Agent 解析出链 |
| note-composer | ✅ 开启 | 合并/拆分笔记，`askBeforeMerging: false` |
| tag-pane | ✅ 保持 | Agent 可用 frontmatter/tags |
| outline | ✅ 保持 | 语义层有价值 |
| workspaces | ✅ 保持 | 多工作区 |
| file-recovery | ✅ 保持 | 批量重构前手动触发快照 |
| bases | ✅ 开启 | 资源占用低，未来可能有用 |

### Agent 无关的插件（已关闭）

| 插件 | 状态 | 原因 |
|------|------|------|
| canvas | ❌ 关闭 | 空间布局 Agent 无法解析 |
| daily-notes | ❌ 关闭 | 与 Memory L1 独立，避免混乱 |
| zk-prefixer | ❌ 关闭 | Agent 直接写文件，不需要 |
| templates | ❌ 关闭 | Agent 直接生成内容，不需要 |
| markdown-importer | ❌ 关闭 | 一次性导入工具，需要时手动开启 |
| publish | ❌ 关闭 | Agent 不涉及发布 |
| sync | ❌ 关闭 | 使用 iCloud/本地存储 |

### 纯 UI 层插件（人类自行决定）

bookmarks, quick-switcher, command-palette, slash-commands, search, graph-view, page-preview, word-count, web-viewer, audio-recorder, slides, random-note, file-explorer — 不影响 Agent 使用。

### 配置文件位置

- `core-plugins.json` — 插件开关
- `note-composer.json` — 合并提示/Extract 行为（`extractBehavior: "link"`）
- `app.json` — 链接格式（`useWikiLinks: true`）、新文件位置（`raw/`）、附件路径（`outputs/`）

### note-composer 配置理由

- `extractBehavior: "link"` — 链接到新笔记优于插入存放，原文干净语义清晰，Agent 处理时上下文更少
- `askBeforeMerging: false` — 避免交互阻塞

---

## 文件操作规范

### 删除文件前必须检查引用

**规则**：Agent 删除任何 `.md` 文件前，**必须**先检查是否有其他文件引用该文件。

**原因**：
- Obsidian 不会自动删除引用，链接会变为"悬空链接"
- 悬空链接会导致 lint 报错，影响 Wiki 健康度
- 提前检查可以避免后续修复成本

**操作步骤**：
1. 搜索引用：`grep -r "\[\[文件名\]\]" wiki/ raw/`
2. 判断处理方式：
   - 引用文件也需要更新 → 先更新引用，再删除
   - 引用文件可以保留悬空 → 标记 `#待修复`，再删除
   - 无引用 → 直接删除
3. 记录操作到 `log.md`

**示例**：
```bash
# 检查引用
grep -r "\[\[旧笔记\]\]" wiki/ raw/

# 有引用时：更新引用文件，替换为 [[新笔记]] 或删除链接
# 然后删除文件
rm wiki/旧笔记.md

# 记录到 log.md
echo "| 2026-05-09 | 删除 | wiki/旧笔记.md（已更新引用）|" >> log.md
```

### 重命名/移动文件

**规则**：Obsidian 自动维护链接，Agent **不需要**额外操作。

**注意**：
- 确保 `app.json` 中 `alwaysUpdateLinks: true`（默认开启）
- 批量重命名时，等待 Obsidian 完成索引更新（约几秒）

---

## 前提条件

- obsidian-cli 已安装：`brew install yakitrak/yakitrak/obsidian-cli`
- 若未安装，脚本会警告但仍创建 vault 结构
