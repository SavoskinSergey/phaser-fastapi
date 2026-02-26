"""
Игровые сессии в памяти: матч до 4 игроков.
Старт: с одного игрока + 10 сек ожидания; при каждом новом подключении таймер сбрасывается на 10 сек.
"""
import asyncio
import logging
import os
import random
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

TILE_SIZE = 56
# Видимая область клиента (800x600, тайл 56) — бонусы и задания только внутри
MAP_TILES_X = 14   # 800 / 56
MAP_TILES_Y = 10   # 600 / 56
# Бонусы = ингредиенты: 1 яблоко, 2 апельсин, 3 ананас. При сборе дают ингредиент + монеты
BONUS_TYPES = [1, 2, 3]  # тип ингредиента
BONUS_COINS = {1: 100, 2: 200, 3: 300}  # монет за бонус
BONUS_COUNT = 10
# Верхнюю линию тайлов (y=0) и первый столбец (x=0) не занимать бонусами и заданиями
BONUS_TILE_X_MIN, BONUS_TILE_X_MAX = 1, MAP_TILES_X - 1
BONUS_TILE_Y_MIN, BONUS_TILE_Y_MAX = 1, MAP_TILES_Y - 1
TASK_COUNT = 10
# Уровни заданий: (сколько ингредиентов сдать, очков награды, сколько случайных ингредиентов в награду)
TASK_LEVELS = {
    1: {"required_total": 2, "reward_points": 10, "reward_ingredient_count": 1},
    2: {"required_total": 4, "reward_points": 30, "reward_ingredient_count": 3},
    3: {"required_total": 6, "reward_points": 70, "reward_ingredient_count": 5},
}
MAX_PLAYERS = 4
COUNTDOWN_SECONDS = 0 if os.environ.get("TESTING") == "1" else 10
GAME_DURATION_SECONDS = 30
# Цены покупки ингредиентов за монеты (в игре)
INGREDIENT_PRICES = {1: 100, 2: 200, 3: 300}  # яблоко, апельсин, ананас


@dataclass
class GameSession:
    id: str
    status: str  # waiting | starting | in_progress | finished
    players: List[str] = field(default_factory=list)  # user_id
    player_usernames: Dict[str, str] = field(default_factory=dict)
    connections: Dict[str, Any] = field(default_factory=dict)  # user_id -> WebSocket
    players_state: Dict[str, dict] = field(default_factory=dict)
    bonuses_state: List[Dict[str, Any]] = field(default_factory=list)
    tasks_state: List[Dict[str, Any]] = field(default_factory=list)
    scores: Dict[str, int] = field(default_factory=dict)  # очки в матче
    session_coins: Dict[str, int] = field(default_factory=dict)  # монеты в сессии по user_id
    session_ingredients: Dict[str, Dict[int, int]] = field(default_factory=dict)  # user_id -> {1: qty, 2: qty, 3: qty}
    started_at: Optional[float] = None
    ends_at: Optional[float] = None
    countdown_seconds_left: Optional[int] = None
    _countdown_task: Optional[asyncio.Task] = None
    _end_task: Optional[asyncio.Task] = None

    @property
    def registration_closed(self) -> bool:
        return len(self.players) >= MAX_PLAYERS or self.status in ("in_progress", "finished")


# Глобальное хранилище сессий (in-memory)
game_sessions: Dict[str, GameSession] = {}
_lock = asyncio.Lock()


def _occupied_tiles(session: GameSession) -> set:
    out = set()
    for b in session.bonuses_state:
        out.add((b["tile_x"], b["tile_y"]))
    for t in session.tasks_state:
        out.add((t["tile_x"], t["tile_y"]))
    return out


def _random_free_tile(occupied: set) -> tuple | None:
    candidates = [
        (x, y)
        for x in range(BONUS_TILE_X_MIN, BONUS_TILE_X_MAX + 1)
        for y in range(BONUS_TILE_Y_MIN, BONUS_TILE_Y_MAX + 1)
        if (x, y) not in occupied
    ]
    return random.choice(candidates) if candidates else None


def _add_bonus_to_session(session: GameSession) -> Dict[str, Any] | None:
    occupied = _occupied_tiles(session)
    tile = _random_free_tile(occupied)
    if not tile:
        return None
    tile_x, tile_y = tile
    bonus_type = random.choice(BONUS_TYPES)
    bonus = {
        "id": str(uuid.uuid4()),
        "type": bonus_type,
        "tile_x": tile_x,
        "tile_y": tile_y,
    }
    session.bonuses_state.append(bonus)
    return bonus


