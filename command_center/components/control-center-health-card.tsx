"use client";

import { useEffect, useMemo, useState } from "react";

type ProbeState = {
  status: "idle" | "ok" | "error";
  message: string;
};

function getBaseUrl() {
  return process.env.NEXT_PUBLIC_CONTROL_CENTER_URL ?? "http://localhost:8000";
}

function getControlCenterToken() {
  return process.env.NEXT_PUBLIC_WHERECODE_TOKEN ?? "change-me";
}

export function ControlCenterHealthCard() {
  const [probe, setProbe] = useState<ProbeState>({
    status: "idle",
    message: "Checking Control/Action layers..."
  });
  const baseUrl = useMemo(getBaseUrl, []);
  const token = useMemo(getControlCenterToken, []);

  useEffect(() => {
    let cancelled = false;

    async function runProbe() {
      try {
        const [controlResponse, actionResponse] = await Promise.all([
          fetch(`${baseUrl}/healthz`, { cache: "no-store" }),
          fetch(`${baseUrl}/action-layer/health`, {
            cache: "no-store",
            headers: { "X-WhereCode-Token": token }
          })
        ]);
        if (!controlResponse.ok) {
          throw new Error(`Control Center HTTP ${controlResponse.status}`);
        }
        if (!actionResponse.ok) {
          throw new Error(`Action Layer HTTP ${actionResponse.status}`);
        }
        const controlData = (await controlResponse.json()) as {
          status?: string;
          transport?: string;
        };
        const actionData = (await actionResponse.json()) as {
          status?: string;
          layer?: string;
          transport?: string;
        };
        if (cancelled) {
          return;
        }
        setProbe({
          status: "ok",
          message:
            `Control: ${controlData.status ?? "ok"} (${controlData.transport ?? "http"})` +
            ` | Action: ${actionData.status ?? "ok"} (${actionData.layer ?? "agent"}, ${actionData.transport ?? "http"})`
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setProbe({
          status: "error",
          message: `Layer probe failed: ${error instanceof Error ? error.message : "unknown error"}`
        });
      }
    }

    runProbe();
    const timer = window.setInterval(runProbe, 10000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [baseUrl, token]);

  const style =
    probe.status === "ok"
      ? "bg-success/20 border-success/30 text-success"
      : probe.status === "error"
        ? "bg-danger/15 border-danger/30 text-danger"
        : "bg-panel border-border text-text";

  return (
    <div className={`rounded-xl border p-3 ${style}`}>
      <p className="text-[11px] uppercase tracking-[0.18em]">Control Center Probe</p>
      <p className="mt-1 text-xs">{probe.message}</p>
    </div>
  );
}
