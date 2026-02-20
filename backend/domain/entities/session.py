from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


def _now() -> datetime:
    return datetime.utcnow()


@dataclass
class Session:
    """Domain entity: сессия пользователя."""
    id: UUID
    user_id: UUID
    token: str
    expires_at: datetime
    created_at: datetime = field(default_factory=_now)

    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at
