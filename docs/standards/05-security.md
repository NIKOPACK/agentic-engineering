# 05 安全与护栏

AI 生成的代码有相当比例存在安全问题，近两年由 AI 编码工具引入的 CVE 增长很快（数据见[背景](../background.md)）。所以安全要靠**确定性的机制**兜底，不能只靠提示词。

## 三道防线

1. **本地护栏**（`.agents/hooks/policy.py`）：在智能体执行工具调用之前拦截危险操作。Codex、Claude Code、pi 共用同一份规则。
2. **提交前检查**（pre-commit + gitleaks）：在提交时扫描密钥、私钥和大文件。
3. **CI 与分支保护**：合并前再跑一次所有检查，并且禁止直接推送和强制推送 `main`。

## 护栏规则

| 规则 ID | 拦截什么 | 应该怎么做 |
| --- | --- | --- |
| `rm-root` | `rm -r` 删除根目录、家目录、项目根目录（`/`、`~`、`.`、`*`） | 删除具体的子目录 |
| `force-push` | `git push --force`、`-f`、`+refspec`；对受保护分支的任何强制推送 | 在自己的分支上用 `--force-with-lease` |
| `direct-push` | 直接推送到受保护分支（默认是 `main`、`master`） | 推功能分支，开 PR |
| `no-verify` | `git commit/push --no-verify`、`git commit -n` | 修复 hook 报出的问题 |
| `discard-work` | `git reset --hard`、`git clean -f`、`git checkout .`、`git restore .` | 用 `git stash`，或者先问用户 |
| `pipe-to-shell` | `curl ... \| sh`、`bash <(curl ...)` | 先下载、检查内容，再执行 |
| `secret-file` | 读、写、复制、暂存 `.env*`（`.env.example` 等示例文件除外）、私钥、云凭据 | 用 `.env.example` 说明需要哪些变量 |
| `disk-destroy` | `mkfs`、`dd of=/dev/...`、写入裸磁盘设备、fork 炸弹 | 这些永远不是智能体该做的事 |
| `chmod-777` | 递归设置全局可写权限 | 只授予需要的最小权限 |
| `guard-tamper` | 智能体通过编辑工具修改护栏本身（`.agents/hooks/`、`.agents/policy.json`、`.codex/`、`.claude/settings.json`、`.pi/extensions/agent-policy.ts`） | 由用户自己修改 |

操作被拦截时，智能体会收到 `[agent-policy:<规则 ID>]` 开头的说明。**智能体不能换个写法绕过拦截**，应该把情况告诉用户，由用户决定。

### 按项目调整

在 `.agents/policy.json` 里配置（这个文件只能由用户修改）：

```json
{
  "protected_branches": ["main", "master", "release"],
  "disabled_rules": ["discard-work"],
  "extra_secret_patterns": ["(^|/)config/master\\.key$"]
}
```

### 设计取舍

- **失败放行**：护栏脚本自己出错时（比如输入格式异常），会放行这次调用并打印警告，不会把会话卡死。它是一层额外的保护，不能替代沙箱和代码审查。
- **只用标准库**：护栏只需要 Python 3.9+，不依赖任何第三方包（安装和管理脚本需要 3.11+）。
- **规则有测试**：每条规则在 `tests/test_policy.py` 里都有“应拦截”和“应放行”两类用例。修改规则时，两类用例都要补。

## 沙箱与权限

- **Codex**：`.codex/config.toml` 默认配置为 `sandbox_mode = "workspace-write"`、`approval_policy = "on-request"`，并且关闭网络。需要联网时会弹出审批。不要在本地用 `danger-full-access`。
- **Claude Code**：使用默认的权限模式。不要在本地开启 `bypassPermissions`。只在隔离的容器或云端环境里放开权限。
- **pi**：pi 默认不弹权限确认，工具直接在本机执行，护栏扩展是主要的拦截手段。处理不可信的仓库时，要在容器里运行。

## 编码安全要求

- **密钥**：不要写进代码、日志、测试数据或提交信息。用环境变量或密钥管理服务，并在 `.env.example` 里列出需要的变量名。
- **输入**：所有外部输入都要校验。SQL 用参数化查询，拼接 shell 命令和文件路径时不能直接使用原始输入。
- **依赖**：只在确实需要时新增依赖。选维护活跃的包，提交锁文件。CI 里要有漏洞扫描（Go 用 `govulncheck`；Node 用 `npm audit`；Python 可以用 `pip-audit`）。
- **Ruff 的 `S` 规则**（基于 bandit）和 golangci-lint 的 `gosec` 已经在模板里开启。
- 研究发现，明确要求智能体遵循安全编码实践，就能明显降低生成代码的漏洞率。所以 `self-review` skill 里专门设了一组安全检查项。
