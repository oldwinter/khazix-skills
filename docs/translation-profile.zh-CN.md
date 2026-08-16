# Khazix Skills 中文本地化档案

同步上游后，先读本档案，再处理新增或变更的中文内容。

## 项目定位

- 上游项目：`https://github.com/KKKKhazix/khazix-skills`
- 中文 fork：`https://github.com/oldwinter/khazix-skills`
- 主要安装面：支持 Agent Skills 的工具直接安装单个 skill
- 目标用户：希望直接使用中文 skill 的 Agent 用户
- 用户安装后实际读取的入口文件：`<skill-name>/SKILL.md` 及其 `references/`、`scripts/` 和 `assets/`
- 不应宣传为中文版安装的入口：任何仍指向上游仓库的安装 URL
- 当前同步上游 commit：`7a5c4934be4106ac740ffdb95280bb81b3f4b83c`

## 本地化目标

上游本身以中文为主。本 fork 的目标不是重复改写中文，而是持续吸收上游内容、保留中文 runtime，并确保所有安装入口明确指向 `oldwinter/khazix-skills`。

## 语气

- 保留上游自然、直接的中文表达，不把已有中文机械改写成另一套措辞。
- 面向开发者时保留 agent、skill、workflow、prompt、runtime 和 frontmatter 等常用英文技术词。
- 操作步骤先给可执行命令，再解释原因。

## 术语表

| 英文 | 中文 | 备注 |
|---|---|---|
| skill | skill | Agent Skills 语境下保留英文小写 |
| agent | Agent | 产品或协议名按原文大小写保留 |
| workflow | 工作流 | 命令名或文件名中保留英文 |
| runtime | runtime | 指安装后实际加载环境时保留英文 |
| upstream | 上游 | 指来源项目 |
| fork | fork | GitHub fork 语境下保留英文 |

## 不翻译清单

- 命令、参数、环境变量、URL、文件路径、包名和 skill slug。
- YAML/JSON/TOML key、frontmatter 字段名和 API 字段。
- 测试 fixture、golden string、正则、脚本以及执行器依赖的精确字符串。
- `README.en.md`；它是上游维护的英文入口，不与中文 README 混写。

## README 中文安装区块

README 必须说明这是社区维护 fork、当前同步的上游 commit，以及安装后会读取 `<skill-name>/SKILL.md` 和相邻资源。示例 URL 必须使用 `https://github.com/oldwinter/khazix-skills`。

## 同步后检查

- `git diff --check`
- 精确冲突标记扫描：`rg -n '^(<<<<<<<|=======|>>>>>>>)$' .`
- README 安装 URL 指向中文 fork。
- 新增 skill 的 `SKILL.md` 和引用路径完整。
- 新增英文 user-facing 内容已中文化；上游已有中文内容不做无意义重写。

## 项目特殊规则

- 上游为中文优先项目；同步工作的重点是安装入口、运行时完整性和新增 skill 的中文可用性。
- `README.md` 与 `README.en.md` 各自维护一种语言，不把两者合并成双语长文。
- API path、参数、User-Agent、响应 schema 和命令保持原样。
