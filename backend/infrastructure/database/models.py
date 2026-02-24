from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from infrastructure.database.connection import Base


def _uuid_str():
    return str(uuid4())


class UserModel(Base):
    """SQLAlchemy модель пользователя (инфраструктура)."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    balance_points = Column(Integer, default=0, nullable=False)
    balance_mana = Column(Integer, default=0, nullable=False)
    location_x = Column(Float, default=100.0, nullable=False)
    location_y = Column(Float, default=100.0, nullable=False)
    last_login = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")


class SessionModel(Base):
    """SQLAlchemy модель сессии."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(Text, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=False), nullable=False)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)

    user = relationship("UserModel", back_populates="sessions")


class BonusModel(Base):
    """Бонус на карте (тип = очки: 100, 200, 500)."""
    __tablename__ = "bonuses"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    type = Column(Integer, nullable=False)  # 100 | 200 | 500
    tile_x = Column(Integer, nullable=False)
    tile_y = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)


class BonusCollectionModel(Base):
    """Лог: кто какой бонус собрал."""
    __tablename__ = "bonus_collections"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bonus_id = Column(String(36), ForeignKey("bonuses.id", ondelete="SET NULL"), nullable=True, index=True)
    points = Column(Integer, nullable=False)
    bonus_type = Column(Integer, nullable=False)  # 100 | 200 | 500
    collected_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
