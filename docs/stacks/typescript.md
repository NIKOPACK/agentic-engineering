# TypeScript / Node

## 工具选择

| 用途 | 工具 | 配置文件 |
| --- | --- | --- |
| 格式化 + lint + 整理 import | [Biome](https://biomejs.dev/)（一个工具替代 ESLint 和 Prettier） | `biome.json` |
| 类型检查 | `tsc --noEmit`，开启严格模式 | `tsconfig.json` |
| 测试 | [Vitest](https://vitest.dev/)（零配置即可使用） | 按需添加 `vitest.config.ts` |
| 浏览器验证 | [Playwright](https://playwright.dev/) | 按需添加 `playwright.config.ts` |
| CI | GitHub Actions | `.github/workflows/ci-typescript.yml` |

**已经在用 ESLint 或 Prettier 的项目**：安装脚本检测到它们的配置文件时会跳过 `biome.json`，不会给同一门语言装两套 linter。要迁移的话，运行 `npx @biomejs/biome migrate eslint --write` 和 `npx @biomejs/biome migrate prettier --write`。

## 安装

```bash
npm i -D @biomejs/biome typescript vitest
```

`biome.json` 使用 Biome 2.6 的 `"preset": "recommended"` 写法（已用 2.6.9 验证）。用更早的 2.x 版本时，把它改成 `"recommended": true`，或者运行 `npx biome migrate --write`。

## package.json 脚本

把下面几条加进 `package.json`，并把 `check` 写进 `AGENTS.md`，作为完整检查命令：

```json
{
  "scripts": {
    "format": "biome format --write .",
    "lint": "biome lint .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "check": "biome ci . && tsc --noEmit && vitest run"
  }
}
```

## 配置说明

- `biome.json` 排除了 Markdown 和 `.agents`、`.claude` 目录。原因是 Biome 2.6 开始格式化 Markdown，会在 `SKILL.md` 的 frontmatter 里插入空行，导致 skill 无法被识别。
- `tsconfig.json` 开启了 `strict`、`noUncheckedIndexedAccess`、`noImplicitOverride`，CommonJS 和 ESM 项目都能直接使用。用打包工具（Vite、Next.js 等）的项目，可以把 `module` 和 `moduleResolution` 改成 `"Preserve"` 和 `"Bundler"`。
- CI 默认使用 npm 和 Node 24。用 pnpm 或 yarn 的项目，要改 `npm ci` 和 `cache` 两处。

## 约定

- 不用 `any`。确实不知道类型时用 `unknown`，再做类型收窄。
- 外部输入（请求体、环境变量、文件内容）在边界处用 schema 校验，例如 [Zod](https://zod.dev/)。
- 测试文件和源码放在一起，命名为 `*.test.ts`；端到端测试放在 `e2e/` 目录。
