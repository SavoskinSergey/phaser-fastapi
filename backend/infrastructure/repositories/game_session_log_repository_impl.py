"""Лог сессий игр: результат по игроку (место, очки, победа)."""
from typing import List
from uuid import uuid4

from sqlalchemy.orm import Session

from infrastructure.database.models import GameSessionLogModel


class SqlAlchemyGameSessionLogRepository:
    def __init__(self, db: Session):
        self._db = db

    def log_result(
        self,
        game_session_id: str,
        user_id: str,
        place: int,
        score: int,
        is_winner: bool,
    ) -> None:
        m = GameSessionLogModel(
            id=str(uuid4()),
            game_session_id=game_session_id,
            user_id=user_id,
            place=place,
            score=score,
            is_winner=1 if is_winner else 0,
        )
        self._db.add(m)
        self._db.commit()

    def get_recent_by_user(self, user_id: str, limit: int = 20) -> List[dict]:
        rows = (
            self._db.query(GameSessionLogModel)
            .filter(GameSessionLogModel.user_id == user_id)
            .order_by(GameSessionLogModel.played_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "place": m.place,
                "score": m.score,
                "is_winner": bool(m.is_winner),
                "played_at": m.played_at.isoformat() if m.played_at else None,
            }
            for m in rows
        ]
