# 🌸 小美 - ZURU Melon 智能客服助手

> 一个可爱又专业的AI客服，基于RAG架构，精通公司政策、流程与一般知识问答

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GLM-4](https://img.shields.io/badge/Model-GLM--4.7-purple.svg)](https://open.bigmodel.cn/)

---

## ⚠️ 重要提醒

**`.env` 文件中的API密钥仅供测试使用。**

- **禁止**将此API密钥用于任何生产或商业用途
- **禁止**与任何人分享此API密钥
- **禁止**将包含此API密钥的代码部署到公共仓库
- **禁止**滥用API服务发送过量请求

**您必须从 [智谱AI平台](https://open.bigmodel.cn/) 获取自己的API密钥并替换（ZURU员工除外）**

---

## ✨ 特色亮点

| 特性 | 说明 |
|------|------|
| 🌸 **小美登场** | 友好专业的智能客服助手，随时为您服务 |
| 🧠 **聪明大脑** | GLM-4.7模型驱动，理解准确，响应迅速 |
| 📚 **知识渊博** | RAG架构 + 向量搜索，精通公司知识库 |
| 🌐 **多语言支持** | BAAI/bge-m3嵌入模型，支持100+语言 |
| 🔍 **双引擎检索** | 语义向量 + 关键词BM25混合搜索 |
| 🌐 **联网搜索** | GLM原生搜索 + DuckDuckGo备用方案 |
| 🛡️ **安全过滤** | 三层防护机制，内容安全有保障 |

---

## 🎯 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户提问                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     智能分类器                                   │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐    │
│  │   公司内部  │   外部知识  │    含糊    │    有害    │    │
│  └──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┘    │
└─────────┼─────────────┼─────────────┼─────────────┼────────────┘
          │             │             │             │
          ▼             ▼             │             ▼
    ┌──────────┐  ┌──────────┐       │       ┌──────────┐
    │知识库检索│  │ 联网搜索  │       │       │  拦截响应 │
    └────┬─────┘  └────┬─────┘       │       └──────────┘
         │            │              │
         ▼            ▼              │
    ┌────────────────────────────┐   │
    │     混合检索引擎           │   │
    │  ┌────────┬─────────────┐  │   │
    │  │ 向量搜索│  BM25搜索   │  │   │
    │  └───┬────┴──────┬──────┘  │   │
    │      │           │          │   │
    │      └─────┬─────┘          │   │
    │            ▼                │   │
    │     排序融合算法            │   │
    └────────────┬───────────────┘   │
                 │                   │
                 ▼                   │
         ┌───────────────┐           │
         │   LLM 客户端  │           │
         │  (GLM-4.7)    │           │
         └───────┬───────┘           │
                 │                   │
                 ▼                   │
         ┌───────────────┐           │
         │   生成回答    │◄──────────┘
         └───────────────┘
```

---

## 📁 项目结构

```
company-assistant-agent/
├── src/                           # 源代码
│   ├── cli/                       # 命令行界面
│   │   ├── __init__.py
│   │   └── interface.py           # 交互式CLI实现
│   │
│   ├── core/                      # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── assistant.py           # 主控制器
│   │   ├── classifier.py          # 查询类型分类器
│   │   ├── glm_searcher.py        # GLM联网搜索
│   │   ├── hybrid_retriever.py    # 混合检索引擎
│   │   ├── llm_client.py          # GLM-4.7 API客户端
│   │   ├── safety_filter.py       # 内容安全过滤
│   │   ├── searcher.py            # 联网搜索接口
│   │   └── error_handler.py       # 错误处理工具
│   │
│   ├── knowledge/                 # 知识库处理
│   │   ├── __init__.py
│   │   ├── parser.py              # Markdown文档解析器
│   │   └── vector_store.py        # ChromaDB向量存储封装
│   │
│   ├── utils/                     # 工具函数
│   │   ├── __init__.py
│   │   ├── config.py              # 配置管理
│   │   ├── error_handler.py       # 错误分类与处理
│   │   └── logger.py              # 日志配置
│   │
│   └── web/                       # Web界面
│       ├── api.py                 # FastAPI接口
│       ├── server.py              # 服务器启动
│       └── templates/
│           └── index.html         # 前端页面
│
├── tests/                         # 测试套件
├── Knowledge Base/                # 公司文档（Markdown格式）
├── chroma_db/                     # 向量数据库存储（自动生成）
├── .env                           # 环境变量（从env.example创建）
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python依赖
├── setup.py                       # 包安装脚本
├── pytest.ini                     # Pytest配置
└── README.md                      # 本文件
```

---

## 🚀 快速开始

### 前置要求

- Python 3.12 或更高版本
- pip 或 conda
- 智谱AI API密钥（[在这里获取](https://open.bigmodel.cn/)）

### 安装步骤

```bash
# 1. 进入项目目录
cd company-assistant-agent

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp env.example .env
# 编辑 .env 文件，添加您的 ZHIPUAI_API_KEY

# 5. 初始化知识库
python -m src.main init

# 6. 启动小美！
python -m src.main chat
```

### Web界面使用

```bash
# 启动Web服务
python -m src.main web

# 访问 http://localhost:8000 与小美对话
```

---

## ⚙️ 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ZHIPUAI_API_KEY` | 智谱AI API密钥 | 必填 |
| `ZHIPUAI_MODEL` | 使用的模型 | `glm-4.7` |
| `EMBEDDING_MODEL` | 嵌入模型 | `BAAI/bge-m3` |
| `KNOWLEDGE_BASE_PATH` | 知识库目录 | `Knowledge Base` |
| `VECTOR_DB_PATH` | 向量数据库路径 | `chroma_db` |
| `SEARCH_ENABLED` | 启用联网搜索 | `true` |
| `SEARCH_PROVIDER` | 搜索提供商 (`glm`/`duckduckgo`/`auto`) | `glm` |
| `MAX_TOKENS` | 最大响应token数 | `65536` |
| `TEMPERATURE` | LLM温度参数 | `0.7` |
| `SAFETY_FILTER_ENABLED` | 启用安全过滤 | `true` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

### 检索配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CHUNK_SIZE` | 文档分块大小 | `500` |
| `CHUNK_OVERLAP` | 分块重叠大小 | `50` |
| `SIMILARITY_THRESHOLD` | 最小相似度阈值 | `0.3` |
| `MAX_RESULTS` | 最大知识库结果数 | `10` |
| `TOP_K` | 返回的前K个结果 | `5` |
| `RETRIEVAL_STRATEGY` | 检索策略 | `auto` |

---

## 🎨 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| **大语言模型** | 智谱AI GLM-4.7 | 文本生成 |
| **向量数据库** | ChromaDB | 语义相似度搜索 |
| **嵌入模型** | BAAI/bge-m3 | 多语言文本嵌入 |
| **关键词搜索** | BM25 (rank_bm25) | 词汇搜索 |
| **联网搜索** | GLM原生 + DuckDuckGo | 外部知识检索 |
| **Web框架** | FastAPI + Uvicorn | Web服务 |
| **前端** | Tailwind CSS + 原生JS | 美观的Web界面 |
| **CLI框架** | Typer + Rich | 交互式命令行 |
| **测试框架** | pytest | 单元与集成测试 |

---

## 📖 使用示例

### 命令行对话

```bash
$ python -m src.main chat

╭──────────────────────────────────────────╮
│              欢迎                        │
│                                          │
│  小美 - ZURU Melon 智能客服              │
│  输入您的问题，输入 'exit' 或 'quit' 退出 │
╰──────────────────────────────────────────╯

您: 你好！你是谁？

小美: 你好！我是小美，ZURU Melon 的专业公司助理。

您: 如何申请年假？

小美: 员工可以通过以下步骤申请年假：
1. 至少提前2周通过HR门户提交请假申请
2. 管理者将在5个工作日内审核批准
3. HR将更新请假记录系统并通过邮件确认

您: exit

再见！
```

### Python API调用

```python
from src.core.assistant import Assistant

# 初始化小美
assistant = Assistant()

# 处理查询
response = assistant.process_query("什么是公司的请假政策？")
print(response)

# 清空对话历史
assistant.clear_history()
```

### Web API调用

```bash
# 提交问题
curl -X POST http://localhost:8000/api/query \
  -H 'Content-Type: application/json' \
  -d '{"query": "你好小美", "use_history": true}'

# 查看系统状态
curl http://localhost:8000/api/status

# 清空对话历史
curl -X POST http://localhost:8000/api/clear-history
```

---

## 🔧 开发指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行带覆盖率的测试
pytest --cov=src --cov-report=html

# 运行特定测试文件
pytest tests/test_classifier.py -v
```

### 代码格式化

```bash
# 格式化代码
black src/ tests/

# 排序导入
isort src/ tests/

# 类型检查
mypy src/
```

---

## 🎯 核心功能实现

### 1. 知识库处理 (`src/knowledge/`)

**`parser.py`**: 解析Markdown文档为分块
- 按标题分割文档以保持结构
- 创建重叠分块以提供更好上下文
- 提取元数据（来源文件、标题、分块索引）

**`vector_store.py`**: 管理ChromaDB向量存储
- 初始化持久化向量数据库
- 使用bge-m3生成嵌入
- 执行可配置阈值的相似度搜索

### 2. 混合检索系统 (`src/core/hybrid_retriever.py`)

**混合检索策略**:
1. **向量搜索**: 使用余弦距离的语义相似度
2. **BM25搜索**: 基于关键词的词汇搜索
3. **查询扩展**: 生成多语言查询变体
4. **排序融合**: 使用倒数排名融合(RRF)合并结果

**关键特性**:
- 自动语言检测
- 多语言查询扩展
- 可配置检索策略(vector/bm25/hybrid/auto)
- 相似度阈值过滤

### 3. 查询分类 (`src/core/classifier.py`)

**分类逻辑**:
1. 检查显式联网搜索短语
2. 对公司相关关键词评分
3. 对外部知识关键词评分
4. 基于评分确定查询类型

**查询类型**:
- `COMPANY_INTERNAL`: 政策、流程、HR问题
- `EXTERNAL_KNOWLEDGE`: 最新新闻、实时信息
- `AMBIGUOUS`: 可能是两者之一
- `HARMFUL`: 攻击、黑客、非法活动

### 4. 安全过滤 (`src/core/safety_filter.py`)

**三层过滤机制**:
1. **有害内容**: 攻击、黑客、恶意软件、病毒
2. **不当内容**: 色情、暴力、歧视
3. **违规操作**: 泄露机密、绕过安全

### 5. 联网搜索 (`src/core/searcher.py`, `glm_searcher.py`)

**双提供商系统**:
- **主要**: GLM-4.7原生联网搜索API
- **备用**: DuckDuckGo（免费，无需API密钥）

### 6. 主控制器 (`src/core/assistant.py`)

**查询处理流程**:
1. 安全检查 → 有害则拦截
2. 查询分类 → 确定检索策略
3. 上下文检索 → 知识库或联网搜索
4. 响应生成 → LLM结合上下文
5. 历史管理 → 跟踪对话

---

## 🌟 设计决策

### 为什么选择GLM-4.7？

| 因素 | GLM-4 Flash | GLM-4.7 |
|------|-------------|---------|
| 成本 | 约50%更低 | 更高 |
| 速度 | 更快 | 较慢 |
| 质量 | 适合问答 | 更适合复杂任务 |
| 用途 | 公司助手 | 研究/分析 |

**决策**: 对于公司内部问答，4.7提供更好的质量和理解能力。

### 为什么使用混合检索？

| 方法 | 优势 | 劣势 |
|------|------|------|
| 仅向量 | 语义理解 | 错过精确关键词 |
| 仅BM25 | 精确关键词匹配 | 无语义理解 |
| **混合** | **语义+关键词** | **稍复杂** |

### 为什么选择ChromaDB？

- **本地部署** - 无需外部服务依赖
- **零成本** - 无订阅费用
- **足够用** - 轻松处理公司规模文档
- **隐私保护** - 数据保留在本地

---

## 🤝 贡献指南

欢迎贡献！请：

1. Fork 本仓库
2. 创建功能分支
3. 进行更改
4. 为新功能添加测试
5. 提交Pull Request

---

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

## 🙏 致谢

- **智谱AI** 提供GLM-4.7模型
- **BAAI** 提供bge-m3嵌入模型
- **Chroma** 提供向量数据库

---

**版本**: 1.0.0
**最后更新**: 2025-01-11
**维护者**: 小美团队 🌸
