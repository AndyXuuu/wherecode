# 🛰️ WhereCode: 跨时空 AI 协作指挥中心

**WhereCode** 是一套创新的个人开发工作流架构。它将开发者从书房的显示器前解放出来，利用手机作为意图终端，让 PC 成为执行中枢，并与多位 AI 合作伙伴（如 Claude, Gemini）深度协同。

[English](./README.MD) | [简体中文]

---

### 🤖 AI 声明

**本项目所有代码全部由 AI 编写，包括但不限于：Claude (Anthropic)、Gemini (Google)、ChatGPT (OpenAI)、GLM (智谱)、DeepSeek、MiniMax 等 AI 工具与平台。**

AI 在本项目中扮演的角色包括：
* **架构设计**：基于人类意图进行多层逻辑架构的拆解与设计。
* **代码实现**：全量生成后端逻辑、通信协议封装及各模块功能代码。
* **测试与纠错**：编写自动化测试脚本并根据报错信息进行自主修复。
* **文档撰写**：包括本 README、开发计划 (PLAN.md) 以及技术规范。
* **开源合规引导**：协助进行开源协议选型 (AGPL-3.0) 及合规性声明整理。

> **注**：人类开发者在此过程中的角色为 **“架构师”与“决策官”**，负责定义愿景、审核逻辑节点、通过移动端授权关键执行步骤。

---

## 🏗️ 三层协同架构 (The Trinity Architecture)

1.  **指挥中心 (Command Center | 手机/移动端)**
    * **角色**：首席执行官 (CEO)。
    * **职能**：下达战略指令、审批 AI 执行计划、接收异步简报。
2.  **执行中心 (Control Center | 本地 PC 后端)**
    * **角色**：首席运营官 (COO) / 智能中控。
    * **职能**：意图对齐 (Task Manifesto)、插件化插槽路由、严格质检 (Gatekeeper)。
3.  **执行层 (Action Layer | AI Agent 合作伙伴)**
    * **角色**：资深工程师 (Senior Engineers)。
    * **职能**：利用 MCP Skills 读写文件、重构代码、分析日志。

## 🛠️ 核心工作流 (Workflow)

1.  **意图下达**：用户通过手机发送指令（如：“帮我重构登录模块”）。
2.  **计划共识**：执行中心返回“任务草案”，用户在手机端点击“批准”。
3.  **自主开发**：中控分发任务给选定 Agent，AI 自主搬砖。
4.  **严格质检**：改动完成后自动运行 pytest。若失败，AI 自主修复。
5.  **异步简报**：用户收到包含变更统计和测试状态的消息推送。
6.  **物理终审**：用户回到电脑前在大屏幕上进行最终 Diff 审查与合并。

## 🧩 技能与协议 (Skills & Protocols)
- **MCP (Model Context Protocol)**：系统核心通信协议，确保工具调用的标准化。
- **通信隧道**：支持插件化隧道接口（CF Tunnel, frp, 物理 IP），实现安全远程接入。

## 📅 路线图 (Roadmap)
- [ ] **Phase 1**: 建立基于通用通信隧道的安全双向链路。
- [ ] **Phase 2**: 实现基于 MCP 的 Agent 插件化管理系统。
- [ ] **Phase 3**: 开发手机端极简 UI 与 MiniMax 语音识别模块。
- [ ] **Phase 4**: 构建基于 AI 的任务总结与推送引擎。

---

## 📜 开源协议

本项目基于 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源。
Copyright (C) 2026 AndyXuuu [andy1770@proton.me](mailto:andy1770@proton.me)

**共同作者 (Co-Authored-By):**
- Claude Opus 4.6 <noreply@anthropic.com>
- ChatGPT <noreply@openai.com>
- Gemini <noreply@google.com>
- GLM <noreply@zhipuai.cn>
- DeepSeek <noreply@deepseek.com>
- MiniMax <noreply@minimaxi.com>
