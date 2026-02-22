"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PanelCard } from "@/components/panel-card";
import { StatusChip } from "@/components/status-chip";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getProjectSnapshot } from "@/lib/control-center-client";
import type { ProjectDetail } from "@/types/hierarchy";

export function ProjectSettingsWorkspace({ projectId }: { projectId: string }) {
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getProjectSnapshot(projectId)
      .then(setDetail)
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "加载项目设置失败");
      });
  }, [projectId]);

  return (
    <WorkspaceShell
      title="项目设置"
      subtitle={`project_id: ${projectId} · 配置展示页（后续可扩展为可编辑）`}
    >
      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <PanelCard title="基础设置" subtitle="当前为只读配置，后续可接入更新接口">
          {error ? <p className="mb-3 rounded-xl border border-danger/40 bg-danger/20 p-2 text-xs text-danger">{error}</p> : null}
          {detail ? (
            <div className="space-y-2 text-sm text-text">
              <p className="rounded-xl border border-border bg-card px-3 py-2">项目名: {detail.name}</p>
              <p className="rounded-xl border border-border bg-card px-3 py-2">owner: {detail.owner ?? "未设置"}</p>
              <p className="rounded-xl border border-border bg-card px-3 py-2">
                tags: {detail.tags.length > 0 ? detail.tags.join(", ") : "无"}
              </p>
              <div className="flex items-center gap-2">
                <StatusChip status={detail.status} />
                <span className="text-xs text-muted">task_count: {detail.task_count}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted">加载中...</p>
          )}
        </PanelCard>

        <PanelCard title="安全与流程" subtitle="审批与回滚策略建议">
          <div className="space-y-2 text-sm text-text">
            <p className="rounded-xl border border-border bg-card p-3">
              建议将高风险命令默认设置为 <code>requires_approval=true</code>。
            </p>
            <p className="rounded-xl border border-border bg-card p-3">
              回滚点建议在任务成功后写入命令摘要，便于移动端快速审批。
            </p>
            <div className="flex flex-wrap gap-2">
              <Link
                href={`/project/${projectId}`}
                className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text hover:bg-panel"
              >
                返回项目详情
              </Link>
              <Link
                href="/command-lab"
                className="rounded-lg border border-border bg-bg px-3 py-1.5 text-xs text-text hover:bg-panel"
              >
                回到指挥流
              </Link>
            </div>
          </div>
        </PanelCard>
      </div>
    </WorkspaceShell>
  );
}
