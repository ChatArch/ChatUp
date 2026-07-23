# 工作区脚手架

`chatup workspace` 用于初始化 ChatArch 的人类-AI 协作工作区。这个工作区不是源码仓库本身，而是包裹源码仓库、任务记录、共享 skill 和发布产物的一层协作结构。

## 基本命令

```bash
chatup workspace default ~/Playground
```

常用选项：

```bash
chatup workspace default ~/Playground --language zh
chatup workspace default ~/Playground --with-memory --memory-source https://github.com/ChatArch/ChatMemory.git
chatup workspace default ~/Playground --dry-run
```

## 生成结构

典型结构如下：

```text
Playground/
  AGENTS.md
  TODO.md
  ARCHIVE.md
  .trash/
  projects/
  archive/
  core/
  scripts/
  skills/
  public/
```

## 目录职责

| 路径 | 职责 |
|---|---|
| `projects/` | 当前活跃任务。每个任务应有 `PRD.md` 和 `progress.md`。 |
| `archive/` | 已归档任务，通常按日期分组。 |
| `core/` | 需要修改或引用的源码仓库。 |
| `scripts/` | workspace 级维护脚本。 |
| `skills/` | 共享 skill 入口，通常来自 ChatMemory。 |
| `public/` | 对外发布或本地服务暴露的产物。 |
| `.trash/` | 软删除缓冲区。 |

## 工作约定

- 先创建或确认 project，再进行有状态的实现、调研或发布工作。
- 任务过程写入 `progress.md`；稳定需求和边界写入 `PRD.md`。
- 临时实验和原始输出放入任务内的 `playground/`，不要写到 `/tmp`。
- 需要删除或替换文件时，优先移动到就近 `.trash/`。

## 与源码仓库的关系

ChatUp 推荐把真实源码仓库放在 `core/` 下，例如：

```text
Playground/core/ChatUp
Playground/core/ChatMemory
Playground/core/ChatGH
```

任务记录仍然放在 `projects/` 中。这样可以让 PR、测试和源码变更保持在仓库里，而过程记录、报告和临时输出留在 workspace 外层。
