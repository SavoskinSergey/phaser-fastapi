"""Тесты для профиля: бонусы и выполненные задания."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from infrastructure.repositories import SqlAlchemyTaskCompletionRepository


class TestProfile:
    """GET /api/me/profile."""

    def test_profile_returns_bonus_collections_and_task_completions(self, client: TestClient):
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
        assert "recent_bonus_collections" in data
        assert "recent_task_completions" in data
        assert isinstance(data["recent_bonus_collections"], list)
        assert isinstance(data["recent_task_completions"], list)
        assert data["username"] == "profileuser"
        assert "balance_points" in data

    def test_profile_shows_completed_task_after_log(self, client: TestClient, db_session: Session):
        reg = client.post(
            "/api/register",
            json={
                "username": "taskloguser",
                "email": "taskloguser@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]
        db_session.expire_all()
        repo = SqlAlchemyTaskCompletionRepository(db_session)
        repo.log(user_id, 30, 1, 2)
        response = client.get(
            "/api/me/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["recent_task_completions"]) >= 1
        first = data["recent_task_completions"][0]
        assert first["reward_points"] == 30
        assert first["reward_item_1"] == 1
        assert first["reward_item_2"] == 2
        assert "completed_at" in first
