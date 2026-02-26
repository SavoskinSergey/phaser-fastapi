"""Тесты для профиля: последние игры (место, результат)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from infrastructure.repositories import SqlAlchemyGameSessionLogRepository


class TestProfile:
    """GET /api/me/profile."""

    def test_profile_returns_recent_games(self, client: TestClient):
        reg = client.post(
            "/api/register",
            json={
                "username": "profileuser",
                "email": "profileuser@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]
        response = client.get(
            "/api/me/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "recent_games" in data
        assert isinstance(data["recent_games"], list)
        assert data["username"] == "profileuser"
        assert "balance_points" in data

    def test_profile_shows_game_after_log(self, client: TestClient, db_session: Session):
        reg = client.post(
            "/api/register",
            json={
                "username": "gameloguser",
                "email": "gameloguser@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]
        db_session.expire_all()
        repo = SqlAlchemyGameSessionLogRepository(db_session)
        repo.log_result("session-1", user_id, place=1, score=150, is_winner=True)
        response = client.get(
            "/api/me/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["recent_games"]) >= 1
        first = data["recent_games"][0]
        assert first["place"] == 1
        assert first["score"] == 150
        assert first["is_winner"] is True
        assert "played_at" in first
