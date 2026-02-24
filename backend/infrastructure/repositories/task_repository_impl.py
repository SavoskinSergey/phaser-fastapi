"""Репозиторий заданий пользователя."""
import random
from uuid import uuid4

from sqlalchemy.orm import Session

from infrastructure.database.models import UserTaskModel


REWARD_POINTS_MIN, REWARD_POINTS_MAX = 25, 50
ITEM_TYPES = [1, 2, 3]


def _generate_required_counts() -> tuple[int, int, int]:
    """Сгенерировать 3 случайных типа (сумма количеств = 3). Например (1,1,1) или (2,1,0)."""
    a, b, c = random.choices(ITEM_TYPES, k=3)
    r1 = sum(1 for x in (a, b, c) if x == 1)
    r2 = sum(1 for x in (a, b, c) if x == 2)
    r3 = sum(1 for x in (a, b, c) if x == 3)
    return r1, r2, r3


class SqlAlchemyTaskRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_active_task(self, user_id: str) -> dict | None:
        """Активное задание пользователя."""
        m = (
            self._db.query(UserTaskModel)
            .filter(UserTaskModel.user_id == user_id, UserTaskModel.status == "active")
            .first()
        )
        if not m:
            return None
        return {
            "id": m.id,
            "required_type_1": m.required_type_1,
            "required_type_2": m.required_type_2,
            "required_type_3": m.required_type_3,
            "reward_points": m.reward_points,
            "reward_item_1": m.reward_item_1,
            "reward_item_2": m.reward_item_2,
        }

    def create_task(self, user_id: str) -> dict:
        """Создать новое задание: 3 случайных типа, награда — очки и 2 случайных полуфабриката."""
        r1, r2, r3 = _generate_required_counts()
        reward_points = random.randint(REWARD_POINTS_MIN, REWARD_POINTS_MAX)
        reward_item_1 = random.choice(ITEM_TYPES)
        reward_item_2 = random.choice(ITEM_TYPES)
        m = UserTaskModel(
            id=str(uuid4()),
            user_id=user_id,
            required_type_1=r1,
            required_type_2=r2,
            required_type_3=r3,
            reward_points=reward_points,
            reward_item_1=reward_item_1,
            reward_item_2=reward_item_2,
            status="active",
        )
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return {
            "id": m.id,
            "required_type_1": m.required_type_1,
            "required_type_2": m.required_type_2,
            "required_type_3": m.required_type_3,
            "reward_points": m.reward_points,
            "reward_item_1": m.reward_item_1,
            "reward_item_2": m.reward_item_2,
        }

    def get_or_create_active_task(self, user_id: str) -> dict:
        """Вернуть активное задание или создать новое."""
        t = self.get_active_task(user_id)
        if t:
            return t
        return self.create_task(user_id)

    def complete_task(
        self,
        task_id: str,
        user_id: str,
    ) -> dict | None:
        """Отметить задание выполненным. Вернуть данные задания или None если не найдено."""
        m = (
            self._db.query(UserTaskModel)
            .filter(
                UserTaskModel.id == task_id,
                UserTaskModel.user_id == user_id,
                UserTaskModel.status == "active",
            )
            .first()
        )
        if not m:
            return None
        m.status = "completed"
        self._db.commit()
        return {
            "reward_points": m.reward_points,
            "reward_item_1": m.reward_item_1,
            "reward_item_2": m.reward_item_2,
        }
