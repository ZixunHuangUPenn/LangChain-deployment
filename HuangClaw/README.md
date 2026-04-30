# HuangClaw

HuangClaw 是一个独立 Python coding agent 服务：

- LangGraph node/flow 循环：`agent -> tools -> agent -> ... -> final`
- built-in tools：工作区文件列表、读取、写入、搜索、受限命令执行、PDF RAG 检索
- PDF skill：读取 `../docs` 下所有 PDF，按页切分、chunk、embedding，并持久化到 Chroma
- Slack Events API 接入：使用 `.env` 中的 `SLACK_BOT_TOKEN` 和 `SLACK_SIGNING_SECRET`
- 使用 `uv` 管理 Python package，使用 PM2 后台部署 Slack 服务

## 快速开始

```powershell
cd HuangClaw
uv sync
uv run huangclaw ingest --reset
uv run huangclaw ask "请总结 docs 里的 learning in robotics 资料，并给出引用来源"
```

默认配置会读取仓库根目录的 `.env`，再读取 `HuangClaw/.env` 覆盖值。

如果 chat model 和 embedding model 不是同一个供应商，可以分别设置：

```dotenv
HUANGCLAW_CHAT_API_KEY=...
HUANGCLAW_CHAT_BASE_URL=...
HUANGCLAW_EMBEDDING_API_KEY=...
HUANGCLAW_EMBEDDING_BASE_URL=...
```

不设置时会回退到 `OPENAI_API_KEY` 和 `OPENAI_API_BASE_URL`。

## RAG 数据入库

```powershell
cd HuangClaw
uv run huangclaw ingest --docs-dir ..\docs --reset
```

入库逻辑在 [src/huangclaw/skills/pdf_skill.py](src/huangclaw/skills/pdf_skill.py)。默认参数：

- PDF 目录：`../docs`
- Chroma 目录：`./data/chroma`
- Collection：`learning_robotics_pdf`
- Chunk size：`1200`
- Chunk overlap：`180`

## Embedding 模型建议

默认选择规则：

- `OPENAI_API_BASE_URL` 包含 `siliconflow` 时，默认使用 `Qwen/Qwen3-Embedding-4B`。
- 其他情况默认使用 `text-embedding-3-small`。

原因是当前仓库根 `.env` 使用的是 SiliconFlow API，SiliconFlow 不提供 OpenAI 的 `text-embedding-3-small`；直接使用 provider 支持的 embedding model 才能完成入库。

可选配置：

- `text-embedding-3-small`：推荐默认项，成本低、速度快，适合课程资料、论文讲义这类中等规模知识库。
- `text-embedding-3-large`：推荐在检索质量优先时使用，尤其是跨语言、术语密集、长文档语义匹配场景；代价是索引成本和向量存储更高。
- `text-embedding-ada-002`：只建议兼容旧索引时使用；新建索引不建议优先选它。
- `Qwen/Qwen3-Embedding-4B`：当前仓库使用 SiliconFlow 时的推荐默认项；它支持长上下文、多语言和可变向量维度，成本低于 8B，质量通常强于 0.6B。
- `Qwen/Qwen3-Embedding-0.6B`：SiliconFlow 低成本选项，适合先快速构建索引。
- `Qwen/Qwen3-Embedding-8B`：SiliconFlow 高质量选项，适合检索质量优先、预算不敏感的资料库。

OpenAI 文档显示 `text-embedding-3-small` 与 `text-embedding-3-large` 是第三代 embedding 模型，并支持调整输出维度；模型页也标注 `text-embedding-3-large` 是更强能力版本，`text-embedding-3-small` 是低成本版本：

- https://platform.openai.com/docs/guides/embeddings
- https://platform.openai.com/docs/models/text-embedding-3-small
- https://platform.openai.com/docs/models/text-embedding-3-large
- https://www.siliconflow.com/models/embedding

## Slack 接入

`.env` 中需要：

```dotenv
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
```

本地启动：

```powershell
cd HuangClaw
uv run uvicorn huangclaw.slack_app:api --host 0.0.0.0 --port 3010
```

Slack App 配置：

- Event Request URL：`https://你的公网域名/slack/events`
- Bot Token Scopes：`app_mentions:read`, `chat:write`, `im:history`, `im:read`
- Subscribe Bot Events：`app_mention`, `message.im`

## PM2 部署

```powershell
cd HuangClaw
pm2 start pm2.config.cjs
pm2 logs huangclaw-slack
pm2 save
```

健康检查：

```powershell
curl http://localhost:3010/health
```

## 主要文件

- [src/huangclaw/agent/graph.py](src/huangclaw/agent/graph.py)：LangGraph agent loop
- [src/huangclaw/tools/builtin.py](src/huangclaw/tools/builtin.py)：built-in tools
- [src/huangclaw/skills/pdf_skill.py](src/huangclaw/skills/pdf_skill.py)：PDF RAG + Chroma
- [src/huangclaw/slack_app.py](src/huangclaw/slack_app.py)：Slack Events API
- [pm2.config.cjs](pm2.config.cjs)：PM2 后台服务配置
