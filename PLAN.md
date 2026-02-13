# WhereCode Phase 1 实现计划 — 通信闭环

## Context
WhereCode 已从"远程终端"升级为**三层架构的 AI 指挥中心**。手机端不再是 Terminal，而是极简的卡片式对话界面。Phase 1 目标：建立 FastAPI + WebSocket 通信闭环，手机可远程发送指令并看到卡片式响应。

## 项目结构（13 个文件）
```
wherecode/
├── backend/
│   ├── __init__.py          # 包标记
│   ├── models.py            # Pydantic 模型：消息、卡片、会话
│   ├── auth.py              # Token 认证（REST + WebSocket）
│   ├── session.py           # 会话管理（内存存储，历史回放）
│   ├── main.py              # FastAPI 入口、WebSocket、REST、静态文件
│   └── agents/
│       └── __init__.py      # Agent 接口定义（Phase 2 扩展点）
├── frontend/
│   ├── index.html           # SPA：认证屏 + 卡片对话屏
│   ├── css/
│   │   └── style.css        # 移动优先、暗色主题、卡片样式
│   └── js/
│       ├── api.js           # WebSocket 客户端封装（重连、事件）
│       └── app.js           # 应用逻辑：认证、卡片渲染、命令发送
├── requirements.txt         # fastapi, uvicorn, pydantic, python-dotenv
├── .env.example
└── run.sh
```

## WebSocket 协议设计

### 客户端 → 服务端
```json
{"type": "command", "id": "<uuid>", "payload": {"text": "重构登录模块"}}
{"type": "ping", "id": "<uuid>", "payload": {}}
{"type": "history_request", "id": "<uuid>", "payload": {"limit": 50}}
```

### 服务端 → 客户端
```json
{
  "type": "card",
  "id": "<uuid>",
  "ref_id": "<client_msg_id>",
  "timestamp": "ISO8601",
  "payload": {
    "card_type": "status|result|error|echo|system",
    "title": "Command Received",
    "body": "Processing: **重构登录模块** (markdown)",
    "metadata": {},
    "progress": null,
    "actions": []
  }
}
```
- `card_type` 是核心 UI 单元，Phase 2+ 扩展 `test_result`, `diff`, `agent_activity`
- 二进制/文本混合协议改为**纯 JSON 文本**（卡片 UI 无需二进制流）

### 连接生命周期
1. `ws://host/ws?token=TOKEN` → 验证 token
2. 服务端发送 `session_info`（session_id, history_count）
3. 客户端可请求 `history_request` 回放历史卡片
4. 断线重连时自动恢复会话

## 核心模块说明

### `backend/models.py`
- Pydantic v2 discriminated unions：`ClientMessage` / `ServerMessage`
- `CardPayload`：card_type + title + body(markdown) + metadata(扩展) + progress + actions
- `Session`：session_id + history(CardMessage 列表)

### `backend/main.py`
- `process_command()` 是关键接缝：
  - Phase 1：echo 模式 + `!` 前缀执行 shell 命令（演示用）
  - Phase 2：替换为 `agent_router.dispatch()`
- WebSocket 处理：按 `type` 路由消息，支持 command/ping/history_request

### `backend/agents/__init__.py`
- 定义 `AgentBase` 抽象接口（execute, health_check）
- Phase 2 在此添加 claude_agent.py, gemini_agent.py, router.py, agents.yaml

### `frontend/js/api.js`
- WebSocket 封装：事件驱动（on card/session_info/history/error/status_change）
- 指数退避重连：2s→4s→8s...最大 30s
- 30s 心跳 ping

### `frontend/js/app.js`
- 卡片渲染引擎：按 card_type 染不同边框色（accent/green/red/gray/yellow）
- 用户命令显示为右对齐气泡
- 简易 markdown 渲染（bold/code/code block）
- 历史回放：重连后自动加载

### `frontend/css/style.css`
- 移动优先（基准 320px），44px 触控目标，16px input 防 iOS 缩放
- 暗色主题（#0a0e17 背景）
- 卡片动画（fadeInUp）、状态圆点（connected/disconnected/connecting）
- `@media (min-width: 1920px)` 为 Phase 4 TV 大屏预留

## 实现顺序
1. `requirements.txt` + `.env.example` + `run.sh`
2. `backend/__init__.py` + `backend/models.py`
3. `backend/auth.py` + `backend/session.py`
4. `backend/agents/__init__.py`（接口 stub）
5. `backend/main.py`
6. `frontend/css/style.css`
7. `frontend/js/api.js` + `frontend/js/app.js`
8. `frontend/index.html`

## Phase 2-4 扩展点
| Phase | 改动 | 插入点 |
|-------|------|--------|
| Phase 2: Agent 路由 | agents/ 下新增具体 agent + router + agents.yaml | `process_command()` → `router.dispatch()` |
| Phase 2: PTY 封装 | agents/pty_wrapper.py | Agent 内部用 PTY 执行 CLI，输出转为 card 流 |
| Phase 3: 自动测试 | backend/testing.py | Agent 执行后调用，结果为 test_result 卡片 |
| Phase 3: 推送通知 | backend/push.py + httpx | 任务完成后 POST 到 Bark API |
| Phase 4: TV 大屏 | CSS TV 媒体查询 + dashboard.js | 同一 WebSocket，不同渲染布局 |

## 验证方式
```bash
pip install -r requirements.txt
cp .env.example .env  # 编辑 token
bash run.sh
# 浏览器打开 http://localhost:8000
# 输入 token → 发送命令 → 看到卡片响应
# 测试：!ls 执行 shell、断线重连、历史回放
```
