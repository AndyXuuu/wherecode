# 数据结构：项目 -> 任务 -> 命令

本文件定义 WhereCode 的核心管理层级：

1. **项目（Project）**：业务边界与资源容器  
2. **任务（Task）**：项目下可跟踪的执行目标  
3. **命令（Command）**：任务下最小执行单元（可审计、可回放）

## 关系约束

- `Task.project_id` 必须对应一个 `Project.id`
- `Command.project_id` 与 `Command.task_id` 必须同时匹配其所属 `Task`
- 允许按 `project_id -> task_id -> command_id` 做逐层查询和筛选

## 后端模型位置

- Python / Pydantic:
  - `control_center/models/hierarchy.py`
  - 导出入口：`control_center/models/__init__.py`

## 前端类型位置

- TypeScript:
  - `command_center/types/hierarchy.ts`

## 关键状态枚举

- ProjectStatus: `active | paused | archived`
- TaskStatus: `todo | in_progress | waiting_approval | blocked | done | failed | canceled`
- CommandStatus: `queued | running | success | failed | waiting_approval | canceled`

