# Command Center 内容拆解（交付 Pencil 实现）

本文件用于把 README 里的「Command Center（移动端指挥中心）」拆成可直接落地的设计与实现任务。

## 1) 目标与边界

- 目标：让用户在手机端完成「下达任务 -> 查看执行过程 -> 审批/重试 -> 接收结果摘要」全流程。
- 设备优先级：移动端优先（宽度 320-430），桌面仅做适配，不做主场景。
- 设计风格：卡片式对话流 + 系统状态可视化，低认知负担，单手可操作。
- 通信模型：HTTP 异步（提交后轮询），不依赖长连接常驻。

## 2) 信息架构（IA）

Command Center 拆成 4 个核心页面/视图：

1. 认证页（Auth）
   - Token 输入
   - 连接状态提示
   - 登录动作
2. 指挥主屏（Commander Feed）
   - 顶部状态区（连接状态、当前会话、未读提醒）
   - 卡片流（任务回执、执行进度、测试结果、错误告警）
   - 指令输入区（自然语言输入 + 快捷动作）
3. 任务详情抽屉（Task Detail Sheet）
   - 时间线（事件、日志摘要）
   - 文件变更统计
   - 测试结果与失败上下文
4. 历史与筛选（History Filter）
   - 按状态筛选：running/success/failed
   - 按时间与关键词检索
   - 快速复用历史指令

### 2.1 管理维度（必须统一）

所有页面都按同一条管理主线组织数据：

- `项目（Project）`：业务容器与上下文边界
- `任务（Task）`：项目下的执行目标
- `命令（Command）`：任务下可追踪的最小执行单元

设计与实现约束：

- 页面导航顺序优先体现 `项目 -> 任务 -> 命令`
- 卡片文案必须包含至少一个层级标识（project_id / task_id / command_id）
- 历史检索默认支持三级筛选：按项目、按任务、按命令

## 3) 主屏模块拆解（Pencil 组件级）

### A. Top Status Bar
- 左：系统名 `WhereCode`
- 中：连接状态点（connected/connecting/disconnected）
- 右：会话菜单按钮（历史、设置、退出）

### B. Session Snapshot Card
- 当前任务数（进行中/待审批）
- 最近一次任务结论（成功/失败）
- 最近同步时间

### C. Card Feed（核心）
- 卡片类型：
  - `status`：过程状态（排队、执行、测试中）
  - `result`：执行结果摘要
  - `error`：失败原因与建议动作
  - `system`：轮询恢复、同步完成等系统事件
  - `approval`：需要用户确认的关键动作
- 卡片字段：
  - 标题（title）
  - 主体（body，支持简易 markdown）
  - 元信息（agent、耗时、task_id）
  - 动作按钮（重试、查看详情、批准、拒绝）

### D. Composer（输入区）
- 多行输入框（默认占位：描述你要执行的任务）
- 主按钮：发送指令
- 次按钮：语音输入（预留）、模板命令

### E. Quick Actions
- 常用动作 chips：
  - 重构某模块
  - 运行测试
  - 生成变更摘要
  - 回滚上次尝试

## 4) 关键交互状态

- 空态：首次进入，展示 3 条示例指令与快速引导。
- 加载态：发送后出现本地回显 + 服务端处理中状态卡。
- 成功态：结果卡 + 推荐下一步动作（如“是否执行测试”）。
- 失败态：错误卡 + 一键重试 + 查看上下文。
- 断线态：顶部状态与横幅提示，恢复后继续 HTTP 轮询。

## 5) 可视化与样式约束

- 触控尺寸：关键交互元素高度 >= 44px。
- 输入字体 >= 16px（避免 iOS 自动缩放）。
- 卡片层级：背景、边框、状态色要明显分层。
- 色彩语义：
  - status: 蓝
  - result: 绿
  - error: 红
  - system: 灰
  - approval: 橙

## 6) Pencil 实现分批任务（建议顺序）

### Batch 1：页面骨架
- 建立移动端主 Frame（390x844）
- 插入顶部状态栏
- 插入卡片流容器
- 插入底部输入区

### Batch 2：核心组件
- 创建 5 类卡片组件（status/result/error/system/approval）
- 创建输入组件（输入框 + 主按钮 + 次按钮）
- 创建状态点组件（3 态变体）

### Batch 3：页面状态
- 复制主屏，产出空态/加载态/成功态/失败态/断线态 5 个变体
- 每个变体替换卡片内容与动作按钮

### Batch 4：详情与历史
- 增加任务详情抽屉页面
- 增加历史筛选页面
- 增加从主屏跳转到详情的入口按钮

## 7) 交付验收标准（给 Pencil）

- 必须包含：认证页 + 主屏 + 详情 + 历史，共 4 个页面。
- 主屏必须包含：状态栏、卡片流、输入区、快捷动作。
- 卡片至少 5 种类型，且颜色语义一致。
- 至少提供 5 个状态变体（空/加载/成功/失败/断线）。
- 所有页面在 390x844 下无裁切、无重叠、可滚动浏览。

## 8) 可直接发给 Pencil 的实现提示词

请基于本文件实现一个移动端「Command Center」界面系统，使用卡片式任务流。  
先做信息架构与组件，再做页面状态变体。  
必须产出：Auth、Commander Feed、Task Detail、History Filter 四个页面。  
Commander Feed 必须包含 Top Status Bar、Session Snapshot、Card Feed、Composer、Quick Actions。  
卡片类型必须覆盖 status/result/error/system/approval，并保持颜色语义统一。  
最终请给出可复用组件清单与页面清单。

---

## 9) Next + Tailwind 样式映射（Pencil First）

为保证设计稿与实现一致，前端样式 token 直接对齐 Pencil 变量并启用 class-based dark mode。

- Light 主色：`--primary: 220 233 226`（对应 `theme_light_primary`）
- Dark 主色：`--primary: 47 111 94`（对应 `theme_dark_primary`）
- Light 面板：`--panel: 238 243 239`
- Dark 面板：`--panel: 27 35 32`
- 文本：`--text`，次级文本：`--muted`
- 语义状态：`--success` / `--warning` / `--danger`

建议前端结构：

- `/overview`：总览页（对应 `app_page_dark_overview`）
- `/tasks`：任务列表（按项目筛选）
- `/projects`：项目列表
- `/task/[id]`：任务详情
- `/project/[id]`：项目详情
- `/project/[id]/settings`：项目设置
- `/auth`：扩展认证页（不在 app pages 主画板）
- `/command-lab`：扩展联调页（不在 app pages 主画板）

主题切换建议：

- 通过 `html.dark` 切换 dark token
- 通过 `localStorage` 持久化主题偏好
- 首屏注入主题初始化脚本，避免闪烁

---

## 10) 验收记录（2026-02-22）

本设计稿已完成一次只读验收，详见 `design_acceptance.md`。关键结论：

- 验收对象：`command_center/design/command_center.pen`
- 布局检查：`theme_design_system` 与 `app_pages_dark_showcase` 均无布局问题
- 管理主线：`项目 -> 任务 -> 命令` 已在页面与内容语义中体现
- 组件规模：Light/Dark 成对组件共 36 个，可支撑后续扩展
- 同步原则：以 Pencil 为准，前端按 token 同步
