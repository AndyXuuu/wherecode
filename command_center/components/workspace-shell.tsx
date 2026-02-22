import type { ReactNode } from "react";

import { NavTabs } from "@/components/nav-tabs";
import { ThemeToggle } from "@/components/theme-toggle";

export function WorkspaceShell({
  title,
  subtitle,
  children,
  aside
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <main className="mx-auto w-full max-w-[1480px] px-4 py-6 md:px-6">
      <header className="rounded-2xl border border-border bg-panel p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.24em] text-muted">WhereCode Command Center</p>
            <h1 className="text-2xl font-semibold text-text">{title}</h1>
            <p className="text-sm text-muted">{subtitle}</p>
            <NavTabs />
          </div>
          <div className="flex flex-col gap-2">
            <ThemeToggle />
            {aside}
          </div>
        </div>
      </header>
      <section className="mt-6">{children}</section>
    </main>
  );
}
