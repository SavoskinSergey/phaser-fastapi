# Миграции БД (Alembic)

## Установка

```bash
pip install alembic
```

Либо добавьте в `requirements.txt`:
```
alembic>=1.13.0
```

## Настройка

URL базы задаётся в переменной окружения `DATABASE_URL` или в файле `.env`:

```
DATABASE_URL=postgresql://user:password@localhost:5432/one_day
```

## Команды (выполнять из папки `backend`)

| Команда | Описание |
|--------|----------|
| `alembic upgrade head` | Применить все миграции |
| `alembic upgrade +1` | Применить следующую миграцию |
| `alembic downgrade -1` | Откатить одну миграцию |
| `alembic downgrade base` | Откатить все миграции |
| `alembic current` | Показать текущую ревизию |
| `alembic history` | История миграций |
| `alembic revision --autogenerate -m "описание"` | Создать миграцию по изменениям в моделях |

## Первый запуск

1. Создайте БД в PostgreSQL.
2. Укажите `DATABASE_URL` в `.env`.
3. Выполните:
   ```bash
   cd backend
   alembic upgrade head
   ```

После этого таблицы `users` и `sessions` будут созданы.

## Создание новой миграции

После изменения моделей в `infrastructure/database/models.py`:

```bash
alembic revision --autogenerate -m "add_new_field"
alembic upgrade head
```
