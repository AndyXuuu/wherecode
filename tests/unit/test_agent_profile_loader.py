from pathlib import Path

import pytest

from action_layer.services.agent_profile_loader import (
    AgentProfileAccessError,
    AgentProfileLoader,
    AgentProfileNotFoundError,
)
from action_layer.services.agent_registry import AgentRegistry


def _write_profile(root: Path, role: str, content: str) -> Path:
    role_dir = root / role
    role_dir.mkdir(parents=True, exist_ok=True)
    profile_path = role_dir / "AGENTS.md"
    profile_path.write_text(content, encoding="utf-8")
    return profile_path


def test_load_own_profile_success(tmp_path: Path) -> None:
    profiles_root = tmp_path / "agents"
    profile_path = _write_profile(profiles_root, "module-dev", "dev rules")

    loader = AgentProfileLoader(str(profiles_root))
    profile = loader.load("module-dev")

    assert profile.role == "module-dev"
    assert profile.path == str(profile_path.resolve())
    assert profile.content == "dev rules"
    assert len(profile.profile_hash) == 64

    events = loader.get_audit_events()
    assert events[-1].action == "allow"
    assert events[-1].reason == "role_scoped_profile"


def test_load_legacy_profile_fallback_when_standard_missing(tmp_path: Path) -> None:
    profiles_root = tmp_path / "agents"
    role_dir = profiles_root / "module-dev"
    role_dir.mkdir(parents=True, exist_ok=True)
    legacy_profile = role_dir / "agent.md"
    legacy_profile.write_text("legacy rules", encoding="utf-8")

    loader = AgentProfileLoader(str(profiles_root))
    profile = loader.load("module-dev")

    assert profile.path == str(legacy_profile.resolve())
    assert profile.content == "legacy rules"


def test_cross_role_requested_path_is_denied(tmp_path: Path) -> None:
    profiles_root = tmp_path / "agents"
    _write_profile(profiles_root, "module-dev", "dev rules")
    qa_profile = _write_profile(profiles_root, "qa-test", "qa rules")

    loader = AgentProfileLoader(str(profiles_root))

    with pytest.raises(AgentProfileAccessError):
        loader.load("module-dev", requested_path=str(qa_profile))

    events = loader.get_audit_events()
    assert events[-1].action == "deny"
    assert events[-1].reason == "cross_role_or_custom_path_not_allowed"


def test_path_traversal_is_denied(tmp_path: Path) -> None:
    profiles_root = tmp_path / "agents"
    _write_profile(profiles_root, "module-dev", "dev rules")

    loader = AgentProfileLoader(str(profiles_root))
    with pytest.raises(AgentProfileAccessError):
        loader.load("module-dev", requested_path="../qa-test/agent.md")

    events = loader.get_audit_events()
    assert events[-1].action == "deny"


def test_missing_profile_returns_not_found_and_audit(tmp_path: Path) -> None:
    profiles_root = tmp_path / "agents"
    loader = AgentProfileLoader(str(profiles_root))

    with pytest.raises(AgentProfileNotFoundError):
        loader.load("security-review")

    events = loader.get_audit_events()
    assert events[-1].action == "missing"
    assert events[-1].reason == "profile_file_not_found"


def test_loader_falls_back_to_secondary_root(tmp_path: Path) -> None:
    primary_root = tmp_path / "roles"
    legacy_root = tmp_path / "legacy-agents"
    legacy_profile = _write_profile(legacy_root, "module-dev", "legacy rules")

    loader = AgentProfileLoader(str(primary_root), fallback_roots=(str(legacy_root),))
    profile = loader.load("module-dev")

    assert profile.path == str(legacy_profile.resolve())
    assert profile.content == "legacy rules"


def test_default_registry_roles_have_profiles_in_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    profiles_root = repo_root / ".agents" / "roles"
    loader = AgentProfileLoader(str(profiles_root))
    registry = AgentRegistry()

    for role in registry.list_roles():
        profile = loader.load(role)
        assert profile.role == role
