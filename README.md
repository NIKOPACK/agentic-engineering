# Agentic Engineering

一套面向 AI 编码智能体的开发规范和配套工具，同时适配 **Codex**、**Claude Code** 和 **pi**，覆盖 **TypeScript/Node**、**Python** 和 **Go** 三个技术栈。

核心思路：**人定义“做完”的标准并做最终审核，智能体在规格、测试和护栏组成的约束内完成实现。** 背景和依据见 [docs/background.md](docs/background.md)。

## 包含什么

| 组成 | 作用 | 位置 |
| --- | --- | --- |
| 开发规范 | 流程、上下文工程、验证、Git、安全 | [`docs/standards/`](docs/standards) |
| 技术栈指南 | 各语言的工具选择、命令和约定 | [`docs/stacks/`](docs/stacks) |
| AGENTS.md 模板 | 所有智能体共用的项目指令 | [`templates/common/AGENTS.md`](templates/common/AGENTS.md) |
| 5 个共享 skill | 规格先行、验证、自审、提交、接入规范 | [`agent/skills/`](agent/skills) |
| 护栏 | 拦截危险命令、密钥访问、对护栏本身的修改，三个工具共用一套规则 | [`agent/hooks/policy.py`](agent/hooks/policy.py) |
| 工具接入配置 | Codex hooks 与沙箱、Claude Code hooks、pi 扩展 | [`agent/codex/`](agent/codex)、[`agent/claude/`](agent/claude)、[`agent/pi/`](agent/pi) |
| 项目模板 | PR 模板、规格与 ADR 模板、pre-commit + gitleaks、EditorConfig | [`templates/common/`](templates/common) |
| 技术栈配置 | Biome + tsc、Ruff + mypy + pytest、golangci-lint，以及各自的 CI | [`templates/typescript/`](templates/typescript)、[`templates/python/`](templates/python)、[`templates/go/`](templates/go) |
| 安装脚本 | 把上面这些装进目标项目，不覆盖任何已有文件 | [`scripts/install.py`](scripts/install.py) |

## 快速开始

需要 Python 3.9+ 和 git。

```bash
git clone https://github.com/NIKOPACK/agentic-engineering.git ~/agentic-engineering
```

在目标项目里先预览，再安装：

```bash
python3 ~/agentic-engineering/scripts/install.py --target . --stack typescript --agents codex,claude,pi --dry-run
```

```bash
python3 ~/agentic-engineering/scripts/install.py --target . --stack typescript --agents codex,claude,pi
```

- `--stack`：`typescript`（或 `ts`）、`python`（或 `py`）、`go`，可以多选，用逗号分隔
- `--agents`：`codex`、`claude`、`pi`，默认三个都装
- `--upgrade`：只更新由本仓库管理的文件（护栏脚本、skills、pi 扩展），不动你改过的配置
- `--copy-skills`：给 Claude Code 复制 skills，而不是创建软链接（Windows 用）

**更省事的方式**：先把 `agent/skills/adopt-standards` 装到全局（见下文），然后对智能体说“用 adopt-standards 给这个项目接入开发规范”。它会先审计项目，再安装，并把 `AGENTS.md` 里的占位符换成项目真实的命令。

### 安装后的一次性操作

1. 把 `AGENTS.md` 里的 `<占位符>` 换成项目真实的命令，每条都实际跑一次
2. 运行 `pre-commit install`
3. **Codex**：信任这个项目，然后在 CLI 里用 `/hooks` 审核并信任护栏 hook
4. **Claude Code**：首次启动时批准项目的 hooks（可以用 `/hooks` 查看）
5. **pi**：扩展会从 `.pi/extensions/` 自动加载；如果会话已经在运行，执行 `/reload`

## 安装后的项目结构

```text
your-project/
├── AGENTS.md                      # 项目指令（Codex、pi 直接读取）
├── CLAUDE.md                      # 内容是 @AGENTS.md（Claude Code 读取）
├── .agents/
│   ├── hooks/policy.py            # 共享护栏
│   ├── policy.json                # 护栏的项目配置（只能由人修改）
│   └── skills/                    # 共享 skills（Codex、pi 直接发现）
├── .claude/
│   ├── settings.json              # PreToolUse hook → policy.py
│   └── skills/*                   # 软链接到 .agents/skills/*
├── .codex/
│   ├── config.toml                # 沙箱：workspace-write，按需审批
│   └── hooks.json                 # PreToolUse hook → policy.py
├── .pi/extensions/agent-policy.ts # tool_call 拦截 → policy.py
├── .github/
│   ├── pull_request_template.md
│   └── workflows/                 # quality.yml + ci-<stack>.yml
├── docs/specs/_template.md
├── docs/adr/0000-template.md
├── .pre-commit-config.yaml        # 通用检查 + gitleaks
└── .editorconfig、biome.json、ruff.toml、.golangci.yml 等
```

## Skills

| Skill | 用途 |
| --- | --- |
| [`spec-first`](agent/skills/spec-first/SKILL.md) | 非平凡改动先写规格和可验证的验收标准，确认后再实现 |
| [`verify-change`](agent/skills/verify-change/SKILL.md) | 运行项目真实的检查（包括 UI 验证），给出验证证据 |
| [`self-review`](agent/skills/self-review/SKILL.md) | 交付前审查自己的 diff：正确性、测试、安全、范围 |
| [`ship-change`](agent/skills/ship-change/SKILL.md) | 功能分支 + Conventional Commits + PR 模板 |
| [`adopt-standards`](agent/skills/adopt-standards/SKILL.md) | 审计项目并接入本规范 |

只想全局安装 skills、不改项目时，可以把它们链接到各工具的用户级目录：

```bash
mkdir -p ~/.agents/skills && ln -s ~/agentic-engineering/agent/skills/* ~/.agents/skills/
```

```bash
mkdir -p ~/.claude/skills && ln -s ~/agentic-engineering/agent/skills/* ~/.claude/skills/
```

Codex 和 pi 都会读取 `~/.agents/skills/`，Claude Code 读取 `~/.claude/skills/`。

## 护栏

`policy.py` 在每次工具调用之前运行，拦截下面这些操作：删除根目录或项目目录、强制推送、直接推送 `main`、`--no-verify`、丢弃未提交的改动、`curl | sh`、访问 `.env` 和密钥文件、破坏磁盘、修改护栏本身。完整的规则表和配置方法见 [05 安全](docs/standards/05-security.md)。

## 维护本仓库

```bash
make check
```

这条命令会依次运行：校验配置与 skill 格式、Ruff、mypy（严格模式）、单元测试。`make check` 需要 [uv](https://docs.astral.sh/uv/) 和 Python 3.11+。贡献规则见 [AGENTS.md](AGENTS.md)。

## 许可证

[MIT](LICENSE)
