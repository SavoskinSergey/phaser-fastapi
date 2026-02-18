import pytest
from fastapi.testclient import TestClient
from main import app, users_db, verify_password, get_password_hash, create_access_token, decode_token
from datetime import timedelta

client = TestClient(app)


class TestPasswordHashing:
    """Тесты для хеширования паролей"""
    
    def test_hash_password(self):
        """Проверка хеширования пароля"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt формат
    
    def test_verify_password_correct(self):
        """Проверка правильного пароля"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Проверка неправильного пароля"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False


class TestJWT:
    """Тесты для работы с JWT токенами"""
    
    def test_create_token(self):
        """Проверка создания токена"""
        data = {"sub": "user123", "username": "testuser"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self):
        """Проверка декодирования валидного токена"""
        data = {"sub": "user123", "username": "testuser"}
        token = create_access_token(data)
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
        assert "exp" in payload
    
    def test_decode_invalid_token(self):
        """Проверка декодирования невалидного токена"""
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)
        
        assert payload is None
    
    def test_token_expiration(self):
        """Проверка истечения токена"""
        data = {"sub": "user123", "username": "testuser"}
        expires_delta = timedelta(seconds=-1)  # Токен уже истек
        token = create_access_token(data, expires_delta=expires_delta)
        payload = decode_token(token)
        
        # Токен должен быть None из-за истечения
        assert payload is None


class TestRegister:
    """Тесты для регистрации пользователей"""
    
    def test_register_success(self):
        """Успешная регистрация нового пользователя"""
        response = client.post(
            "/api/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user_id" in data
        assert "username" in data
        assert data["username"] == "newuser"
        assert "newuser" in users_db
    
    def test_register_duplicate_username(self):
        """Регистрация с существующим именем пользователя"""
        # Первая регистрация
        client.post(
            "/api/register",
            json={
                "username": "duplicate",
                "email": "first@example.com",
                "password": "password123"
            }
        )
        
        # Попытка повторной регистрации
        response = client.post(
            "/api/register",
            json={
                "username": "duplicate",
                "email": "second@example.com",
                "password": "password456"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_invalid_email(self):
        """Регистрация с невалидным email"""
        response = client.post(
            "/api/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "password123"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_register_missing_fields(self):
        """Регистрация с отсутствующими полями"""
        response = client.post(
            "/api/register",
            json={
                "username": "testuser"
                # Отсутствуют email и password
            }
        )
        
        assert response.status_code == 422


class TestLogin:
    """Тесты для входа пользователей"""
    
    def test_login_success(self):
        """Успешный вход"""
        # Сначала регистрируем пользователя
        client.post(
            "/api/register",
            json={
                "username": "loginuser",
                "email": "loginuser@example.com",
                "password": "password123"
            }
        )
        
        # Затем входим
        response = client.post(
            "/api/login",
            json={
                "username": "loginuser",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["username"] == "loginuser"
    
    def test_login_wrong_password(self):
        """Вход с неправильным паролем"""
        # Регистрируем пользователя
        client.post(
            "/api/register",
            json={
                "username": "wrongpass",
                "email": "wrongpass@example.com",
                "password": "correctpassword"
            }
        )
        
        # Пытаемся войти с неправильным паролем
        response = client.post(
            "/api/login",
            json={
                "username": "wrongpass",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_login_nonexistent_user(self):
        """Вход несуществующего пользователя"""
        response = client.post(
            "/api/login",
            json={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()


class TestGetCurrentUser:
    """Тесты для получения текущего пользователя"""
    
    def test_get_current_user_success(self):
        """Успешное получение данных пользователя"""
        # Регистрируем и получаем токен
        register_response = client.post(
            "/api/register",
            json={
                "username": "currentuser",
                "email": "currentuser@example.com",
                "password": "password123"
            }
        )
        token = register_response.json()["access_token"]
        
        # Получаем данные пользователя
        response = client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "username" in data
        assert data["username"] == "currentuser"
    
    def test_get_current_user_invalid_token(self):
        """Получение данных с невалидным токеном"""
        response = client.get(
            "/api/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    def test_get_current_user_no_token(self):
        """Получение данных без токена"""
        response = client.get("/api/me")
        
        assert response.status_code == 403  # Forbidden


class TestHealth:
    """Тесты для health check"""
    
    def test_health_endpoint(self):
        """Проверка health endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
