# Issue tracker: 本地文档

Issues 使用本地 Markdown 文件跟踪，存放在 `docs/agents/issues/` 目录下。

## 文件结构

```
docs/agents/issues/
├── _index.md          # 总索引，列出所有 open/closed issues
├── 001-简短标题.md     # 单个 issue
├── 002-简短标题.md
└── ...
```

## 单个 Issue 格式

```markdown
# <标题>

- **ID**: 001
- **标签**: doc-sync / bug / feature
- **优先级**: HIGH / MEDIUM / LOW
- **状态**: open / closed

## 描述

<问题描述>

## 验收标准

- [ ] <具体条件>

## 关联

- 相关 ADR: <编号>
- 阻塞: #<ID>
```

## 操作约定

- **创建 issue**: 在 `docs/agents/issues/` 下新建 `<序号>-<简短标题>.md`，并更新 `_index.md`
- **读取 issue**: 直接读取对应 `.md` 文件
- **列出 issues**: 读取 `_index.md`，或 glob `docs/agents/issues/*.md`
- **添加评论**: 在 issue 文件末尾追加 `## 评论` 段落
- **修改标签/状态**: 编辑 issue 文件的元数据行
- **关闭 issue**: 将状态改为 `closed`，在 `_index.md` 中移动到 closed 区

## 序号分配

从 `_index.md` 中读取已使用的最大序号，+1 即为新序号。

## When a skill says "publish to the issue tracker"

创建本地 issue 文件并更新 `_index.md`。

## When a skill says "fetch the relevant ticket"

读取对应的 `.md` 文件。
