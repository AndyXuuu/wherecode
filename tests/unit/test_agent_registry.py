import pytest

from action_layer.services.agent_registry import AgentRegistry, UnknownAgentRoleError


def test_default_mapping_contains_core_roles() -> None:
    registry = AgentRegistry()

    assert registry.resolve("module-dev") == "coding-agent"
    assert registry.resolve("doc-manager") == "doc-agent"
    assert registry.resolve("qa-test") == "test-agent"
    assert registry.resolve("integration-test") == "test-agent"


def test_resolve_normalizes_case_and_spaces() -> None:
    registry = AgentRegistry({"module-dev": "coding-agent"})

    assert registry.resolve("  MODULE-DEV  ") == "coding-agent"


def test_resolve_unknown_role_raises() -> None:
    registry = AgentRegistry({"module-dev": "coding-agent"})

    with pytest.raises(UnknownAgentRoleError):
        registry.resolve("acceptance")


def test_register_new_role_and_has_role() -> None:
    registry = AgentRegistry({"module-dev": "coding-agent"})
    registry.register("acceptance", "acceptance-agent")

    assert registry.has_role("acceptance")
    assert registry.resolve("acceptance") == "acceptance-agent"


def test_register_existing_role_without_overwrite_raises() -> None:
    registry = AgentRegistry({"module-dev": "coding-agent"})

    with pytest.raises(ValueError):
        registry.register("module-dev", "coding-v2-agent")


def test_register_existing_role_with_overwrite_updates_value() -> None:
    registry = AgentRegistry({"module-dev": "coding-agent"})
    registry.register("module-dev", "coding-v2-agent", overwrite=True)

    assert registry.resolve("module-dev") == "coding-v2-agent"


def test_register_rejects_invalid_values() -> None:
    registry = AgentRegistry({"module-dev": "coding-agent"})

    with pytest.raises(ValueError):
        registry.register(" ", "review-agent")
    with pytest.raises(ValueError):
        registry.register("review", " ")
