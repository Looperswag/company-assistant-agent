# Company Assistant Agent

> An intelligent company assistant based on RAG architecture, capable of answering questions about company policies, procedures, and general knowledge.

## ⚠️ IMPORTANT WARNING

**The API key in the `.env` file is for TESTING PURPOSES ONLY.**

- **DO NOT** use this API key for any production or commercial purposes
- **DO NOT** share this API key with anyone
- **DO NOT** deploy this code with the included API key to public repositories
- **DO NOT** abuse the API service with excessive requests

**You must replace the API key with your own from [ZhipuAI Platform](https://open.bigmodel.cn/), except ZURU's coworkers**

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Development](#development)
- [Demo Scenarios](#demo-scenarios)
- [Technology Stack](#technology-stack)
- [License](#license)

---

## Features

- 🤖 **Intelligent Q&A**: Powered by GLM-4 Flash model for accurate, context-aware responses
- 📚 **Knowledge Base**: RAG architecture with vector similarity search over company documents
- 🔍 **Hybrid Retrieval**: Combines semantic search (vector) and keyword search (BM25)
- 🌐 **Multilingual Support**: BAAI/bge-m3 embedding model supports 100+ languages
- 🔒 **Safety Filter**: Blocks harmful, inappropriate, or policy-violating queries
- 🌐 **Web Search**: GLM native web search with DuckDuckGo fallback
- 📊 **Query Classification**: Automatically classifies queries for optimal routing

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Query                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Query Classifier                              │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐    │
│  │   Company   │   External  │   Ambiguous │    Harmful  │    │
│  │  Internal   │  Knowledge  │             │             │    │
│  └──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┘    │
└─────────┼─────────────┼─────────────┼─────────────┼────────────┘
          │             │             │             │
          ▼             ▼             │             ▼
    ┌──────────┐  ┌──────────┐       │       ┌──────────┐
    │Knowledge │  │  Web     │       │       │  Blocked │
    │   Base   │  │ Search   │       │       │ Response │
    └────┬─────┘  └────┬─────┘       │       └──────────┘
         │            │              │
         ▼            ▼              │
    ┌────────────────────────────┐   │
    │     Hybrid Retriever       │   │
    │  ┌────────┬─────────────┐  │   │
    │  │ Vector│    BM25      │  │   │
    │  │ Search│   Search     │  │   │
    │  └───┬────┴──────┬──────┘  │   │
    │      │           │          │   │
    │      └─────┬─────┘          │   │
    │            ▼                │   │
    │     Rank & Fuse            │   │
    └────────────┬───────────────┘   │
                 │                   │
                 ▼                   │
         ┌───────────────┐           │
         │   LLM Client  │           │
         │  (GLM-4 Flash) │           │
         └───────┬───────┘           │
                 │                   │
                 ▼                   │
         ┌───────────────┐           │
         │   Response    │◄──────────┘
         └───────────────┘
```

### Data Flow

1. **Input**: User submits a query
2. **Classification**: Query is classified into one of four types
3. **Retrieval**:
   - Company internal: Search knowledge base
   - External knowledge: Web search
   - Ambiguous: Try both, ask for clarification if needed
4. **Generation**: LLM generates response using retrieved context
5. **Output**: Formatted response returned to user

---

## Project Structure

```
Company Assistant Agent/
├── src/                           # Source code
│   ├── cli/                       # Command-line interface
│   │   ├── __init__.py
│   │   └── interface.py           # Interactive CLI implementation
│   │
│   ├── core/                      # Core business logic
│   │   ├── __init__.py
│   │   ├── assistant.py            # Main orchestrator
│   │   ├── classifier.py           # Query type classifier
│   │   ├── glm_searcher.py        # GLM web search
│   │   ├── hybrid_retriever.py    # Hybrid vector+BM25 retrieval
│   │   ├── llm_client.py          # GLM-4 Flash API client
│   │   ├── retriever.py           # Legacy knowledge retriever
│   │   ├── safety_filter.py       # Content safety filter
│   │   └── searcher.py            # Web search interface
│   │
│   ├── knowledge/                 # Knowledge base processing
│   │   ├── __init__.py
│   │   ├── parser.py              # Markdown document parser
│   │   └── vector_store.py        # ChromaDB vector store wrapper
│   │
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── config.py              # Configuration management
│       └── logger.py              # Logging setup
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_classifier.py        # Query classifier tests
│   ├── test_integration.py       # Integration tests
│   ├── test_llm_client.py        # LLM client tests
│   ├── test_parser.py            # Parser tests
│   └── test_safety_filter.py     # Safety filter tests
│
├── Knowledge Base/                # Company documents (Markdown)
│   ├── Company Policies.md
│   ├── Company Procedures & Guidelines.md
│   └── Coding Style.md
│
├── chroma_db/                     # Vector database storage (auto-generated)
├── .env                           # Environment variables (CREATE FROM env.example)
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
├── setup.py                       # Package setup script
├── pytest.ini                     # Pytest configuration
├── README.md                      # This file
└── DEMO.md                        # Demo scenarios documentation
```

---

## Installation

### Prerequisites

- Python 3.12 or higher
- pip or conda
- ZhipuAI API key ([Get one here](https://open.bigmodel.cn/))

### Quick Start

```bash
# 1. Clone or download the project
cd "Company Assistant Agent"

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp env.example .env
# Edit .env and add your ZHIPUAI_API_KEY

# 5. Run the assistant
python -m src.main
```

### Using setup.py

```bash
pip install -e .
company-assistant
```

---

## Usage

### Command-Line Interface

```bash
python -m src.main
```

### Example Session

```
Company Assistant Agent (type 'quit' to exit)
====================================================

You: How do I apply for annual leave?

Assistant: Employees can apply for annual leave through the following steps:

1. Submit a leave request through the HR Portal at least 2 weeks in advance.
2. The manager will review and approve within 5 business days.
3. HR will update the leave record system and confirm via email.

You: What's the difference between lists and tuples in Python?

Assistant: [Provides detailed Python explanation...]

You: quit

Goodbye!
```

### Python API

```python
from src.core.assistant import Assistant

# Initialize assistant
assistant = Assistant()

# Process a query
response = assistant.process_query("What is the vacation policy?")
print(response)

# Clear conversation history
assistant.clear_history()
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ZHIPUAI_API_KEY` | ZhipuAI API key | Required |
| `ZHIPUAI_MODEL` | Model to use | `glm-4-flash` |
| `EMBEDDING_MODEL` | Embedding model | `BAAI/bge-m3` |
| `KNOWLEDGE_BASE_PATH` | Knowledge base directory | `Knowledge Base` |
| `VECTOR_DB_PATH` | Vector database path | `chroma_db` |
| `SEARCH_ENABLED` | Enable web search | `true` |
| `SEARCH_PROVIDER` | Search provider (`glm`/`duckduckgo`/`auto`) | `glm` |
| `MAX_TOKENS` | Maximum tokens per response | `65536` |
| `TEMPERATURE` | LLM temperature | `0.7` |
| `SAFETY_FILTER_ENABLED` | Enable safety filter | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Retrieval Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `CHUNK_SIZE` | Document chunk size | `500` |
| `CHUNK_OVERLAP` | Chunk overlap size | `50` |
| `SIMILARITY_THRESHOLD` | Minimum similarity score | `0.3` |
| `MAX_RESULTS` | Max knowledge base results | `10` |
| `TOP_K` | Top K results to return | `5` |
| `RETRIEVAL_STRATEGY` | Retrieval strategy | `auto` |

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_classifier.py -v
```

### Project Commands

```bash
# Format code
black src/ tests/

# Run linting
flake8 src/ tests/

# Type checking
mypy src/
```

---

## Demo Scenarios

See [DEMO.md](DEMO.md) for detailed demonstration of:

1. **Company Internal Query**: Vacation policy, leave requests
2. **General Knowledge Query**: Python programming questions
3. **Ambiguous Query**: Questions requiring clarification
4. **Harmful Content**: Safety filter demonstration

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | ZhipuAI GLM-4 Flash | Text generation |
| **Vector Database** | ChromaDB | Semantic similarity search |
| **Embedding Model** | BAAI/bge-m3 | Multilingual text embeddings |
| **Keyword Search** | BM25 (rank_bm25) | Lexical search |
| **Web Search** | GLM Native + DuckDuckGo | External knowledge retrieval |
| **CLI Framework** | Custom + argparse | Interactive terminal interface |
| **Testing** | pytest | Unit and integration tests |
| **Type Hints** | typing | Python type annotations |

---

## Implementation Details

### 1. Knowledge Base Processing (`src/knowledge/`)

**`parser.py`**: Parses Markdown documents into chunks
- Splits documents by headings to preserve structure
- Creates overlapping chunks for better context
- Extracts metadata (source file, title, chunk index)

**`vector_store.py`**: Manages ChromaDB vector store
- Initializes persistent vector database
- Generates embeddings using bge-m3
- Performs similarity search with configurable thresholds

### 2. Retrieval System (`src/core/hybrid_retriever.py`)

**Hybrid Retrieval Strategy**:
1. **Vector Search**: Semantic similarity using cosine distance
2. **BM25 Search**: Keyword-based lexical search
3. **Query Expansion**: Generates multilingual query variants
4. **Rank Fusion**: Combines results using Reciprocal Rank Fusion (RRF)

**Key Features**:
- Automatic language detection
- Query expansion for multilingual support
- Configurable retrieval strategy (vector/bm25/hybrid/auto)
- Similarity threshold filtering

### 3. Query Classification (`src/core/classifier.py`)

**Classification Logic**:
1. Check for explicit web search phrases
2. Score company-related keywords
3. Score external knowledge keywords
4. Determine query type based on scores

**Query Types**:
- `COMPANY_INTERNAL`: Policy, procedure, HR questions
- `EXTERNAL_KNOWLEDGE`: Latest news, real-time information
- `AMBIGUOUS`: Could be either
- `HARMFUL`: Attack, hack, illegal activities

### 4. Safety Filter (`src/core/safety_filter.py`)

**Three-Tier Filtering**:
1. **Harmful Content**: attack, hack, malware, virus
2. **Inappropriate Content**: porn, violence, discrimination
3. **Policy Violations**: leak confidential, bypass security

### 5. Web Search (`src/core/searcher.py`, `glm_searcher.py`)

**Dual Provider System**:
- **Primary**: GLM-4 Flash native web search API
- **Fallback**: DuckDuckGo (free, no API key needed)

**Query Cleanup**:
- Removes redundant phrases ("从互联网上", "tell me")
- Strips punctuation
- Preserves query intent

### 6. LLM Client (`src/core/llm_client.py`)

**Features**:
- Streaming and non-streaming modes
- Thinking parameter for complex reasoning
- Configurable temperature and max tokens
- System prompt with knowledge base context

### 7. Main Assistant (`src/core/assistant.py`)

**Query Processing Pipeline**:
1. Safety check → Block if harmful
2. Query classification → Determine retrieval strategy
3. Context retrieval → Knowledge base or web search
4. Response generation → LLM with context
5. History management → Track conversation

---

## Key Design Decisions

### Why GLM-4 Flash Over GLM-4.7?

| Factor | GLM-4 Flash | GLM-4.7 |
|--------|-------------|---------|
| Cost | ~50% lower | Higher |
| Speed | Faster | Slower |
| Quality | Good for Q&A | Better for complex tasks |
| Use Case | Company assistant | Research/analysis |

**Decision**: For company internal Q&A, Flash provides sufficient quality at significantly lower cost.

### Why Hybrid Retrieval?

| Method | Strength | Weakness |
|--------|----------|----------|
| Vector Only | Semantic understanding | Misses exact keywords |
| BM25 Only | Precise keyword matching | No semantic understanding |
| **Hybrid** | **Both semantic + keyword** | **Slightly more complex** |

### Why ChromaDB Over Pinecone/Weaviate?

- **Local deployment** - No external service dependency
- **Zero cost** - No subscription fees
- **Sufficient** - Handles company-scale documents easily
- **Privacy** - Data stays on-premise

---

## Extensibility

The modular architecture allows easy customization:

1. **Replace LLM**: Modify `llm_client.py` to use OpenAI, Anthropic, etc.
2. **Change Embedding Model**: Update `EMBEDDING_MODEL` in `.env`
3. **Add Search Providers**: Extend `searcher.py` with new providers
4. **Custom Classification Rules**: Edit keywords in `classifier.py`
5. **Additional Safety Rules**: Add keywords to `safety_filter.py`

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

---

## License

MIT License - see LICENSE file for details.

---

## Acknowledgments

- **ZhipuAI** for the GLM-4 Flash model
- **BAAI** for the bge-m3 embedding model
- **Chroma** for the vector database
---

**Version**: 1.0.0
**Last Updated**: 2025-01-11
**Maintainer**: Company Assistant Agent Team
