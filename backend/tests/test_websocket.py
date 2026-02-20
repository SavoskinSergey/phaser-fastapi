import pytest
import time
from fastapi.testclient import TestClient

from api.websocket_handlers import ws_manager


class TestWebSocketConnection:
    """Тесты для WebSocket соединений."""

    def test_websocket_connection_without_token(self, client: TestClient):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/game"):
                pass

    def test_websocket_connection_with_invalid_token(self, client: TestClient):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/game?token=invalid.token"):
                pass

    def test_websocket_connection_success(self, client: TestClient):
        reg = client.post(
            "/api/register",
            json={
                "username": "wsuser",
                "email": "wsuser@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "state"
            assert "players" in data
            assert len(ws_manager.active_connections) == 1

    def test_websocket_player_state_initialization(self, client: TestClient):
        reg = client.post(
            "/api/register",
            json={
                "username": "player1",
                "email": "player1@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            data = websocket.receive_json()
            assert user_id in data["players"]
            player = data["players"][user_id]
            assert player["x"] == 100
            assert player["y"] == 100
            assert player["username"] == "player1"

    def test_websocket_player_move(self, client: TestClient):
        reg = client.post(
            "/api/register",
            json={
                "username": "mover",
                "email": "mover@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            initial_data = websocket.receive_json()
            initial_x = initial_data["players"][user_id]["x"]
            initial_y = initial_data["players"][user_id]["y"]
            websocket.send_json({"type": "move", "dx": 10, "dy": 5})
            move_data = websocket.receive_json()
            assert move_data["type"] == "state"
            assert move_data["players"][user_id]["x"] == initial_x + 10
            assert move_data["players"][user_id]["y"] == initial_y + 5

    def test_websocket_multiple_moves(self, client: TestClient):
        reg = client.post(
            "/api/register",
            json={
                "username": "multimover",
                "email": "multimover@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "move", "dx": 5, "dy": 0})
            websocket.receive_json()
            websocket.send_json({"type": "move", "dx": 0, "dy": 10})
            final_data = websocket.receive_json()
            player = final_data["players"][user_id]
            assert player["x"] == 105
            assert player["y"] == 110

    def test_websocket_exit_saves_position(self, client: TestClient):
        """Позиция при выходе сохраняется в БД; проверяем через /api/me."""
        reg = client.post(
            "/api/register",
            json={
                "username": "exiter",
                "email": "exiter@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "move", "dx": 50, "dy": 30})
            websocket.receive_json()
            websocket.send_json({"type": "exit", "x": 150, "y": 130})
            try:
                websocket.receive_json()
            except Exception:
                pass
        time.sleep(0.1)
        me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        data = me.json()
        assert data["user_id"] == user_id
        assert data["location_x"] == 150
        assert data["location_y"] == 130

    def test_websocket_restore_saved_position(self, client: TestClient):
        """После выхода позиция восстанавливается из БД при новом подключении."""
        reg = client.post(
            "/api/register",
            json={
                "username": "restorer",
                "email": "restorer@example.com",
                "password": "password123",
            },
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            websocket.receive_json()
            websocket.send_json({"type": "move", "dx": 25, "dy": 15})
            websocket.receive_json()
            websocket.send_json({"type": "exit", "x": 125, "y": 115})
            try:
                websocket.receive_json()
            except Exception:
                pass
        time.sleep(0.1)
        with client.websocket_connect(f"/ws/game?token={token}") as websocket:
            data = websocket.receive_json()
            player = data["players"][user_id]
            assert player["x"] == 125
            assert player["y"] == 115

    def test_websocket_multiple_players(self, client: TestClient):
        r1 = client.post(
            "/api/register",
            json={
                "username": "player1",
                "email": "player1@example.com",
                "password": "password123",
            },
        )
        r2 = client.post(
            "/api/register",
            json={
                "username": "player2",
                "email": "player2@example.com",
                "password": "password123",
            },
        )
        token1 = r1.json()["access_token"]
        token2 = r2.json()["access_token"]
        user_id1 = r1.json()["user_id"]
        user_id2 = r2.json()["user_id"]
        with client.websocket_connect(f"/ws/game?token={token1}") as ws1:
            data1 = ws1.receive_json()
            assert user_id1 in data1["players"]
            with client.websocket_connect(f"/ws/game?token={token2}") as ws2:
                update1 = ws1.receive_json()
                update2 = ws2.receive_json()
                assert user_id1 in update1["players"]
                assert user_id2 in update1["players"]
                assert user_id1 in update2["players"]
                assert user_id2 in update2["players"]
                ws1.send_json({"type": "move", "dx": 20, "dy": 10})
                move_update1 = ws1.receive_json()
                move_update2 = ws2.receive_json()
                assert move_update1["players"][user_id1]["x"] == 120
                assert move_update2["players"][user_id1]["x"] == 120
