🛰️ WhereCode: 跨时空 AI 协作指挥中心
WhereCode 是一套创新的个人开发工作流架构。它将开发者从书房的显示器前解放出来，利用手机作为意图终端，让 PC 成为执行中枢，并与多位 AI 合作伙伴（如 Claude, Gemini）深度协同。

核心哲学：人类负责直觉与战略决策，AI 负责逻辑与具体执行。彼此是平等的合作伙伴，共同完成复杂的工程目标。

🏗️ 三层协同架构 (The Trinity Architecture)
1. 指挥中心 (Command Center | 手机/移动端)
角色：首席执行官 (CEO)。

交互：极简对话流，支持语音/文字意图输入。

职能：下达战略指令、审批 AI 执行计划、接收异步简报、进行资源配置。

愿景：让你在公园散步、在电视前休息时，依然能掌控项目的生命周期。

2. 执行中心 (Control Center | 本地 PC 后端)
角色：首席运营官 (COO) / 智能中控。

职能：

意图对齐：将模糊意图拆解为标准任务包（Task Manifesto）。

插槽路由：根据任务特性及用户会员权益（MCP 协议），调用最适合的 AI Agent。

严格质检 (Gatekeeper)：强制执行自动化测试（Unit/Integration Tests），拦截幻觉错误。

异步通知：任务完成后，自动通过 Webhook 推送精炼报告。

3. 执行层 (Action Layer | AI Agent 合作伙伴)
角色：资深工程师 (Senior Engineers)。

职能：

具体作业：利用 MCP Skills 读写文件、重构代码、分析日志。

技术反馈：遇到分歧时主动求助，完成任务后提交变更明细与待办建议。

🛠️ 核心工作流 (Workflow)
意图下达：用户通过手机发送：“帮我重构登录模块，支持海外手机号验证。”

计划共识：执行中心返回一份“任务草案”，用户在手机端点击“批准”。

自主开发：中控分发任务给选定的 Agent（如 Claude-3.5）。AI 开始搬砖，期间用户无需在线。

严格质检：改动完成后，系统自动运行 pytest。若测试失败，AI 自主修复；若成功，生成简报。

异步简报：用户收到消息推送，包含：完成步骤、变更统计、测试状态、下一步建议。

物理终审：用户回到电脑前，在大屏幕上审查最终 Diff，完成物理合并（Merge）。

🧩 技能与协议 (Skills & Protocols)
MCP (Model Context Protocol)：系统核心通信协议，确保 AI 能标准化地访问本地文件、终端和测试工具。

动态 Agent 插槽：

Logic_Expert (Claude): 负责复杂业务逻辑。

Context_Master (Gemini): 负责分析长文档与全库扫描。

Local_Sentinel (Llama/DeepSeek): 负责本地私密任务。

Skill Sets：

File_Operator: 受限的文件读写。

Test_Runner: 自动化测试执行。

Report_Generator: 降噪后的任务总结提取。

🛡️ 安全与管理原则
伙伴关系：AI 不是工具，是具备技术专长的合作伙伴。系统设计应体现双向透明。

权力边界：手机端拥有“终极否决权”；执行中心拥有“环境隔离权”；AI 拥有“执行自主权”。

物理安全：所有高危操作（如生产部署）必须在物理电脑前进行人工二次确认。

📅 路线图 (Roadmap)
[ ] Phase 1: 建立基于 Cloudflare Tunnel 的安全通信链路。

[ ] Phase 2: 实现基于 MCP 的 Agent 插件化管理系统。

[ ] Phase 3: 开发手机端极简对话 UI 与语音识别模块。

[ ] Phase 4: 构建基于 AI 的测试报告总结与推送引擎。

WhereCode —— 让代码在魔法发生的地方流淌。

## 📜 开源协议

本项目基于 [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html) 开源。

Copyright (C) 2026 AndyXuuu <andy1770@proton.me>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.