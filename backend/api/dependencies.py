from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config import settings
from domain.entities.user import User
from infrastructure.database import get_db
from infrastructure.repositories import SqlAlchemyUserRepository, SqlAlchemySessionRepository
from application.services import AuthService, UserService

security = HTTPBearer()


def get_user_repository(db: Session = Depends(get_db)) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(db)


def get_session_repository(db: Session = Depends(get_db)) -> SqlAlchemySessionRepository:
    return SqlAlchemySessionRepository(db)


def get_auth_service(
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repository),
    session_repo: SqlAlchemySessionRepository = Depends(get_session_repository),
) -> AuthService:
    return AuthService(user_repo, session_repo)


def get_user_service(
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(user_repo)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    token = credentials.credentials
    user = auth_service.get_user_by_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user
