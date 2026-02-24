"""Репозиторий инвентаря пользователя (типы элементов 1, 2, 3)."""
import random
from uuid import uuid4

from sqlalchemy.orm import Session

from infrastructure.database.models import UserInventoryModel, ITEM_TYPE_PRICES


class SqlAlchemyInventoryRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_by_user(self, user_id: str) -> dict[int, int]:
        """Вернуть { item_type: quantity } для пользователя."""
        rows = self._db.query(UserInventoryModel).filter(UserInventoryModel.user_id == user_id).all()
        return {m.item_type: m.quantity for m in rows}

    def ensure_user_rows(self, user_id: str) -> None:
        """Создать строки для типов 1, 2, 3 с quantity=0 если нет."""
        for t in (1, 2, 3):
            if self._db.query(UserInventoryModel).filter(
                UserInventoryModel.user_id == user_id,
                UserInventoryModel.item_type == t,
            ).first() is None:
                m = UserInventoryModel(id=str(uuid4()), user_id=user_id, item_type=t, quantity=0)
                self._db.add(m)
        self._db.commit()

    def add_quantity(self, user_id: str, item_type: int, delta: int) -> int:
        """Добавить delta к quantity. Вернуть новый quantity."""
        self.ensure_user_rows(user_id)
        m = self._db.query(UserInventoryModel).filter(
            UserInventoryModel.user_id == user_id,
            UserInventoryModel.item_type == item_type,
        ).first()
        if not m:
            m = UserInventoryModel(id=str(uuid4()), user_id=user_id, item_type=item_type, quantity=0)
            self._db.add(m)
            self._db.flush()
        m.quantity = max(0, m.quantity + delta)
        self._db.commit()
        self._db.refresh(m)
        return m.quantity

    def grant_random_on_enter(self, user_id: str) -> dict[int, int]:
        """При входе в игру: выдать случайное кол-во элементов по каждому типу. Вернуть итоговый инвентарь."""
        self.ensure_user_rows(user_id)
        for item_type in (1, 2, 3):
            add = random.randint(0, 3)
            if add > 0:
                self.add_quantity(user_id, item_type, add)
        return self.get_by_user(user_id)

    def has_at_least(self, user_id: str, required: dict[int, int]) -> bool:
        """Проверить, что у пользователя есть хотя бы required[type] элементов каждого типа."""
        inv = self.get_by_user(user_id)
        for t, need in required.items():
            if inv.get(t, 0) < need:
                return False
        return True

    def deduct(self, user_id: str, required: dict[int, int]) -> None:
        """Списать требуемое количество (после проверки has_at_least)."""
        for item_type, count in required.items():
            if count > 0:
                self.add_quantity(user_id, item_type, -count)

    def get_price(self, item_type: int) -> int:
        return ITEM_TYPE_PRICES.get(item_type, 0)
