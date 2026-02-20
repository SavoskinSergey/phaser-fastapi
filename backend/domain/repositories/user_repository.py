from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from domain.entities.user import User


class UserRepository(ABC):
    """Репозиторий пользователей (интерфейс)."""

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        pass

    @abstractmethod
    def add(self, user: User) -> User:
        pass

    @abstractmethod
    def save(self, user: User) -> User:
        pass
