# Action Layer 说明

本目录承载 AI Agent 能力层，负责执行具体任务（编码、测试、诊断、摘要）。

## 目录角色

- 抽象 Agent 接口（统一 execute/health_check/capability）
- 管理多 Agent 实现（如 coding/test/review agent）
- 输出可回放的结构化执行结果给 Control Center
  - `services/runtime_execution.py`：执行决策服务（角色解析、LLM/mock 执行选择、返回契约）
  - `services/llm_executor.py`：LLM 路由与执行器组装（OpenAI-compatible / Ollama）
  - `services/llm_executor_runtime_helpers.py`：LLM HTTP 调用、响应解析、路由选择辅助逻辑
  - `services/llm_executor_exceptions.py`：LLM 配置与执行异常类型

## 设计原则

- 所有 Agent 必须遵循统一输入输出模型。
- 失败必须返回可诊断上下文，不允许静默失败。
- 执行过程可流式回传进度，便于移动端卡片展示。

## 本地运行

```bash
bash action_layer/run.sh
```

默认地址：`http://127.0.0.1:8100`

可用检查接口：

- `GET /healthz`
- `GET /capabilities`
- `POST /execute`（默认仅 `llm`；`mock` 仅诊断模式）

可选环境变量（放在 `action_layer/.env`）：

- `ACTION_LAYER_HOST`（默认 `127.0.0.1`）
- `ACTION_LAYER_PORT`（默认 `8100`）
- `ACTION_LAYER_REQUIRE_LLM`（默认 `true`，未就绪时服务启动失败）
- `ACTION_LAYER_EXECUTION_MODE`（`mock`/`llm`，默认 `llm`）
- `ACTION_LAYER_LLM_PROVIDER`（支持 `openai-compatible` / `ollama`）
- `ACTION_LAYER_LLM_BASE_URL`（默认 `https://api.openai.com`）
- `ACTION_LAYER_LLM_WIRE_API`（`chat_completions` / `responses`，默认 `chat_completions`）
- `ACTION_LAYER_LLM_API_KEY`（可选；OpenAI 通常需要）
- `ACTION_LAYER_LLM_MODEL`（`mode=llm` 必填）
- `ACTION_LAYER_LLM_TIMEOUT_SECONDS`（默认 `120`）
- `ACTION_LAYER_LLM_TEMPERATURE`（默认 `0.2`）
- `ACTION_LAYER_LLM_MAX_TOKENS`（默认 `800`）
- `ACTION_LAYER_LLM_USER_AGENT`（默认 `wherecode-action-layer/0.1`）
- `ACTION_LAYER_LLM_MAX_RETRIES`（默认 `2`，仅重试 5xx/网络错误）
- `ACTION_LAYER_LLM_RETRY_DELAY_SECONDS`（默认 `0.6`）
- `ACTION_LAYER_LLM_SYSTEM_PROMPT`（可选，建议短且结构化）
- `ACTION_LAYER_LLM_ROUTE_DEFAULT`（默认 `default`）
- `ACTION_LAYER_LLM_ROUTE_BY_ROLE_JSON`（可选，按角色路由 target）
- `ACTION_LAYER_LLM_ROUTE_BY_MODULE_PREFIX_JSON`（可选，按模块前缀路由 target）
- `ACTION_LAYER_AGENT_RULES_REGISTRY_FILE`（默认 `control_center/capabilities/agent_rules_registry.json`，Action Layer 角色映射注册表）
- `ACTION_LAYER_AGENT_RULES_SCOPES`（默认 `subproject,main`，注册表 scope 读取优先级）
- `ACTION_LAYER_LLM_TARGETS_JSON`（可选，多 target 配置；设置后覆盖单 target 变量）
- `ACTION_LAYER_USE_CODEX_CONFIG`（默认 `true`，自动读取用户本机 Codex 配置作为缺省值）
- `ACTION_LAYER_CODEX_CONFIG_PATH`（可选，默认 `${CODEX_HOME:-$HOME/.codex}/config.toml`）
- `ACTION_LAYER_CODEX_AUTH_PATH`（可选，默认 `${CODEX_HOME:-$HOME/.codex}/auth.json`）

