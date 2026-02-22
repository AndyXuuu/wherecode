"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import {
  getProjectSnapshot,
  getTask,
  listCommands,
  listProjects,
  listTasks
} from "@/lib/control-center-client";
import type { Command, Project, ProjectDetail, Task, TaskStatus } from "@/types/hierarchy";

const colors = {
  surface: "rgb(17 23 20)",
  surfaceContainer: "rgb(27 35 32)",
  outline: "rgb(58 74 66)",
  textPrimary: "rgb(229 242 234)",
  textSecondary: "rgb(182 200 188)",
  primary: "rgb(47 111 94)",
  onPrimary: "rgb(255 255 255)",
  error: "rgb(239 68 68)",
  onError: "rgb(255 255 255)"
};

const ACTIVE_TASK_STATUSES: TaskStatus[] = ["todo", "in_progress", "waiting_approval"];
const BLOCKED_TASK_STATUSES: TaskStatus[] = ["blocked", "failed"];

function statusLabel(status: TaskStatus): string {
  return status.replaceAll("_", " ");
}

function commandSummary(command: Command | undefined): string {
  if (!command) {
    return "助手: 暂无命令记录。";
  }
  if (command.output_summary) {
    return `助手: ${command.output_summary}`;
  }
  if (command.error_message) {
    return `助手: ${command.error_message}`;
  }
  return `助手: ${command.text}`;
}

function formatRelativeMinutes(iso: string | undefined): string {
  if (!iso) {
    return "-";
  }
  const ms = Date.now() - new Date(iso).getTime();
  const minutes = Math.max(1, Math.round(ms / 60000));
  return `${minutes}m`;
}

function pickFocusProject(projects: Project[]): Project | undefined {
  if (projects.length === 0) {
    return undefined;
  }
  return [...projects].sort((a, b) => {
    if (b.active_task_count !== a.active_task_count) {
      return b.active_task_count - a.active_task_count;
    }
    return b.task_count - a.task_count;
  })[0];
}

function Canvas({ children }: { children: ReactNode }) {
  return (
    <main
      className="flex min-h-screen items-center justify-center p-6"
      style={{
        background: colors.surface,
        fontFamily: 'Roboto, "Noto Sans SC", "PingFang SC", sans-serif'
      }}
    >
      {children}
    </main>
  );
}

function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <section
      className="flex h-[640px] w-[320px] flex-col overflow-hidden rounded-xl border"
      style={{ background: colors.surface, borderColor: colors.outline }}
    >
      {children}
    </section>
  );
}

function PageIntro({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="space-y-1">
      <h2 className="text-[18px] font-semibold leading-[1.2]" style={{ color: colors.textPrimary }}>
        {title}
      </h2>
      <p className="text-[12px] leading-[1.4]" style={{ color: colors.textPrimary }}>
        {subtitle}
      </p>
    </div>
  );
}

function InfoCard({ title, body }: { title: string; body: string }) {
  return (
    <article
      className="rounded-xl border p-[10px] shadow-[0_1px_3px_rgba(0,0,0,0.4)]"
      style={{ background: colors.surface, borderColor: colors.outline }}
    >
      <h3 className="text-[11px] font-semibold" style={{ color: colors.textPrimary }}>
        {title}
      </h3>
      <p className="mt-1 whitespace-pre-line text-[10px] leading-[1.4]" style={{ color: colors.textPrimary }}>
        {body}
      </p>
    </article>
  );
}

function KPITriplet({ items }: { items: Array<{ title: string; value: string }> }) {
  return (
    <div className="grid grid-cols-3 gap-[10px]">
      {items.map((item) => (
        <article
          key={item.title}
          className="rounded-xl border p-[10px] shadow-[0_1px_3px_rgba(0,0,0,0.4)]"
          style={{ background: colors.surface, borderColor: colors.outline }}
        >
          <h3 className="text-[10px] font-medium" style={{ color: colors.textPrimary }}>
            {item.title}
          </h3>
          <p className="mt-1 text-[13px] font-bold" style={{ color: colors.textPrimary }}>
            {item.value}
          </p>
        </article>
      ))}
    </div>
  );
}

