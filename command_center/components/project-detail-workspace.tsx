"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PanelCard } from "@/components/panel-card";
import { StatusChip } from "@/components/status-chip";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getProjectSnapshot } from "@/lib/control-center-client";
import type { ProjectDetail } from "@/types/hierarchy";

export function ProjectDetailWorkspace({ projectId }: { projectId: string }) {
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getProjectSnapshot(projectId)
      .then(setDetail)
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "加载项目详情失败");
      });
  }, [projectId]);

  return (
    <WorkspaceShell
      title="项目详情"
      subtitle={`project_id: ${projectId} · 汇总任务与命令执行概况`}
    >
      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <PanelCard title="项目信息" subtitle="项目作为任务与命令的容器边界">
          {detail ? (
            <div className="space-y-2 text-sm text-text">
              <p className="rounded-xl border border-border bg-card px-3 py-2">{detail.name}</p>
              <div className="flex items-center gap-2">
                <StatusChip status={detail.status} />
                <span className="text-xs text-muted">owner: {detail.owner ?? "n/a"}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-muted">
                <span className="rounded-lg border border-border bg-bg px-2 py-1">tasks: {detail.task_count}</span>
                <span className="rounded-lg border border-border bg-bg px-2 py-1">active: {detail.active_task_count}</span>
              </div>
              <div className="flex gap-2">
                <Link
                  href={`/project/${projectId}/settings`}
                  className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text hover:bg-panel"
                >
                  项目设置
                </Link>
                <Link
                  href="/projects"
                  className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text hover:bg-panel"
                >
                  返回项目列表
                </Link>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted">加载中...</p>
          )}
        </PanelCard>

        <PanelCard title="任务概览" subtitle="项目 -> 任务 -> 命令">
          {error ? <p className="mb-3 rounded-xl border border-danger/40 bg-danger/20 p-2 text-xs text-danger">{error}</p> : null}
          {detail && detail.tasks.length > 0 ? (
            <div className="space-y-2">
              {detail.tasks.map((task) => (
                <article key={task.id} className="rounded-xl border border-border bg-card p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-text">{task.title}</p>
                      <p className="text-xs text-muted">task_id: {task.id} · commands: {task.command_count}</p>
                    </div>
                    <StatusChip status={task.status} />
                  </div>
                  <div className="mt-2 flex gap-2">
                    <Link
                      href={`/task/${task.id}`}
                      className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text hover:bg-panel"
                    >
                      查看任务
                    </Link>
                    <span className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-muted">
                      success {task.success_count} / failed {task.failed_count}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">项目下暂无任务。</p>
          )}
        </PanelCard>
      </div>
    </WorkspaceShell>
  );
}
