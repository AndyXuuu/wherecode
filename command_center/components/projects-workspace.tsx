"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PanelCard } from "@/components/panel-card";
import { StatusChip } from "@/components/status-chip";
import { WorkspaceShell } from "@/components/workspace-shell";
import { listProjects } from "@/lib/control-center-client";
import type { Project } from "@/types/hierarchy";

export function ProjectsWorkspace() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "加载项目失败");
      });
  }, []);

  return (
    <WorkspaceShell
      title="项目中心"
      subtitle="查看项目负载，进入任务与命令视图。"
    >
      <PanelCard title="项目列表" subtitle="每个项目对应一个任务容器与命令轨迹。">
        {error ? <p className="mb-3 rounded-xl border border-danger/40 bg-danger/20 p-2 text-xs text-danger">{error}</p> : null}
        {projects.length === 0 ? (
          <p className="text-sm text-muted">暂无项目，请前往指挥流创建。</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {projects.map((project) => (
              <article key={project.id} className="rounded-xl border border-border bg-card p-4">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-text">{project.name}</h3>
                  <StatusChip status={project.status} />
                </div>
                <p className="mt-1 text-xs text-muted">project_id: {project.id}</p>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted">
                  <span className="rounded-lg border border-border bg-bg px-2 py-1">
                    tasks: {project.task_count}
                  </span>
                  <span className="rounded-lg border border-border bg-bg px-2 py-1">
                    active: {project.active_task_count}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Link
                    href={`/project/${project.id}`}
                    className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text hover:bg-panel"
                  >
                    项目详情
                  </Link>
                  <Link
                    href={`/project/${project.id}/settings`}
                    className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text hover:bg-panel"
                  >
                    项目设置
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </PanelCard>
    </WorkspaceShell>
  );
}
