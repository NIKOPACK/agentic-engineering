# Skills 目录

这里存放本仓库收录的所有 skill，按**分类**组织，按**预设组合（profile）**按需安装。Codex、Claude Code、pi 三个工具共用同一份 skill。

## 目录

下表由 `python3 scripts/skills.py catalog --write` 根据 [`catalog.toml`](catalog.toml) 和各 skill 的文件自动生成，请不要手动编辑。

<!-- catalog:start -->

| 分类 | 用途 | 数量 |
| --- | --- | --- |
| `workflow` 通用开发流程 | 规格、验证、审查、提交等每个项目都用得上的流程 | 4 |
| `kit` 规范接入与维护 | 接入、升级本规范；建议全局安装，不装进项目 | 1 |
| `frontend` 前端与 UI | 组件、样式、可访问性、浏览器验证 | 0 |
| `backend` 后端与 API | 接口设计、数据库、迁移、性能 | 0 |
| `testing` 测试与调试 | 测试策略、端到端测试、排查与调试 | 0 |
| `devops` 构建、部署与运维 | CI/CD、容器、云资源、监控、发布 | 0 |
| `data` 数据与 AI 应用 | 数据处理与分析、LLM 应用、提示词与评测 | 0 |
| `docs` 文档与写作 | README、API 文档、变更日志、技术方案 | 0 |
| `security` 安全 | 威胁建模、依赖审计、安全审查 | 0 |
| `stacks` 语言与框架 | 某种语言或框架的惯用法与最佳实践 | 0 |

### `workflow` 通用开发流程

| Skill | 名称 | 说明 |
| --- | --- | --- |
| [`self-review`](workflow/self-review/SKILL.md) | 自我审查 | 交付前像严格的审查者一样审查自己的 diff |
| [`ship-change`](workflow/ship-change/SKILL.md) | 提交与 PR | 按 Conventional Commits 提交并按模板创建 PR |
| [`spec-first`](workflow/spec-first/SKILL.md) | 规格先行 | 非平凡改动先写规格与验收标准，确认后再实现 |
| [`verify-change`](workflow/verify-change/SKILL.md) | 验证改动 | 运行项目真实的检查并给出验证证据 |

### `kit` 规范接入与维护

| Skill | 名称 | 说明 |
| --- | --- | --- |
| [`adopt-standards`](kit/adopt-standards/SKILL.md) | 接入开发规范 | 把 agentic-engineering 规范与工具安装到当前仓库 |

### 预设组合（profile）

| Profile | 默认安装 | 说明 | 包含 |
| --- | --- | --- | --- |
| `core` | 是 | 每个项目都装：规格先行、验证、自审、提交 | `spec-first`、`verify-change`、`self-review`、`ship-change` |
| `kit` |  | 全局安装，用来给项目接入或升级本规范 | `adopt-standards` |

<!-- catalog:end -->

## 组织方式

```text
skills/
├── catalog.toml              # 分类定义、预设组合、外部 skill 的来源
├── README.md                 # 本文件，目录表格自动生成
└── <分类>/
    └── <skill 名>/
        ├── SKILL.md          # 必需：frontmatter（name、description）+ 正文
        ├── agents/openai.yaml # 必需：中文显示名、简介、默认提示词
        ├── references/       # 可选：长篇参考资料
        ├── scripts/          # 可选：确定性操作的脚本
        └── LICENSE           # 外部 skill 必需：原许可证
```

每项信息只在一个地方维护：

| 信息 | 来源 |
| --- | --- |
| 属于哪个分类 | skill 所在的目录 |
| 名称、触发条件 | `SKILL.md` 的 frontmatter |
| 中文显示名、一句话简介 | `agents/openai.yaml` |
| 分类说明、预设组合、外部来源 | `catalog.toml` |

### 分类

分类按**用途**划分，与技术栈无关。只适用于某一种语言或框架的 skill 放进 `stacks`。还没有 skill 的分类也可以先保留在 `catalog.toml` 里。

### 预设组合（profile）

profile 是一组经常一起安装的 skill。`default = true` 的 profile（目前是 `core`）会在接入规范时自动安装，其他的按项目需要再加。一个 skill 可以属于多个 profile，也可以不属于任何 profile，单独安装。

