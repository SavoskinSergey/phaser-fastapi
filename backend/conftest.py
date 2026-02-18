import pytest
from fastapi.testclient import TestClient
from main import app, users_db, players_state, saved_positions, manager

@pytest.fixture(autouse=True)
def reset_state():
    """Очищает состояние перед каждым тестом"""
    users_db.clear()
    players_state.clear()
    saved_positions.clear()
    manager.active_connections.clear()
    yield
    users_db.clear()
    players_state.clear()
    saved_positions.clear()
    manager.active_connections.clear()

@pytest.fixture
def client():
    """Тестовый клиент FastAPI"""
    return TestClient(app)
