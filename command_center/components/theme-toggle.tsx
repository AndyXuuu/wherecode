"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function getStoredTheme(): Theme {
  if (typeof window === "undefined") {
    return "light";
  }
  const saved = window.localStorage.getItem("wherecode-theme");
  if (saved === "dark" || saved === "light") {
    return saved;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const activeTheme = getStoredTheme();
    setTheme(activeTheme);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "light" ? "dark" : "light";
    document.documentElement.classList.toggle("dark", nextTheme === "dark");
    window.localStorage.setItem("wherecode-theme", nextTheme);
    setTheme(nextTheme);
  };

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="inline-flex h-9 items-center rounded-full border border-border bg-panel px-3 text-sm text-text transition hover:bg-card"
      aria-label="Toggle color mode"
    >
      <span className="mr-2">{theme === "light" ? "Light" : "Dark"}</span>
      <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground">
        Toggle
      </span>
    </button>
  );
}
