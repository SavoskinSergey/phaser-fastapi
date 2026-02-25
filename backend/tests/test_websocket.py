"""
Тесты WebSocket под новую логику: сессии (join_or_create), lobby → game_started → state.
В тестах COUNTDOWN=0, игра стартует сразу после join.
"""
import time
import pytest
from fastapi.testclient import TestClient


def _register_and_join(client: TestClient, username: str, email: str) -> tuple[str, str, str]:
    """Регистрация и вход в игру. Возвращает (token, user_id, session_id)."""
    reg = client.post(
        "/api/register",
        json={"username": username, "email": email, "password": "password123"},
    )
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    join_resp = client.post(
        "/api/game/join_or_create",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert join_resp.status_code == 200
    data = join_resp.json()
    session_id = data["session_id"]
    return token, user_id, session_id


def _receive_until_state(websocket) -> dict:
    """Читать сообщения до первого state (пропуская lobby, game_started)."""
    while True:
        msg = websocket.receive_json()
        if msg.get("type") == "state":
            return msg
        if msg.get("type") == "game_ended":
            pytest.fail("Получен game_ended до state")


def _drain_after_state(websocket) -> None:
    """После первого state сервер шлёт ещё state и/или inventory. Читать до inventory (макс. 2 сообщения)."""
    for _ in range(2):
        msg = websocket.receive_json()
        if msg.get("type") == "inventory":
            return


class TestWebSocketConnection:
    """Подключение: токен и session_id обязательны."""

    def test_websocket_connection_without_token(self, client: TestClient):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/game?session_id=fake"):
                pass

    def test_websocket_connection_without_session_id(self, client: TestClient):
        reg = client.post(
            "/api/register",
            json={"username": "u", "email": "u@x.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/game?token={token}"):
                pass

    def test_websocket_connection_invalid_token(self, client: TestClient):
        _, _, session_id = _register_and_join(client, "owner", "owner@example.com")
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"/ws/game?token=invalid.token&session_id={session_id}"
            ):
                pass

    def test_websocket_connection_success(self, client: TestClient):
        token, user_id, session_id = _register_and_join(
            client, "wsuser", "wsuser@example.com"
        )
        with client.websocket_connect(
            f"/ws/game?token={token}&session_id={session_id}"
        ) as ws:
            state = _receive_until_state(ws)
            assert state["type"] == "state"
            assert "players" in state
            assert user_id in state["players"]
            assert "scores" in state
            assert "ends_at" in state

    def test_websocket_player_state_initialization(self, client: TestClient):
        token, user_id, session_id = _register_and_join(
            client, "player1", "player1@example.com"
        )
        with client.websocket_connect(
            f"/ws/game?token={token}&session_id={session_id}"
        ) as ws:
            state = _receive_until_state(ws)
            assert user_id in state["players"]
            player = state["players"][user_id]
            assert player["x"] == 100
            assert player["y"] == 100
            assert player["username"] == "player1"
            _drain_after_state(ws)

    def test_websocket_player_move(self, client: TestClient):
        token, user_id, session_id = _register_and_join(
            client, "mover", "mover@example.com"
        )
        with client.websocket_connect(
            f"/ws/game?token={token}&session_id={session_id}"
        ) as ws:
            state = _receive_until_state(ws)
            _drain_after_state(ws)
            initial_x = state["players"][user_id]["x"]
            initial_y = state["players"][user_id]["y"]
            ws.send_json({"type": "move", "dx": 10, "dy": 5})
            move_data = ws.receive_json()
            assert move_data["type"] == "state"
            assert move_data["players"][user_id]["x"] == initial_x + 10
            assert move_data["players"][user_id]["y"] == initial_y + 5

    def test_websocket_multiple_moves(self, client: TestClient):
        token, user_id, session_id = _register_and_join(
            client, "multimover", "multimover@example.com"
        )
        with client.websocket_connect(
            f"/ws/game?token={token}&session_id={session_id}"
        ) as ws:
            _receive_until_state(ws)
            _drain_after_state(ws)
            ws.send_json({"type": "move", "dx": 5, "dy": 0})
            ws.receive_json()  # state
            ws.send_json({"type": "move", "dx": 0, "dy": 10})
            final_data = ws.receive_json()
            assert final_data["type"] == "state"
            player = final_data["players"][user_id]
            assert player["x"] == 105
            assert player["y"] == 110

    def test_websocket_exit(self, client: TestClient):
        """Выход по type=exit закрывает соединение."""
        token, user_id, session_id = _register_and_join(
            client, "exiter", "exiter@example.com"
        )
        with client.websocket_connect(
            f"/ws/game?token={token}&session_id={session_id}"
        ) as ws:
            _receive_until_state(ws)
            _drain_after_state(ws)
            ws.send_json({"type": "exit", "x": 150, "y": 130})
            try:
                ws.receive_json()
            except Exception:
                pass

    def test_websocket_multiple_players_same_session(self, client: TestClient):
        """Два игрока в одной сессии: второй подключается к сессии первого."""
        token1, user_id1, session_id = _register_and_join(
            client, "player1", "player1@example.com"
        )
        # Второй игрок: регистрация и join_or_create подхватит ту же сессию
        reg2 = client.post(
            "/api/register",
            json={
                "username": "player2",
                "email": "player2@example.com",
                "password": "password123",
            },
        )
        token2 = reg2.json()["access_token"]
        user_id2 = reg2.json()["user_id"]
        join2 = client.post(
            "/api/game/join_or_create",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert join2.status_code == 200
        assert join2.json()["session_id"] == session_id
        assert join2.json()["players_count"] == 2

        with client.websocket_connect(
            f"/ws/game?token={token1}&session_id={session_id}"
        ) as ws1:
            state1 = _receive_until_state(ws1)
            _drain_after_state(ws1)
            with client.websocket_connect(
                f"/ws/game?token={token2}&session_id={session_id}"
            ) as ws2:
                state2 = _receive_until_state(ws2)
                _drain_after_state(ws2)
                assert user_id1 in state2["players"]
                assert user_id2 in state2["players"]
                ws1.send_json({"type": "move", "dx": 20, "dy": 10})
                upd1 = ws1.receive_json()
                upd2 = ws2.receive_json()
                assert upd1["type"] == "state"
                assert upd2["type"] == "state"
                assert upd1["players"][user_id1]["x"] == 120
                assert upd2["players"][user_id1]["x"] == 120


class TestWebSocketStateAndInventory:
    """State с бонусами/заданиями и инвентарь после старта игры."""

    def test_state_includes_bonuses_and_tasks(self, client: TestClient):
        token, user_id, session_id = _register_and_join(
            client, "stateuser", "stateuser@example.com"
        )
        with client.websocket_connect(
            f"/ws/game?token={token}&session_id={session_id}"
        ) as ws:
            state = _receive_until_state(ws)
            assert "bonuses" in state
            assert "tasks" in state
            assert isinstance(state["bonuses"], list)
            assert isinstance(state["tasks"], list)
            # Следующие два сообщения: state и inventory
            msgs = [ws.receive_json() for _ in range(2)]
            inv = next(m for m in msgs if m.get("type") == "inventory")
            assert "items" in inv
            assert "1" in inv["items"] and "2" in inv["items"] and "3" in inv["items"]
            assert "items" in inv
            assert "1" in inv["items"]
            assert "2" in inv["items"]
            assert "3" in inv["items"]

    def test_sync_returns_state(self, client: TestClient):
        token, user_id, session_id = _register_and_join(
            client, "syncuser", "syncuser@example.com"
        )
        with client.websocket_connect(
            f"/ws/game?token={token}&session_id={session_id}"
        ) as ws:
            _receive_until_state(ws)
            _drain_after_state(ws)
            ws.send_json({"type": "sync"})
            data = ws.receive_json()
            assert data["type"] == "state"
            assert "tasks" in data
            assert "scores" in data
            assert "ends_at" in data


class TestWebSocketSubmitTask:
    """Сдача задания по tile_x, tile_y."""

    def test_submit_task_wrong_tile_returns_error(self, client: TestClient):
        token, user_id, session_id = _register_and_join(
            client, "submituser", "submituser@example.com"
        )
        with client.websocket_connect(
            f"/ws/game?token={token}&session_id={session_id}"
        ) as ws:
            _receive_until_state(ws)
            _drain_after_state(ws)
            ws.send_json({
                "type": "submit_task",
                "tile_x": 999,
                "tile_y": 999,
                "type_1": 1,
                "type_2": 1,
                "type_3": 1,
            })
            data = ws.receive_json()
            assert data["type"] == "task_error"
            assert "detail" in data
