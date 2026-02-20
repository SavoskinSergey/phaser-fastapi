import pytest
from fastapi.testclient import TestClient

from application.services.auth_service import verify_password, get_password_hash


class TestPasswordHashing:
    """Тесты для хеширования паролей (unit)."""

    def test_hash_password(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password("wrongpassword", hashed) is False


class TestRegister:
    """Тесты для регистрации пользователей (API)."""

    def test_register_success(self, client: TestClient):
        response = client.post(
            "/api/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user_id" in data
        assert data["username"] == "newuser"

    def test_register_duplicate_username(self, client: TestClient):
        client.post(
            "/api/register",
            json={
                "username": "duplicate",
                "email": "first@example.com",
                "password": "password123",
            },
        )
        response = client.post(
            "/api/register",
            json={
                "username": "duplicate",
                "email": "second@example.com",
                "password": "password456",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        response = client.post(
            "/api/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    def test_register_missing_fields(self, client: TestClient):
        response = client.post(
            "/api/register",
            json={"username": "testuser"},
        )
        assert response.status_code == 422


class TestLogin:
    """Тесты для входа пользователей (API)."""

    def test_login_success(self, client: TestClient):
        client.post(
            "/api/register",
            json={
                "username": "loginuser",
                "email": "loginuser@example.com",
                "password": "password123",
            },
        )
        response = client.post(
            "/api/login",
            json={"username": "loginuser", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["username"] == "loginuser"

    def test_login_wrong_password(self, client: TestClient):
        client.post(
            "/api/register",
            json={
                "username": "wrongpass",
                "email": "wrongpass@example.com",
                "password": "correctpassword",
            },
        )
        response = client.post(
            "/api/login",
            json={"username": "wrongpass", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        response = client.post(
            "/api/login",
            json={"username": "nonexistent", "password": "password123"},
        )
        assert response.status_code == 401


class TestGetCurrentUser:
    """Тесты для /api/me."""

    def test_get_current_user_success(self, client: TestClient):
        reg = client.post(
            "/api/register",
            json={
                "username": "currentuser",
                "email": "currentuser@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        response = client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert data["username"] == "currentuser"
        assert "balance_points" in data
        assert "balance_mana" in data
        assert "location_x" in data
        assert "location_y" in data
        assert "last_login" in data
        assert data["balance_points"] == 0
        assert data["balance_mana"] == 0

    def test_get_current_user_invalid_token(self, client: TestClient):
        response = client.get(
            "/api/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_get_current_user_no_token(self, client: TestClient):
        response = client.get("/api/me")
        assert response.status_code == 403


class TestHealth:
    def test_health_endpoint(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
