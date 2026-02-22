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
