"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PanelCard } from "@/components/panel-card";
import { StatusChip } from "@/components/status-chip";
import { WorkspaceShell } from "@/components/workspace-shell";
import { listProjects, listTasks } from "@/lib/control-center-client";
import type { Project, Task } from "@/types/hierarchy";

export function TasksWorkspace() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState("");

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId]
  );

  useEffect(() => {
    listProjects()
      .then((all) => {
        setProjects(all);
        if (all.length > 0) {
          setSelectedProjectId(all[0].id);
        }
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "加载项目失败");
      });
  }, []);

  useEffect(() => {
    if (!selectedProjectId) {
      setTasks([]);
      return;
    }
    listTasks(selectedProjectId)
      .then(setTasks)
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "加载任务失败");
      });
  }, [selectedProjectId]);

  return (
    <WorkspaceShell
      title="任务中心"
      subtitle="按项目查看任务线程，向下进入命令细节。"
    >
      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <PanelCard title="项目筛选" subtitle="切换项目后刷新任务列表">
          <div className="space-y-2">
            <select
              value={selectedProjectId}
              onChange={(event) => setSelectedProjectId(event.target.value)}
              className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text"
            >
              <option value="">请选择项目</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted">
              {selectedProject ? `project_id: ${selectedProject.id}` : "尚未选择项目"}
            </p>
          </div>
        </PanelCard>

        <PanelCard title="任务列表" subtitle="管理维度：项目 -> 任务 -> 命令">
          {error ? <p className="mb-3 rounded-xl border border-danger/40 bg-danger/20 p-2 text-xs text-danger">{error}</p> : null}
          {tasks.length === 0 ? (
            <p className="text-sm text-muted">当前项目下暂无任务。</p>
          ) : (
            <div className="space-y-2">
              {tasks.map((task) => (
                <article key={task.id} className="rounded-xl border border-border bg-card p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-text">{task.title}</p>
                      <p className="text-xs text-muted">
                        task_id: {task.id} · command_count: {task.command_count}
                      </p>
                    </div>
                    <StatusChip status={task.status} />
                  </div>
                  <div className="mt-2 grid gap-2 text-xs text-muted md:grid-cols-3">
                    <span>success: {task.success_count}</span>
                    <span>failed: {task.failed_count}</span>
                    <span>priority: {task.priority}</span>
                  </div>
                  <div className="mt-3 flex gap-2">
                    <Link
                      href={`/task/${task.id}`}
                      className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text hover:bg-panel"
                    >
                      查看任务详情
                    </Link>
                    <Link
                      href="/command-lab"
                      className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text hover:bg-panel"
                    >
                      继续发命令
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </PanelCard>
      </div>
    </WorkspaceShell>
  );
}
