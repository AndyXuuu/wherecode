"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PanelCard } from "@/components/panel-card";
import { StatusChip } from "@/components/status-chip";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getTask, listCommands } from "@/lib/control-center-client";
import type { Command, Task } from "@/types/hierarchy";

function commandBody(command: Command): string {
  if (command.output_summary) {
    return command.output_summary;
  }
  if (command.error_message) {
    return command.error_message;
  }
  return command.text;
}

export function TaskDetailWorkspace({ taskId }: { taskId: string }) {
  const [task, setTask] = useState<Task | null>(null);
  const [commands, setCommands] = useState<Command[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [taskDetail, commandList] = await Promise.all([
          getTask(taskId),
          listCommands(taskId)
        ]);
        if (cancelled) {
          return;
        }
        setTask(taskDetail);
        setCommands(commandList);
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "加载任务详情失败");
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

  return (
    <WorkspaceShell
      title="任务详情"
      subtitle={`task_id: ${taskId} · 轮询命令状态，追踪执行轨迹`}
    >
      <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
        <PanelCard title="任务摘要" subtitle="管理维度：项目 -> 任务 -> 命令">
          {task ? (
            <div className="space-y-2 text-sm text-text">
              <p className="rounded-xl border border-border bg-card px-3 py-2">project_id: {task.project_id}</p>
              <p className="rounded-xl border border-border bg-card px-3 py-2">title: {task.title}</p>
              <div className="flex flex-wrap items-center gap-2">
                <StatusChip status={task.status} />
                <span className="text-xs text-muted">priority: {task.priority}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-muted">
                <span className="rounded-lg border border-border bg-bg px-2 py-1">commands: {task.command_count}</span>
                <span className="rounded-lg border border-border bg-bg px-2 py-1">success: {task.success_count}</span>
                <span className="rounded-lg border border-border bg-bg px-2 py-1">failed: {task.failed_count}</span>
                <span className="rounded-lg border border-border bg-bg px-2 py-1">last: {task.last_command_id ?? "n/a"}</span>
              </div>
              <Link
                href="/command-lab"
                className="inline-flex rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text hover:bg-panel"
              >
                返回指挥流
              </Link>
            </div>
          ) : (
            <p className="text-sm text-muted">加载中...</p>
          )}
        </PanelCard>

        <PanelCard title="命令时间线" subtitle="按 sequence 顺序展示命令状态">
          {error ? <p className="mb-3 rounded-xl border border-danger/40 bg-danger/20 p-2 text-xs text-danger">{error}</p> : null}
          {commands.length === 0 ? (
            <p className="text-sm text-muted">当前任务暂无命令。</p>
          ) : (
            <div className="space-y-2">
              {commands.map((command) => (
                <article key={command.id} className="rounded-xl border border-border bg-card p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-text">#{command.sequence} · {command.id}</p>
                      <p className="text-xs text-muted">{command.created_at}</p>
                    </div>
                    <StatusChip status={command.status} />
                  </div>
                  <p className="mt-2 rounded-xl border border-border bg-bg p-2 text-sm text-text">{commandBody(command)}</p>
                </article>
              ))}
            </div>
          )}
        </PanelCard>
      </div>
    </WorkspaceShell>
  );
}
