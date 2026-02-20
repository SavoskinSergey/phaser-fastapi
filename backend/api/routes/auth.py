from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas import UserRegister, UserLogin, Token, UserMe
from api.dependencies import get_auth_service, get_current_user
from application.services import AuthService
from domain.entities.user import User

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register", response_model=Token)
def register(
    data: UserRegister,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user, token = auth_service.register(data.username, data.email, data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return Token(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
        username=user.username,
    )


@router.post("/login", response_model=Token)
def login(
    data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user, token = auth_service.login(data.username, data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return Token(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
        username=user.username,
    )


@router.get("/me", response_model=UserMe)
def me(current_user: User = Depends(get_current_user)):
    return UserMe(
        user_id=str(current_user.id),
        username=current_user.username,
        balance_points=current_user.balance_points,
        balance_mana=current_user.balance_mana,
        location_x=current_user.location_x,
        location_y=current_user.location_y,
        last_login=current_user.last_login.isoformat() if current_user.last_login else None,
    )
