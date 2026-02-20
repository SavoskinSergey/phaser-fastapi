import logging
from datetime import datetime, timedelta
from typing import Dict
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from config import settings
from application.services import AuthService, UserService
from infrastructure.database import SessionLocal
from infrastructure.repositories import SqlAlchemyUserRepository, SqlAlchemySessionRepository

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def broadcast(self, message: dict):
        for ws in list(self.active_connections.values()):
            try:
                await ws.send_json(message)
            except Exception:
                pass


# In-memory state for real-time game (синхронизация между игроками)
players_state: Dict[str, dict] = {}
ws_manager = ConnectionManager()


def get_db_session():
    return SessionLocal()


async def websocket_game_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("WebSocket /ws/game: connection rejected, no token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db: Session = get_db_session()
    try:
        user_repo = SqlAlchemyUserRepository(db)
        session_repo = SqlAlchemySessionRepository(db)
        auth_service = AuthService(user_repo, session_repo)
        user_service = UserService(user_repo)

        # Проверяем сессию в БД (и не истёкшую); fallback на JWT для совместимости с тестами/кэшем
        user = auth_service.get_user_by_session_token(token)
        if not user:
            user = auth_service.get_user_by_token(token)
        if not user:
            logger.warning("WebSocket /ws/game: connection rejected, invalid or expired token/session")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Продлеваем сессию на время игры (если есть в БД), чтобы не разрывать соединение через 30 мин
        new_expires = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        session_repo.extend_expiry(token, new_expires)

        user_id_str = str(user.id)
        username = user.username

        # Начальная позиция из БД
        start_x = user.location_x
        start_y = user.location_y

        await ws_manager.connect(user_id_str, websocket)
        players_state[user_id_str] = {
            "x": start_x,
            "y": start_y,
            "username": username,
        }

        await ws_manager.broadcast({"type": "state", "players": players_state})

        try:
            while True:
                data = await websocket.receive_json()

                if data.get("type") == "move":
                    player = players_state.get(user_id_str)
                    if player:
                        player["x"] += data.get("dx", 0)
                        player["y"] += data.get("dy", 0)
                        players_state[user_id_str] = player
                        await ws_manager.broadcast({"type": "state", "players": players_state})

                elif data.get("type") == "exit":
                    player = players_state.get(user_id_str) or {}
                    x = data.get("x", player.get("x", start_x))
                    y = data.get("y", player.get("y", start_y))
                    # Сохраняем позицию в БД
                    user_service.update_location(UUID(user_id_str), x, y)

                    ws_manager.disconnect(user_id_str)
                    players_state.pop(user_id_str, None)
                    await ws_manager.broadcast({"type": "state", "players": players_state})
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                    return
        except WebSocketDisconnect:
            player = players_state.get(user_id_str)
            if player:
                x, y = player.get("x", start_x), player.get("y", start_y)
                user_service.update_location(UUID(user_id_str), x, y)
            ws_manager.disconnect(user_id_str)
            players_state.pop(user_id_str, None)
            await ws_manager.broadcast({"type": "state", "players": players_state})
    finally:
        db.close()
