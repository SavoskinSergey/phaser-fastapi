from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str


class UserMe(BaseModel):
    user_id: str
    username: str
    balance_points: int
    balance_mana: int
    location_x: float
    location_y: float
    last_login: str | None


class BonusCollectionItem(BaseModel):
    points: int
    bonus_type: int
    collected_at: str | None


class TaskCompletionItem(BaseModel):
    reward_points: int
    reward_item_1: int
    reward_item_2: int
    completed_at: str | None


class ProfileResponse(BaseModel):
    user_id: str
    username: str
    balance_points: int
    balance_mana: int
    location_x: float
    location_y: float
    last_login: str | None
    recent_bonus_collections: list[BonusCollectionItem]
    recent_task_completions: list[TaskCompletionItem]


class InventoryResponse(BaseModel):
    items: dict[str, int]  # {"1": qty, "2": qty, "3": qty}


class BuyItemRequest(BaseModel):
    item_type: int  # 1 | 2 | 3


class TaskResponse(BaseModel):
    id: str
    required_type_1: int
    required_type_2: int
    required_type_3: int
    reward_points: int
    reward_item_1: int
    reward_item_2: int