function BottomNav({ active }: { active: "overview" | "tasks" | "projects" }) {
  const tabs: Array<{ key: "overview" | "tasks" | "projects"; label: string; href: string }> = [
    { key: "overview", label: "总览", href: "/overview" },
    { key: "tasks", label: "任务", href: "/tasks" },
    { key: "projects", label: "项目", href: "/projects" }
  ];

  return (
    <nav
      className="grid h-14 grid-cols-3 overflow-hidden border shadow-[0_2px_6px_rgba(0,0,0,0.35)]"
      style={{ background: colors.surface, borderColor: colors.outline }}
    >
      {tabs.map((tab) => {
        const isActive = tab.key === active;
        return (
          <Link
            key={tab.key}
            href={tab.href}
            className="flex items-center justify-center text-xs"
            style={{
              background: isActive ? colors.primary : colors.surface,
              color: isActive ? colors.onPrimary : colors.textPrimary
            }}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

function SecondaryHeader({ title, backHref }: { title: string; backHref: string }) {
  return (
    <header
      className="flex h-10 items-center justify-between rounded-lg border px-1 shadow-[0_1px_3px_rgba(0,0,0,0.4)]"
      style={{ background: colors.surface, borderColor: "transparent" }}
    >
      <Link
        href={backHref}
        className="flex h-10 w-10 items-center justify-center text-sm"
        style={{ color: colors.textPrimary }}
      >
        ←
      </Link>
      <h2 className="text-[15px] font-semibold" style={{ color: colors.textPrimary }}>
        {title}
      </h2>
      <div className="h-10 w-10" />
    </header>
  );
}

function SubMeta({ text }: { text: string }) {
  return (
    <p className="text-[10px] leading-[1.4]" style={{ color: colors.textPrimary }}>
      {text}
    </p>
  );
}

function TaskThread({
  title,
  meta,
  assistant,
  user,
  href
}: {
  title: string;
  meta: string;
  assistant: string;
  user: string;
  href: string;
}) {
  return (
    <article
      className="space-y-[6px] rounded-xl border p-[10px] shadow-[0_1px_3px_rgba(0,0,0,0.4)]"
      style={{ background: colors.surface, borderColor: colors.outline }}
    >
      <Link href={href} className="text-[13px] font-semibold hover:underline" style={{ color: colors.textPrimary }}>
        {title}
      </Link>
      <p className="text-[11px]" style={{ color: colors.textSecondary }}>
        {meta}
      </p>
      <p
        className="rounded-lg border p-2 text-[11px]"
        style={{ background: colors.surfaceContainer, borderColor: colors.outline, color: colors.textPrimary }}
      >
        {assistant}
      </p>
      <p className="rounded-lg p-2 text-[11px]" style={{ background: colors.surface, color: colors.textPrimary }}>
        {user}
      </p>
    </article>
  );
}

function ChatAssistant({ text }: { text: string }) {
  return (
    <div
      className="w-[236px] rounded-lg border p-2 text-[11px]"
      style={{ background: colors.surface, borderColor: colors.outline, color: colors.textPrimary }}
    >
      {text}
    </div>
  );
}

function ChatUser({ text }: { text: string }) {
  return (
    <div className="ml-auto w-[214px] rounded-lg p-2 text-[11px]" style={{ background: colors.surface, color: colors.textPrimary }}>
      {text}
    </div>
  );
}

function ChatComposer() {
  return (
    <div
      className="flex items-center gap-2 rounded-lg border px-2 py-[6px] shadow-[0_2px_6px_rgba(0,0,0,0.35)]"
      style={{ background: colors.surface, borderColor: colors.outline }}
    >
      <p className="flex-1 text-[11px]" style={{ color: colors.textSecondary }}>
        输入回复或补充命令...
      </p>
      <button
        className="flex h-7 items-center justify-center rounded-full border px-2 text-[10px] font-semibold"
        style={{ background: colors.surface, borderColor: colors.outline, color: colors.textPrimary }}
      >
        语音
      </button>
      <button
        className="flex h-7 items-center justify-center rounded-full px-2 text-[10px] font-semibold"
        style={{ background: colors.primary, color: colors.onPrimary }}
      >
        发送
      </button>
    </div>
  );
}

function StatTriplet({ taskCount, doneCount, riskCount }: { taskCount: number; doneCount: number; riskCount: number }) {
  return (
    <div className="grid grid-cols-3 gap-[10px]">
      {[
        { label: "任务", value: taskCount.toString() },
        { label: "完成", value: doneCount.toString() },
        { label: "风险", value: riskCount.toString() }
      ].map((item) => (
        <div key={item.label} className="rounded-lg border p-2" style={{ background: colors.surface, borderColor: colors.outline }}>
          <p className="text-[10px] font-medium" style={{ color: colors.textPrimary }}>
            {item.label}
          </p>
          <p className="text-[13px] font-bold" style={{ color: colors.textPrimary }}>
            {item.value}
          </p>
        </div>
      ))}
    </div>
  );
}

function SaveCancelRow() {
  return (
    <div className="grid h-9 grid-cols-2 gap-2">
      <button className="rounded-lg text-[10px] font-semibold" style={{ background: colors.primary, color: colors.onPrimary }}>
        保存设置
      </button>
      <button
        className="rounded-lg border text-[10px] font-semibold"
        style={{ background: colors.surface, borderColor: colors.outline, color: colors.textPrimary }}
      >
        取消
      </button>
    </div>
  );
}

export function OverviewReplicaPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [snapshots, setSnapshots] = useState<ProjectDetail[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const projectList = await listProjects();
        const snapshotResults = await Promise.all(projectList.map((project) => getProjectSnapshot(project.id)));
        if (cancelled) {
          return;
        }
        setProjects(projectList);
        setSnapshots(snapshotResults);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载总览失败");
        }
      }
    };
    load().catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const taskList = useMemo(() => snapshots.flatMap((snapshot) => snapshot.tasks), [snapshots]);
  const activeTasks = taskList.filter((task) => ACTIVE_TASK_STATUSES.includes(task.status));
  const blockedTasks = taskList.filter((task) => BLOCKED_TASK_STATUSES.includes(task.status));
  const doneTasks = taskList.filter((task) => task.status === "done");
  const activeProjects = projects.filter((project) => project.status === "active");
  const riskProjects = snapshots.filter((snapshot) =>
    snapshot.tasks.some((task) => BLOCKED_TASK_STATUSES.includes(task.status))
  );

  const focusLines = [
    blockedTasks[0]
      ? `• 风险任务：${blockedTasks[0].title}（${statusLabel(blockedTasks[0].status)}）`
      : "• 当前无阻塞任务",
    activeProjects[0]
      ? `• 项目 ${activeProjects[0].name} 仍有 ${activeProjects[0].active_task_count} 个活跃任务`
      : "• 当前无活跃项目"
  ].join("\n");

  return (
    <Canvas>
      <PhoneFrame>
        <div className="flex-1 space-y-2 p-3">
          <PageIntro title="总览" subtitle="今天 3 个任务待推进，2 个项目有里程碑更新。" />
          {error ? <InfoCard title="系统提示" body={error} /> : null}
          <InfoCard title="待办事项" body={`${activeTasks.length} 项待办\n${blockedTasks.length} 项阻塞`} />
          <div className="grid grid-cols-2 gap-2">
            <InfoCard title="任务统计" body={`完成 ${doneTasks.length} / ${taskList.length || 0}`} />
            <InfoCard title="项目统计" body={`进行中 ${activeProjects.length} · 风险 ${riskProjects.length}`} />
          </div>
          <InfoCard title="今日关注" body={focusLines} />
        </div>
        <BottomNav active="overview" />
      </PhoneFrame>
    </Canvas>
  );
}

export function AuthReplicaPage() {
  const [token, setToken] = useState("");
  const [session, setSession] = useState("Session-A12");
  const [projectHint, setProjectHint] = useState("wherecode-mobile");
  const [notice, setNotice] = useState("");

  const onSave = () => {
    window.localStorage.setItem("wherecode-access-token", token);
    window.localStorage.setItem("wherecode-session-label", session);
    window.localStorage.setItem("wherecode-project-hint", projectHint);
    setNotice("已保存本地认证信息。");
  };

  return (
    <Canvas>
      <PhoneFrame>
        <div className="flex flex-1 flex-col gap-2 p-3">
          <PageIntro title="认证" subtitle="输入 token，建立移动端会话并绑定默认项目上下文。" />
          <label className="space-y-1 text-[10px]" style={{ color: colors.textSecondary }}>
            Access Token
            <input
              value={token}
              onChange={(event) => setToken(event.target.value)}
              placeholder="token_xxx"
              className="w-full rounded-lg border px-2 py-2 text-[11px]"
              style={{ background: colors.surface, borderColor: colors.outline, color: colors.textPrimary }}
            />
          </label>
          <label className="space-y-1 text-[10px]" style={{ color: colors.textSecondary }}>
            Session
            <input
              value={session}
              onChange={(event) => setSession(event.target.value)}
              className="w-full rounded-lg border px-2 py-2 text-[11px]"
              style={{ background: colors.surface, borderColor: colors.outline, color: colors.textPrimary }}
            />
          </label>
          <label className="space-y-1 text-[10px]" style={{ color: colors.textSecondary }}>
            默认项目
            <input
              value={projectHint}
              onChange={(event) => setProjectHint(event.target.value)}
              className="w-full rounded-lg border px-2 py-2 text-[11px]"
              style={{ background: colors.surface, borderColor: colors.outline, color: colors.textPrimary }}
            />
          </label>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={onSave}
              className="h-9 rounded-lg border text-[11px] font-semibold"
              style={{ background: colors.surface, borderColor: colors.outline, color: colors.textPrimary }}
            >
              保存
            </button>
            <Link
              href="/overview"
              className="flex h-9 items-center justify-center rounded-lg text-[11px] font-semibold"
              style={{ background: colors.primary, color: colors.onPrimary }}
            >
              进入总览
            </Link>
          </div>
          {notice ? <SubMeta text={notice} /> : null}
          <InfoCard
            title="通信策略"
            body={"HTTP 异步提交 + 轮询状态\n管理维度：项目 -> 任务 -> 命令"}
          />
          <Link
            href="/command-lab"
            className="text-center text-[11px] underline"
            style={{ color: colors.textSecondary }}
          >
            打开指挥联调页
          </Link>
        </div>
      </PhoneFrame>
    </Canvas>
  );
}

export function TasksReplicaPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [latestCommands, setLatestCommands] = useState<Record<string, Command | undefined>>({});
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    listProjects()
      .then((list) => {
        if (cancelled) {
          return;
        }
        setProjects(list);
        const focus = pickFocusProject(list);
        if (focus) {
          setSelectedProjectId(focus.id);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载任务页失败");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!selectedProjectId) {
      setTasks([]);
      return;
    }
    const load = async () => {
      try {
        const list = await listTasks(selectedProjectId);
        if (cancelled) {
          return;
        }
        setTasks(list);
        const topTasks = list.slice(0, 3);
        const commandPairs = await Promise.all(
          topTasks.map(async (task) => {
            const commands = await listCommands(task.id);
            const latest = [...commands].sort((a, b) => b.sequence - a.sequence)[0];
            return [task.id, latest] as const;
          })
        );
        if (!cancelled) {
          setLatestCommands(Object.fromEntries(commandPairs));
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载任务列表失败");
        }
      }
    };
    load().catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [selectedProjectId]);

  const selectedProject = projects.find((project) => project.id === selectedProjectId);
  const displayTasks = tasks.slice(0, 2);

  return (
    <Canvas>
      <PhoneFrame>
        <div className="flex-1 space-y-2 p-3">
          <PageIntro title="任务" subtitle="每个任务按一组命令对话组织，便于追踪上下文和执行结果。" />
          {error ? <InfoCard title="系统提示" body={error} /> : null}
          {displayTasks.length === 0 ? (
            <InfoCard title="任务空态" body="当前项目暂无任务，请去指挥联调页创建任务。" />
          ) : (
            displayTasks.map((task, index) => {
              const latest = latestCommands[task.id];
              return (
                <TaskThread
                  key={task.id}
                  href={`/task/${task.id}`}
                  title={task.title || `任务 ${index + 1}`}
                  meta={`命令 ${task.command_count} 条 · 最近更新 ${formatRelativeMinutes(latest?.updated_at)}`}
                  assistant={commandSummary(latest)}
                  user={`我: 状态 ${statusLabel(task.status)}，已同步上下文。`}
                />
              );
            })
          )}
          {selectedProject ? (
            <SubMeta text={`当前项目：${selectedProject.name} · project_id ${selectedProject.id}`} />
          ) : null}
        </div>
        <BottomNav active="tasks" />
      </PhoneFrame>
    </Canvas>
  );
}

export function ProjectsReplicaPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [snapshots, setSnapshots] = useState<ProjectDetail[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const projectList = await listProjects();
        const snapshotList = await Promise.all(projectList.map((project) => getProjectSnapshot(project.id)));
        if (!cancelled) {
          setProjects(projectList);
          setSnapshots(snapshotList);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载项目页失败");
        }
      }
    };
    load().catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const inProgressLines = projects
    .filter((project) => project.active_task_count > 0)
    .slice(0, 3)
    .map((project) => `• ${project.name} · 任务 ${project.active_task_count}/${project.task_count}`);

  const blockedLines = snapshots
    .filter((snapshot) => snapshot.tasks.some((task) => BLOCKED_TASK_STATUSES.includes(task.status)))
    .slice(0, 2)
    .map((snapshot) => `• ${snapshot.name} · 包含失败/阻塞任务`);

  const doneLines = projects
    .filter((project) => project.task_count > 0 && project.active_task_count === 0)
    .slice(0, 2)
    .map((project) => `• ${project.name} · 已归档任务 ${project.task_count} 条`);

  const totalTasks = snapshots.reduce((sum, snapshot) => sum + snapshot.tasks.length, 0);
  const riskCount = blockedLines.length;
  const inProgressCount = inProgressLines.length;
  const doneCount = doneLines.length;

  return (
    <Canvas>
      <PhoneFrame>
        <div className="flex-1 space-y-2 p-3">
          <PageIntro title="项目" subtitle="按状态查看项目与任务负载，快速定位风险。" />
          {error ? <InfoCard title="系统提示" body={error} /> : null}
          <KPITriplet
            items={[
              { title: "项目数", value: `${projects.length}` },
              { title: "任务数", value: `${totalTasks}` },
              { title: "风险项", value: `${riskCount}` }
            ]}
          />
          <InfoCard
            title={`进行中 (${inProgressCount})`}
            body={inProgressLines.length > 0 ? inProgressLines.join("\n") : "• 暂无进行中项目"}
          />
          <InfoCard
            title={`阻塞 (${riskCount})`}
            body={blockedLines.length > 0 ? blockedLines.join("\n") : "• 当前无阻塞项目"}
          />
          <InfoCard
            title={`已完成 (${doneCount})`}
            body={doneLines.length > 0 ? doneLines.join("\n") : "• 当前无已完成项目"}
          />
          <InfoCard title="提示" body="项目项可映射到任务页中的会话任务组。" />
        </div>
        <BottomNav active="projects" />
      </PhoneFrame>
    </Canvas>
  );
}

export function TaskDetailReplicaPage({ taskId }: { taskId: string }) {
  const [task, setTask] = useState<Task | null>(null);
  const [commands, setCommands] = useState<Command[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [taskDetail, commandList] = await Promise.all([getTask(taskId), listCommands(taskId)]);
        if (!cancelled) {
          setTask(taskDetail);
          setCommands(commandList.sort((a, b) => a.sequence - b.sequence));
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载任务详情失败");
        }
      }
    };
    load().catch(() => undefined);
    const timer = window.setInterval(() => {
      load().catch(() => undefined);
    }, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [taskId]);

  const meta = task
    ? `${statusLabel(task.status)} · ${task.title} · 会话记录 ${commands.length} 条 · 更新于 ${formatRelativeMinutes(task.updated_at)} 前`
    : `task_id ${taskId} · 加载中`;
  const timelineCommands = commands.slice(-3);

  return (
    <Canvas>
      <PhoneFrame>
        <div className="flex flex-1 flex-col gap-2 p-3">
          <SecondaryHeader title="任务详情" backHref="/tasks" />
          <SubMeta text={meta} />
          <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
            {error ? <InfoCard title="系统提示" body={error} /> : null}
            {timelineCommands.length === 0 ? (
              <ChatAssistant text="助手: 当前暂无命令记录，请先在指挥联调页下发命令。" />
            ) : (
              timelineCommands.map((command) =>
                command.source === "user" ? (
                  <ChatUser key={command.id} text={`我: ${command.text}`} />
                ) : (
                  <ChatAssistant key={command.id} text={commandSummary(command)} />
                )
              )
            )}
          </div>
          <ChatComposer />
        </div>
      </PhoneFrame>
    </Canvas>
  );
}

