import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# В тестах игра стартует сразу (без ожидания 10 сек)
os.environ["TESTING"] = "1"

# Тестовая БД (SQLite in-memory) — одно соединение для всех, иначе таблицы не видны
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Подменяем подключение к БД на тестовое (для всех эндпоинтов и WebSocket)
import infrastructure.database.connection as db_conn
db_conn.engine = test_engine
db_conn.SessionLocal = TestSessionLocal

from infrastructure.database.connection import Base, get_db
from infrastructure.database.models import (
    UserModel,
    SessionModel,
    BonusModel,
    BonusCollectionModel,
    UserInventoryModel,
    UserTaskModel,
    MapTaskModel,
    TaskCompletionModel,
)
from main import app
from api import game_sessions as game_sessions_module


@pytest.fixture(scope="function")
def db_session():
    """Создаёт таблицы и выдаёт сессию для теста."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _reset_db(session):
    session.execute(delete(TaskCompletionModel))
    session.execute(delete(MapTaskModel))
    session.execute(delete(UserTaskModel))
    session.execute(delete(UserInventoryModel))
    session.execute(delete(BonusCollectionModel))
    session.execute(delete(BonusModel))
    session.execute(delete(SessionModel))
    session.execute(delete(UserModel))
    session.commit()


@pytest.fixture(autouse=True)
def reset_state(db_session):
    """Очищает состояние перед каждым тестом."""
    game_sessions_module.game_sessions.clear()
    _reset_db(db_session)
    yield
    game_sessions_module.game_sessions.clear()


def override_get_db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Тестовый клиент FastAPI с подменой БД на SQLite."""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    # WebSocket не использует get_db — подменяем get_db_session, чтобы видеть тестовую БД
    import api.websocket_handlers as ws_handlers
    original_get_db_session = ws_handlers.get_db_session
    ws_handlers.get_db_session = lambda: TestSessionLocal()
    try:
        with TestClient(app) as c:
            yield c
    finally:
        ws_handlers.get_db_session = original_get_db_session
        app.dependency_overrides.clear()
