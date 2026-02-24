"""Репозиторий заданий на карте (общих для всех игроков)."""
import random
from uuid import uuid4

from sqlalchemy.orm import Session

from infrastructure.database.models import MapTaskModel


REWARD_POINTS_MIN, REWARD_POINTS_MAX = 25, 50
ITEM_TYPES = [1, 2, 3]


def generate_required_counts() -> tuple[int, int, int]:
    a, b, c = random.choices(ITEM_TYPES, k=3)
    r1 = sum(1 for x in (a, b, c) if x == 1)
    r2 = sum(1 for x in (a, b, c) if x == 2)
    r3 = sum(1 for x in (a, b, c) if x == 3)
    return r1, r2, r3


def _to_dict(m: MapTaskModel) -> dict:
    return {
        "id": m.id,
        "tile_x": m.tile_x,
        "tile_y": m.tile_y,
        "required_type_1": m.required_type_1,
        "required_type_2": m.required_type_2,
        "required_type_3": m.required_type_3,
        "reward_points": m.reward_points,
        "reward_item_1": m.reward_item_1,
        "reward_item_2": m.reward_item_2,
    }


class SqlAlchemyMapTaskRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_all(self) -> list[dict]:
        rows = self._db.query(MapTaskModel).all()
        return [_to_dict(m) for m in rows]

    def get_by_tile(self, tile_x: int, tile_y: int) -> dict | None:
        m = (
            self._db.query(MapTaskModel)
            .filter(MapTaskModel.tile_x == tile_x, MapTaskModel.tile_y == tile_y)
            .first()
        )
        return _to_dict(m) if m else None

    def create(
        self,
        tile_x: int,
        tile_y: int,
    ) -> dict:
        r1, r2, r3 = generate_required_counts()
        reward_points = random.randint(REWARD_POINTS_MIN, REWARD_POINTS_MAX)
        reward_item_1 = random.choice(ITEM_TYPES)
        reward_item_2 = random.choice(ITEM_TYPES)
        m = MapTaskModel(
            id=str(uuid4()),
            tile_x=tile_x,
            tile_y=tile_y,
            required_type_1=r1,
            required_type_2=r2,
            required_type_3=r3,
            reward_points=reward_points,
            reward_item_1=reward_item_1,
            reward_item_2=reward_item_2,
        )
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return _to_dict(m)

    def delete_by_id(self, task_id: str) -> None:
        self._db.query(MapTaskModel).filter(MapTaskModel.id == task_id).delete()
        self._db.commit()

    def delete_by_tile(self, tile_x: int, tile_y: int) -> dict | None:
        m = (
            self._db.query(MapTaskModel)
            .filter(MapTaskModel.tile_x == tile_x, MapTaskModel.tile_y == tile_y)
            .first()
        )
        if not m:
            return None
        out = _to_dict(m)
        self._db.delete(m)
        self._db.commit()
        return out
