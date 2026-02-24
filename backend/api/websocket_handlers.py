import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from config import settings
from application.services import AuthService, UserService
from infrastructure.database import SessionLocal
from infrastructure.repositories import SqlAlchemyUserRepository, SqlAlchemySessionRepository, SqlAlchemyBonusRepository

logger = logging.getLogger(__name__)

TILE_SIZE = 56
MAP_TILES_X = 20
MAP_TILES_Y = 15
BONUS_TYPES = [100, 200, 500]  # очки за тип бонуса (зелёный, жёлтый, красный)
BONUS_COUNT = 10
# Тайлы, на которых могут появляться бонусы (включительно)
BONUS_TILE_X_MIN, BONUS_TILE_X_MAX = 1, 11
BONUS_TILE_Y_MIN, BONUS_TILE_Y_MAX = 1, 9


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
bonuses_state: List[Dict[str, Any]] = []  # [{"id": str, "type": 100|200|500, "tile_x": int, "tile_y": int}]
ws_manager = ConnectionManager()


def _add_random_bonus(bonus_repo: SqlAlchemyBonusRepository) -> Dict[str, Any]:
    """Добавляет один бонус в БД и в состояние. Тайлы: x 1..11, y 1..9."""
    bonus_type = random.choice(BONUS_TYPES)
    tile_x = random.randint(BONUS_TILE_X_MIN, BONUS_TILE_X_MAX)
    tile_y = random.randint(BONUS_TILE_Y_MIN, BONUS_TILE_Y_MAX)
    bonus = bonus_repo.create(bonus_type, tile_x, tile_y)
    bonuses_state.append(bonus)
    return bonus


def ensure_bonuses(bonus_repo: SqlAlchemyBonusRepository) -> None:
    """Гарантирует наличие BONUS_COUNT бонусов: при пустом состоянии грузит из БД, иначе добивает новыми."""
    if not bonuses_state:
        for b in bonus_repo.get_all():
            bonuses_state.append(b)
    while len(bonuses_state) < BONUS_COUNT:
        _add_random_bonus(bonus_repo)


def get_db_session():
    return SessionLocal()


def load_or_create_initial_bonuses() -> None:
    """При старте сервера: загрузить бонусы из БД или создать начальные."""
    db = SessionLocal()
    try:
        bonus_repo = SqlAlchemyBonusRepository(db)
        ensure_bonuses(bonus_repo)
    finally:
        db.close()


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

        bonus_repo = SqlAlchemyBonusRepository(db)
        ensure_bonuses(bonus_repo)
        await ws_manager.connect(user_id_str, websocket)
        players_state[user_id_str] = {
            "x": start_x,
            "y": start_y,
            "username": username,
            "balance_points": user.balance_points,
        }

        await ws_manager.broadcast({"type": "state", "players": players_state, "bonuses": bonuses_state})

        try:
            while True:
                data = await websocket.receive_json()

                if data.get("type") == "move":
                    player = players_state.get(user_id_str)
                    if player:
                        player["x"] += data.get("dx", 0)
                        player["y"] += data.get("dy", 0)
                        players_state[user_id_str] = player
                        await ws_manager.broadcast({"type": "state", "players": players_state, "bonuses": bonuses_state})

                elif data.get("type") == "collect_bonus":
                    # Игрок нажал пробел: собираем бонус, если стоит в той же клетке
                    player = players_state.get(user_id_str)
                    if not player:
                        continue
                    tile_x = int(player["x"] // TILE_SIZE)
                    tile_y = int(player["y"] // TILE_SIZE)
                    bonus_idx = None
                    for i, b in enumerate(bonuses_state):
                        if b["tile_x"] == tile_x and b["tile_y"] == tile_y:
                            bonus_idx = i
                            break
                    if bonus_idx is not None:
                        bonus = bonuses_state.pop(bonus_idx)
                        points = bonus["type"]
                        bonus_repo.log_collection(user_id_str, bonus.get("id"), points, bonus["type"])
                        bonus_repo.delete_by_id(bonus["id"])
                        updated_user = user_service.add_points(UUID(user_id_str), points)
                        if updated_user:
                            player["balance_points"] = updated_user.balance_points
                        _add_random_bonus(bonus_repo)
                        # Синхронизация бонусов и игроков всем клиентам при активации бонуса
                        await ws_manager.broadcast({"type": "state", "players": players_state, "bonuses": bonuses_state})

                elif data.get("type") == "sync":
                    # Ручная синхронизация: отправить текущее состояние только запросившему клиенту
                    await websocket.send_json({"type": "state", "players": players_state, "bonuses": bonuses_state})

                elif data.get("type") == "exit":
                    player = players_state.get(user_id_str) or {}
                    x = data.get("x", player.get("x", start_x))
                    y = data.get("y", player.get("y", start_y))
                    # Сохраняем позицию в БД
                    user_service.update_location(UUID(user_id_str), x, y)

                    ws_manager.disconnect(user_id_str)
                    players_state.pop(user_id_str, None)
                    await ws_manager.broadcast({"type": "state", "players": players_state, "bonuses": bonuses_state})
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                    return
        except WebSocketDisconnect:
            player = players_state.get(user_id_str)
            if player:
                x, y = player.get("x", start_x), player.get("y", start_y)
                user_service.update_location(UUID(user_id_str), x, y)
            ws_manager.disconnect(user_id_str)
            players_state.pop(user_id_str, None)
            await ws_manager.broadcast({"type": "state", "players": players_state, "bonuses": bonuses_state})
    finally:
        db.close()
