import os

from fastapi import FastAPI, status
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from control_center.models import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    ActionLayerHealthResponse,
    ApproveCommandRequest,
    Command,
    CommandAcceptedResponse,
    CreateCommandRequest,
    CreateProjectRequest,
    CreateTaskRequest,
    Project,
    ProjectDetail,
    Task,
)
from control_center.services import (
    ActionLayerClient,
    ActionLayerClientError,
    InMemoryOrchestrator,
)

app = FastAPI(title="WhereCode Control Center")
action_layer = ActionLayerClient(
    base_url=os.getenv("ACTION_LAYER_BASE_URL", "http://127.0.0.1:8100")
)


async def execute_with_action_layer(command: Command) -> ActionExecuteResponse:
    return await action_layer.execute(
        ActionExecuteRequest(
            text=command.text,
            requested_by=command.requested_by,
            task_id=command.task_id,
            project_id=command.project_id,
        )
    )


store = InMemoryOrchestrator(action_executor=execute_with_action_layer)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("WHERECODE_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "transport": "http-async"}


@app.get("/action-layer/health", response_model=ActionLayerHealthResponse)
async def action_layer_health() -> ActionLayerHealthResponse:
    try:
        return await action_layer.get_health()
    except ActionLayerClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/action-layer/execute", response_model=ActionExecuteResponse)
async def action_layer_execute(payload: ActionExecuteRequest) -> ActionExecuteResponse:
    try:
        return await action_layer.execute(payload)
    except ActionLayerClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(payload: CreateProjectRequest) -> Project:
    return await store.create_project(payload)


@app.get("/projects", response_model=list[Project])
async def list_projects() -> list[Project]:
    return await store.list_projects()


@app.post(
    "/projects/{project_id}/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(project_id: str, payload: CreateTaskRequest) -> Task:
    return await store.create_task(project_id, payload)


@app.get("/projects/{project_id}/tasks", response_model=list[Task])
async def list_tasks(project_id: str) -> list[Task]:
    return await store.list_tasks(project_id)


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str) -> Task:
    return await store.get_task(task_id)


@app.post(
    "/tasks/{task_id}/commands",
    response_model=CommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_command(task_id: str, payload: CreateCommandRequest) -> CommandAcceptedResponse:
    command = await store.create_command(task_id, payload)
    return CommandAcceptedResponse(
        command_id=command.id,
        task_id=command.task_id,
        project_id=command.project_id,
        status=command.status,
        poll_url=f"/commands/{command.id}",
    )


@app.get("/tasks/{task_id}/commands", response_model=list[Command])
async def list_commands(task_id: str) -> list[Command]:
    return await store.list_commands(task_id)


@app.get("/commands/{command_id}", response_model=Command)
async def get_command(command_id: str) -> Command:
    return await store.get_command(command_id)


@app.post("/commands/{command_id}/approve", response_model=Command)
async def approve_command(command_id: str, payload: ApproveCommandRequest) -> Command:
    return await store.approve_command(command_id, payload.approved_by)


@app.get("/projects/{project_id}/snapshot", response_model=ProjectDetail)
async def get_project_snapshot(project_id: str) -> ProjectDetail:
    return await store.get_project_detail(project_id)
