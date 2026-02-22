# Command Center 页面映射（Pencil -> Next）

更新日期：2026-02-22

本文件用于把 Pencil `app_pages_dark_showcase` 的节点与 Next 路由实现逐项对应，便于验收和后续微调。

## 1) 画板与路由对应

- `INjl3` `app_pages_dark_showcase` -> `/overview` + `/tasks` + `/projects` + `/task/[id]` + `/project/[id]` + `/project/[id]/settings`
- `V6pG0` `app_page_dark_overview` -> `/overview`（兼容重定向：`/feed`）
- `KfvKg` `app_page_dark_tasks` -> `/tasks`
- `sfdRA` `app_page_dark_projects` -> `/projects`
- `kijgk` `app_page_dark_task_detail` -> `/task/[id]`
- `beaNL` `app_page_dark_project_detail` -> `/project/[id]`
- `qVcDu` `app_page_dark_project_settings` -> `/project/[id]/settings`

## 2) 组件节点与实现对应

- `egBc9` `theme_dark_component_page_intro` -> `PageIntro`（`command_center/components/app-pages-replica.tsx`）
- `YKImA` `theme_dark_component_info_card` -> `InfoCard`
- `MLYqt` `theme_dark_component_bottom_nav_3tab` -> `BottomNav`
- `kyFyl` `theme_dark_component_task_thread` -> `TaskThread`
- `Tc5Uu` `theme_dark_component_secondary_header` -> `SecondaryHeader`
- `W9bSe` `theme_dark_component_subpage_meta` -> `SubMeta`
- `6gOqd` `theme_dark_component_chat_composer` -> `ChatComposer`
- `fuuiR` `theme_dark_component_kpi_triplet` -> `KPITriplet`
- `oqhZo` `theme_dark_component_stat_triplet` -> `StatTriplet`
- `VmM4t` `theme_dark_component_project_detail_panel` -> `ProjectDetailReplicaPage` 内部组合
- `G2bzP` `theme_dark_component_project_settings_panel` -> `ProjectSettingsReplicaPage` 内部组合

## 3) 数据映射策略

- 总览页：项目快照聚合（项目数、任务数、风险项、关注卡片）
- 任务页：聚焦项目的任务线程（每条线程展示命令数量与最近命令摘要）
- 项目页：按 in-progress / blocked / done 分组展示项目状态
- 任务详情：展示最近 3 条命令会话，保留“会话总数”元信息
- 项目详情：展示任务统计、里程碑、任务进展、最近命令摘要
- 项目设置：展示项目信息、通知策略、权限统计、危险操作与保存区

## 4) 当前差异（可继续微调）

- 认证页 (`/auth`) 不在 `app_pages_dark_showcase` 主画板中，作为扩展页保留。
- 实际业务数据长度会导致文本换行与 Pencil 示例文案略有不同。
- 图标使用纯文本符号（例如返回箭头、语音按钮），未引入 icon font 精准复刻。

## 5) 代码定位

- 页面复刻主文件：`/Users/andyxu/Documents/project/wherecode/command_center/components/app-pages-replica.tsx`
- 路由入口：
  - `/Users/andyxu/Documents/project/wherecode/command_center/app/overview/page.tsx`
  - `/Users/andyxu/Documents/project/wherecode/command_center/app/tasks/page.tsx`
  - `/Users/andyxu/Documents/project/wherecode/command_center/app/projects/page.tsx`
  - `/Users/andyxu/Documents/project/wherecode/command_center/app/task/[id]/page.tsx`
  - `/Users/andyxu/Documents/project/wherecode/command_center/app/project/[id]/page.tsx`
  - `/Users/andyxu/Documents/project/wherecode/command_center/app/project/[id]/settings/page.tsx`
