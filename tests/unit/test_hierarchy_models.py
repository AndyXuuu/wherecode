from pydantic import ValidationError

from control_center.models import Command, ProjectDetail, TaskDetail


def test_command_has_prefixed_id() -> None:
    cmd = Command(project_id="proj_alpha", task_id="task_login", sequence=1, text="run tests")
    assert cmd.id.startswith("cmd_")


def test_task_detail_rejects_command_with_wrong_task_id() -> None:
    with_validation_error = False
    try:
        TaskDetail(
            id="task_login",
            project_id="proj_alpha",
            title="Login Refactor",
            commands=[
                Command(
                    project_id="proj_alpha",
                    task_id="task_other",
                    sequence=1,
                    text="run tests",
                )
            ],
        )
    except ValidationError:
        with_validation_error = True

    assert with_validation_error


def test_project_detail_rejects_task_with_wrong_project_id() -> None:
    with_validation_error = False
    try:
        ProjectDetail(
            id="proj_alpha",
            name="WhereCode Mobile",
            tasks=[
                TaskDetail(
                    project_id="proj_beta",
                    title="Task mismatch",
                )
            ],
        )
    except ValidationError:
        with_validation_error = True

    assert with_validation_error
