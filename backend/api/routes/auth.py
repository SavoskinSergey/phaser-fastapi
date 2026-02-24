from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.schemas import (
    UserRegister,
    UserLogin,
    Token,
    UserMe,
    ProfileResponse,
    InventoryResponse,
    BuyItemRequest,
)
from api.dependencies import get_auth_service, get_current_user
from infrastructure.database import get_db
from application.services import AuthService
from domain.entities.user import User
from infrastructure.repositories import (
    SqlAlchemyBonusRepository,
    SqlAlchemyInventoryRepository,
    SqlAlchemyTaskCompletionRepository,
)
from infrastructure.database.models import ITEM_TYPE_PRICES

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


@router.get("/me/profile", response_model=ProfileResponse)
def profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bonus_repo = SqlAlchemyBonusRepository(db)
    task_completion_repo = SqlAlchemyTaskCompletionRepository(db)
    recent_bonuses = bonus_repo.get_recent_collections_by_user(str(current_user.id), limit=20)
    recent_tasks = task_completion_repo.get_recent_by_user(str(current_user.id), limit=20)
    return ProfileResponse(
        user_id=str(current_user.id),
        username=current_user.username,
        balance_points=current_user.balance_points,
        balance_mana=current_user.balance_mana,
        location_x=current_user.location_x,
        location_y=current_user.location_y,
        last_login=current_user.last_login.isoformat() if current_user.last_login else None,
        recent_bonus_collections=[
            {"points": c["points"], "bonus_type": c["bonus_type"], "collected_at": c["collected_at"]}
            for c in recent_bonuses
        ],
        recent_task_completions=[
            {"reward_points": t["reward_points"], "reward_item_1": t["reward_item_1"], "reward_item_2": t["reward_item_2"], "completed_at": t["completed_at"]}
            for t in recent_tasks
        ],
    )


@router.get("/me/inventory", response_model=InventoryResponse)
def get_inventory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inv_repo = SqlAlchemyInventoryRepository(db)
    inv_repo.ensure_user_rows(str(current_user.id))
    items = inv_repo.get_by_user(str(current_user.id))
    return InventoryResponse(items={str(k): v for k, v in items.items()})


@router.post("/me/inventory/buy")
def buy_item(
    data: BuyItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.item_type not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="item_type must be 1, 2 or 3")
    price = ITEM_TYPE_PRICES.get(data.item_type, 0)
    if current_user.balance_points < price:
        raise HTTPException(status_code=400, detail="Недостаточно очков")
    from application.services import UserService
    from infrastructure.repositories import SqlAlchemyUserRepository
    user_repo = SqlAlchemyUserRepository(db)
    user_service = UserService(user_repo)
    from uuid import UUID
    updated = user_service.add_points(UUID(str(current_user.id)), -price)
    if not updated:
        raise HTTPException(status_code=500, detail="Ошибка списания очков")
    inv_repo = SqlAlchemyInventoryRepository(db)
    inv_repo.ensure_user_rows(str(current_user.id))
    inv_repo.add_quantity(str(current_user.id), data.item_type, 1)
    items = inv_repo.get_by_user(str(current_user.id))
    return {"balance_points": updated.balance_points, "items": {str(k): v for k, v in items.items()}}


