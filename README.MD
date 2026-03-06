# 🛰️ WhereCode: The Intertemporal AI Orchestrator

> **⚡ Fuel the Machine**: This project is 100% AI-authored. To help us maintain high-quality model outputs and explore the boundaries of MCP, consider sponsoring **Tokens** or **API Credits**.
> **Sponsorship / Contact**: [andy1770@proton.me](mailto:andy1770@proton.me)

**WhereCode** is a pioneering cross-device development framework. It liberates developers from their desks, using mobile devices as intent terminals, PC as the execution engine, and collaborating with a diverse team of AI partners.

[English](./README.md) | [简体中文](./README.zh-CN.md)

---

## 🤖 AI Declaration (AI 声明)

**Every line of code in this repository is authored by AI, including but not limited to: Claude (Anthropic), Gemini (Google), ChatGPT (OpenAI), GLM (Zhipu), DeepSeek, and MiniMax.**

AI's roles in this project include:
- **Architecture Design**: Deconstructing and designing multi-layer logic based on human intent.
- **Implementation**: Generating full backend logic, protocol encapsulation, and functional modules.
- **QA & Debugging**: Writing automated test scripts and self-healing based on error logs.
- **Documentation**: Authoring this README, PLAN.md, and technical specifications.
- **Compliance Guidance**: Selecting open-source licenses (AGPL-3.0) and organizing declarations.

> **Note**: The human developer acts as the **"Architect" and "Decision Maker"**, defining the vision, auditing logic nodes, and authorizing key execution steps via mobile.

## 🏗️ The Trinity Architecture (三层协同架构)

1. **Command Center (Mobile)**
   - **Role**: CEO.
   - **Function**: Strategic instructions, task approval, and resource allocation via a minimalist dialogue UI.
2. **Control Center (Local PC)**
   - **Role**: COO / Orchestrator.
   - **Function**: Intent alignment (Task Manifesto), MCP-based tool routing, and automated Gatekeeper (testing).
3. **Action Layer (AI Agents)**
   - **Role**: Senior Engineers.
   - **Function**: Executing file operations, refactoring, and providing technical feedback via MCP Skills.

## 🛠️ Workflow (核心工作流)

1. **Intent**: User sends a command via mobile (e.g., "Refactor login module").
2. **Consensus**: PC returns a "Task Manifesto"; user approves.
3. **Autonomy**: Orchestrator assigns tasks to specific Agents (e.g., Claude-3.5).
4. **QA**: PC runs `pytest` automatically; AI fixes issues autonomously if tests fail.
5. **Briefing**: User receives a push notification with a summary of changes.
6. **Final Review**: User performs a physical merge review at the PC.

## 🧩 Protocols & Skills (技能与协议)

- **MCP (Model Context Protocol)**: The core protocol for standardized tool access.
- **Communication Tunnel**: Pluggable support for secure remote access (CF Tunnel, frp, Direct IP).

## 📦 Monorepo Dependency Policy (Monorepo 依赖策略)

This repository contains three subprojects with different stacks and dependency sets.

- `command_center/`: Next.js + Tailwind (Node.js ecosystem)
- `control_center/`: FastAPI + Pydantic (Python ecosystem)
- `action_layer/`: Agent runtime and integrations (can vary by provider/runtime)

To avoid cross-stack coupling, dependency and environment files must stay inside each subproject.
Root-level dependency files (such as `requirements.txt`, `.env.example`, `run.sh`) are intentionally not used.

Unified subproject command entry:

```bash
bash scripts/stationctl.sh install all
bash scripts/stationctl.sh dev all
bash scripts/stationctl.sh start all
bash scripts/stationctl.sh status all
bash scripts/stationctl.sh stop all
bash scripts/stationctl.sh check
bash scripts/stationctl.sh check quick
bash scripts/stationctl.sh check release
```

## 📅 Plan & Milestones (计划与里程碑)

### Completed (已完成)

- [x] `K1-K50`: workflow orchestration, role pipeline, policy gates, state persistence.
- [x] `M-TEST-ENTRY`: milestone gate passed.
- [x] `TST1`: integration matrix + rollback/policy regression completed.
- [x] `BOUNDARY-1`: subproject workspace (`project/`) switched to automation-managed only.
- [x] `MB1` (2026-03-06): decompose -> orchestrate -> recover API closed loop.
- [x] `MB2` (2026-03-06): command intent -> orchestrate flow trigger and state persistence.
- [x] `MB3` (2026-03-06): stock-sentiment dry-run + recover + execute full-loop evidence captured.
- [x] `MB4` (2026-03-06): release baseline + readiness evidence package + go/no-go draft completed.
- [x] `MB5` (2026-03-06): acceptance package + strict milestone gate + launch recommendation completed.
- [x] `REL1` (2026-03-06): bilingual release notes + signoff package completed.
- [x] `GO1` (2026-03-06): launch rehearsal + post-launch sanity checklist completed.
- [x] `GO2` (2026-03-06): stability checkpoint + observation queue completed.
- [x] `GO3` (2026-03-06): target-host validation package completed (readiness not ready due provider execution failures).
- [x] `GO4` (2026-03-06): local codex-config alignment + provider execute path + recovery drill rerun passed.

### Milestone Plan (Expected)（里程碑计划（预期））

- [x] `MB3` (target: 2026-03-08): real stock-sentiment project dry-run (single-host).
- [x] `MB4` (target: 2026-03-09): local release readiness package green.
- [x] `MB5` (target: 2026-03-10): go-live decision package ready.
- [x] `GO1` (target: 2026-03-11): launch rehearsal and post-checklist complete.
- [x] `GO2` (target: 2026-03-12): stability observation report and issue queue complete.
- [x] `GO3` (target: 2026-03-13): target-host provider/recovery validation complete.
- [x] `GO4` (target: 2026-03-14): provider/recovery remediation and rerun pass.

### Current Sprint (GO4 Remediation)（当前冲刺）

- [x] `GO4-T1`: remediate provider/network access on target host.
- [x] `GO4-T2`: rerun provider check + recovery drill until pass.

---

## 📜 License (开源协议)

Licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.
Copyright (C) 2026 AndyXuuu [andy1770@proton.me](mailto:andy1770@proton.me)

**Co-Authored-By:**
- Claude Opus 4.6 <noreply@anthropic.com>
- ChatGPT <noreply@openai.com>
- Gemini <noreply@google.com>
- GLM <noreply@zhipuai.cn>
- DeepSeek <noreply@deepseek.com>
- MiniMax <noreply@minimaxi.com>
