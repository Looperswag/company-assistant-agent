# Web界面使用指南

## 概述

Company Assistant Agent 提供了两种使用方式：
1. **Web界面** - 适合所有用户，无需命令行知识
2. **CLI界面** - 适合开发者和高级用户

两种方式使用相同的后端API和服务，只是前端交互方式不同。

## 启动Web服务器

### 基本启动

```bash
python -m src.main web
```

默认配置：
- 主机：`0.0.0.0`（所有网络接口）
- 端口：`8000`

### 自定义配置

```bash
# 指定主机和端口
python -m src.main web --host 127.0.0.1 --port 8080

# 开发模式（自动重载）
python -m src.main web --reload
```

### 访问Web界面

启动后，在浏览器中访问：
- 本地访问：`http://localhost:8000`
- 局域网访问：`http://<服务器IP>:8000`

## Web界面功能

### 1. 对话界面

- **输入框**：在底部输入您的问题
- **发送按钮**：点击发送或按Enter键
- **消息显示**：
  - 用户消息显示在右侧（紫色）
  - 助手回复显示在左侧（白色）
  - 支持Markdown格式渲染

### 2. 功能按钮

- **清空历史**：清除当前对话历史
- **系统状态**：查看系统运行状态和知识库信息

### 3. 特性

- ✨ 现代化的UI设计
- 📱 响应式布局，支持移动设备
- ⚡ 实时响应和加载动画
- 🎨 美观的消息气泡设计
- 🔄 自动滚动到最新消息

## API接口

Web界面使用RESTful API与后端通信。API端点包括：

### POST /api/query

发送查询请求。

**请求体：**
```json
{
  "query": "公司的编码规范是什么？",
  "use_history": true,
  "session_id": "optional_session_id"
}
```

**响应：**
```json
{
  "response": "根据ZURU Melon编码规范...",
  "session_id": "default"
}
```

### POST /api/clear-history

清空对话历史。

**请求体：**
```json
{
  "session_id": "optional_session_id"
}
```

**响应：**
```json
{
  "status": "success",
  "message": "对话历史已清空"
}
```

### GET /api/history

获取对话历史。

**响应：**
```json
{
  "history": [
    {"role": "user", "content": "问题1"},
    {"role": "assistant", "content": "回答1"}
  ]
}
```

### GET /api/status

获取系统状态。

**响应：**
```json
{
  "status": "ok",
  "message": "系统运行正常。知识库包含 150 个文档块。"
}
```

### GET /health

健康检查端点。

**响应：**
```json
{
  "status": "healthy"
}
```

## 部署建议

### 开发环境

```bash
python -m src.main web --reload
```

### 生产环境

使用生产级ASGI服务器：

```bash
# 使用uvicorn
uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --workers 4

# 或使用gunicorn + uvicorn workers
gunicorn src.web.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker部署（可选）

创建 `Dockerfile`：

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.web.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

构建和运行：

```bash
docker build -t company-assistant .
docker run -p 8000:8000 company-assistant
```

## 安全考虑

### CORS配置

当前配置允许所有来源访问（开发环境）。生产环境应限制：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # 指定允许的域名
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### 认证（可选）

如需添加认证，可以使用FastAPI的依赖注入：

```python
from fastapi import Depends, HTTPException, Header

async def verify_token(x_token: str = Header(...)):
    if x_token != "your-secret-token":
        raise HTTPException(status_code=403, detail="Invalid token")
    return x_token

@app.post("/api/query")
async def query(request: QueryRequest, token: str = Depends(verify_token)):
    ...
```

## 故障排除

### 端口被占用

如果8000端口被占用，使用其他端口：

```bash
python -m src.main web --port 8080
```

### 无法访问

1. 检查防火墙设置
2. 确认使用 `0.0.0.0` 而不是 `127.0.0.1`（如果需要外部访问）
3. 检查服务器是否正在运行

### API错误

查看服务器日志了解详细错误信息。日志文件位置在配置中指定（默认：`assistant.log`）。

## 与CLI的对比

| 特性 | Web界面 | CLI界面 |
|------|---------|---------|
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 美观度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 功能完整性 | ✅ 相同 | ✅ 相同 |
| 适合用户 | 所有用户 | 开发者/技术用户 |
| 移动支持 | ✅ | ❌ |
| 部署复杂度 | 中等 | 低 |

## 下一步

- 阅读 [README.md](README.md) 了解完整功能
- 查看 [ARCHITECTURE.md](ARCHITECTURE.md) 了解系统架构
- 参考 [DEMO_SCENARIOS.md](DEMO_SCENARIOS.md) 查看演示场景
