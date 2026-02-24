"""Репозиторий бонусов и лога сборов."""
from typing import List
from uuid import uuid4

from sqlalchemy.orm import Session

from infrastructure.database.models import BonusModel, BonusCollectionModel


def _to_dict(m: BonusModel) -> dict:
    return {
        "id": m.id,
        "type": m.type,
        "tile_x": m.tile_x,
        "tile_y": m.tile_y,
    }


class SqlAlchemyBonusRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_all(self) -> List[dict]:
        """Все активные бонусы на карте."""
        rows = self._db.query(BonusModel).all()
        return [_to_dict(m) for m in rows]

    def create(self, bonus_type: int, tile_x: int, tile_y: int) -> dict:
        """Создать бонус в БД и вернуть dict для состояния."""
        m = BonusModel(
            id=str(uuid4()),
            type=bonus_type,
            tile_x=tile_x,
            tile_y=tile_y,
        )
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return _to_dict(m)

    def delete_by_id(self, bonus_id: str) -> None:
        self._db.query(BonusModel).filter(BonusModel.id == bonus_id).delete()
        self._db.commit()

    def log_collection(self, user_id: str, bonus_id: str | None, points: int, bonus_type: int) -> None:
        """Записать в лог сбор бонуса."""
        m = BonusCollectionModel(
            id=str(uuid4()),
            user_id=user_id,
            bonus_id=bonus_id,
            points=points,
            bonus_type=bonus_type,
        )
        self._db.add(m)
        self._db.commit()

    def get_recent_collections_by_user(self, user_id: str, limit: int = 20) -> List[dict]:
        """Последние собранные бонусы пользователя."""
        rows = (
            self._db.query(BonusCollectionModel)
            .filter(BonusCollectionModel.user_id == user_id)
            .order_by(BonusCollectionModel.collected_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "points": m.points,
                "bonus_type": m.bonus_type,
                "collected_at": m.collected_at.isoformat() if m.collected_at else None,
            }
            for m in rows
        ]
