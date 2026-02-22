import type { CommandStatus, ProjectStatus, TaskStatus } from "@/types/hierarchy";

type AnyStatus = CommandStatus | TaskStatus | ProjectStatus | "idle";

function styleByStatus(status: AnyStatus): string {
  switch (status) {
    case "success":
    case "done":
    case "active":
      return "border-success/40 bg-success/20 text-success";
    case "running":
    case "in_progress":
      return "border-primary/40 bg-primary/25 text-text";
    case "queued":
    case "todo":
    case "paused":
    case "idle":
      return "border-border bg-panel text-muted";
    case "waiting_approval":
      return "border-warning/40 bg-warning/20 text-warning";
    case "failed":
    case "blocked":
    case "canceled":
    case "archived":
      return "border-danger/40 bg-danger/20 text-danger";
    default:
      return "border-border bg-panel text-text";
  }
}

function labelByStatus(status: AnyStatus): string {
  return status.replaceAll("_", " ");
}

export function StatusChip({ status }: { status: AnyStatus }) {
  return (
    <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold capitalize ${styleByStatus(status)}`}>
      {labelByStatus(status)}
    </span>
  );
}
