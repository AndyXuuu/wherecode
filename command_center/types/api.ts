import type { CommandSource, CommandStatus } from "@/types/hierarchy";

export interface CreateProjectInput {
  name: string;
  description?: string;
  owner?: string;
  tags?: string[];
}

export interface CreateTaskInput {
  title: string;
  description?: string;
  priority?: 1 | 2 | 3 | 4 | 5;
  assignee_agent?: string;
}

export interface CreateCommandInput {
  text: string;
  source?: CommandSource;
  requested_by?: string;
  requires_approval?: boolean;
}

export interface ApproveCommandInput {
  approved_by: string;
}

export interface CommandAcceptedResponse {
  command_id: string;
  task_id: string;
  project_id: string;
  status: CommandStatus;
  poll_url: string;
}

export interface ActionLayerHealthResponse {
  status: string;
  layer: string;
  transport: string;
}

export interface ActionExecuteInput {
  text: string;
  requested_by?: string;
  task_id?: string;
  project_id?: string;
}

export interface ActionExecuteResponse {
  status: string;
  summary: string;
  agent: string;
  trace_id: string;
}

export interface MetricsSummaryResponse {
  total_projects: number;
  total_tasks: number;
  total_commands: number;
  in_flight_command_count: number;
  waiting_approval_count: number;
  success_count: number;
  failed_count: number;
  success_rate: number;
  average_duration_ms: number;
  executor_agent_counts: Record<string, number>;
  routing_reason_counts: Record<string, number>;
  routing_keyword_counts: Record<string, number>;
  routing_rule_counts: Record<string, number>;
  recent_windows: Array<{
    window_minutes: number;
    total_commands: number;
    success_count: number;
    failed_count: number;
    success_rate: number;
    average_duration_ms: number;
  }>;
}
