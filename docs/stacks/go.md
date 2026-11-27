# Go

## 工具选择

| 用途 | 工具 | 配置文件 |
| --- | --- | --- |
| 格式化 | `gofmt` + `goimports`（通过 golangci-lint 的 formatters 运行） | `.golangci.yml` |
| lint | [golangci-lint](https://golangci-lint.run/) v2 | `.golangci.yml` |
| 静态检查 | `go vet` | — |
| 测试 | `go test -race` | — |
| 漏洞扫描 | [govulncheck](https://go.dev/doc/security/vuln/) | — |
| CI | GitHub Actions + `golangci/golangci-lint-action` | `.github/workflows/ci-go.yml` |

## 安装

```bash
go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@v2.15.0
```

## 常用命令

| 用途 | 命令 |
| --- | --- |
| 格式化 | `golangci-lint fmt` |
| lint | `golangci-lint run ./...` |
| 测试 | `go test -race -count=1 ./...` |
| 单个测试 | `go test ./pkg/foo -run TestName -v` |
| 漏洞扫描 | `go run golang.org/x/vuln/cmd/govulncheck@v1.10.0 ./...` |
| 完整检查 | `golangci-lint run ./... && go vet ./... && go test -race -count=1 ./...` |

## 配置说明

- `.golangci.yml` 使用 v2 格式（`version: "2"`），在 `standard` 默认规则集之上增加了 `bodyclose`、`errorlint`、`gocritic`、`gosec`、`misspell`、`nilerr`、`revive`、`unconvert`。已经用 golangci-lint v2.15.0 的 `config verify` 校验过。
- 旧的 v1 配置可以用 `golangci-lint migrate` 转换。
- `revive` 默认要求每个包都有包注释。确实不需要时，在配置里关掉 `package-comments` 规则，不要在代码里逐行加 `//nolint`。

## 约定

- 错误要用 `fmt.Errorf("...: %w", err)` 包装后返回，判断错误类型时用 `errors.Is` 或 `errors.As`。
- 测试用表驱动的写法，并行测试要调用 `t.Parallel()`。
- 不要在库代码里调用 `panic` 或 `os.Exit`。
