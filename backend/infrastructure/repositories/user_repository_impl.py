from uuid import UUID

from sqlalchemy.orm import Session

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.database.models import UserModel


def _to_domain(m: UserModel) -> User:
    return User(
        id=UUID(m.id),
        username=m.username,
        email=m.email,
        hashed_password=m.hashed_password,
        balance_points=m.balance_points,
        balance_mana=m.balance_mana,
        location_x=float(m.location_x),
        location_y=float(m.location_y),
        last_login=m.last_login,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _to_model(u: User) -> UserModel:
    return UserModel(
        id=str(u.id),
        username=u.username,
        email=u.email,
        hashed_password=u.hashed_password,
        balance_points=u.balance_points,
        balance_mana=u.balance_mana,
        location_x=u.location_x,
        location_y=u.location_y,
        last_login=u.last_login,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    """Реализация репозитория пользователей на SQLAlchemy."""

    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        m = self._db.query(UserModel).filter(UserModel.id == str(user_id)).first()
        return _to_domain(m) if m else None

    def get_by_username(self, username: str) -> User | None:
        m = self._db.query(UserModel).filter(UserModel.username == username).first()
        return _to_domain(m) if m else None

    def add(self, user: User) -> User:
        m = _to_model(user)
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return _to_domain(m)

    def save(self, user: User) -> User:
        m = self._db.query(UserModel).filter(UserModel.id == str(user.id)).first()
        if not m:
            return self.add(user)
        m.username = user.username
        m.email = user.email
        m.hashed_password = user.hashed_password
        m.balance_points = user.balance_points
        m.balance_mana = user.balance_mana
        m.location_x = user.location_x
        m.location_y = user.location_y
        m.last_login = user.last_login
        m.updated_at = user.updated_at
        self._db.commit()
        self._db.refresh(m)
        return _to_domain(m)
