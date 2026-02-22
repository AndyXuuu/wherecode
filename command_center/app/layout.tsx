import type { Metadata } from "next";
import Script from "next/script";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "WhereCode Command Center",
  description: "Mobile-first command center UI aligned to Pencil tokens with dark/light modes."
};

const themeInitScript = `
(() => {
  try {
    const saved = localStorage.getItem("wherecode-theme");
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const useDark = saved ? saved === "dark" : systemDark;
    document.documentElement.classList.toggle("dark", useDark);
  } catch (_) {}
})();
`;

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-bg text-text">
        <Script id="theme-init" strategy="beforeInteractive">
          {themeInitScript}
        </Script>
        {children}
      </body>
    </html>
  );
}
