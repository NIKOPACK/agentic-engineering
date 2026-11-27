# 背景：从 vibe coding 到 agentic engineering

这套规范基于 2026 年业界对 AI 辅助开发的主流共识。整理于 2026-11，下面的数字大多来自厂商报告、调查和预印本，仅作参考。

## 范式变化

- 据媒体报道，“vibe coding”这个词的提出者 Karpathy 在 2026 年初表示 vibe coding 已经过时，提出用 **agentic engineering** 代替：vibe coding 抬高的是下限，agentic engineering 抬高的是上限。（[The New Stack](https://thenewstack.io/vibe-coding-is-passe-karpathy-has-a-new-name-for-the-future-of-software/)）
- Addy Osmani 对 agentic engineering 的定义是：AI 是很强的实现引擎，但要放在由约束、测试和反馈循环组成的系统里运行；架构、正确性和质量仍然由人把关。（[Agentic Engineering](https://addyosmani.com/blog/agentic-engineering/)）
- Anthropic 的《2026 Agentic Coding Trends Report》认为，软件开发正在从“写代码”转向“编排写代码的智能体”。（[报告](https://resources.anthropic.com/2026-agentic-coding-trends-report)）

## 支撑这套规范的几个发现

| 发现 | 对应的规范 |
| --- | --- |
| 2026 年中，约 90% 的职业开发者每周都在工作中使用 AI 编码智能体（[JetBrains](https://blog.jetbrains.com/research/2026/08/ai-coding-agent-adoption-2026/)） | 规范要同时适配多种智能体 → 三个工具共用一套文件 |
| 智能体的自我评估有偏差，会把原地打转当成进展；可靠的做法是由测试套件或独立的评估者来判定（[arXiv 2607.25152](https://arxiv.org/pdf/2607.25152)） | [03 验证](standards/03-verification.md)、`verify-change` |
| 有 AGENTS.md 时，智能体的任务完成率差不多，但运行时间和 token 消耗更低；AGENTS.md 正在成为跨工具的通用标准（[arXiv 2602.14690](https://arxiv.org/html/2602.14690v3)） | [02 上下文](standards/02-context.md) |
| 规格驱动开发（SDD）被视为解决 vibe coding 不可控问题的主要办法，GitHub Spec Kit、AWS Kiro 等专门工具已经出现（[arXiv 2602.00180](https://arxiv.org/html/2602.00180)） | `spec-first`、`docs/specs/` |
| 约 45% 的 AI 生成代码存在 OWASP Top 10 类漏洞；2026 年第一季度，由 AI 工具引入的 CVE 数量已经超过 2025 年全年（[CSA](https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/03/CSA_research_note_AI_generated_code_security_vibe_coding_20260331-csa-styled.pdf)、[Georgia Tech](https://www.cc.gatech.edu/news/bad-vibes-ai-generated-code-vulnerable-researchers-warn)） | [05 安全](standards/05-security.md)、护栏、gitleaks |
| METR 2025 年的随机对照试验发现，资深开发者用 AI 后反而慢了 19%，而他们自己以为快了 20%；2026 年的后续研究因为选择偏差，结论还不确定（[METR](https://metr.org/blog/2026-02-24-uplift-update/)） | 效率要靠流程和验证保障，不能只凭感觉 |
