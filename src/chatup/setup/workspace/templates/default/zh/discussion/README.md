# Discussion

`discussion/` 用于需要一起消化、纠偏、分流或沉淀的 Discussion item。

## 什么时候新开 Discussion

当多个 Project item 或材料需要被一起 review、归类、纠偏、分流，或输出到 skill/blog/infra/archive/discard 时，新建：

```text
discussion/MM-DD-<topic>/
  card.md
  PRD.md
  progress.md
  reports/
  Items/
```

## card.md

Discussion 自带 `card.md`。它用来说明：

- 这个 Discussion 在讨论什么议题
- 为什么这些 items 被放在一起
- 当前判断是什么
- `Items/` 里的材料如何分类
- 下一步应该如何处理

## Review 流程

1. 先列出候选相关 items。
2. 已有 `card.md` 的 item，先读 card，再按需核对项目材料。
3. 没有 `card.md` 的 item，先浏览 `PRD.md`、`progress.md`、reports 和关键文件，再补一张简洁 card。
4. 写或更新 Discussion 自己的 `card.md`，说明议题、收纳目标、item 分组、当前判断和下一步。
5. review 确认后，再把被收纳 items 放入 `Items/`。

## 收尾

Discussion 完成时，处理并清空 `Items/`。具体 items 可以归档、丢弃、拆回新 Project，或在 `progress.md` / reports 中留下处理结果。
