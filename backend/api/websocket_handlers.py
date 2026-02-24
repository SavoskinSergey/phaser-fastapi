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
from infrastructure.repositories import (
    SqlAlchemyUserRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyBonusRepository,
    SqlAlchemyInventoryRepository,
    SqlAlchemyMapTaskRepository,
    SqlAlchemyTaskCompletionRepository,
)

logger = logging.getLogger(__name__)

TILE_SIZE = 56
MAP_TILES_X = 20
MAP_TILES_Y = 15
BONUS_TYPES = [100, 200, 500]  # очки за тип бонуса (зелёный, жёлтый, красный)
BONUS_COUNT = 10
# Тайлы, на которых могут появляться бонусы (включительно)
BONUS_TILE_X_MIN, BONUS_TILE_X_MAX = 1, 11
BONUS_TILE_Y_MIN, BONUS_TILE_Y_MAX = 1, 9
TASK_COUNT = 10


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


# In-memory state for real-time game
players_state: Dict[str, dict] = {}
bonuses_state: List[Dict[str, Any]] = []
tasks_state: List[Dict[str, Any]] = []  # задания на карте, общие для всех
ws_manager = ConnectionManager()


def _occupied_tiles() -> set[tuple[int, int]]:
    """Тайлы, занятые бонусами и заданиями (задание и бонус не могут на одном тайле)."""
    out = set()
    for b in bonuses_state:
        out.add((b["tile_x"], b["tile_y"]))
    for t in tasks_state:
        out.add((t["tile_x"], t["tile_y"]))
    return out


def _random_free_tile(occupied: set[tuple[int, int]]) -> tuple[int, int] | None:
    """Случайный свободный тайл в зоне x 1..11, y 1..9."""
    candidates = [
        (x, y)
        for x in range(BONUS_TILE_X_MIN, BONUS_TILE_X_MAX + 1)
        for y in range(BONUS_TILE_Y_MIN, BONUS_TILE_Y_MAX + 1)
        if (x, y) not in occupied
    ]
    return random.choice(candidates) if candidates else None


def _add_random_bonus(bonus_repo: SqlAlchemyBonusRepository) -> Dict[str, Any] | None:
    """Добавляет один бонус на свободный тайл (не занятый бонусами и заданиями)."""
    occupied = _occupied_tiles()
    tile = _random_free_tile(occupied)
    if not tile:
        return None
    tile_x, tile_y = tile
    bonus_type = random.choice(BONUS_TYPES)
    bonus = bonus_repo.create(bonus_type, tile_x, tile_y)
    bonuses_state.append(bonus)
    return bonus


def ensure_bonuses(bonus_repo: SqlAlchemyBonusRepository) -> None:
    if not bonuses_state:
        for b in bonus_repo.get_all():
            bonuses_state.append(b)
    while len(bonuses_state) < BONUS_COUNT:
        if _add_random_bonus(bonus_repo) is None:
            break


def _add_random_task(map_task_repo: SqlAlchemyMapTaskRepository) -> Dict[str, Any] | None:
    """Добавляет одно задание на свободный тайл."""
    occupied = _occupied_tiles()
    tile = _random_free_tile(occupied)
    if not tile:
        return None
    tile_x, tile_y = tile
    task = map_task_repo.create(tile_x, tile_y)
    tasks_state.append(task)
    return task


def ensure_tasks(map_task_repo: SqlAlchemyMapTaskRepository) -> None:
    """Гарантирует TASK_COUNT заданий на карте (общих для всех)."""
    if not tasks_state:
        for t in map_task_repo.get_all():
            tasks_state.append(t)
    while len(tasks_state) < TASK_COUNT:
        if _add_random_task(map_task_repo) is None:
            break


def get_db_session():
    return SessionLocal()


def load_or_create_initial_bonuses() -> None:
    db = SessionLocal()
    try:
        bonus_repo = SqlAlchemyBonusRepository(db)
        ensure_bonuses(bonus_repo)
    finally:
        db.close()


