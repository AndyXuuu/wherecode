import os
import time
from uuid import uuid4
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
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
    SQLiteStateStore,
)

app = FastAPI(title="WhereCode Control Center")
logger = logging.getLogger("wherecode.control_center")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.getenv("WHERECODE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
action_layer = ActionLayerClient(
    base_url=os.getenv("ACTION_LAYER_BASE_URL", "http://127.0.0.1:8100")
)
AUTH_ENABLED = os.getenv("WHERECODE_AUTH_ENABLED", "true").lower() == "true"
AUTH_TOKEN = os.getenv("WHERECODE_TOKEN", "change-me")
AUTH_WHITELIST_PREFIXES = (
    "/healthz",
    "/docs",
    "/redoc",
    "/openapi.json",
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


state_backend = os.getenv("WHERECODE_STATE_BACKEND", "memory").lower()
sqlite_path = os.getenv("WHERECODE_SQLITE_PATH", ".wherecode/state.db")
state_store = SQLiteStateStore(sqlite_path) if state_backend == "sqlite" else None
store = InMemoryOrchestrator(
    action_executor=execute_with_action_layer,
    state_store=state_store,
)

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


def _extract_request_token(request: Request) -> str | None:
    bearer = request.headers.get("Authorization", "")
    if bearer.startswith("Bearer "):
        return bearer[7:].strip()
    header_token = request.headers.get("X-WhereCode-Token")
    if header_token:
        return header_token.strip()
    return None


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = f"req_{uuid4().hex[:12]}"
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Request-Id"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not AUTH_ENABLED:
        return await call_next(request)

    if request.url.path.startswith(AUTH_WHITELIST_PREFIXES):
        return await call_next(request)

    token = _extract_request_token(request)
    if not token or token != AUTH_TOKEN:
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})

    return await call_next(request)


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
