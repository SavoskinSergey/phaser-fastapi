from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MapLocation:
    """Value object: координаты на карте."""
    x: float
    y: float

    def __post_init__(self):
        object.__setattr__(self, "x", float(self.x))
        object.__setattr__(self, "y", float(self.y))

    @classmethod
    def default(cls) -> "MapLocation":
        return cls(x=100.0, y=100.0)
