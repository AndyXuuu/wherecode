# Command Center 说明

本目录已升级为 `Next.js + Tailwind CSS` 前端工程，用于手机优先的控制端 UI。
核心目标：统一样式、以 Pencil 设计 token 为准、支持 `dark/light` 模式切换。
管理维度主线：`项目 -> 任务 -> 命令`。
通信方式：`HTTP 异步提交 + 轮询状态`（不使用常驻连接）。

## 目录结构

- `app/`: Next App Router 页面与全局样式
- `components/`: 业务组件（含主题切换）
- `lib/control-center-client.ts`: HTTP 异步接口封装
- `types/hierarchy.ts`: 项目->任务->命令的数据类型定义
- `types/api.ts`: 请求/响应类型定义
- `tailwind.config.ts`: Tailwind 主题映射（颜色由 Pencil token 驱动）
- `postcss.config.mjs`: PostCSS 配置
- `package.json`: 前端依赖与脚本

## 路由清单（Pencil 对齐）

- 一级页面（4）：
  - `/overview`: 总览页
  - `/tasks`: 任务页
  - `/projects`: 项目页
  - `/auth`: 认证入口（扩展页，不在 Pencil 主画板）
- 子页面（3）：
  - `/task/[id]`: 任务详情
  - `/project/[id]`: 项目详情
  - `/project/[id]/settings`: 项目设置
- 联调页面：
  - `/command-lab`: 指挥流联调页（创建项目/任务、提交命令、轮询状态、审批）

## 本地开发

```bash
cd command_center
pnpm install
pnpm dev
```

默认访问：`http://localhost:3000`

构建命令统一：

```bash
pnpm build
```

可选环境变量：

- `NEXT_PUBLIC_CONTROL_CENTER_URL`（默认 `http://localhost:8000`）
- 用于 HTTP 异步探活与后续命令轮询

## 主题策略

- 使用 CSS 变量定义语义色板，颜色以 Pencil 变量为唯一准则。
- 通过 `html.dark` 切换变量组，实现整站 dark/light 切换。
- 首屏通过内联脚本读取 `localStorage` + 系统偏好，避免闪烁。

## 设计交付

- Command Center 的详细拆解与 Pencil 实施说明见：
  - `../docs/command_center_pencil_spec.md`
- Pencil 设计验收记录（2026-02-22，只读验收）见：
  - `../docs/design_acceptance.md`
- Pencil 节点与页面实现映射见：
  - `../docs/pencil_app_pages_mapping.md`

## 当前状态说明

- 设计结构验收：已通过（布局检查无异常）。
- 管理维度：已按 `项目 -> 任务 -> 命令` 落地。
- 样式同步：Next + Tailwind 主题变量已对齐 Pencil token。
- 页面复刻：`/auth` + 总览/任务/项目 + 3 个子页面均采用单屏复刻结构。
- 通信接入：`/command-lab` 已接入 Control Center 的 HTTP 异步链路（提交 + 轮询 + 审批）。
- 联通探活：`/command-lab` 侧边探针同时检查 Control Center 与 Action Layer（经 Control Center 代理）。
- 路由兼容：`/feed` 保留为旧地址并重定向到 `/overview`。
