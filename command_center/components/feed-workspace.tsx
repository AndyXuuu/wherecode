"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ControlCenterHealthCard } from "@/components/control-center-health-card";
import { PanelCard } from "@/components/panel-card";
import { StatusChip } from "@/components/status-chip";
import { WorkspaceShell } from "@/components/workspace-shell";
import {
  approveCommand,
  createProject,
  createTask,
  getCommand,
  listProjects,
  listTasks,
  submitCommand
} from "@/lib/control-center-client";
import type { Command, CommandStatus, Project, Task } from "@/types/hierarchy";

type FeedEventTone = "neutral" | "success" | "warning" | "danger";

interface FeedEvent {
  id: string;
  title: string;
  body: string;
  tone: FeedEventTone;
  createdAt: string;
}

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString("zh-CN", { hour12: false });
}

function toneClass(tone: FeedEventTone): string {
  switch (tone) {
    case "success":
      return "border-success/35 bg-success/10";
    case "warning":
      return "border-warning/35 bg-warning/10";
    case "danger":
      return "border-danger/35 bg-danger/10";
    default:
      return "border-border bg-card";
  }
}

function eventToneByStatus(status: CommandStatus): FeedEventTone {
  if (status === "success") {
    return "success";
  }
  if (status === "waiting_approval") {
    return "warning";
  }
  if (status === "failed" || status === "canceled") {
    return "danger";
  }
  return "neutral";
}

const FINAL_STATUSES: CommandStatus[] = ["success", "failed", "canceled"];

