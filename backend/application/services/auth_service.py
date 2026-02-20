from datetime import datetime, timedelta
from uuid import UUID, uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from domain.entities.user import User
from domain.entities.session import Session
from domain.repositories.user_repository import UserRepository
from domain.repositories.session_repository import SessionRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


class AuthService:
    """Сервис аутентификации (Application Service)."""

    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: SessionRepository,
    ):
        self._user_repo = user_repository
        self._session_repo = session_repository

    def create_access_token(self, user_id: str, username: str) -> tuple[str, datetime]:
        """Создаёт JWT и время истечения. jti гарантирует уникальность токена (нет дубликата в sessions.token)."""
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode = {
            "sub": user_id,
            "username": username,
            "exp": expire,
            "jti": str(uuid4()),
        }
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt, expire

    def decode_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        except JWTError:
            return None

    def register(self, username: str, email: str, password: str) -> tuple[User, str]:
        """Регистрация. Возвращает (user, access_token)."""
        if self._user_repo.get_by_username(username):
            raise ValueError("Username already registered")
        user = User(
            id=uuid4(),
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
        )
        user = self._user_repo.add(user)
        token, expires_at = self.create_access_token(str(user.id), user.username)
        session = Session(id=uuid4(), user_id=user.id, token=token, expires_at=expires_at)
        self._session_repo.add(session)
        return user, token

    def login(self, username: str, password: str) -> tuple[User, str]:
        """Вход. Возвращает (user, access_token)."""
        user = self._user_repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Incorrect username or password")
        user.touch_last_login()
        self._user_repo.save(user)
        token, expires_at = self.create_access_token(str(user.id), user.username)
        session = Session(id=uuid4(), user_id=user.id, token=token, expires_at=expires_at)
        self._session_repo.add(session)
        return user, token

    def get_user_by_token(self, token: str) -> User | None:
        """Возвращает пользователя по JWT (проверяем payload, не таблицу sessions)."""
        payload = self.decode_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        try:
            return self._user_repo.get_by_id(UUID(user_id))
        except (ValueError, TypeError):
            return None

    def get_user_by_session_token(self, token: str) -> User | None:
        """Возвращает пользователя по токену сессии (из БД)."""
        session = self._session_repo.get_by_token(token)
        if not session:
            return None
        return self._user_repo.get_by_id(session.user_id)
