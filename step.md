Общая идея
Минимальная функциональность:
На сцене Phaser есть, например, квадратик‑персонаж.
Каждый игрок управляет своим квадратиком с клавиатуры.
Движения уходят на сервер (FastAPI + WebSocket).
Сервер рассылает всем актуальные позиции игроков.
Ниже — максимально по шагам, от нуля до минимально работающего прототипа.
1. Подготовка окружения
Установить зависимости глобально
Node.js (LTS)
Python 3.10+
Создать папку проекта, например C:\Users\Sergey\phaser-fastapi-mp
2. Структура проекта
Примерно так:
phaser-fastapi-mp/  backend/    main.py    requirements.txt  frontend/    package.json    vite.config.ts (или webpack.config.js)    src/      main.ts      GameScene.ts      types.d.ts
3. Backend: FastAPI + WebSocket
3.1. Установка и базовый сервер
В папке backend:
python -m venv venvvenv\Scripts\activatepip install fastapi uvicorn[standard]pip freeze > requirements.txt
main.py (минимальный HTTP + healthcheck):
from fastapi import FastAPIapp = FastAPI()@app.get("/health")async def health():    return {"status": "ok"}
Запуск:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
3.2. Добавить WebSocket для игры
pip install "fastapi[all]"
main.py (дополнить):
from fastapi import FastAPI, WebSocket, WebSocketDisconnectfrom typing import Dictapp = FastAPI()class ConnectionManager:    def __init__(self):        self.active_connections: Dict[str, WebSocket] = {}    async def connect(self, player_id: str, websocket: WebSocket):        await websocket.accept()        self.active_connections[player_id] = websocket    def disconnect(self, player_id: str):        self.active_connections.pop(player_id, None)    async def broadcast(self, message: dict):        for ws in list(self.active_connections.values()):            await ws.send_json(message)manager = ConnectionManager()# простейшее хранение состояний игроковplayers_state: Dict[str, dict] = {}@app.websocket("/ws/game")async def websocket_endpoint(websocket: WebSocket):    # для простоты берем player_id как query-параметр: /ws/game?player_id=abc    player_id = websocket.query_params.get("player_id", "unknown")    await manager.connect(player_id, websocket)    # добавить игрока в состояние    players_state[player_id] = {"x": 100, "y": 100}    # рассылаем новое состояние всем    await manager.broadcast({"type": "state", "players": players_state})    try:        while True:            data = await websocket.receive_json()            # ожидаем, например: {"type": "move", "dx": 5, "dy": 0}            if data.get("type") == "move":                p = players_state.get(player_id, {"x": 100, "y": 100})                p["x"] += data.get("dx", 0)                p["y"] += data.get("dy", 0)                players_state[player_id] = p                # рассылаем всем новое состояние                await manager.broadcast({"type": "state", "players": players_state})    except WebSocketDisconnect:        manager.disconnect(player_id)        players_state.pop(player_id, None)        await manager.broadcast({"type": "state", "players": players_state})
Это даст простой сервер: клиенты подключаются, отправляют “move”, получают общее состояние всех игроков.
4. Frontend: Phaser + сборщик (Vite)
4.1. Инициализация проекта
В папке frontend:
npm init vite@latest frontend -- --template vanilla-tscd frontendnpm installnpm install phaser
(Если Vite не нужен, можно Webpack или простую HTML+script-сборку, но Vite быстрый и простой.)
4.2. Конфиг Phaser-сцены
src/GameScene.ts:
import Phaser from 'phaser';interface PlayersState {  [playerId: string]: { x: number; y: number };}export class GameScene extends Phaser.Scene {  private ws?: WebSocket;  private playerId: string = Math.random().toString(36).slice(2);  private mySprite?: Phaser.GameObjects.Rectangle;  private otherPlayers: Map<string, Phaser.GameObjects.Rectangle> = new Map();  private keys!: { up: Phaser.Input.Keyboard.Key; down: Phaser.Input.Keyboard.Key; left: Phaser.Input.Keyboard.Key; right: Phaser.Input.Keyboard.Key };  constructor() {    super('GameScene');  }  preload() {}  create() {    // свой квадрат (начальные координаты совпадают с сервером)    this.mySprite = this.add.rectangle(100, 100, 20, 20, 0x00ff00);    this.keys = {      up: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.W),      down: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.S),      left: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.A),      right: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.D)    };    const url = `ws://localhost:8000/ws/game?player_id=${this.playerId}`;    this.ws = new WebSocket(url);    this.ws.onmessage = (event) => {      const msg = JSON.parse(event.data) as { type: string; players: PlayersState };      if (msg.type === 'state') {        this.syncPlayers(msg.players);      }    };  }  update() {    if (!this.ws || this.ws.readyState !== WebSocket.OPEN || !this.mySprite) return;    const speed = 3;    let dx = 0;    let dy = 0;    if (this.keys.left.isDown) dx -= speed;    if (this.keys.right.isDown) dx += speed;    if (this.keys.up.isDown) dy -= speed;    if (this.keys.down.isDown) dy += speed;    if (dx !== 0 || dy !== 0) {      this.ws.send(JSON.stringify({ type: 'move', dx, dy }));    }  }  private syncPlayers(players: PlayersState) {    // обновляем свой спрайт    const me = players[this.playerId];    if (me && this.mySprite) {      this.mySprite.setPosition(me.x, me.y);    }    // обновляем/создаем чужие спрайты    Object.entries(players).forEach(([id, pos]) => {      if (id === this.playerId) return;      let sprite = this.otherPlayers.get(id);      if (!sprite) {        sprite = this.add.rectangle(pos.x, pos.y, 20, 20, 0xff0000);        this.otherPlayers.set(id, sprite);      } else {        sprite.setPosition(pos.x, pos.y);      }    });    // удаляем ушедших игроков    for (const [id, sprite] of this.otherPlayers.entries()) {      if (!players[id]) {        sprite.destroy();        this.otherPlayers.delete(id);      }    }  }}
src/main.ts:
import Phaser from 'phaser';import { GameScene } from './GameScene';const config: Phaser.Types.Core.GameConfig = {  type: Phaser.AUTO,  width: 800,  height: 600,  backgroundColor: '#222222',  parent: 'app',  scene: [GameScene]};new Phaser.Game(config);
index.html (Vite уже создает; убедись, что есть контейнер с id app).
5. Запуск фронтенда
В папке frontend:
npm run dev -- --host
Зайти в браузер на http://localhost:5173 (порт может отличаться, смотри лог Vite).
Убедиться, что FastAPI запущен на http://localhost:8000.
Открой в двух вкладках одну и ту же страницу — должны появиться два квадратика, которые двигаются независимо.
6. Минимальные доработки и улучшения
Стабильность:
Обработать ws.onclose, показывать "переподключиться?".
Авторизация/ID игрока:
Заменить случайный playerId на реальный логин/токен.
Тик-сервер:
Сейчас сервер просто применяет пришедшее движение и сразу рассылает состояние.
Для чуть более "правильной" логики можно ввести игровой тик (например, каждые 50мс обновлять и рассылать состояние, а от клиентов принимать только инпут).
Кратко по шагам
Создать проект, разделив на backend (FastAPI) и frontend (Phaser + Vite).
В backend поднять FastAPI и добавить WebSocket /ws/game, который хранит players_state и рассылает его всем.
В frontend создать сцену Phaser, в create подключаться WebSocket‑ом, а в update отправлять события движения.
На приход состояния от сервера рисовать/обновлять спрайты всех игроков по их координатам.
Проверить в нескольких вкладках браузера, что движение синхронизируется.
Если хочешь, дальше можем углубиться в любую часть: детально описать структуру FastAPI‑проекта, настроить типизацию в Phaser, или добавить, например, комнаты/лобби.
Авторизация/ID игрока:

Заменить случайный playerId на реальный логин/токен.

Проверяю структуру проекта перед добавлением авторизации с токенами (JWT) вместо случайного playerId.
Создаю структуру проекта с авторизацией: регистрация/логин, JWT-токены и их проверка в WebSocket.
Создать структуру проекта (backend и frontend папки)
Настроить backend: добавить JWT авторизацию, эндпоинты регистрации/логина
Модифицировать WebSocket для проверки токена и использования user_id из токена
Создать frontend: форму логина/регистрации перед игрой
Обновить GameScene для использования токена при подключении к WebSocket
Создать requirements.txt и package.json с зависимостями
cd C:\Users\Sergey && mkdir phaser-fastapi-mp 2>$null; cd phaser-fastapi-mp && mkdir backend,frontend 2>$null
Rejected: Review cancelled or failed
Создаю структуру проекта с авторизацией:
main.py(new)
+239
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, statusfrom fastapi.security import HTTPBearer, HTTPAuthorizationCredentialsfrom fastapi.middleware.cors import CORSMiddlewarefrom pydantic import BaseModel, EmailStrfrom typing import Dict, Optional
requirements.txt(new)
+7
fastapi==0.104.1uvicorn[standard]==0.24.0python-jose[cryptography]==3.3.0passlib[bcrypt]==1.7.4python-multipart==0.0.6
package.json(new)
+19
{  "name": "phaser-multiplayer-frontend",  "version": "1.0.0",  "type": "module",  "scripts": {
vite.config.ts(new)
+9
import { defineConfig } from 'vite'export default defineConfig({  server: {    port: 5173,
tsconfig.json(new)
+20
{  "compilerOptions": {    "target": "ES2020",    "useDefineForClassFields": true,    "module": "ESNext",
index.html(new)
+146
<!DOCTYPE html><html lang="ru">  <head>    <meta charset="UTF-8" />    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
main.ts(new)
+139
import Phaser from 'phaser';import { GameScene } from './GameScene';import { AuthService } from './AuthService';const API_URL = 'http://localhost:8000';
AuthService.ts(new)
+59
const API_URL = 'http://localhost:8000';export interface TokenData {  access_token: string;  token_type: string;
GameScene.ts(new)
+164
import Phaser from 'phaser';interface PlayerState {  x: number;  y: number;
README.md(new)
+99
# Phaser Multiplayer Game с авторизациейМногопользовательская игра на Phaser с бэкендом на FastAPI и JWT авторизацией.## Структура проекта
Добавлена авторизация с JWT-токенами. Реализовано:
Что сделано:
Backend (FastAPI):
JWT-авторизация с использованием python-jose
Хеширование паролей через bcrypt
Эндпоинты:
POST /api/register — регистрация
POST /api/login — вход
GET /api/me — информация о текущем пользователе
WebSocket /ws/game проверяет токен из query-параметра и использует user_id из токена
Frontend (Phaser):
Форма логина/регистрации перед игрой
AuthService для работы с API
GameScene использует токен при подключении к WebSocket
Отображение имен игроков над спрайтами
Как запустить:
Backend:
cd phaser-fastapi-mp/backendpython -m venv venvvenv\Scripts\activatepip install -r requirements.txtuvicorn main:app --reload --host 0.0.0.0 --port 8000
Frontend:
cd phaser-fastapi-mp/frontendnpm installnpm run dev
Откройте http://localhost:5173 в браузере:
Зарегистрируйте аккаунт или войдите
После авторизации откроется игровая сцена
Используйте WASD для движения
Особенности:
Токены хранятся в памяти браузера (через глобальную переменную)
Пароли хешируются на сервере
WebSocket требует валидный токен для подключения
Каждый игрок идентифицируется по user_id из токена
Готово к тестированию. Откройте несколько вкладок с разными аккаунтами, чтобы проверить мультиплеер.
на чцене игры добавить кнопку выйти и при выходе сохранять позицию игрока

Ок — сделаю кнопку «Выйти» прямо в сцене Phaser и добавлю сохранение позиции: при выходе клиент отправит серверу координаты, сервер запомнит их и при следующем подключении поставит игрока на сохранённое место. Сейчас прочитаю текущие main.py и GameScene.ts и внесу правки.
Нашёл, где лучше сделать: на бэкенде добавим простое in-memory хранилище saved_positions и будем писать туда координаты при exit/дисконнекте; на фронте добавим интерактивную кнопку «Выйти» в GameScene и коллбек, который возвращает на экран логина и уничтожает Phaser-инстанс.
main.py
+25
-3
players_state: Dict[str, dict] = {}    
players_state: Dict[str, dict] = {}# Последняя сохранённая позиция игрока (in-memory)saved_positions: Dict[str, dict] = {}    
main.ts
+17
  // коллбек, который вызовет сцена при выходе  (window as any).exitToLogin = () => {    try {      if (game) {        game.destroy(true);
GameScene.ts
+55
  private myLabel?: Phaser.GameObjects.Text;  private otherPlayers: Map<string, { sprite: Phaser.GameObjects.Rectangle; label: Phaser.GameObjects.Text }> = new Map();  private readonly MOVE_COOLDOWN_TIME = 50; // мс между отправками движения
  private myLabel?: Phaser.GameObjects.Text;  private exitButton?: Phaser.GameObjects.Text;  private otherPlayers: Map<string, { sprite: Phaser.GameObjects.Rectangle; label: Phaser.GameObjects.Text }> = new Map();  private readonly MOVE_COOLDOWN_TIME = 50; // мс между отправками движения  private hasExited: boolean = false;
Почти готово: кнопка «Выйти» уже в сцене и сервер сохраняет координаты при exit и при обрыве соединения. Сейчас быстро прогоню линтер/диагностику по изменённым файлам, чтобы не осталось TypeScript/py ошибок.
Похоже диагностика не увидела файлы по относительному пути — перепроверю абсолютными путями и если надо, поправлю мелкие ошибки в коде.
Что добавлено
Кнопка “Выйти” в сцене Phaser: frontend/src/GameScene.ts
По клику отправляет на сервер сообщение {"type":"exit","x":...,"y":...}
Закрывает WebSocket
Возвращает на экран логина (через window.exitToLogin())
Сохранение позиции игрока на бэкенде: backend/main.py
Добавлено in-memory хранилище saved_positions
Позиция сохраняется:
при получении сообщения type="exit"
при WebSocketDisconnect
При следующем подключении игрок появляется на сохранённой позиции
Как проверить
Запусти backend и frontend как раньше.
Зайди, подвигайся, нажми “Выйти”.
Снова зайди тем же пользователем — должен появиться на последней позиции.
Если хочешь, следующим шагом сделаю сохранение в БД (SQLite/Postgres), чтобы позиции не терялись при перезапуске сервера.