## 按需安装

先查看有哪些 skill：

```bash
python3 scripts/skills.py list
```

**装进项目**：skill 会被复制到项目的 `.agents/skills/`，需要随项目一起提交，这样团队成员和 CI 里的智能体用的都是同一份。Claude Code 通过 `.claude/skills/` 下的软链接读取。

```bash
python3 scripts/skills.py install --target ../my-app --profile core
```

```bash
python3 scripts/skills.py install --target ../my-app --skill <skill 名>
```

**装到全局**：在用户目录（`~/.agents/skills/`、`~/.claude/skills/`）里创建指向本仓库的软链接，在本仓库执行 `git pull` 后全局 skill 会自动更新。适合跨项目使用、又不该进入项目仓库的 skill，例如 `kit` 分类。

```bash
python3 scripts/skills.py install --global --profile kit
```

**查看与维护**：

| 操作 | 命令 |
| --- | --- |
| 项目里装了哪些、是否最新 | `python3 scripts/skills.py status --target ../my-app` |
| 全局装了哪些 | `python3 scripts/skills.py status --global` |
| 更新项目里的 kit skill | `python3 scripts/skills.py install --target ../my-app --upgrade` |
| 卸载 | `python3 scripts/skills.py remove --target ../my-app --skill <名>` |

`--upgrade` 会把项目里已安装的 kit skill 替换成本仓库的最新版本。在项目里本地改过的 skill 也会被覆盖，所以需要定制时，应该改名另存为项目自己的 skill。`remove` 默认只删除和本仓库内容一致的副本，删除本地改过的副本需要加 `--force`。

## 新增 skill

1. **确认值得收录**：它解决的是一类反复出现的任务，而不是一次性的问题；现有 skill 无法覆盖；能写出明确的“何时用、何时不用”。
2. **生成骨架**：

   ```bash
   python3 scripts/skills.py new <分类> <skill 名> --display-name "<中文名>" --short-description "<一句话简介>"
   ```

3. **编写内容**：按 [02 上下文工程](../docs/standards/02-context.md#skill-写作规范) 的要求编写 `SKILL.md`。正文用英文写，`agents/openai.yaml` 里的显示内容用中文。
4. **归入 profile**（可选）：把它加到 `catalog.toml` 里合适的 profile。只有确实每个项目都需要的 skill，才能放进 `core`。
5. **更新目录并检查**：

   ```bash
   python3 scripts/skills.py catalog --write
   ```

   ```bash
   make check
   ```

6. **实际试用**：至少在一个真实项目里，用一种智能体跑一遍，确认它会在该触发的时候被触发，并且能产出预期的结果。
7. **提交**：在功能分支上提交，提交信息写成 `feat(skills): add <name>`。

### 收录外部 skill

1. 把 skill 目录原样复制到对应的分类下，**保留它的 LICENSE 文件**。
2. 在 `catalog.toml` 里登记来源和许可证，`source` 最好指向某个固定的 commit：

   ```toml
   [skills.some-skill]
   source = "https://github.com/owner/repo/tree/<commit>/skills/some-skill"
   license = "Apache-2.0"
   ```

3. 检查许可证是否允许再分发，然后通读全部内容，包括 `scripts/`：skill 会被智能体执行，相当于运行别人的代码。
4. 补上 `agents/openai.yaml`；`name` 或目录名不符合规范时要改名。之后按上面第 5 步到第 7 步操作。

### 命名

- 用小写字母、数字和连字符，不超过 64 个字符。名字要说明这个 skill **做什么**，例如 `verify-change`，不要用 `helper`、`utils` 这类泛泛的名字。
- 所有分类里的 skill 名必须唯一，因为安装后它们会放在同一个目录里。
- 避免和工具的内置命令重名，例如 Claude Code 自带的 `code-review`、`init`。

### 移动和删除

- **换分类**：用 `git mv` 移动目录，然后运行 `catalog --write`。已经安装的项目不受影响，因为安装后的目录只按 skill 名组织。
- **删除**：先从所有 profile 里去掉，再删除目录，并在提交信息里说明替代方案。已经装进项目的副本不会被自动删除，需要在各项目里运行 `skills.py remove`。
