# 04 Git 与 PR

## 分支

- `main` 是受保护分支：只能通过 PR 合并，智能体不能直接推送（护栏会拦截）。
- 分支命名：`<type>/<short-slug>`，例如 `feat/export-csv`、`fix/login-timeout`、`docs/agents-md`。
- 一个分支只做一件事，合并后删除。

## 提交信息：Conventional Commits

```text
<type>(<scope>): <祈使句摘要，不超过 72 个字符>

<为什么要改、改了什么，每行不超过 72 个字符>

<footer：Closes #123、BREAKING CHANGE: ...，以及项目要求的 trailer>
```

| type | 用途 |
| --- | --- |
| `feat` | 新功能 |
| `fix` | 修 bug |
| `docs` | 只改文档 |
| `refactor` | 不改变行为的重构 |
| `perf` | 性能优化 |
| `test` | 只改测试 |
| `build` / `ci` | 构建系统、依赖、CI |
| `chore` | 其他杂项 |
| `revert` | 回滚 |

- 摘要用英文或中文都可以，但同一个仓库要统一。
- 无关的改动拆成不同的提交。
- 由智能体生成的提交，按工具的约定保留 `Co-Authored-By` 之类的 trailer，方便追溯。

## 暂存

- 按路径明确暂存文件。只有确认工作区里所有改动都属于本任务时，才能用 `git add -A`。
- 绝不能暂存 `.env`、密钥、凭据文件（护栏和 gitleaks 都会拦截）。

## 推送

- 首次推送：`git push -u origin <branch>`
- rebase 之后只能用 `--force-with-lease`，而且只能推到自己的分支。普通的 `--force` 会被护栏拦截。

## Pull Request

- 按 `.github/pull_request_template.md` 填写：概要、改动、验证、风险。
- **一个 PR 只关注一件事**，改动最好不超过 400 行。太大就拆开。
- 检查还在跑或者还有待决问题时，开 Draft PR。
- 验证部分必须写实际运行过的命令和结果；UI 改动要附截图。
- 只有用户要求时，智能体才创建 PR。

## 合并

- 合并前 CI 必须全部通过，并且至少有一位人类审核者批准。
- 推荐用 squash merge，PR 标题按 Conventional Commits 格式写，作为最终的提交信息。
- 建议在 GitHub 仓库设置里开启分支保护：要求 PR、要求 CI 通过、禁止强制推送。这和本地护栏形成双重保障。
