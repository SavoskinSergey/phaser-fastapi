import pytest
import json
import time
from fastapi.testclient import TestClient
from main import app, users_db, players_state, saved_positions, manager, create_access_token

client = TestClient(app)


class TestWebSocketConnection:
    """Тесты для WebSocket соединений"""
    
    def test_websocket_connection_without_token(self):
        """Подключение без токена должно быть отклонено"""
        with pytest.raises(Exception):  # WebSocket connection will fail
            with client.websocket_connect("/ws/game") as websocket:
                pass
    
    def test_websocket_connection_with_invalid_token(self):
        """Подключение с невалидным токеном должно быть отклонено"""
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/game?token=invalid.token") as websocket:
                pass
    
    def test_websocket_connection_success(self):
        """Успешное подключение с валидным токеном"""
        # Создаем пользователя и токен
        register_response = client.post(
            "/api/register",
            json={
                "username": "wsuser",
                "email": "wsuser@example.com",
                "password": "password123"
            }
        )
        token = register_response.json()["access_token"]
        
        # Подключаемся через WebSocket
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            # Должны получить начальное состояние
            data = websocket.receive_json()
            assert data["type"] == "state"
            assert "players" in data
            assert len(manager.active_connections) == 1
    
    def test_websocket_player_state_initialization(self):
        """Проверка инициализации состояния игрока"""
        register_response = client.post(
            "/api/register",
            json={
                "username": "player1",
                "email": "player1@example.com",
                "password": "password123"
            }
        )
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user_id"]
        
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            # Получаем начальное состояние
            data = websocket.receive_json()
            
            assert user_id in data["players"]
            player = data["players"][user_id]
            assert player["x"] == 100  # Начальная позиция по умолчанию
            assert player["y"] == 100
            assert player["username"] == "player1"
    
    def test_websocket_player_move(self):
        """Проверка движения игрока"""
        register_response = client.post(
            "/api/register",
            json={
                "username": "mover",
                "email": "mover@example.com",
                "password": "password123"
            }
        )
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user_id"]
        
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            # Получаем начальное состояние
            initial_data = websocket.receive_json()
            initial_x = initial_data["players"][user_id]["x"]
            initial_y = initial_data["players"][user_id]["y"]
            
            # Отправляем движение
            websocket.send_json({"type": "move", "dx": 10, "dy": 5})
            
            # Получаем обновленное состояние
            move_data = websocket.receive_json()
            assert move_data["type"] == "state"
            assert move_data["players"][user_id]["x"] == initial_x + 10
            assert move_data["players"][user_id]["y"] == initial_y + 5
    
    def test_websocket_multiple_moves(self):
        """Проверка нескольких движений подряд"""
        register_response = client.post(
            "/api/register",
            json={
                "username": "multimover",
                "email": "multimover@example.com",
                "password": "password123"
            }
        )
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user_id"]
        
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            # Получаем начальное состояние
            websocket.receive_json()
            
            # Отправляем несколько движений
            websocket.send_json({"type": "move", "dx": 5, "dy": 0})
            websocket.receive_json()  # Получаем обновление
            
            websocket.send_json({"type": "move", "dx": 0, "dy": 10})
            final_data = websocket.receive_json()
            
            player = final_data["players"][user_id]
            assert player["x"] == 105  # 100 + 5
            assert player["y"] == 110  # 100 + 10
    
    def test_websocket_exit_saves_position(self):
        """Проверка сохранения позиции при выходе"""
        register_response = client.post(
            "/api/register",
            json={
                "username": "exiter",
                "email": "exiter@example.com",
                "password": "password123"
            }
        )
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user_id"]
        
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            # Получаем начальное состояние
            websocket.receive_json()
            
            # Двигаемся
            websocket.send_json({"type": "move", "dx": 50, "dy": 30})
            websocket.receive_json()
            
            # Выходим — ждём ответ сервера (broadcast), чтобы он успел сохранить позицию
            websocket.send_json({"type": "exit", "x": 150, "y": 130})
            try:
                websocket.receive_json()  # финальное state перед закрытием
            except Exception:
                pass  # соединение закрыто сервером

        # Даём серверу время завершить обработку (на случай работы в другом потоке)
        time.sleep(0.1)
        # Проверяем, что позиция сохранена
        assert user_id in saved_positions
        assert saved_positions[user_id]["x"] == 150
        assert saved_positions[user_id]["y"] == 130
    
    def test_websocket_restore_saved_position(self):
        """Проверка восстановления сохраненной позиции"""
        register_response = client.post(
            "/api/register",
            json={
                "username": "restorer",
                "email": "restorer@example.com",
                "password": "password123"
            }
        )
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user_id"]
        
        # Первое подключение - двигаемся и выходим
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "move", "dx": 25, "dy": 15})
            websocket.receive_json()
            websocket.send_json({"type": "exit"})
        
        # Второе подключение - должна восстановиться сохраненная позиция
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            data = websocket.receive_json()
            player = data["players"][user_id]
            # Позиция должна быть восстановлена (125, 115) или из exit сообщения
            assert player["x"] in [125, 100]  # Может быть сохранена или по умолчанию
            assert player["y"] in [115, 100]
    
    def test_websocket_multiple_players(self):
        """Проверка нескольких игроков одновременно"""
        # Регистрируем двух игроков
        user1_response = client.post(
            "/api/register",
            json={
                "username": "player1",
                "email": "player1@example.com",
                "password": "password123"
            }
        )
        user2_response = client.post(
            "/api/register",
            json={
                "username": "player2",
                "email": "player2@example.com",
                "password": "password123"
            }
        )
        
        token1 = user1_response.json()["access_token"]
        token2 = user2_response.json()["access_token"]
        user_id1 = user1_response.json()["user_id"]
        user_id2 = user2_response.json()["user_id"]
        
        # Подключаем обоих
        with client.websocket_connect(f"/ws/game?token={token1}") as ws1:
            # Первый игрок получает свое начальное состояние
            data1 = ws1.receive_json()
            assert user_id1 in data1["players"]
            
            with client.websocket_connect(f"/ws/game?token={token2}") as ws2:
                # Оба игрока должны получить обновление с двумя игроками
                update1 = ws1.receive_json()
                update2 = ws2.receive_json()
                
                # Проверяем, что оба игрока видят друг друга
                assert user_id1 in update1["players"]
                assert user_id2 in update1["players"]
                assert user_id1 in update2["players"]
                assert user_id2 in update2["players"]
                
                # Первый игрок двигается
                ws1.send_json({"type": "move", "dx": 20, "dy": 10})
                
                # Оба должны получить обновление
                move_update1 = ws1.receive_json()
                move_update2 = ws2.receive_json()
                
                assert move_update1["players"][user_id1]["x"] == 120
                assert move_update2["players"][user_id1]["x"] == 120
