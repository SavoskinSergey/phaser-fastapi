from fastapi import APIRouter, Depends

from api.dependencies import get_current_user
from domain.entities.user import User
from api.game_sessions import join_or_create

router = APIRouter(prefix="/api/game", tags=["game"])


@router.post("/join_or_create")
async def join_or_create_session(current_user: User = Depends(get_current_user)):
    """Найти открытую сессию (до 4 игроков) или создать новую. Возвращает session_id и данные лобби."""
    result = await join_or_create(str(current_user.id), current_user.username)
    return result