def _random_required_for_total(total: int) -> tuple:
    """Случайное разбиение total на три неотрицательных: required_type_1, 2, 3."""
    a = random.randint(0, total)
    b = random.randint(0, total - a)
    c = total - a - b
    return (a, b, c)


def _add_task_to_session(session: GameSession, level: int) -> Dict[str, Any] | None:
    cfg = TASK_LEVELS.get(level, TASK_LEVELS[1])
    total = cfg["required_total"]
    r1, r2, r3 = _random_required_for_total(total)
    occupied = _occupied_tiles(session)
    tile = _random_free_tile(occupied)
    if not tile:
        return None
    tile_x, tile_y = tile
    task = {
        "id": str(uuid.uuid4()),
        "tile_x": tile_x,
        "tile_y": tile_y,
        "level": level,
        "required_type_1": r1,
        "required_type_2": r2,
        "required_type_3": r3,
        "reward_points": cfg["reward_points"],
        "reward_ingredient_count": cfg["reward_ingredient_count"],
    }
    session.tasks_state.append(task)
    return task


def init_session_world(session: GameSession) -> None:
    """Заполняет бонусы и задания для сессии при старте игры."""
    while len(session.bonuses_state) < BONUS_COUNT:
        if _add_bonus_to_session(session) is None:
            break
    for _ in range(TASK_COUNT):
        level = random.choice([1, 2, 3])
        if _add_task_to_session(session, level) is None:
            break


async def broadcast_session(session: GameSession, message: dict) -> None:
    """Отправить сообщение всем подключённым в сессии."""
    for ws in list(session.connections.values()):
        try:
            await ws.send_json(message)
        except Exception:
            pass


def _cancel_countdown(session: GameSession) -> None:
    """Отменить текущий обратный отсчёт (при новом подключении сбрасываем таймер)."""
    if session._countdown_task and not session._countdown_task.done():
        session._countdown_task.cancel()
        session._countdown_task = None


async def _run_countdown(session: GameSession) -> None:
    """Обратный отсчёт 10 сек: каждую секунду рассылаем lobby, затем старт игры."""
    try:
        for sec in range(COUNTDOWN_SECONDS, 0, -1):
            await asyncio.sleep(1)
            async with _lock:
                if session.status != "starting":
                    return
                session.countdown_seconds_left = sec
            await broadcast_session(
                session,
                {
                    "type": "lobby",
                    "players": session.players,
                    "player_usernames": session.player_usernames,
                    "countdown_seconds": sec,
                    "registration_closed": len(session.players) >= MAX_PLAYERS,
                },
            )
        await _start_game(session)
    except asyncio.CancelledError:
        pass


def _schedule_countdown(session: GameSession) -> None:
    """Запустить или перезапустить обратный отсчёт 10 сек (при новом игроке — сброс)."""
    _cancel_countdown(session)
    session.countdown_seconds_left = COUNTDOWN_SECONDS
    session._countdown_task = asyncio.create_task(_run_countdown(session))


async def _start_game(session: GameSession) -> None:
    async with _lock:
        if session.status != "starting":
            return
        session.status = "in_progress"
        import time
        session.started_at = time.time()
        session.ends_at = session.started_at + GAME_DURATION_SECONDS
        session.countdown_seconds_left = None
        for uid in session.players:
            session.scores[uid] = 0
            session.session_coins[uid] = 0
            session.session_ingredients[uid] = {1: 0, 2: 0, 3: 0}
            if uid not in session.players_state:
                session.players_state[uid] = {
                    "x": 100.0,
                    "y": 100.0,
                    "username": session.player_usernames.get(uid, "?"),
                    "score": 0,
                }
            else:
                session.players_state[uid]["score"] = 0
        init_session_world(session)

    await broadcast_session(session, {
        "type": "game_started",
        "duration_seconds": GAME_DURATION_SECONDS,
        "ends_at": session.ends_at,
    })
    await broadcast_session(session, {
        "type": "state",
        "players": session.players_state,
        "bonuses": session.bonuses_state,
        "tasks": session.tasks_state,
        "scores": session.scores,
        "coins": session.session_coins,
        "ingredients": {uid: dict(session.session_ingredients.get(uid, {1: 0, 2: 0, 3: 0})) for uid in session.players},
        "ends_at": session.ends_at,
    })

    async def end_game():
        await asyncio.sleep(GAME_DURATION_SECONDS)
        async with _lock:
            if session.status != "in_progress":
                return
            session.status = "finished"
        winner_id = max(session.scores, key=session.scores.get) if session.scores else None
        winner_name = session.player_usernames.get(winner_id, "—") if winner_id else "—"
        await broadcast_session(session, {
            "type": "game_ended",
            "winner_id": winner_id,
            "winner_username": winner_name,
            "scores": session.scores,
        })
        # Сохраняем результаты в БД (место, очки, победа) для профиля
        _save_game_results_sync(session.id, dict(session.scores), winner_id)

    session._end_task = asyncio.create_task(end_game())