运行时环境加载顺序（`action_layer/run.sh`）：

1. 用户 Codex 配置缺省值（`~/.codex/config.toml` + `~/.codex/auth.json`，仅在对应 `ACTION_LAYER_*` 变量为空时回填）
2. `ACTION_LAYER_SYSTEM_ENV_FILES`（默认 `/etc/wherecode/action_layer.env:$HOME/.wherecode/action_layer.env`，按顺序加载）
3. `action_layer/.env`（本地覆盖）
4. 当前 shell 已导出的环境变量（可直接提供 `OPENAI_API_KEY` 等）

自动回填字段：

- `ACTION_LAYER_EXECUTION_MODE=llm`
- `ACTION_LAYER_REQUIRE_LLM=true`
- `ACTION_LAYER_LLM_PROVIDER`
- `ACTION_LAYER_LLM_BASE_URL`
- `ACTION_LAYER_LLM_WIRE_API`
- `ACTION_LAYER_LLM_MODEL`
- `ACTION_LAYER_LLM_API_KEY`（优先 `~/.codex/auth.json` 的 `OPENAI_API_KEY`）

启用真实 LLM（OpenAI-compatible）示例：

```bash
ACTION_LAYER_REQUIRE_LLM=true
ACTION_LAYER_EXECUTION_MODE=llm
ACTION_LAYER_LLM_PROVIDER=openai-compatible
ACTION_LAYER_LLM_BASE_URL=https://api.openai.com
ACTION_LAYER_LLM_WIRE_API=chat_completions
ACTION_LAYER_LLM_API_KEY=sk-xxxxx
ACTION_LAYER_LLM_MODEL=gpt-4.1-mini
```

说明：

- `openai-compatible` 支持：
  - `ACTION_LAYER_LLM_WIRE_API=chat_completions` -> `POST /v1/chat/completions`
  - `ACTION_LAYER_LLM_WIRE_API=responses` -> `POST /v1/responses`
- `ollama` 通过 `POST /api/chat`（本地模型常用）。
- 当 `ACTION_LAYER_REQUIRE_LLM=true` 时：
  - 配置错误会阻止 Action Layer 启动；
  - `/execute` 在 LLM 未就绪时返回 `503`。
- 期望模型输出 JSON：`status`、`summary`、`discussion`（可选）、`metadata`（可选）。
- 非 JSON 输出会自动降级为 `success + 文本摘要`，保证协议可用。

多 target 路由示例：

```bash
ACTION_LAYER_EXECUTION_MODE=llm
ACTION_LAYER_LLM_TARGETS_JSON='{"openai":{"provider":"openai-compatible","base_url":"https://api.openai.com","wire_api":"chat_completions","api_key_env":"OPENAI_API_KEY","model":"gpt-4.1-mini"},"gateway":{"provider":"openai-compatible","base_url":"https://gateway.example.com","wire_api":"responses","api_key_env":"GATEWAY_API_KEY","model":"qwen-max"},"local":{"provider":"ollama","base_url":"http://127.0.0.1:11434","model":"qwen2.5:7b"}}'
ACTION_LAYER_LLM_ROUTE_DEFAULT=openai
ACTION_LAYER_LLM_ROUTE_BY_ROLE_JSON='{"doc-manager":"gateway","qa-test":"local"}'
ACTION_LAYER_LLM_ROUTE_BY_MODULE_PREFIX_JSON='{"module_x":"gateway"}'
```

仅本地诊断需要 mock 时：

```bash
ACTION_LAYER_REQUIRE_LLM=false
ACTION_LAYER_EXECUTION_MODE=mock
```

角色 profile（v3）：

- 路径：`action_layer/agents/<role>/AGENTS.md`（兼容回退：`agent.md`）
- 约束：SubAgent 仅允许读取本角色 profile

角色映射来源（v3）：

- Action Layer 优先从 `ACTION_LAYER_AGENT_RULES_REGISTRY_FILE` 加载 role->executor 映射。
- 若注册表加载失败，回退内置默认映射，保证服务可启动。