export function ProjectDetailReplicaPage({ projectId }: { projectId: string }) {
  const [snapshot, setSnapshot] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getProjectSnapshot(projectId)
      .then((data) => {
        if (!cancelled) {
          setSnapshot(data);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载项目详情失败");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const tasks = snapshot?.tasks ?? [];
  const doneCount = tasks.filter((task) => task.status === "done").length;
  const riskCount = tasks.filter((task) => BLOCKED_TASK_STATUSES.includes(task.status)).length;
  const latestCommand = tasks
    .flatMap((task) => task.commands)
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())[0];

  const progressLines = tasks
    .slice(0, 3)
    .map((task) => `• ${task.title}：${statusLabel(task.status)}（命令 ${task.command_count} 条）`)
    .join("\n");

  const projectName = snapshot?.name ?? "未知项目";

  return (
    <Canvas>
      <PhoneFrame>
        <div className="flex flex-1 flex-col gap-2 p-3">
          <SecondaryHeader title="项目详情" backHref="/projects" />
          <SubMeta text={`${projectName} · 负责人 ${snapshot?.owner ?? "Andy"} · project_id ${projectId}`} />
          {error ? <InfoCard title="系统提示" body={error} /> : null}
          <StatTriplet taskCount={tasks.length} doneCount={doneCount} riskCount={riskCount} />
          <InfoCard
            title="里程碑"
            body={snapshot?.description ?? "4/30 前完成验收文档、灰度发布和回归签收。"}
          />
          <InfoCard
            title="任务进展"
            body={progressLines || "• 暂无任务，请先在指挥联调页创建任务。"}
          />
          <InfoCard
            title="最近会话摘要"
            body={
              latestCommand
                ? `命令：${latestCommand.text}\n结果：${latestCommand.output_summary ?? latestCommand.error_message ?? latestCommand.status}`
                : "命令：暂无\n结果：暂无"
            }
          />
          <SubMeta text="提示：点击任务项可进入对应任务详情页继续对话。" />
        </div>
      </PhoneFrame>
    </Canvas>
  );
}

export function ProjectSettingsReplicaPage({ projectId }: { projectId: string }) {
  const [snapshot, setSnapshot] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getProjectSnapshot(projectId)
      .then((data) => {
        if (!cancelled) {
          setSnapshot(data);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载项目设置失败");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const projectName = snapshot?.name ?? "Alpha 平台重构";
  const owner = snapshot?.owner ?? "Andy";
  const taskCount = snapshot?.tasks.length ?? 0;
  const riskCount = snapshot?.tasks.filter((task) => BLOCKED_TASK_STATUSES.includes(task.status)).length ?? 0;

  return (
    <Canvas>
      <PhoneFrame>
        <div className="flex flex-1 flex-col gap-2 p-3">
          <SecondaryHeader title="项目设置" backHref={`/project/${projectId}`} />
          {error ? <InfoCard title="系统提示" body={error} /> : null}
          <InfoCard title="项目信息" body={`名称：${projectName}\n负责人：${owner}\nproject_id：${projectId}`} />
          <InfoCard title="通知设置" body={`任务变更：开启\n风险升级：${riskCount > 0 ? "开启" : "关闭"}\n日报提醒：关闭`} />
          <InfoCard title="权限管理" body={`管理员 2 人 · 开发 5 人 · 访客 3 人\n当前任务 ${taskCount} 条`} />
          <div className="space-y-2 rounded-xl border p-[10px]" style={{ background: colors.surface, borderColor: colors.outline }}>
            <p className="text-[11px] font-semibold" style={{ color: colors.error }}>
              危险操作
            </p>
            <button className="h-9 w-full rounded-lg text-[10px] font-semibold" style={{ background: colors.error, color: colors.onError }}>
              归档项目
            </button>
          </div>
          <SaveCancelRow />
        </div>
      </PhoneFrame>
    </Canvas>
  );
}
