from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID

from domain.entities.session import Session


class SessionRepository(ABC):
    """Репозиторий сессий (интерфейс)."""

    @abstractmethod
    def get_by_token(self, token: str) -> Optional[Session]:
        pass

    @abstractmethod
    def add(self, session: Session) -> Session:
        pass

    @abstractmethod
    def delete_by_token(self, token: str) -> None:
        pass

    @abstractmethod
    def extend_expiry(self, token: str, new_expires_at: datetime) -> bool:
        """Продлевает срок действия сессии. Возвращает True если сессия найдена и обновлена."""
        pass

    @abstractmethod
    def delete_expired(self) -> int:
        """Удаляет истёкшие сессии. Возвращает количество удалённых."""
        pass
