# 小美（ZURU Melon Company Assistant Agent）

基于 **FastAPI + 原生 JS + Tailwind + RAG** 的企业智能客服系统，支持：

- 企业知识库检索（向量 + BM25 混合检索）
- 多轮会话（按 `session_id` 隔离，24h TTL）
- SSE 流式回复与来源引用展示
- Web 联网搜索（GLM / DuckDuckGo 自动路由与回退）
- CLI 与 Web 双入口

## 当前模型说明（重要）

当前使用模型为 **GLM-5**。请在 `.env` 中显式设置：

```env
ZHIPUAI_MODEL=glm-5
```

说明：代码中存在历史默认回退值，建议始终在 `.env` 明确指定模型，避免环境差异导致模型不一致。

## 核心特性

### 1. RAG 与检索

- `HybridRetriever`：向量检索 + BM25 + 结果融合
- 语言感知策略（中英文查询自动策略）
- 查询扩展、相似度阈值过滤、低结果自适应降阈值
- 向量库基于 ChromaDB，本地持久化

### 2. 会话与回答

- 会话隔离：`session_id -> history + last_accessed`
- 24 小时 TTL 自动清理
- 每会话最多保留 20 条消息上下文
- LLM 异常时提供检索上下文回退答案

### 3. Web 界面（Aurora Editorial 2.1）

- 桌面双栏：知识库 + 对话
- 移动双 Tab：`Chat` / `Knowledge`
- 玻璃拟物化（Glassmorphism）+ Aurora 背景
- 来源折叠卡片、Toast、状态 Popover、自定义确认弹窗
- 流式增量渲染采用 `requestAnimationFrame` 节流

### 4. Web 搜索能力

- 搜索源：GLM 原生搜索 + DuckDuckGo
- 自动路由（语言与查询复杂度）
- 失败回退、缓存、质量评分与去重

## 技术栈

- Python 3.12+
- FastAPI / Uvicorn
- ZhipuAI Python SDK
- ChromaDB
- sentence-transformers（默认嵌入）
- Typer + Rich（CLI）
- 原生 JS + Tailwind（前端）

## 项目结构

```text
company-assistant-agent/
├── Knowledge Base/              # 企业知识库（Markdown）
├── chroma_db/                   # 向量数据库目录
├── src/
│   ├── cli/                     # CLI 入口
│   ├── core/                    # 分类、检索、LLM、搜索、安全过滤
│   ├── knowledge/               # 解析与向量存储
│   ├── utils/                   # 配置、日志、错误处理
│   └── web/                     # FastAPI + 前端模板
├── tests/
├── env.example
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
cd company-assistant-agent
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp env.example .env
```

至少配置：

```env
ZHIPUAI_API_KEY=你的密钥
ZHIPUAI_MODEL=glm-5
```

### 3. 初始化知识库

```bash
python -m src.main init
```

### 4. 启动

CLI 对话：

```bash
python -m src.main chat
```

Web 服务：

```bash
python -m src.main web
# 浏览器访问 http://localhost:8000
```

开发热重载：

```bash
python -m src.main web --reload
```

## CLI 命令

| 命令 | 说明 |
|---|---|
| `python -m src.main chat` | 交互式多轮对话 |
| `python -m src.main init` | 解析知识库并写入向量库 |
| `python -m src.main query "..."` | 单次提问 |
| `python -m src.main status` | 查看系统与向量库状态 |
| `python -m src.main web` | 启动 Web 服务 |

## Web API 概览

### 问答相关

- `POST /api/query`：非流式问答
- `POST /api/query/stream`：SSE 流式问答（`chunk/sources/done/error`）

`/api/query` 响应包含：

- `response: str`
- `session_id: str`
- `sources: SourceItem[]`
- `latency_ms: int`

### 知识库相关

- `POST /api/knowledge/search`
- `GET /api/knowledge/overview`

### 会话相关

