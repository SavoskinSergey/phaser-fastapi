import logging
import os
import random
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
from api.game_sessions import (
    get_session,
    add_connection,
    remove_connection,
    broadcast_session,
    _add_bonus_to_session,
    _add_task_to_session,
    _start_game,
    TILE_SIZE,
)

logger = logging.getLogger(__name__)


def get_db_session():
    return SessionLocal()


async def websocket_game_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    session_id = websocket.query_params.get("session_id")
    if not token:
        logger.warning("WebSocket /ws/game: connection rejected, no token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if not session_id:
        logger.warning("WebSocket /ws/game: connection rejected, no session_id")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db: Session = get_db_session()
    try:
        user_repo = SqlAlchemyUserRepository(db)
        session_repo = SqlAlchemySessionRepository(db)
        auth_service = AuthService(user_repo, session_repo)
        user_service = UserService(user_repo)

        user = auth_service.get_user_by_session_token(token)
        if not user:
            user = auth_service.get_user_by_token(token)
        if not user:
            logger.warning("WebSocket /ws/game: connection rejected, invalid or expired token/session")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        new_expires = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        session_repo.extend_expiry(token, new_expires)

        user_id_str = str(user.id)
        username = user.username
        start_x, start_y = 100.0, 100.0

        game_session = await add_connection(session_id, user_id_str, websocket, start_x, start_y, username)
        if not game_session:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()

        # В тестах: один игрок в сессии — стартуем игру при подключении по WebSocket
        if os.environ.get("TESTING") == "1" and game_session.status == "starting" and len(game_session.players) == 1:
            await _start_game(game_session)

        inv_repo = SqlAlchemyInventoryRepository(db)
        inv_repo.grant_random_on_enter(user_id_str)
        bonus_repo = SqlAlchemyBonusRepository(db)
        task_completion_repo = SqlAlchemyTaskCompletionRepository(db)

        if game_session.status in ("waiting", "starting"):
            await websocket.send_json({
                "type": "lobby",
                "players": game_session.players,
                "player_usernames": game_session.player_usernames,
                "countdown_seconds": game_session.countdown_seconds_left,
                "registration_closed": game_session.registration_closed,
            })
        elif game_session.status == "in_progress":
            await websocket.send_json({
                "type": "state",
                "players": game_session.players_state,
                "bonuses": game_session.bonuses_state,
                "tasks": game_session.tasks_state,
                "scores": game_session.scores,
                "ends_at": game_session.ends_at,
            })
            items = inv_repo.get_by_user(user_id_str)
            await websocket.send_json({"type": "inventory", "items": {str(k): v for k, v in items.items()}})
        elif game_session.status == "finished":
            await websocket.send_json({
                "type": "game_ended",
                "winner_id": max(game_session.scores, key=game_session.scores.get) if game_session.scores else None,
                "winner_username": game_session.player_usernames.get(max(game_session.scores, key=game_session.scores.get), "—") if game_session.scores else "—",
                "scores": game_session.scores,
            })

        try:
            while True:
                data = await websocket.receive_json()

                if game_session.status != "in_progress":
                    if data.get("type") == "exit":
                        remove_connection(session_id, user_id_str)
                        await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                        return
                    continue

                if data.get("type") == "move":
                    player = game_session.players_state.get(user_id_str)
                    if player:
                        player["x"] += data.get("dx", 0)
                        player["y"] += data.get("dy", 0)
                        game_session.players_state[user_id_str] = player
                    await broadcast_session(game_session, {
                        "type": "state",
                        "players": game_session.players_state,
                        "bonuses": game_session.bonuses_state,
                        "tasks": game_session.tasks_state,
                        "scores": game_session.scores,
                        "ends_at": game_session.ends_at,
                    })

                elif data.get("type") == "collect_bonus":
                    player = game_session.players_state.get(user_id_str)
                    if not player:
                        continue
                    tile_x = int(player["x"] // TILE_SIZE)
                    tile_y = int(player["y"] // TILE_SIZE)
                    bonus_idx = None
                    for i, b in enumerate(game_session.bonuses_state):
                        if b["tile_x"] == tile_x and b["tile_y"] == tile_y:
                            bonus_idx = i
                            break
                    if bonus_idx is not None:
                        bonus = game_session.bonuses_state.pop(bonus_idx)
                        points = bonus["type"]
                        bonus_repo.log_collection(user_id_str, None, points, bonus["type"])
                        game_session.scores[user_id_str] = game_session.scores.get(user_id_str, 0) + points
                        if user_id_str in game_session.players_state:
                            game_session.players_state[user_id_str]["score"] = game_session.scores[user_id_str]
                        _add_bonus_to_session(game_session)
                        await broadcast_session(game_session, {
                            "type": "state",
                            "players": game_session.players_state,
                            "bonuses": game_session.bonuses_state,
                            "tasks": game_session.tasks_state,
                            "scores": game_session.scores,
                            "ends_at": game_session.ends_at,
                        })

                elif data.get("type") == "sync":
                    await websocket.send_json({
                        "type": "state",
                        "players": game_session.players_state,
                        "bonuses": game_session.bonuses_state,
                        "tasks": game_session.tasks_state,
                        "scores": game_session.scores,
                        "ends_at": game_session.ends_at,
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
                    for i, t in enumerate(game_session.tasks_state):
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
                    game_session.tasks_state.pop(task_idx)
                    inv_repo.deduct(user_id_str, required)
                    reward_pts = task_at_tile["reward_points"]
                    game_session.scores[user_id_str] = game_session.scores.get(user_id_str, 0) + reward_pts
                    inv_repo.add_quantity(user_id_str, task_at_tile["reward_item_1"], 1)
                    inv_repo.add_quantity(user_id_str, task_at_tile["reward_item_2"], 1)
                    task_completion_repo.log(user_id_str, reward_pts, task_at_tile["reward_item_1"], task_at_tile["reward_item_2"])
                    _add_task_to_session(game_session, {
                        1: random.randint(0, 2),
                        2: random.randint(0, 2),
                        3: random.randint(0, 2),
                        "reward_points": task_at_tile.get("reward_points", 10),
                        "reward_item_1": task_at_tile.get("reward_item_1", 1),
                        "reward_item_2": task_at_tile.get("reward_item_2", 2),
                    })
                    if user_id_str in game_session.players_state:
                        game_session.players_state[user_id_str]["score"] = game_session.scores[user_id_str]
                    items = inv_repo.get_by_user(user_id_str)
                    await websocket.send_json({
                        "type": "inventory",
                        "items": {str(k): v for k, v in items.items()},
                        "task_completed": {
                            "reward_points": reward_pts,
                            "reward_item_1": task_at_tile["reward_item_1"],
                            "reward_item_2": task_at_tile["reward_item_2"],
                        },
                    })
                    await broadcast_session(game_session, {
                        "type": "state",
                        "players": game_session.players_state,
                        "bonuses": game_session.bonuses_state,
                        "tasks": game_session.tasks_state,
                        "scores": game_session.scores,
                        "ends_at": game_session.ends_at,
                    })

                elif data.get("type") == "exit":
                    remove_connection(session_id, user_id_str)
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                    return

        except WebSocketDisconnect:
            remove_connection(session_id, user_id_str)
    finally:
        db.close()
