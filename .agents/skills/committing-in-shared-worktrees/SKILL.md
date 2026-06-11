---
name: committing-in-shared-worktrees
description: Use before any git add/commit in the main G:\Werewolf-agent checkout, when a commit landed on the wrong branch, when unexpected files appear in a commit, or when starting multi-step implementation work.
---

# 共享工作树提交纪律(多 Claude 并行)

## 背景

用户常开多个 AI 会话并行作业于**同一个 checkout**:分支、index、未跟踪文件全是共享可变状态。两类真实事故都发生过:

1. 写作期间对方把工作树切到别的分支 → 我的 commit 落到对方分支顶上。
2. 对方 stage 了文件没提交 → 我的 `git add <单文件> && git commit` 把整个 index(含对方 18 个 `.runs/` 残留)扫进了我的提交。`git commit` 提交的是**整个 index**,不只是刚 add 的文件。

## commit 前两查(每次,无例外)

```bash
git branch --show-current   # 还在自己以为的分支上吗
git status --short          # 有非本任务的 staged(左列非空)项吗 → 有就停下报告,不提交
```

## 隔离规则

- 执行多步实现计划**一律开隔离 worktree**(superpowers:using-git-worktrees),不在共享主树上跑 subagent。worktree 隔离的批次零事故,共享主树的批次出过事。
- Windows 删 worktree:先 `cd` 出来再删(否则 Permission denied),残留用 `git worktree prune`。

## 修复手法(已验证)

- **commit 落错分支**:不要 reset 对方活跃分支。`git worktree add <tmp> main` + cherry-pick 把 commit 补回 main,删临时 worktree。
- **脏提交(扫进残留)**:从 main 重建干净分支逐个 cherry-pick;脏的用 `cherry-pick -n` + `git restore --staged <脏路径>` 剥离;最后 `git diff 旧分支 新分支 --name-only` 证明差异恰好 = 剥离物。
- 跨线合并不抢 checkout:`git fetch . <branch>:main`;跨线删分支先 `git merge-base --is-ancestor` 验证再 `-D`。

## 误读陷阱

`git log A...B`(三点)是**对称差**,会把对方侧提交也列出来,别误判成自己分支的内容;看父链用 `git rev-list --parents`。
