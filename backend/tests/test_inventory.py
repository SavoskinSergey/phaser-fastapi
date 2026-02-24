"""Тесты для инвентаря и покупки предметов."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from infrastructure.database.models import UserModel


class TestGetInventory:
    """GET /api/me/inventory."""

    def test_inventory_returns_items_keys(self, client: TestClient):
        reg = client.post(
            "/api/register",
            json={
                "username": "invuser",
                "email": "invuser@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        response = client.get(
            "/api/me/inventory",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "1" in data["items"]
        assert "2" in data["items"]
        assert "3" in data["items"]
        assert data["items"]["1"] >= 0
        assert data["items"]["2"] >= 0
        assert data["items"]["3"] >= 0

    def test_inventory_unauthorized(self, client: TestClient):
        response = client.get("/api/me/inventory")
        assert response.status_code == 403


class TestBuyItem:
    """POST /api/me/inventory/buy."""

    def test_buy_item_type_1_success(self, client: TestClient, db_session: Session):
        reg = client.post(
            "/api/register",
            json={
                "username": "buyer1",
                "email": "buyer1@example.com",
                "password": "password123",
            },
        )
        assert reg.status_code == 200
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]
        db_session.expire_all()  # увидеть данные, закоммиченные в другом сеансе
        u = db_session.query(UserModel).filter(UserModel.id == user_id).first()
        assert u is not None, "Пользователь должен быть создан регистрацией"
        u.balance_points = 50
        db_session.commit()
        response = client.post(
            "/api/me/inventory/buy",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"item_type": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["balance_points"] == 40  # 50 - 10
        assert data["items"]["1"] >= 1

    def test_buy_item_insufficient_points(self, client: TestClient):
        reg = client.post(
            "/api/register",
            json={
                "username": "pooruser",
                "email": "pooruser@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        response = client.post(
            "/api/me/inventory/buy",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"item_type": 1},
        )
        assert response.status_code == 400
        assert "недостаточно" in response.json().get("detail", "").lower()

    def test_buy_item_invalid_type(self, client: TestClient):
        reg = client.post(
            "/api/register",
            json={
                "username": "badtype",
                "email": "badtype@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        response = client.post(
            "/api/me/inventory/buy",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"item_type": 99},
        )
        assert response.status_code == 400
