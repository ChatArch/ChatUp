# Projects

这里放当前所有实际进行中的工作。每个 project 都应该足够自洽，使执行阶段可以尽量只在该 project 内部完成。

## 什么时候新开一个 project

当前 workspace 的目录协议只有两类基本 item：Project item 和 Discussion item。二者都是 project-like 任务单元，只是处在不同状态/阶段。`projects/` 放当前活跃 Project item；`discussion/` 放需要一起消化、纠偏、分流或沉淀的 Discussion item；已完成或不活跃 item 归档到 `archive/`；软删除或无继续价值的 item 放入 `discard/`。

当一项工作有自己明确的目标、上下文和交付物时，就应该新开一个 project。例如：

- 一次调研
- 一次性开发任务
- 一个 bugfix 流
- 一个后续可能拆成多个任务的大目标

## 命名与分组规则

每个 Project item 都必须使用日期前缀：

```text
MM-DD-<project-name>
```

但规范允许更灵活的组织方式：

```text
projects/<topic>/<name>/
```

例如：

```text
projects/agent-collab/`date`-feishu-links/
projects/chatrss/`date`-topic-auth-debug/
```

建议：
- **所有具体任务单元**：统一使用 `MM-DD-<project-name>`
- **集中处理同类任务**：可以按 topic 分组，但 topic 下的具体任务仍然必须带日期前缀
- **长期主题**：可以作为 `projects/<topic>/` 分组目录存在，但它只是索引层，不是具体执行 project

## topic 分组目录的推荐写法

当你在一段时间内会集中处理同一主题下的多个子任务时，推荐使用 topic 分组：

```text
projects/<topic>/<name>/
```

推荐原则：
- `topic/` 表示一个持续主题、领域或工作束，例如 `agent-collab/`、`chatrss/`、`feishu/`
- `topic/` 根目录默认只做索引层，保持简洁；通常只保留 `README.md`、`.trash/` 和子项目目录
- `<name>/` 表示这个主题下的具体任务单元，也是实际执行单元
- 新建任务必须使用日期前缀，例如：`projects/feishu/05-25-doc-sync/`
- 不设置“长期子项目可省略日期”的例外；长期主题放在 `projects/<topic>/` 索引层，具体执行单元仍然带日期前缀

推荐示例：

```text
projects/agent-collab/data-feishu-links/
projects/agent-collab/topic-routing/
projects/feishu/05-25-doc-sync/
projects/chatrss/auth-debug/
```

不推荐：
- 为了分组而分组；如果只有一个独立任务，直接放在 `projects/MM-DD-<project-name>/` 即可
- topic 层级过深；一般保持 `projects/<topic>/<name>/` 两层就够了
- 把 topic 目录本身当作执行单元；真正执行仍应落在具体 `<name>/` 目录中
- 在 `projects/<topic>/` 根目录直接放 `reports/`、`playground/`、`reference/`、`submission/`、`leaderboard/` 这类执行产物或任务目录，造成主题根目录污染

默认先从最简单的结构开始，并按任务需求逐步补目录，而不是一开始把所有可能目录都建满：

```text
<project-root>/
  PRD.md
  progress.md
  memory.md
  .trash/
  reports/
  scripts/
  playground/
  reference/
```

其中：
- `PRD.md`、`progress.md`、`memory.md` 是 project 根目录里的控制文件
- `.trash/` 用于临时收纳待删除文件；默认先移动再清理，避免直接执行 `rm`
- 其他任务产物优先进入对应子目录，不要直接散放在 project 根目录
- `reports/`、`scripts/` 等目录按任务需要创建；不是每个 project 都必须一次性全部创建

## 文件职责

- `PRD.md`：需求、范围、约束、预期交付和完成标准
- `progress.md`：当前进展、关键决定、下一步；每次有实质动作后都应更新
- `memory.md`：局部上下文、关键文件、工作记忆
- `reports/`：报告、总结、阶段性输出；文件名应按任务命名，例如 `feishu-session-isolation-report.md`，避免直接使用泛名 `report.md`
- `scripts/`：当前 project 专属脚本；脚本名应体现用途，避免 `temp.py`、`run.sh` 这类过于模糊的命名
- `playground/`：草稿、实验、中间产物，以及项目调试临时文件；不要把这类文件写到 `/tmp`
- `reference/`：当前 project 局部参考和样例
- `.trash/`：project 内优先级最高的“软删除”缓冲区；需要删除或重构文件时，先移动到这里，确认无误后再统一处理

其中：

- `PRD.md` 是主入口
- `progress.md` 是会话连续性的主日志，优先保证最新
- `memory.md` 用于补充局部上下文
- project 根目录应尽量保持简洁，避免直接堆放报告、脚本、临时输出和杂项文件
- 删除动作默认优先采用“移动到 workspace 或 project 的 `.trash/`”而不是直接 `rm`；仅在明确确认后才做不可恢复删除

## 归档

- `projects/` 只保留当前活跃或近期仍在推进的工作
- 对明显不再活跃的 project，归档到 `../archive/YYYY-MM-DD/`；这里的 `YYYY-MM-DD` 是执行归档当天日期，不是 project 创建日期
- 归档索引写入 `../archive/index.md`，归档流程见 `../ARCHIVE.md`
- 归档不删除内容，只移动位置，并保留原 project 目录名
- 归档过程应采用“脚本筛候选 + 模型审查”的方式，而不是纯脚本盲搬

## Discussion 与 Discard

- `../discussion/` 用于 Discussion item。Discussion 是 project-like 任务单元，不是完整聊天记录转储。
- Discussion topic 使用 `MM-DD-<topic>/`，并自带 `card.md`；`card.md` 用来说明议题、收纳目标、当前判断和 `Items/` 分类逻辑。
- Discussion 也可拥有自己的 `PRD.md`、`progress.md` 和 `reports/`，用于记录需求、过程和结论。
- 被收纳的任务移动到 `discussion/MM-DD-<topic>/Items/<project-name>/`，避免同时出现在 `projects/`。
- Discussion 适合记录用户纠偏、Agent 判断修正、任务分流、以及输出到 skill/blog/infra/archive/discard 的决策。开 Discussion 时应先 review 相关 project：已有 `card.md` 的先读 card 再按需核对项目材料；没有 `card.md` 的先浏览项目材料并补一张 card，再决定是否收纳。
- Discussion 完成时，处理并清空 `Items/` 即可；具体可以归档、丢弃、拆回新 project，或在 `progress.md` / reports 中留下处理结果。Discussion 自己保留为一个普通 project-like 记录。
- `../discard/` 是软删除/回收站区域；用户明确删除或模型判断无继续价值的任务移动到这里。
- `.trash/` 仍可作为底层文件操作安全缓冲，但不作为主任务生命周期区域。

## 源码仓库访问

- 真实源码仓库默认保留在 `core/`
- 如果当前 project 需要隔离修改源码，优先从 `core/<repo-name>` 创建 Git worktree 到当前 project，例如 `git -C ../../core/ChatTool worktree add ./ChatTool <branch-name>`
- worktree 是按需行为，不作为默认模板自动生成；任务结束后清理对应 worktree
