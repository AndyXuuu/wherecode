import type {
  Command,
  Project,
  ProjectDetail,
  Task
} from "@/types/hierarchy";
import type {
  ActionExecuteInput,
  ActionExecuteResponse,
  ActionLayerHealthResponse,
  ApproveCommandInput,
  CommandAcceptedResponse,
  CreateCommandInput,
  CreateProjectInput,
  CreateTaskInput
} from "@/types/api";

const DEFAULT_BASE_URL = "http://localhost:8000";

export class ControlCenterRequestError extends Error {
  readonly status: number;
  readonly detail?: string;

  constructor(status: number, detail?: string) {
    super(detail ? `HTTP ${status}: ${detail}` : `HTTP ${status}`);
    this.name = "ControlCenterRequestError";
    this.status = status;
    this.detail = detail;
  }
}

export function getControlCenterBaseUrl(): string {
  return process.env.NEXT_PUBLIC_CONTROL_CENTER_URL ?? DEFAULT_BASE_URL;
}

function getControlCenterToken(): string {
  return process.env.NEXT_PUBLIC_WHERECODE_TOKEN ?? "change-me";
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = getControlCenterBaseUrl();
  const token = getControlCenterToken();
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-WhereCode-Token": token,
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    let detail = "";
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? "";
    } catch {
      detail = "";
    }
    throw new ControlCenterRequestError(response.status, detail);
  }

  return (await response.json()) as T;
}

export interface HealthPayload {
  status: string;
  transport: string;
}

export async function healthz(): Promise<HealthPayload> {
  return requestJson<HealthPayload>("/healthz", { method: "GET" });
}

export async function actionLayerHealth(): Promise<ActionLayerHealthResponse> {
  return requestJson<ActionLayerHealthResponse>("/action-layer/health", {
    method: "GET"
  });
}

export async function executeActionLayer(
  input: ActionExecuteInput
): Promise<ActionExecuteResponse> {
  return requestJson<ActionExecuteResponse>("/action-layer/execute", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function createProject(input: CreateProjectInput): Promise<Project> {
  return requestJson<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function listProjects(): Promise<Project[]> {
  return requestJson<Project[]>("/projects", { method: "GET" });
}

export async function createTask(projectId: string, input: CreateTaskInput): Promise<Task> {
  return requestJson<Task>(`/projects/${projectId}/tasks`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function listTasks(projectId: string): Promise<Task[]> {
  return requestJson<Task[]>(`/projects/${projectId}/tasks`, { method: "GET" });
}

export async function getTask(taskId: string): Promise<Task> {
  return requestJson<Task>(`/tasks/${taskId}`, { method: "GET" });
}

export async function submitCommand(
  taskId: string,
  input: CreateCommandInput
): Promise<CommandAcceptedResponse> {
  return requestJson<CommandAcceptedResponse>(`/tasks/${taskId}/commands`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function listCommands(taskId: string): Promise<Command[]> {
  return requestJson<Command[]>(`/tasks/${taskId}/commands`, { method: "GET" });
}

export async function getCommand(commandId: string): Promise<Command> {
  return requestJson<Command>(`/commands/${commandId}`, { method: "GET" });
}

export async function approveCommand(
  commandId: string,
  input: ApproveCommandInput
): Promise<Command> {
  return requestJson<Command>(`/commands/${commandId}/approve`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function getProjectSnapshot(projectId: string): Promise<ProjectDetail> {
  return requestJson<ProjectDetail>(`/projects/${projectId}/snapshot`, {
    method: "GET"
  });
}