- `GET /api/sessions/{session_id}/history`
- `DELETE /api/sessions/{session_id}/history`

### 兼容接口

- `GET /api/history`
- `POST /api/clear-history`

### 健康检查

- `GET /health`
- `GET /api/status`

## 关键配置（与当前代码对齐）

### 模型与请求

| 变量 | 说明 | 推荐/默认 |
|---|---|---|
| `ZHIPUAI_API_KEY` | 智谱 API Key | 必填 |
| `ZHIPUAI_BASE_URL` | 智谱基地址 | `https://open.bigmodel.cn/api/paas/v4` |
| `ZHIPUAI_MODEL` | 对话模型 | **推荐 `glm-5`** |
| `GLM_API_TIMEOUT` | 请求超时（秒） | `60` |
| `GLM_MAX_RETRIES` | 重试次数 | `3` |
| `GLM_CONNECTION_TIMEOUT` | 连接超时（秒） | `30` |
| `MAX_TOKENS` | 最大 token | `65536` |
| `TEMPERATURE` | 温度 | `0.7` |
| `STREAM_ENABLED` | 默认启用流式 | `true` |
| `THINKING_ENABLED` | 启用 thinking 参数 | `true` |

### 知识库与检索

| 变量 | 说明 | 默认 |
|---|---|---|
| `KNOWLEDGE_BASE_PATH` | 知识库路径 | `Knowledge Base` |
| `VECTOR_DB_PATH` | 向量库存储目录 | `chroma_db` |
| `EMBEDDING_MODEL` | 嵌入模型 | `sentence-transformers/all-MiniLM-L6-v2` |
| `CHUNK_SIZE` | 分块大小 | `500` |
| `CHUNK_OVERLAP` | 分块重叠 | `50` |
| `MIN_SIMILARITY` | 最低相似度 | `0.25` |
| `MAX_RESULTS` | 最大检索结果 | `10` |
| `TOP_K` | Top-K | `5` |
| `RETRIEVAL_STRATEGY` | `auto/vector/bm25/hybrid` | `auto` |

### 联网搜索与系统

| 变量 | 说明 | 默认 |
|---|---|---|
| `SEARCH_ENABLED` | 是否启用联网搜索 | `true` |
| `SEARCH_PROVIDER` | `auto/glm/duckduckgo` | `auto` |
| `SEARCH_STRATEGY` | `auto/glm_first/ddg_first/...` | `auto` |
| `SEARCH_FALLBACK_ENABLED` | 搜索失败回退 | `true` |
| `SEARCH_CACHE_ENABLED` | 搜索缓存 | `true` |
| `SEARCH_CACHE_TTL` | 缓存 TTL（秒） | `3600` |
| `SEARCH_QUALITY_THRESHOLD` | 质量阈值 | `0.3` |
| `SAFETY_FILTER_ENABLED` | 安全过滤 | `true` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `LOG_FILE` | 日志文件 | `assistant.log` |

## 测试

运行全部测试：

```bash
pytest --no-cov -q
```

常用测试集：

```bash
pytest --no-cov -q tests/test_web_api.py
pytest --no-cov -q tests/test_integration.py
pytest --no-cov -q tests/test_llm_client.py
```

## 常见问题

### 1) Web 页无知识库数据

- 先执行 `python -m src.main init`
- 或调用任一 API 触发懒初始化（若知识库目录存在 Markdown）

### 2) 流式无输出

- 检查代理层是否关闭缓冲
- 确认服务端 `text/event-stream` 未被中间件截断

### 3) 会话不连续

- 检查浏览器 `assistant_session_id` 是否被清理
- 检查是否切换了域名/端口

## 安全说明

- 请勿将真实 `ZHIPUAI_API_KEY` 提交到仓库
- 建议在生产环境中启用鉴权、限流、审计日志
- 当前仓库默认面向本地/内网验证，不包含完整多租户安全隔离

## 许可证

MIT
