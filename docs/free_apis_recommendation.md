# 免费API推荐方案

## 一、知识库相关API

### 1.1 Wikipedia API ⭐⭐⭐⭐⭐

**优势：**
- 完全免费，无调用限制
- 权威性强，内容质量高
- 支持多语言（包括中文）
- 无需API密钥
- 提供结构化数据

**使用场景：**
- 百科知识查询
- 定义和概念解释
- 历史背景信息
- 技术术语解释

**Python实现示例：**
```python
import wikipedia

def search_wikipedia(query: str, n_results: int = 3) -> List[dict]:
    results = []
    try:
        wikipedia.set_lang("zh")  # 设置中文
        search_results = wikipedia.search(query, results=n_results)
        
        for title in search_results:
            try:
                page = wikipedia.page(title, auto_suggest=False)
                results.append({
                    "title": page.title,
                    "summary": page.summary[:500],
                    "content": page.content[:1000],
                    "url": page.url,
                    "source": "Wikipedia"
                })
            except wikipedia.exceptions.PageError:
                continue
    except Exception as e:
        logger.error(f"Wikipedia search error: {e}")
    
    return results
```

**安装依赖：**
```bash
pip install wikipedia
```

---

### 1.2 GitHub API ⭐⭐⭐⭐

**优势：**
- 免费额度高：5000次/小时
- 技术文档和代码资源丰富
- 可搜索README、Wiki、Issues
- 支持代码片段检索

**使用场景：**
- 技术问题解决方案
- 代码示例查找
- 项目文档查询
- 最佳实践参考

**Python实现示例：**
```python
import requests

def search_github(query: str, language: str = None, n_results: int = 5) -> List[dict]:
    results = []
    
    url = "https://api.github.com/search/code"
    params = {
        "q": f"{query} in:file,readme,wiki",
        "per_page": n_results
    }
    
    if language:
        params["q"] += f" language:{language}"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for item in data.get("items", []):
            results.append({
                "name": item.get("name"),
                "path": item.get("path"),
                "html_url": item.get("html_url"),
                "repository": item.get("repository", {}).get("full_name"),
                "source": "GitHub"
            })
    except Exception as e:
        logger.error(f"GitHub search error: {e}")
    
    return results
```

**安装依赖：**
```bash
pip install requests
```

---

### 1.3 ArXiv API ⭐⭐⭐⭐

**优势：**
- 完全免费，无限制
- 学术论文资源丰富
- 包含最新研究成果
- 提供PDF和摘要

**使用场景：**
- 学术问题查询
- 最新技术研究
- 理论依据查找
- 参考文献获取

**Python实现示例：**
```python
import requests

def search_arxiv(query: str, n_results: int = 3) -> List[dict]:
    results = []
    
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": n_results
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            summary = entry.find("{http://www.w3.org/2005/Atom}summary").text
            paper_id = entry.find("{http://www.w3.org/2005/Atom}id").text
            published = entry.find("{http://www.w3.org/2005/Atom}published").text
            
            results.append({
                "title": title,
                "summary": summary[:500],
                "paper_id": paper_id.split("/")[-1],
                "published": published,
                "url": paper_id,
                "source": "ArXiv"
            })
    except Exception as e:
        logger.error(f"ArXiv search error: {e}")
    
    return results
```

**安装依赖：**
```bash
pip install requests
```

---

## 二、网络搜索API

### 2.1 DuckDuckGo Search ⭐⭐⭐⭐⭐

**优势：**
- 完全免费，无限制
- 无需API密钥
- 隐私友好
- 即时结果

**使用场景：**
- 通用网络搜索
- 实时信息查询
- 新闻和资讯
- 综合信息获取

**Python实现示例：**
```python
from duckduckgo_search import DDGS

def search_duckduckgo(query: str, max_results: int = 5) -> List[dict]:
    results = []
    
    try:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=max_results))
        
        for result in search_results:
            results.append({
                "title": result.get("title", ""),
                "snippet": result.get("body", ""),
                "url": result.get("href", ""),
                "source": "DuckDuckGo"
            })
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
    
    return results
```

**安装依赖：**
```bash
pip install duckduckgo-search
```

---

### 2.2 Google Custom Search API ⭐⭐⭐

**优势：**
- 搜索结果质量高
- 可定制搜索范围
- 支持多种搜索类型

**限制：**
- 免费额度：100次/天
- 需要API密钥和搜索引擎ID

**使用场景：**
- 高质量网络搜索
- 特定网站搜索
- 学术和权威内容

**Python实现示例：**
```python
import requests

def search_google_custom(query: str, api_key: str, cx: str, n_results: int = 5) -> List[dict]:
    results = []
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": n_results
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for item in data.get("items", []):
            results.append({
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "url": item.get("link"),
                "source": "Google"
            })
    except Exception as e:
        logger.error(f"Google Custom Search error: {e}")
    
    return results
```

---

### 2.3 Bing Web Search API ⭐⭐⭐

**优势：**
- 搜索结果质量高
- 免费额度：1000次/月
- 全球搜索覆盖

**限制：**
- 需要API密钥
- 免费额度有限

**使用场景：**
- 高质量网络搜索
- 国际内容检索
- 多语言搜索

