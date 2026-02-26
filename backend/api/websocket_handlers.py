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
    BONUS_COINS,
    INGREDIENT_PRICES,
)

logger = logging.getLogger(__name__)


def _state_message(game_session):
    return {
        "type": "state",
        "players": game_session.players_state,
        "bonuses": game_session.bonuses_state,
        "tasks": game_session.tasks_state,
        "scores": game_session.scores,
        "coins": game_session.session_coins,
        "ingredients": {uid: dict(game_session.session_ingredients.get(uid, {1: 0, 2: 0, 3: 0})) for uid in game_session.players},
        "ends_at": game_session.ends_at,
    }


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
            ing = game_session.session_ingredients.get(user_id_str, {1: 0, 2: 0, 3: 0})
            coins = game_session.session_coins.get(user_id_str, 0)
            await websocket.send_json({
                "type": "state",
                "players": game_session.players_state,
                "bonuses": game_session.bonuses_state,
                "tasks": game_session.tasks_state,
                "scores": game_session.scores,
                "coins": game_session.session_coins,
                "ingredients": {uid: dict(game_session.session_ingredients.get(uid, {1: 0, 2: 0, 3: 0})) for uid in game_session.players},
                "ends_at": game_session.ends_at,
            })
            await websocket.send_json({"type": "inventory", "items": {str(k): ing.get(k, 0) for k in (1, 2, 3)}, "coins": coins})
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
                    await broadcast_session(game_session, _state_message(game_session))

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
                        btype = bonus["type"]  # 1, 2, 3
                        if user_id_str not in game_session.session_ingredients:
                            game_session.session_ingredients[user_id_str] = {1: 0, 2: 0, 3: 0}
                        game_session.session_ingredients[user_id_str][btype] = game_session.session_ingredients[user_id_str].get(btype, 0) + 1
                        game_session.session_coins[user_id_str] = game_session.session_coins.get(user_id_str, 0) + BONUS_COINS.get(btype, 0)
                        _add_bonus_to_session(game_session)
                        await broadcast_session(game_session, _state_message(game_session))
                        ing = game_session.session_ingredients.get(user_id_str, {1: 0, 2: 0, 3: 0})
                        coins = game_session.session_coins.get(user_id_str, 0)
                        await websocket.send_json({"type": "inventory", "items": {str(k): ing.get(k, 0) for k in (1, 2, 3)}, "coins": coins})

                elif data.get("type") == "sync":
                    await websocket.send_json(_state_message(game_session))
                    ing = game_session.session_ingredients.get(user_id_str, {1: 0, 2: 0, 3: 0})
                    coins = game_session.session_coins.get(user_id_str, 0)
                    await websocket.send_json({"type": "inventory", "items": {str(k): ing.get(k, 0) for k in (1, 2, 3)}, "coins": coins})

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
                    r1 = task_at_tile.get("required_type_1", 0)
                    r2 = task_at_tile.get("required_type_2", 0)
                    r3 = task_at_tile.get("required_type_3", 0)
                    if t1 < r1 or t2 < r2 or t3 < r3:
                        await websocket.send_json({"type": "task_error", "detail": "Недостаточно ингредиентов для сдачи"})
                        continue
                    ing = game_session.session_ingredients.get(user_id_str, {1: 0, 2: 0, 3: 0})
                    if ing.get(1, 0) < t1 or ing.get(2, 0) < t2 or ing.get(3, 0) < t3:
                        await websocket.send_json({"type": "task_error", "detail": "Недостаточно ингредиентов в инвентаре"})
                        continue
                    game_session.tasks_state.pop(task_idx)
                    for k, deduct in ((1, t1), (2, t2), (3, t3)):
                        game_session.session_ingredients[user_id_str][k] = ing.get(k, 0) - deduct
                    reward_pts = task_at_tile.get("reward_points", 10)
                    game_session.scores[user_id_str] = game_session.scores.get(user_id_str, 0) + reward_pts
                    reward_count = task_at_tile.get("reward_ingredient_count", 1)
                    reward_ingredients = [random.choice([1, 2, 3]) for _ in range(reward_count)]
                    for itype in reward_ingredients:
                        game_session.session_ingredients[user_id_str][itype] = (
                            game_session.session_ingredients[user_id_str].get(itype, 0) + 1
                        )
                    _add_task_to_session(game_session, random.choice([1, 2, 3]))
                    if user_id_str in game_session.players_state:
                        game_session.players_state[user_id_str]["score"] = game_session.scores[user_id_str]
                    ing2 = game_session.session_ingredients.get(user_id_str, {1: 0, 2: 0, 3: 0})
                    await websocket.send_json({
                        "type": "inventory",
                        "items": {str(k): ing2.get(k, 0) for k in (1, 2, 3)},
                        "coins": game_session.session_coins.get(user_id_str, 0),
                        "task_completed": {"reward_points": reward_pts, "reward_ingredients": reward_ingredients},
                    })
                    await broadcast_session(game_session, _state_message(game_session))

                elif data.get("type") == "buy_ingredient":
                    item_type = int(data.get("item_type", 0))
                    if item_type not in (1, 2, 3):
                        await websocket.send_json({"type": "task_error", "detail": "Неверный тип ингредиента"})
                        continue
                    price = INGREDIENT_PRICES.get(item_type, 0)
                    coins = game_session.session_coins.get(user_id_str, 0)
                    if coins < price:
                        await websocket.send_json({"type": "task_error", "detail": "Недостаточно монет"})
                        continue
                    game_session.session_coins[user_id_str] = coins - price
                    if user_id_str not in game_session.session_ingredients:
                        game_session.session_ingredients[user_id_str] = {1: 0, 2: 0, 3: 0}
                    game_session.session_ingredients[user_id_str][item_type] = game_session.session_ingredients[user_id_str].get(item_type, 0) + 1
                    ing = game_session.session_ingredients[user_id_str]
                    await websocket.send_json({
                        "type": "inventory",
                        "items": {str(k): ing.get(k, 0) for k in (1, 2, 3)},
                        "coins": game_session.session_coins[user_id_str],
                    })

                elif data.get("type") == "exit":
                    remove_connection(session_id, user_id_str)
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                    return

        except WebSocketDisconnect:
            remove_connection(session_id, user_id_str)
    finally:
        db.close()
