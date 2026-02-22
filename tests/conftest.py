import pytest

from control_center.main import store


@pytest.fixture(autouse=True)
def reset_inmemory_store() -> None:
    store.reset()
    yield
    store.reset()