**Python实现示例：**
```python
import requests

def search_bing(query: str, api_key: str, n_results: int = 5) -> List[dict]:
    results = []
    
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": query, "count": n_results}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for item in data.get("webPages", {}).get("value", []):
            results.append({
                "title": item.get("name"),
                "snippet": item.get("snippet"),
                "url": item.get("url"),
                "source": "Bing"
            })
    except Exception as e:
        logger.error(f"Bing search error: {e}")
    
    return results
```

---

## 三、嵌入和重排序模型

### 3.1 嵌入模型

| 模型 | 平台 | 优势 | 推荐指数 |
|-----|------|------|---------|
| **sentence-transformers/all-MiniLM-L6-v2** | HuggingFace | 轻量、快速、中文支持好 | ⭐⭐⭐⭐⭐ |
| **moka-ai/m3e-base** | HuggingFace | 中文优化、性能好 | ⭐⭐⭐⭐⭐ |
| **paraphrase-multilingual-MiniLM-L12-v2** | HuggingFace | 多语言、语义理解强 | ⭐⭐⭐⭐ |
| **BAAI/bge-base-zh-v1.5** | HuggingFace | 中文专用、高性能 | ⭐⭐⭐⭐⭐ |

**推荐使用：**
```python
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer('moka-ai/m3e-base')

def get_embedding(text: str) -> list:
    return embedding_model.encode(text, convert_to_tensor=True).tolist()
```

---

### 3.2 重排序模型

| 模型 | 平台 | 优势 | 推荐指数 |
|-----|------|------|---------|
| **BAAI/bge-reranker-v2-m3** | HuggingFace | 多语言、性能优异 | ⭐⭐⭐⭐⭐ |
| **BAAI/bge-reranker-base** | HuggingFace | 轻量、快速 | ⭐⭐⭐⭐ |
| **cross-encoder/ms-marco-MiniLM-L-6-v2** | HuggingFace | 英文优化 | ⭐⭐⭐ |

**推荐使用：**
```python
from FlagEmbedding import FlagReranker

reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)

def rerank(query: str, documents: List[str]) -> List[float]:
    pairs = [[query, doc] for doc in documents]
    scores = reranker.compute_score(pairs)
    return scores
```

---

## 四、综合推荐方案

### 4.1 最优免费组合

```python
class FreeAPIIntegrator:
    def __init__(self):
        self.wikipedia_searcher = WikipediaSearcher()
        self.github_searcher = GitHubSearcher()
        self.arxiv_searcher = ArXivSearcher()
        self.duckduckgo_searcher = DuckDuckGoSearcher()
    
    async def search_all(self, query: str) -> dict:
        results = {
            "query": query,
            "wikipedia": await self.wikipedia_searcher.search(query),
            "github": await self.github_searcher.search(query),
            "arxiv": await self.arxiv_searcher.search(query),
            "web": await self.duckduckgo_searcher.search(query)
        }
        return results
```

### 4.2 使用建议

**针对不同查询类型的API选择：**

| 查询类型 | 推荐API | 优先级 |
|---------|---------|--------|
| 事实查询 | Wikipedia | 1 |
| 技术问题 | GitHub | 1 |
| 学术研究 | ArXiv | 1 |
| 通用搜索 | DuckDuckGo | 1 |
| 实时新闻 | DuckDuckGo | 1 |
| 代码示例 | GitHub | 1 |
| 定义解释 | Wikipedia | 1 |

### 4.3 成本估算

**完全免费方案：**
- Wikipedia: $0
- DuckDuckGo: $0
- GitHub: $0（5000次/小时）
- ArXiv: $0
- **总计：$0/月**

**付费扩展方案（如需要）：**
- Google Custom Search: $5/月（100次/天）
- Bing Web Search: $7/月（1000次/月）
- **总计：$12/月**

---

## 五、集成到现有系统

### 5.1 配置文件更新

```python
# src/utils/config.py

class Config:
    def __init__(self):
        # API配置
        self.wikipedia_enabled = True
        self.github_enabled = True
        self.arxiv_enabled = True
        self.duckduckgo_enabled = True
        
        # 可选的付费API
        self.google_api_key = os.getenv("GOOGLE_API_KEY", "")
        self.google_cx = os.getenv("GOOGLE_CX", "")
        self.bing_api_key = os.getenv("BING_API_KEY", "")
```

### 5.2 搜索器集成

```python
# src/core/external_searcher.py

class ExternalSearcher:
    def __init__(self):
        self.wikipedia = WikipediaSearcher()
        self.github = GitHubSearcher()
        self.arxiv = ArXivSearcher()
        self.duckduckgo = DuckDuckGoSearcher()
    
    async def search(self, query: str, sources: List[str] = None) -> List[dict]:
        all_results = []
        
        if sources is None:
            sources = ["wikipedia", "github", "arxiv", "web"]
        
        if "wikipedia" in sources:
            all_results.extend(await self.wikipedia.search(query))
        
        if "github" in sources:
            all_results.extend(await self.github.search(query))
        
        if "arxiv" in sources:
            all_results.extend(await self.arxiv.search(query))
        
        if "web" in sources:
            all_results.extend(await self.duckduckgo.search(query))
        
        return all_results
```

---

## 六、总结

### 推荐的免费API组合：

1. **DuckDuckGo** - 通用网络搜索（无限制）
2. **Wikipedia** - 百科知识（无限制）
3. **GitHub** - 技术文档（5000次/小时）
4. **ArXiv** - 学术论文（无限制）

这个组合完全免费，覆盖了企业助手的主要使用场景，无需任何API密钥即可使用。
