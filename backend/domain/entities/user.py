from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from domain.value_objects.location import MapLocation


def _now() -> datetime:
    return datetime.utcnow()


@dataclass
class User:
    """Domain entity: пользователь."""
    id: UUID
    username: str
    email: str
    hashed_password: str
    balance_points: int = 0
    balance_mana: int = 0
    experience: int = 0
    location_x: float = 100.0
    location_y: float = 100.0
    last_login: Optional[datetime] = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @property
    def location(self) -> MapLocation:
        return MapLocation(x=self.location_x, y=self.location_y)

    def set_location(self, x: float, y: float) -> None:
        object.__setattr__(self, "location_x", float(x))
        object.__setattr__(self, "location_y", float(y))
        object.__setattr__(self, "updated_at", datetime.utcnow())

    def touch_last_login(self) -> None:
        object.__setattr__(self, "last_login", datetime.utcnow())
        object.__setattr__(self, "updated_at", datetime.utcnow())
