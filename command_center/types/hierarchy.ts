export type ProjectStatus = "active" | "paused" | "archived";

export type TaskStatus =
  | "todo"
  | "in_progress"
  | "waiting_approval"
  | "blocked"
  | "done"
  | "failed"
  | "canceled";

export type CommandStatus =
  | "queued"
  | "running"
  | "success"
  | "failed"
  | "waiting_approval"
  | "canceled";

export type CommandSource = "user" | "agent" | "automation" | "system";

export interface Command {
  id: string;
  project_id: string;
  task_id: string;
  sequence: number;
  text: string;
  source: CommandSource;
  status: CommandStatus;
  output_summary?: string;
  error_message?: string;
  requested_by?: string;
  requires_approval: boolean;
  approved_by?: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  finished_at?: string;
  metadata: Record<string, unknown>;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: 1 | 2 | 3 | 4 | 5;
  assignee_agent?: string;
  command_count: number;
  success_count: number;
  failed_count: number;
  last_command_id?: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: ProjectStatus;
  owner?: string;
  task_count: number;
  active_task_count: number;
  tags: string[];
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface TaskDetail extends Task {
  commands: Command[];
}

export interface ProjectDetail extends Project {
  tasks: TaskDetail[];
}

export interface HierarchySnapshot {
  projects: ProjectDetail[];
  generated_at: string;
}
