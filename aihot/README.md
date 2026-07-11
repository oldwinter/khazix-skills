# AI HOT — Agent Skill

让 AI Agent 只用一句自然的中文，就能获取 [aihot.virxact.com](https://aihot.virxact.com) 每天的 AI HOT 日报和全部 AI 动态，无需配置。

> 跨 Claude Code · Codex CLI · Cursor · Gemini CLI · GitHub Copilot · OpenCode · Cline · Windsurf 等任意支持 SKILL.md 格式的 Agent 平台。

## 这是什么

[AI HOT](https://aihot.virxact.com) 是一个面向中文 AI 创业者的资讯站，每天早上 08:00 整理出分版块日报，并在全天持续抓取资讯，经 LLM 评分后筛选出精选条目。

这个 Skill 让 Agent 直接调用 AI HOT 的公开 REST API，无需打开浏览器。

## 安装

### 方式 A：让 Agent 自动安装（Claude Code / Codex 通用）

在你的 Agent 中直接发送这句话：

```
帮我安装这个 Skill：https://aihot.virxact.com/aihot-skill/
```

Agent 会获取 `SKILL.md`，然后写入对应平台的 Skill 目录。

### 方式 B：用一行命令手动安装（适用于 Codex / Gemini CLI / OpenCode 等不会自动安装的工具）

```bash
curl -fsSL https://aihot.virxact.com/aihot-skill/install.sh | bash
```

默认安装到 `~/.claude/skills/aihot/`。如需安装到 Codex / Gemini / OpenCode 等其他路径，请先设置环境变量再运行：

```bash
SKILL_DIR=~/.codex/skills/aihot \
  bash <(curl -fsSL https://aihot.virxact.com/aihot-skill/install.sh)
```

（`install.sh` 不会执行 `chmod` 或 `sudo`，只会用 `mkdir` 创建目录，再用 `curl` 下载 `SKILL.md` 和 `README.md`。可运行 `curl https://aihot.virxact.com/aihot-skill/install.sh` 查看并审查安装脚本。）

### 方式 C：从仓库获取

本 Skill 也同步到了卡兹克的 Skills 合集 [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills/tree/main/aihot)，与 hv-analysis / khazix-writer / neat-freak 等其他 Skill 一同维护。使用 `git clone` 拉取仓库后，取出对应子目录即可。

## 触发示例

随便问，不需要记关键字：

- 今天 AI 圈有什么新东西？
- 看一下今天的 AI 日报
- 最近 OpenAI 有什么发布？
- 最近一周的 AI 论文
- 看下精选条目
- AI 模型发布列表
- 最近 3 天 AI 行业动态

Skill 会自动调用 [aihot.virxact.com](https://aihot.virxact.com) 的公开 API（无须配置 API Key），并通过可识别的 `aihot-skill/` User-Agent 标明身份，不伪装成浏览器；获取结果后，会整理成中文 Markdown 简报返回给你。

## 不需要登录、不需要 API Key

AI HOT 的数据 100% 公开免费，匿名可访。Skill 调以下接口：

| 路径 | 用途 |
|---|---|
| `/api/public/daily` | 最新 AI HOT 日报 |
| `/api/public/daily/{YYYY-MM-DD}` | 指定日期日报 |
| `/api/public/dailies` | 日报归档索引 |
| `/api/public/items` | 全部 AI 动态（按精选 / 分类 / 时间 / 关键词筛选） |
| `/api/public/hot-topics` | 当前热点（多源热度排序） |
| `/api/public/fingerprint` | 轻量新鲜度指纹（供 `cron` / 监控轮询使用） |
| `/api/public/version` | 版本信息（Skill 自检更新用） |

进阶用法（RSS 订阅 / REST API 详细参数）见 [aihot.virxact.com/agent](https://aihot.virxact.com/agent)。

## 反馈

Skill 漏触发、漏筛选、想加新查询场景？

- 在 [aihot.virxact.com/feedback](https://aihot.virxact.com/feedback) 留言
- 或直接在 [Skills 合集仓库](https://github.com/KKKKhazix/khazix-skills/tree/main/aihot) 提交 Issue

## 许可证

MIT
