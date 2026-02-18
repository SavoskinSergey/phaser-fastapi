from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Dict, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets

app = FastAPI()

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite и другие dev серверы
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройки JWT
SECRET_KEY = secrets.token_urlsafe(32)  # В продакшене использовать переменную окружения
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Хеширование паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Простое хранилище пользователей (в продакшене использовать БД)
users_db: Dict[str, dict] = {}

# Модели данных
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

# Утилиты для работы с паролями и токенами
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Security
security = HTTPBearer()

# Connection Manager для WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def broadcast(self, message: dict):
        for ws in list(self.active_connections.values()):
            try:
                await ws.send_json(message)
            except:
                pass  # Игнорируем ошибки отправки

manager = ConnectionManager()

# Хранение состояний игроков
players_state: Dict[str, dict] = {}
# Последняя сохранённая позиция игрока (in-memory)
saved_positions: Dict[str, dict] = {}

# API эндпоинты
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/register", response_model=Token)
async def register(user_data: UserRegister):
    # Проверка существования пользователя
    if user_data.username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Создание пользователя
    user_id = secrets.token_urlsafe(16)
    hashed_password = get_password_hash(user_data.password)
    
    users_db[user_data.username] = {
        "user_id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_password
    }
    
    # Создание токена
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id, "username": user_data.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "username": user_data.username
    }

@app.post("/api/login", response_model=Token)
async def login(user_data: UserLogin):
    user = users_db.get(user_data.username)
    
    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Создание токена
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["user_id"], "username": user["username"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user["user_id"],
        "username": user["username"]
    }

@app.get("/api/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = payload.get("sub")
    username = payload.get("username")
    
    return {"user_id": user_id, "username": username}

# WebSocket эндпоинт с авторизацией
@app.websocket("/ws/game")
async def websocket_endpoint(websocket: WebSocket):
    # Получаем токен из query параметров
    token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Декодируем токен
    payload = decode_token(token)
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id = payload.get("sub")
    username = payload.get("username")
    
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    await manager.connect(user_id, websocket)
    
    # Добавляем игрока в состояние (если есть сохранённая позиция — используем её)
    start_pos = saved_positions.get(user_id) or {"x": 100, "y": 100}
    players_state[user_id] = {
        "x": start_pos.get("x", 100),
        "y": start_pos.get("y", 100),
        "username": username
    }
    
    # Рассылаем новое состояние всем
    await manager.broadcast({
        "type": "state",
        "players": players_state
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "move":
                player = players_state.get(user_id)
                if player:
                    player["x"] += data.get("dx", 0)
                    player["y"] += data.get("dy", 0)
                    players_state[user_id] = player
                    # Рассылаем всем новое состояние
                    await manager.broadcast({
                        "type": "state",
                        "players": players_state
                    })
            elif data.get("type") == "exit":
                # Сохраняем позицию при выходе
                player = players_state.get(user_id) or {}
                x = data.get("x", player.get("x", 100))
                y = data.get("y", player.get("y", 100))
                saved_positions[user_id] = {"x": x, "y": y}

                manager.disconnect(user_id)
                players_state.pop(user_id, None)
                await manager.broadcast({
                    "type": "state",
                    "players": players_state
                })
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                return
    except WebSocketDisconnect:
        # Сохраняем позицию при обрыве соединения
        player = players_state.get(user_id)
        if player:
            saved_positions[user_id] = {"x": player.get("x", 100), "y": player.get("y", 100)}
        manager.disconnect(user_id)
        players_state.pop(user_id, None)
        await manager.broadcast({
            "type": "state",
            "players": players_state
        })
