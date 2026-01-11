# 快速启动指南

## 前置要求

- Python 3.10 或更高版本
- 网络连接（用于下载依赖和搜索功能）
- 智谱AI API密钥（已配置在env.example中）

## 安装步骤

### 1. 创建虚拟环境(Conda环境也可以)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**注意**: 首次安装sentence-transformers时会下载模型，可能需要几分钟时间。

### 3. 配置环境变量

复制 `env.example` 为 `.env`：

```bash
# Windows
copy env.example .env

# Linux/macOS
cp env.example .env
```

API密钥已预配置在env.example中，如果需要修改，请编辑 `.env` 文件。

### 4. 初始化知识库

首次使用前，必须初始化知识库向量存储：

```bash
python -m src.main init
```

这将：
- 解析 `Knowledge Base` 目录下的所有Markdown文件
- 生成文本嵌入
- 存储到ChromaDB向量数据库

**预计时间**: 1-3分钟（取决于文件大小和模型下载）

## 使用

### 交互式对话

启动交互式对话界面：

```bash
python -m src.main chat
```

### 单次查询

```bash
python -m src.main query "公司的编码规范是什么？"
```

### 查看系统状态

```bash
python -m src.main status
```

## 常见问题

### Q: 初始化知识库时出错

**A**: 确保：
1. `Knowledge Base` 目录存在且包含Markdown文件
2. 有足够的磁盘空间
3. 网络连接正常（首次需要下载模型）

### Q: API调用失败

**A**: 检查：
1. `.env` 文件中的API密钥是否正确
2. 网络连接是否正常
3. API密钥是否有足够的余额

### Q: 搜索功能不工作

**A**: 
1. 检查网络连接
2. 确认 `SEARCH_ENABLED=true` 在 `.env` 文件中
3. DuckDuckGo可能在某些地区受限

### Q: 响应速度慢

**A**: 
- 首次查询需要加载模型，会较慢
- 后续查询会更快
- 可以禁用流式输出以提升速度（设置 `STREAM_ENABLED=false`）

## 下一步

- 阅读 [README.md](README.md) 了解完整功能
- 查看 [ARCHITECTURE.md](ARCHITECTURE.md) 了解系统架构
- 参考 [DEMO_SCENARIOS.md](DEMO_SCENARIOS.md) 查看演示场景
