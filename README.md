# Phaser Multiplayer Game с авторизацией

Многопользовательская игра на Phaser с бэкендом на FastAPI и JWT авторизацией.

## Структура проекта

```
phaser-fastapi-mp/
├── backend/          # FastAPI сервер
│   ├── main.py      # Основной файл с API и WebSocket
│   └── requirements.txt
└── frontend/        # Phaser клиент
    ├── src/
    │   ├── main.ts          # Точка входа
    │   ├── AuthService.ts   # Сервис авторизации
    │   └── GameScene.ts     # Игровая сцена
    ├── index.html
    ├── package.json
    └── vite.config.ts
```

## Установка и запуск

### Backend

1. Перейдите в папку `backend`:
```bash
cd backend
```

2. Создайте виртуальное окружение (Windows):
```bash
python -m venv venv
venv\Scripts\activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Запустите сервер:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Сервер будет доступен на `http://localhost:8000`

### Frontend

1. Перейдите в папку `frontend`:
```bash
cd frontend
```

2. Установите зависимости:
```bash
npm install
```

3. Запустите dev сервер:
```bash
npm run dev
```

Приложение будет доступно на `http://localhost:5173`

## Использование

1. Откройте браузер и перейдите на `http://localhost:5173`
2. Зарегистрируйте новый аккаунт или войдите существующим
3. После авторизации откроется игровая сцена
4. Используйте WASD для движения вашего персонажа (зеленый квадрат)
5. Откройте игру в нескольких вкладках/браузерах для тестирования мультиплеера

## API эндпоинты

- `POST /api/register` - Регистрация нового пользователя
- `POST /api/login` - Вход пользователя
- `GET /api/me` - Получение информации о текущем пользователе (требует токен)
- `WebSocket /ws/game?token=...` - Подключение к игровому серверу

## Особенности

- JWT токены для авторизации
- WebSocket для реального времени
- Простая система регистрации/логина
- Хеширование паролей с помощью bcrypt
- CORS настроен для разработки

## Миграции БД (backend)

В папке `backend` настроен Alembic. Подробнее: [backend/README_MIGRATIONS.md](backend/README_MIGRATIONS.md).

Кратко:
```bash
cd backend
pip install alembic
# Задайте DATABASE_URL в .env
alembic upgrade head
```

## Безопасность

⚠️ **Важно для продакшена:**
- Используйте переменные окружения для `SECRET_KEY`
- Добавьте базу данных вместо словаря `users_db`
- Добавьте rate limiting
- Используйте HTTPS и WSS для WebSocket
- Добавьте валидацию входных данных