export function FeedWorkspace() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [newProjectName, setNewProjectName] = useState("wherecode-mobile");
  const [newTaskTitle, setNewTaskTitle] = useState("登录模块重构");
  const [commandText, setCommandText] = useState("重构登录模块并运行单元测试");
  const [requestedBy, setRequestedBy] = useState("andy");
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [currentCommand, setCurrentCommand] = useState<Command | null>(null);
  const [pollingCommandId, setPollingCommandId] = useState<string | null>(null);
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lastStatusRef = useRef<CommandStatus | null>(null);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId]
  );
  const selectedTask = useMemo(() => tasks.find((task) => task.id === selectedTaskId) ?? null, [tasks, selectedTaskId]);

  const pushEvent = (title: string, body: string, tone: FeedEventTone) => {
    setEvents((previous) => [
      {
        id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
        title,
        body,
        tone,
        createdAt: new Date().toISOString()
      },
      ...previous
    ].slice(0, 12));
  };

  const loadProjects = async () => {
    const all = await listProjects();
    setProjects(all);
    if (!selectedProjectId && all.length > 0) {
      setSelectedProjectId(all[0].id);
    }
  };

  const loadTasks = async (projectId: string) => {
    if (!projectId) {
      setTasks([]);
      setSelectedTaskId("");
      return;
    }
    const all = await listTasks(projectId);
    setTasks(all);
    if (all.length === 0) {
      setSelectedTaskId("");
      return;
    }
    setSelectedTaskId((previous) => {
      if (previous && all.some((task) => task.id === previous)) {
        return previous;
      }
      return all[0].id;
    });
  };

  useEffect(() => {
    loadProjects().catch((loadError) => {
      setError(loadError instanceof Error ? loadError.message : "加载项目失败");
    });
  }, []);

  useEffect(() => {
    loadTasks(selectedProjectId).catch((loadError) => {
      setError(loadError instanceof Error ? loadError.message : "加载任务失败");
    });
  }, [selectedProjectId]);

  useEffect(() => {
    if (!pollingCommandId) {
      return;
    }

    let cancelled = false;
    const poll = async () => {
      try {
        const detail = await getCommand(pollingCommandId);
        if (cancelled) {
          return;
        }
        setCurrentCommand(detail);
        if (detail.status !== lastStatusRef.current) {
          lastStatusRef.current = detail.status;
          pushEvent(
            `命令状态更新: ${detail.status}`,
            `${detail.id} (${detail.task_id})`,
            eventToneByStatus(detail.status)
          );
        }

        if (detail.status === "waiting_approval" || FINAL_STATUSES.includes(detail.status)) {
          setPollingCommandId(null);
        }
      } catch (pollError) {
        if (cancelled) {
          return;
        }
        setError(pollError instanceof Error ? pollError.message : "轮询命令状态失败");
        setPollingCommandId(null);
      }
    };

    poll().catch(() => undefined);
    const timer = window.setInterval(() => {
      poll().catch(() => undefined);
    }, 1200);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [pollingCommandId]);

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      setError("请输入项目名称");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const project = await createProject({
        name: newProjectName.trim(),
        owner: requestedBy || undefined
      });
      await loadProjects();
      setSelectedProjectId(project.id);
      pushEvent("项目已创建", `${project.name} (${project.id})`, "success");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "创建项目失败");
    } finally {
      setBusy(false);
    }
  };

  const handleCreateTask = async () => {
    if (!selectedProjectId) {
      setError("请先选择项目");
      return;
    }
    if (!newTaskTitle.trim()) {
      setError("请输入任务标题");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const task = await createTask(selectedProjectId, {
        title: newTaskTitle.trim(),
        priority: 3
      });
      await loadTasks(selectedProjectId);
      setSelectedTaskId(task.id);
      pushEvent("任务已创建", `${task.title} (${task.id})`, "success");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "创建任务失败");
    } finally {
      setBusy(false);
    }
  };

  const handleSubmitCommand = async () => {
    if (!selectedTaskId) {
      setError("请先选择任务");
      return;
    }
    if (!commandText.trim()) {
      setError("请输入命令内容");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const accepted = await submitCommand(selectedTaskId, {
        text: commandText.trim(),
        requested_by: requestedBy || undefined,
        requires_approval: requiresApproval
      });
      pushEvent(
        "命令已提交",
        `${accepted.command_id} 已加入队列，状态 ${accepted.status}`,
        eventToneByStatus(accepted.status)
      );
      lastStatusRef.current = accepted.status;
      setPollingCommandId(accepted.command_id);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "提交命令失败");
    } finally {
      setBusy(false);
    }
  };

  const handleApproveCommand = async () => {
    if (!currentCommand || currentCommand.status !== "waiting_approval") {
      return;
    }
    setBusy(true);
    setError("");
    try {
      const approved = await approveCommand(currentCommand.id, {
        approved_by: requestedBy || "mobile-user"
      });
      setCurrentCommand(approved);
      setPollingCommandId(approved.id);
      pushEvent("命令已批准", `${approved.id} 进入执行队列`, "success");
    } catch (approveError) {
      setError(approveError instanceof Error ? approveError.message : "命令审批失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <WorkspaceShell
      title="指挥流 (HTTP Async)"
      subtitle="以项目 -> 任务 -> 命令为主线，提交命令后通过轮询追踪执行状态。"
      aside={<ControlCenterHealthCard />}
    >
      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <PanelCard title="指挥上下文" subtitle="先确定项目与任务，再发命令。">
          <div className="space-y-3">
            <div className="grid gap-2 md:grid-cols-2">
              <label className="space-y-1 text-xs text-muted">
                选择项目
                <select
                  className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text"
                  value={selectedProjectId}
                  onChange={(event) => setSelectedProjectId(event.target.value)}
                >
                  <option value="">请选择项目</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name} ({project.id})
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1 text-xs text-muted">
                选择任务
                <select
                  className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text"
                  value={selectedTaskId}
                  onChange={(event) => setSelectedTaskId(event.target.value)}
                >
                  <option value="">请选择任务</option>
                  {tasks.map((task) => (
                    <option key={task.id} value={task.id}>
                      {task.title} ({task.id})
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              <label className="space-y-1 text-xs text-muted">
                新建项目名
                <input
                  className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text"
                  value={newProjectName}
                  onChange={(event) => setNewProjectName(event.target.value)}
                  placeholder="wherecode-mobile"
                />
              </label>
              <button
                type="button"
                disabled={busy}
                onClick={handleCreateProject}
                className="mt-5 rounded-xl border border-border bg-card px-3 py-2 text-sm text-text hover:bg-bg disabled:opacity-60"
              >
                创建项目
              </button>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              <label className="space-y-1 text-xs text-muted">
                新建任务标题
                <input
                  className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text"
                  value={newTaskTitle}
                  onChange={(event) => setNewTaskTitle(event.target.value)}
                  placeholder="登录模块重构"
                />
              </label>
              <button
                type="button"
                disabled={busy || !selectedProjectId}
                onClick={handleCreateTask}
                className="mt-5 rounded-xl border border-border bg-card px-3 py-2 text-sm text-text hover:bg-bg disabled:opacity-60"
              >
                创建任务
              </button>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              <label className="space-y-1 text-xs text-muted">
                请求人
                <input
                  className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text"
                  value={requestedBy}
                  onChange={(event) => setRequestedBy(event.target.value)}
                  placeholder="andy"
                />
              </label>
              <label className="mt-6 flex items-center gap-2 text-xs text-muted">
                <input
                  type="checkbox"
                  checked={requiresApproval}
                  onChange={(event) => setRequiresApproval(event.target.checked)}
                />
                该命令需要审批
              </label>
            </div>
          </div>
        </PanelCard>

        <PanelCard title="命令下发" subtitle="Control Center 返回 202，并通过 GET /commands/{id} 轮询。">
          <div className="space-y-3">
            <label className="space-y-1 text-xs text-muted">
              命令内容
              <textarea
                className="min-h-28 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text"
                value={commandText}
                onChange={(event) => setCommandText(event.target.value)}
                placeholder="描述你要执行的任务"
              />
            </label>
            <button
              type="button"
              disabled={busy || !selectedTaskId}
              onClick={handleSubmitCommand}
              className="w-full rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-60"
            >
              发送命令
            </button>
            {error ? <p className="rounded-xl border border-danger/40 bg-danger/20 p-2 text-xs text-danger">{error}</p> : null}
          </div>
        </PanelCard>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <PanelCard title="当前命令状态" subtitle="管理维度：项目 -> 任务 -> 命令">
          {currentCommand ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <StatusChip status={currentCommand.status} />
                <span className="text-xs text-muted">command_id: {currentCommand.id}</span>
              </div>
              <div className="grid gap-2 text-sm text-text md:grid-cols-3">
                <p className="rounded-xl border border-border bg-card px-2 py-1">项目: {currentCommand.project_id}</p>
                <p className="rounded-xl border border-border bg-card px-2 py-1">任务: {currentCommand.task_id}</p>
                <p className="rounded-xl border border-border bg-card px-2 py-1">序号: #{currentCommand.sequence}</p>
              </div>
              <p className="rounded-xl border border-border bg-bg p-2 text-sm text-text">{currentCommand.text}</p>
              {currentCommand.output_summary ? (
                <p className="rounded-xl border border-success/40 bg-success/20 p-2 text-sm text-success">
                  输出: {currentCommand.output_summary}
                </p>
              ) : null}
              {currentCommand.error_message ? (
                <p className="rounded-xl border border-danger/40 bg-danger/20 p-2 text-sm text-danger">
                  错误: {currentCommand.error_message}
                </p>
              ) : null}
              {currentCommand.status === "waiting_approval" ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={handleApproveCommand}
                  className="rounded-xl bg-warning px-3 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60"
                >
                  批准并继续执行
                </button>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-muted">尚未提交命令。请先创建/选择任务后发送命令。</p>
          )}
        </PanelCard>

        <PanelCard title="事件流" subtitle="异步事件回执（最新在前）">
          <div className="space-y-2">
            {events.length === 0 ? (
              <p className="text-sm text-muted">暂无事件</p>
            ) : (
              events.map((event) => (
                <article key={event.id} className={`rounded-xl border p-3 ${toneClass(event.tone)}`}>
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-text">{event.title}</p>
                    <span className="text-xs text-muted">{timeLabel(event.createdAt)}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted">{event.body}</p>
                </article>
              ))
            )}
          </div>
        </PanelCard>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-border bg-panel p-3">
          <p className="text-xs text-muted">项目</p>
          <p className="mt-1 truncate text-sm text-text">{selectedProject ? `${selectedProject.name} (${selectedProject.id})` : "未选择"}</p>
        </div>
        <div className="rounded-xl border border-border bg-panel p-3">
          <p className="text-xs text-muted">任务</p>
          <p className="mt-1 truncate text-sm text-text">{selectedTask ? `${selectedTask.title} (${selectedTask.id})` : "未选择"}</p>
        </div>
        <div className="rounded-xl border border-border bg-panel p-3">
          <p className="text-xs text-muted">命令</p>
          <p className="mt-1 truncate text-sm text-text">{currentCommand ? `${currentCommand.id} (${currentCommand.status})` : "未提交"}</p>
        </div>
      </div>
    </WorkspaceShell>
  );
}
