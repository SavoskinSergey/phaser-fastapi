"""
Тесты для игровых сессий (api.game_sessions): рассылка по сессии, get_session, add_connection.
Раньше тестировался ConnectionManager — он удалён, логика перенесена в сессии.
"""
import pytest
from unittest.mock import AsyncMock
from api.game_sessions import (
    GameSession,
    game_sessions,
    get_session,
    broadcast_session,
    add_connection,
    remove_connection,
)


class TestGameSession:
    """Тесты сущности GameSession."""

    def test_session_init(self):
        s = GameSession(id="sid1", status="waiting")
        assert s.id == "sid1"
        assert s.status == "waiting"
        assert s.players == []
        assert s.connections == {}
        assert s.players_state == {}
        assert s.scores == {}

    def test_registration_closed_when_full(self):
        s = GameSession(id="s", status="waiting", players=["a", "b", "c", "d"])
        assert s.registration_closed is True

    def test_registration_closed_when_in_progress(self):
        s = GameSession(id="s", status="in_progress", players=["a"])
        assert s.registration_closed is True

    def test_registration_open(self):
        s = GameSession(id="s", status="waiting", players=["a", "b"])
        assert s.registration_closed is False


class TestGetSession:
    def test_get_session_missing(self):
        game_sessions.clear()
        assert get_session("nonexistent") is None

    def test_get_session_exists(self):
        game_sessions.clear()
        s = GameSession(id="sid1", status="waiting")
        game_sessions["sid1"] = s
        assert get_session("sid1") is s
        game_sessions.clear()


class TestBroadcastAndConnections:
    """Рассылка и добавление/удаление соединений в сессии."""

    @pytest.mark.asyncio
    async def test_add_connection_and_broadcast(self):
        game_sessions.clear()
        s = GameSession(
            id="sid1",
            status="in_progress",
            players=["u1"],
            player_usernames={"u1": "Alice"},
        )
        game_sessions["sid1"] = s

        ws = AsyncMock()
        session = await add_connection("sid1", "u1", ws, 100.0, 100.0, "Alice")
        assert session is s
        assert "u1" in s.connections
        assert s.connections["u1"] == ws
        assert "u1" in s.players_state
        assert s.players_state["u1"]["x"] == 100
        assert s.players_state["u1"]["username"] == "Alice"

        msg = {"type": "test", "data": "hello"}
        await broadcast_session(s, msg)
        ws.send_json.assert_called_once_with(msg)

        remove_connection("sid1", "u1")
        assert "u1" not in s.connections
        assert "u1" not in s.players_state
        game_sessions.clear()

    @pytest.mark.asyncio
    async def test_add_connection_wrong_session(self):
        game_sessions.clear()
        session = await add_connection("nonexistent", "u1", AsyncMock(), 100, 100, "A")
        assert session is None

    @pytest.mark.asyncio
    async def test_add_connection_user_not_in_players(self):
        game_sessions.clear()
        s = GameSession(id="sid1", status="waiting", players=["u1"])
        game_sessions["sid1"] = s
        session = await add_connection("sid1", "u2", AsyncMock(), 100, 100, "B")
        assert session is None
        game_sessions.clear()

    @pytest.mark.asyncio
    async def test_broadcast_empty_connections(self):
        s = GameSession(id="s", status="in_progress", players=[])
        # Не должно падать
        await broadcast_session(s, {"type": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_skips_failed_send(self):
        s = GameSession(id="s", status="in_progress", players=[])
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json.side_effect = Exception("send error")
        s.connections["u1"] = ws1
        s.connections["u2"] = ws2
        await broadcast_session(s, {"type": "test"})
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
