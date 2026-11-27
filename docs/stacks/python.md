# Python

## 工具选择

| 用途 | 工具 | 配置文件 |
| --- | --- | --- |
| 依赖和虚拟环境 | [uv](https://docs.astral.sh/uv/) | `pyproject.toml`、`uv.lock` |
| 格式化 + lint | [Ruff](https://docs.astral.sh/ruff/)（替代 Black、isort、Flake8，并包含 bandit 的安全规则） | `ruff.toml` |
| 类型检查 | [mypy](https://mypy.readthedocs.io/)，严格模式 | `mypy.ini` |
| 测试 | [pytest](https://docs.pytest.org/) | `pytest.ini` |
| CI | GitHub Actions + `astral-sh/setup-uv` | `.github/workflows/ci-python.yml` |

**已经在 `pyproject.toml` 里配置了 `[tool.ruff]`、`[tool.mypy]` 或 `[tool.pytest...]` 的项目**：安装脚本会跳过对应的独立配置文件。这些独立文件的优先级高于 `pyproject.toml`，直接加进去会悄悄覆盖原有的配置。

## 安装

```bash
uv add --dev ruff mypy pytest
```

## 常用命令

| 用途 | 命令 |
| --- | --- |
| 格式化 | `uv run ruff format .` |
| lint（可自动修复） | `uv run ruff check --fix .` |
| 类型检查 | `uv run mypy .` |
| 测试 | `uv run pytest` |
| 完整检查 | `uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest` |

建议把完整检查写进 `Makefile` 或 `justfile`，然后在 `AGENTS.md` 里写 `make check`。

## 配置说明

- `ruff.toml` 开启了 E/W/F/I/B/UP/SIM/C4/S/N/PT/RUF 这几组规则。其中 `S` 是安全规则，测试目录里允许使用 `assert` 和 `subprocess`。
- `mypy.ini` 开启了 `strict`。**已有的项目如果一下子开不了**，可以先设 `strict = False` 加 `disallow_untyped_defs = True`，然后按模块逐步收紧。不要用 `# type: ignore` 批量压掉报错。
- `pytest.ini` 开启了 `--strict-markers`、`--strict-config` 和 `xfail_strict`，防止写错的 marker 和“意外通过”的 xfail 被忽略。

## 约定

- 公开函数都要写类型标注。
- 外部输入在边界处用 [Pydantic](https://docs.pydantic.dev/) 或 dataclass 校验。
- 不要用裸的 `except:` 或者 `except Exception: pass` 吞掉错误。
