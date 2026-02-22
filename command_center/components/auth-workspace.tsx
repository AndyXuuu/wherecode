"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { ControlCenterHealthCard } from "@/components/control-center-health-card";
import { PanelCard } from "@/components/panel-card";
import { WorkspaceShell } from "@/components/workspace-shell";
import { getControlCenterBaseUrl } from "@/lib/control-center-client";

export function AuthWorkspace() {
  const [token, setToken] = useState("");
  const [sessionLabel, setSessionLabel] = useState("Session-A12");
  const [projectHint, setProjectHint] = useState("wherecode-mobile");
  const [notice, setNotice] = useState("");
  const baseUrl = useMemo(getControlCenterBaseUrl, []);

  const handleSave = () => {
    window.localStorage.setItem("wherecode-access-token", token);
    window.localStorage.setItem("wherecode-session-label", sessionLabel);
    window.localStorage.setItem("wherecode-project-hint", projectHint);
    setNotice("本地认证信息已保存。");
  };

  return (
    <WorkspaceShell
      title="认证页"
      subtitle="建立移动端会话入口，保存本地 token 与默认项目上下文。"
      aside={<ControlCenterHealthCard />}
    >
      <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <PanelCard title="会话认证" subtitle="当前版本为本地 token 会话模型。">
          <div className="space-y-3">
            <label className="space-y-1 text-xs text-muted">
              Access Token
              <input
                value={token}
                onChange={(event) => setToken(event.target.value)}
                placeholder="token_xxx"
                className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text"
              />
            </label>
            <label className="space-y-1 text-xs text-muted">
              Session Label
              <input
                value={sessionLabel}
                onChange={(event) => setSessionLabel(event.target.value)}
                className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text"
              />
            </label>
            <label className="space-y-1 text-xs text-muted">
              默认项目提示
              <input
                value={projectHint}
                onChange={(event) => setProjectHint(event.target.value)}
                className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text"
              />
            </label>
            <div className="grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                onClick={handleSave}
                className="rounded-xl bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground"
              >
                保存并进入
              </button>
              <Link
                href="/command-lab"
                className="rounded-xl border border-border bg-card px-3 py-2 text-center text-sm text-text hover:bg-bg"
              >
                跳到指挥流
              </Link>
            </div>
            {notice ? <p className="text-xs text-success">{notice}</p> : null}
          </div>
        </PanelCard>

        <PanelCard title="连接信息" subtitle="Control Center 通信策略：HTTP 异步 + 轮询">
          <div className="space-y-3 text-sm text-text">
            <p className="rounded-xl border border-border bg-card p-3">
              基础地址: <span className="text-muted">{baseUrl}</span>
            </p>
            <ol className="space-y-2 text-xs text-muted">
              <li>1. 创建项目与任务，形成上下文容器。</li>
              <li>2. 提交命令获取 command_id。</li>
              <li>3. 轮询 /commands/{`{id}`} 获取最终结果。</li>
            </ol>
            <p className="rounded-xl border border-border bg-bg p-3 text-xs text-muted">
              管理维度固定为 项目 -&gt; 任务 -&gt; 命令。
            </p>
          </div>
        </PanelCard>
      </div>
    </WorkspaceShell>
  );
}
