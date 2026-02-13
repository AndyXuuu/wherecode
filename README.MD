🛰️ WhereCode: Cross-Spacetime AI Collaboration Command Center

[简体中文](./README.zh-CN.md)

WhereCode is an innovative personal development workflow architecture. It frees developers from being tied to their desk monitors, using a phone as the intent terminal, a PC as the execution hub, and deeply collaborating with multiple AI partners (e.g., Claude, Gemini).

Core Philosophy: Humans handle intuition and strategic decisions; AI handles logic and concrete execution. They are equal partners, working together to accomplish complex engineering goals.

🏗️ The Trinity Architecture
1. Command Center (Mobile)
Role: Chief Executive Officer (CEO).

Interaction: Minimalist conversational flow, supporting voice/text intent input.

Functions: Issue strategic directives, approve AI execution plans, receive async briefings, manage resource allocation.

Vision: Stay in control of the project lifecycle while walking in the park or relaxing on the couch.

2. Control Center (Local PC Backend)
Role: Chief Operating Officer (COO) / Intelligent Hub.

Functions:

Intent Alignment: Decompose vague intents into standardized task packages (Task Manifesto).

Slot Routing: Invoke the most suitable AI Agent based on task characteristics and user permissions (MCP Protocol).

Strict QA (Gatekeeper): Enforce automated testing (Unit/Integration Tests), intercept hallucination errors.

Async Notification: Automatically push refined reports via Webhook upon task completion.

3. Action Layer (AI Agent Partners)
Role: Senior Engineers.

Functions:

Task Execution: Use MCP Skills to read/write files, refactor code, analyze logs.

Technical Feedback: Proactively seek help when encountering disagreements, submit change details and follow-up suggestions after task completion.

🛠️ Workflow
Intent Dispatch: User sends via phone: "Help me refactor the login module to support international phone number verification."

Plan Consensus: The Control Center returns a "task draft", user taps "Approve" on mobile.

Autonomous Development: The hub distributes tasks to the selected Agent (e.g., Claude-3.5). AI starts working; user doesn't need to be online.

Strict QA: After changes are complete, the system automatically runs pytest. If tests fail, AI self-repairs; if successful, generates a briefing.

Async Briefing: User receives a push notification containing: completed steps, change statistics, test status, next-step suggestions.

Physical Review: User returns to the computer, reviews the final Diff on the big screen, and completes the physical merge.

🧩 Skills & Protocols
MCP (Model Context Protocol): The core system communication protocol, ensuring AI can access local files, terminals, and testing tools in a standardized way.

Dynamic Agent Slots:

Logic_Expert (Claude): Handles complex business logic.

Context_Master (Gemini): Handles long document analysis and full-repo scanning.

Local_Sentinel (Llama/DeepSeek): Handles local private tasks.

Skill Sets:

File_Operator: Restricted file read/write.

Test_Runner: Automated test execution.

Report_Generator: Noise-reduced task summary extraction.

🛡️ Security & Management Principles
Partnership: AI is not a tool — it is a partner with technical expertise. System design should reflect bidirectional transparency.

Authority Boundaries: Mobile holds the "ultimate veto power"; Control Center holds "environment isolation rights"; AI holds "execution autonomy".

Physical Security: All high-risk operations (e.g., production deployment) require in-person secondary confirmation at the physical computer.

📅 Roadmap
[ ] Phase 1: Establish a secure communication link based on Cloudflare Tunnel.

[ ] Phase 2: Implement an MCP-based Agent plugin management system.

[ ] Phase 3: Develop a minimalist mobile conversational UI and voice recognition module.

[ ] Phase 4: Build an AI-powered test report summarization and push notification engine.

WhereCode — Let code flow where the magic happens.

## 🤖 AI Declaration

All code in this project is entirely written by AI, including but not limited to: Claude (Anthropic), Gemini (Google), ChatGPT (OpenAI), GLM (Zhipu AI), DeepSeek, MiniMax, and other AI tools and platforms.

The roles AI plays in this project include but are not limited to:

- **Architecture Design**: Decomposing and designing multi-layer logical architectures based on human intent.
- **Code Implementation**: Generating backend logic, communication protocol encapsulation, and functional code for all modules.
- **Testing & Debugging**: Writing automated test scripts and performing autonomous fixes based on error reports.
- **Documentation**: Writing this README, the development plan (PLAN.md), and technical specifications.
- **Open Source Compliance**: Assisting with open source license selection (AGPL-3.0) and compliance declarations.

> Note: The human developer's role in this process is that of "Architect" and "Decision Officer", responsible for defining the vision, reviewing logical nodes, and authorizing key execution steps via mobile devices.

## 📜 License

This project is licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html).

Copyright (C) 2026 AndyXuuu <andy1770@proton.me>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.