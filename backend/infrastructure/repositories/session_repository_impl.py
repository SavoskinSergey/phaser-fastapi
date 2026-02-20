from datetime import datetime

from sqlalchemy.orm import Session

from domain.entities.session import Session as DomainSession
from domain.repositories.session_repository import SessionRepository
from infrastructure.database.models import SessionModel


def _to_domain(m: SessionModel) -> DomainSession:
    from uuid import UUID
    return DomainSession(
        id=UUID(m.id),
        user_id=UUID(m.user_id),
        token=m.token,
        expires_at=m.expires_at,
        created_at=m.created_at,
    )


class SqlAlchemySessionRepository(SessionRepository):
    """Реализация репозитория сессий на SQLAlchemy."""

    def __init__(self, db: Session):
        self._db = db

    def get_by_token(self, token: str) -> DomainSession | None:
        m = self._db.query(SessionModel).filter(SessionModel.token == token).first()
        if not m or m.expires_at < datetime.utcnow():
            return None
        return _to_domain(m)

    def add(self, session: DomainSession) -> DomainSession:
        m = SessionModel(
            id=str(session.id),
            user_id=str(session.user_id),
            token=session.token,
            expires_at=session.expires_at,
            created_at=session.created_at,
        )
        self._db.add(m)
        self._db.commit()
        self._db.refresh(m)
        return _to_domain(m)

    def delete_by_token(self, token: str) -> None:
        self._db.query(SessionModel).filter(SessionModel.token == token).delete()
        self._db.commit()

    def extend_expiry(self, token: str, new_expires_at: datetime) -> bool:
        m = self._db.query(SessionModel).filter(SessionModel.token == token).first()
        if not m:
            return False
        m.expires_at = new_expires_at
        self._db.commit()
        return True

    def delete_expired(self) -> int:
        n = self._db.query(SessionModel).filter(SessionModel.expires_at < datetime.utcnow()).delete()
        self._db.commit()
        return n
