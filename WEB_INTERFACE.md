# Web界面使用指南（Aurora Editorial 2.1）

## 概述

Web 界面已升级为 **Aurora Editorial 2.1**：

- 视觉：浅色玻璃主导 + 暗色切换，动态 Aurora 背景（低振幅慢速）
- 布局：桌面双栏（知识库 / 对话），移动端双 Tab（Chat / Knowledge）
- 会话：按 `session_id` 隔离历史（24 小时 TTL）
- 回复：SSE 流式回答，失败自动回退普通接口
- 来源：助手回答支持“引用来源”折叠展示与一键提问

## 启动Web服务器

```bash
python -m src.main web
```

默认访问地址：

- 本地：`http://localhost:8000`
- 局域网：`http://<服务器IP>:8000`

开发模式（自动重载）：

```bash
python -m src.main web --reload
```

## 前端功能说明

### 1. 对话窗口

- 支持多轮对话（会话历史按 `session_id` 隔离）
- 发送优先走流式接口，失败自动回退普通接口
- 流式渲染做了 `requestAnimationFrame` 批量刷帧，长回答更稳定
- 流式结束后再进行 Markdown + 代码高亮渲染
- 助手回答下方来源默认折叠，展开可“加入提问”或“直接提问”

### 2. 知识库区域

- 输入即搜（300ms 防抖）+ Enter 立即触发
- 结果卡片展示标题、来源、相似度、摘要
- 卡片操作区主按钮为“直接提问”，次按钮为“加入提问”
- 顶部展示文档总数与分块总数

### 3. 状态反馈与交互

- `系统状态` 使用右上角玻璃 Popover 展示，不再使用浏览器 `alert`
- `清空会话` 使用自定义确认模态框，不再使用浏览器 `confirm`
- 错误统一通过 `role=alert` + Toast 双通道反馈
- 发送按钮具备 `idle / sending / sent` 三态视觉反馈

### 4. 响应式与可访问性

- 桌面端双栏并行操作，聊天区视觉优先
- 移动端底部双 Tab，切换时保留 Chat 与 Knowledge 的滚动位置
- 输入区在 Chat 视图底部稳定停靠，避免跳动
- 支持 `focus-visible`、键盘可达、`prefers-reduced-motion` 自动降级

## API接口（无变更）

本次 2.1 升级仅改前端表现层与交互层，API 与字段保持兼容：

- `POST /api/query`
- `POST /api/query/stream`
- `POST /api/knowledge/search`
- `GET /api/knowledge/overview`
- `GET /api/sessions/{session_id}/history`
- `DELETE /api/sessions/{session_id}/history`

兼容旧接口：

- `POST /api/clear-history`
- `GET /api/history`

## 部署建议

生产环境建议：

```bash
uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --workers 4
```

## 故障排除

- 流式无输出：检查反向代理是否禁用缓冲（`X-Accel-Buffering: no`）
- 会话不连续：确认 `assistant_session_id` 未被清除
- 知识库为空：检查是否已完成初始化（或触发接口懒加载）
- 动画不生效：检查是否系统开启“减少动态效果”

## 参考

- [README.md](README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DEMO_SCENARIOS.md](DEMO_SCENARIOS.md)
