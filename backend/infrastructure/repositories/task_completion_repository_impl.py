"""Лог выполненных заданий."""
from typing import List
from uuid import uuid4

from sqlalchemy.orm import Session

from infrastructure.database.models import TaskCompletionModel


class SqlAlchemyTaskCompletionRepository:
    def __init__(self, db: Session):
        self._db = db

    def log(self, user_id: str, reward_points: int, reward_item_1: int, reward_item_2: int) -> None:
        m = TaskCompletionModel(
            id=str(uuid4()),
            user_id=user_id,
            reward_points=reward_points,
            reward_item_1=reward_item_1,
            reward_item_2=reward_item_2,
        )
        self._db.add(m)
        self._db.commit()

    def get_recent_by_user(self, user_id: str, limit: int = 20) -> List[dict]:
        rows = (
            self._db.query(TaskCompletionModel)
            .filter(TaskCompletionModel.user_id == user_id)
            .order_by(TaskCompletionModel.completed_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "reward_points": m.reward_points,
                "reward_item_1": m.reward_item_1,
                "reward_item_2": m.reward_item_2,
                "completed_at": m.completed_at.isoformat() if m.completed_at else None,
            }
            for m in rows
        ]