def load_or_create_initial_tasks() -> None:
    db = SessionLocal()
    try:
        map_task_repo = SqlAlchemyMapTaskRepository(db)
        ensure_tasks(map_task_repo)
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
        map_task_repo = SqlAlchemyMapTaskRepository(db)
        task_completion_repo = SqlAlchemyTaskCompletionRepository(db)
        ensure_bonuses(bonus_repo)
        ensure_tasks(map_task_repo)
        inv_repo = SqlAlchemyInventoryRepository(db)
        inv_repo.grant_random_on_enter(user_id_str)
        await ws_manager.connect(user_id_str, websocket)
        players_state[user_id_str] = {
            "x": start_x,
            "y": start_y,
            "username": username,
            "balance_points": user.balance_points,
        }

        await ws_manager.broadcast({
            "type": "state",
            "players": players_state,
            "bonuses": bonuses_state,
            "tasks": tasks_state,
        })
        items = inv_repo.get_by_user(user_id_str)
        await websocket.send_json({"type": "inventory", "items": {str(k): v for k, v in items.items()}})

        try:
            while True:
                data = await websocket.receive_json()

                if data.get("type") == "move":
                    player = players_state.get(user_id_str)
                    if player:
                        player["x"] += data.get("dx", 0)
                        player["y"] += data.get("dy", 0)
                        players_state[user_id_str] = player
                        await ws_manager.broadcast({"type": "state", "players": players_state, "bonuses": bonuses_state, "tasks": tasks_state})

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
                        await ws_manager.broadcast({"type": "state", "players": players_state, "bonuses": bonuses_state, "tasks": tasks_state})

                elif data.get("type") == "sync":
                    await websocket.send_json({
                        "type": "state",
                        "players": players_state,
                        "bonuses": bonuses_state,
                        "tasks": tasks_state,
                    })
                    items = inv_repo.get_by_user(user_id_str)
                    await websocket.send_json({"type": "inventory", "items": {str(k): v for k, v in items.items()}})

                elif data.get("type") == "submit_task":
                    tile_x = int(data.get("tile_x", -1))
                    tile_y = int(data.get("tile_y", -1))
                    t1 = int(data.get("type_1", 0))
                    t2 = int(data.get("type_2", 0))
                    t3 = int(data.get("type_3", 0))
                    task_at_tile = None
                    task_idx = None
                    for i, t in enumerate(tasks_state):
                        if t["tile_x"] == tile_x and t["tile_y"] == tile_y:
                            task_at_tile = t
                            task_idx = i
                            break
                    if not task_at_tile:
                        await websocket.send_json({"type": "task_error", "detail": "Задание не найдено на этой клетке"})
                        continue
                    if t1 != task_at_tile["required_type_1"] or t2 != task_at_tile["required_type_2"] or t3 != task_at_tile["required_type_3"]:
                        await websocket.send_json({"type": "task_error", "detail": "Нужно сдать другое количество элементов"})
                        continue
                    required = {1: t1, 2: t2, 3: t3}
                    if not inv_repo.has_at_least(user_id_str, required):
                        await websocket.send_json({"type": "task_error", "detail": "Недостаточно элементов в инвентаре"})
                        continue
                    tasks_state.pop(task_idx)
                    map_task_repo.delete_by_tile(tile_x, tile_y)
                    inv_repo.deduct(user_id_str, required)
                    user_service.add_points(UUID(user_id_str), task_at_tile["reward_points"])
                    inv_repo.add_quantity(user_id_str, task_at_tile["reward_item_1"], 1)
                    inv_repo.add_quantity(user_id_str, task_at_tile["reward_item_2"], 1)
                    task_completion_repo.log(
                        user_id_str,
                        task_at_tile["reward_points"],
                        task_at_tile["reward_item_1"],
                        task_at_tile["reward_item_2"],
                    )
                    _add_random_task(map_task_repo)
                    player = players_state.get(user_id_str)
                    if player:
                        u = user_service.get_by_id(UUID(user_id_str))
                        if u:
                            player["balance_points"] = u.balance_points
                    items = inv_repo.get_by_user(user_id_str)
                    await websocket.send_json({
                        "type": "inventory",
                        "items": {str(k): v for k, v in items.items()},
                        "task_completed": {
                            "reward_points": task_at_tile["reward_points"],
                            "reward_item_1": task_at_tile["reward_item_1"],
                            "reward_item_2": task_at_tile["reward_item_2"],
                        },
                    })
                    await ws_manager.broadcast({"type": "state", "players": players_state, "bonuses": bonuses_state, "tasks": tasks_state})

                elif data.get("type") == "exit":
                    player = players_state.get(user_id_str) or {}
                    x = data.get("x", player.get("x", start_x))
                    y = data.get("y", player.get("y", start_y))
                    # Сохраняем позицию в БД
                    user_service.update_location(UUID(user_id_str), x, y)

                    ws_manager.disconnect(user_id_str)
                    players_state.pop(user_id_str, None)
                    await ws_manager.broadcast({"type": "state", "players": players_state, "bonuses": bonuses_state, "tasks": tasks_state})
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                    return
        except WebSocketDisconnect:
            player = players_state.get(user_id_str)
            if player:
                x, y = player.get("x", start_x), player.get("y", start_y)
                user_service.update_location(UUID(user_id_str), x, y)
            ws_manager.disconnect(user_id_str)
            players_state.pop(user_id_str, None)
            await ws_manager.broadcast({"type": "state", "players": players_state, "bonuses": bonuses_state, "tasks": tasks_state})
    finally:
        db.close()
