from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes import auth_router
from api.websocket_handlers import websocket_game_endpoint
from infrastructure.database.connection import engine, Base
from infrastructure.database import models  # noqa: F401 - register models with Base
from api.websocket_handlers import load_or_create_initial_bonuses, load_or_create_initial_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    load_or_create_initial_bonuses()
    load_or_create_initial_tasks()
    yield
    # Shutdown: nothing for now


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/game")
async def ws_game(websocket: WebSocket):
    await websocket_game_endpoint(websocket)
