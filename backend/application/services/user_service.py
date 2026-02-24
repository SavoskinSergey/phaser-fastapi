from uuid import UUID

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository


class UserService:
    """Сервис пользователей (Application Service)."""

    def __init__(self, user_repository: UserRepository):
        self._user_repo = user_repository

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._user_repo.get_by_id(user_id)

    def update_location(self, user_id: UUID, x: float, y: float) -> User | None:
        user = self._user_repo.get_by_id(user_id)
        if not user:
            return None
        user.set_location(x, y)
        return self._user_repo.save(user)

    def add_points(self, user_id: UUID, points: int) -> User | None:
        """Добавляет очки к балансу игрока."""
        user = self._user_repo.get_by_id(user_id)
        if not user:
            return None
        object.__setattr__(user, "balance_points", user.balance_points + points)
        return self._user_repo.save(user)

    def update_balances(self, user_id: UUID, balance_points: int | None = None, balance_mana: int | None = None) -> User | None:
        user = self._user_repo.get_by_id(user_id)
        if not user:
            return None
        if balance_points is not None:
            object.__setattr__(user, "balance_points", balance_points)
        if balance_mana is not None:
            object.__setattr__(user, "balance_mana", balance_mana)
        return self._user_repo.save(user)
