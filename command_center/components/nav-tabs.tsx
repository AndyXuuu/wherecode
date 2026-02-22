"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/overview", label: "总览" },
  { href: "/tasks", label: "任务" },
  { href: "/projects", label: "项目" },
  { href: "/command-lab", label: "指挥联调" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/overview" && (pathname === "/overview" || pathname === "/feed")) {
    return true;
  }
  if (pathname === href) {
    return true;
  }
  if (href === "/projects" && pathname.startsWith("/project/")) {
    return true;
  }
  if (href === "/tasks" && pathname.startsWith("/task/")) {
    return true;
  }
  return false;
}

export function NavTabs() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap items-center gap-2">
      {tabs.map((tab) => {
        const active = isActive(pathname, tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
              active
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-panel text-text hover:bg-card"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
