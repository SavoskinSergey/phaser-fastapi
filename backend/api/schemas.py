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


class ProfileResponse(BaseModel):
    user_id: str
    username: str
    balance_points: int
    balance_mana: int
    location_x: float
    location_y: float
    last_login: str | None
    recent_bonus_collections: list[BonusCollectionItem]
