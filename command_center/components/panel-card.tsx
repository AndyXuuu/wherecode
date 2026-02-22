import type { ReactNode } from "react";

export function PanelCard({
  title,
  subtitle,
  children
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <article className="rounded-2xl border border-border bg-panel p-4 shadow-panel">
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-text">{title}</h2>
        {subtitle ? <p className="mt-1 text-xs text-muted">{subtitle}</p> : null}
      </div>
      {children}
    </article>
  );
}