# Опыт за место: 1-е 40, 2-е 30, 3-е 20, 4-е 10, остальные 0
XP_BY_PLACE = {1: 40, 2: 30, 3: 20, 4: 10}


def _save_game_results_sync(game_session_id: str, scores: dict, winner_id: Optional[str]) -> None:
    """Синхронно записать в БД лог сессии: место, очки, победа; начислить опыт по месту."""
    try:
        from infrastructure.database import SessionLocal
        from infrastructure.repositories import SqlAlchemyGameSessionLogRepository, SqlAlchemyUserRepository
        db = SessionLocal()
        try:
            log_repo = SqlAlchemyGameSessionLogRepository(db)
            user_repo = SqlAlchemyUserRepository(db)
            sorted_players = sorted(scores.items(), key=lambda x: -x[1])
            for place, (user_id, score) in enumerate(sorted_players, start=1):
                log_repo.log_result(
                    game_session_id, user_id, place, score,
                    is_winner=(user_id == winner_id),
                )
                xp = XP_BY_PLACE.get(place, 0)
                if xp:
                    user_repo.add_experience(user_id, xp)
        finally:
            db.close()
    except Exception as e:
        logger.exception("Не удалось сохранить лог игры: %s", e)


async def join_or_create(user_id: str, username: str) -> dict:
    """Найти открытую сессию или создать новую. Возвращает данные для клиента."""
    async with _lock:
        # Ищем сессию: waiting/starting, есть место, пользователь ещё не в ней
        for sid, s in list(game_sessions.items()):
            if s.status in ("waiting", "starting") and len(s.players) < MAX_PLAYERS and user_id not in s.players:
                s.players.append(user_id)
                s.player_usernames[user_id] = username
                # Старт с одного игрока: запускаем/сбрасываем обратный отсчёт 10 сек (при каждом новом подключении)
                s.status = "starting"
                _schedule_countdown(s)

                return {
                    "session_id": s.id,
                    "players_count": len(s.players),
                    "players": s.players,
                    "player_usernames": s.player_usernames,
                    "registration_closed": s.registration_closed,
                    "status": s.status,
                    "countdown_seconds": s.countdown_seconds_left,
                }

        # Создаём новую сессию (старт с одного игрока — сразу обратный отсчёт 10 сек)
        session_id = str(uuid.uuid4())
        s = GameSession(id=session_id, status="starting", players=[user_id], player_usernames={user_id: username})
        game_sessions[session_id] = s
        # В тестах не запускаем таймер для одного игрока — второй успеет присоединиться; старт по WebSocket для 1 игрока
        if not (os.environ.get("TESTING") == "1" and len(s.players) == 1):
            _schedule_countdown(s)
        return {
            "session_id": s.id,
            "players_count": 1,
            "players": s.players,
            "player_usernames": s.player_usernames,
            "registration_closed": False,
            "status": "starting",
            "countdown_seconds": COUNTDOWN_SECONDS,
        }


def get_session(session_id: str) -> Optional[GameSession]:
    return game_sessions.get(session_id)


async def add_connection(session_id: str, user_id: str, websocket: Any, start_x: float, start_y: float, username: str) -> Optional[GameSession]:
    """Добавить WebSocket в сессию. Если игра ещё не началась — добавляем игрока в state."""
    session = game_sessions.get(session_id)
    if not session or user_id not in session.players:
        return None
    session.connections[user_id] = websocket
    session.players_state[user_id] = {
        "x": start_x,
        "y": start_y,
        "username": username,
        "score": session.scores.get(user_id, 0),
    }
    return session


def remove_connection(session_id: str, user_id: str) -> None:
    session = game_sessions.get(session_id)
    if session:
        session.connections.pop(user_id, None)
        session.players_state.pop(user_id, None)
        if not session.connections and session.status in ("waiting", "starting"):
            _cancel_countdown(session)
            game_sessions.pop(session_id, None)
