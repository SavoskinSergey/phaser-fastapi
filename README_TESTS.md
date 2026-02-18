# Тесты проекта

Этот документ описывает как запускать тесты для бэкенда и фронтенда.

## Бэкенд тесты

### Установка зависимостей

```bash
cd backend
pip install -r test_requirements.txt
```

### Запуск тестов

```bash
# Все тесты
pytest

# С подробным выводом
pytest -v

# Конкретный файл тестов
pytest tests/test_auth.py

# Конкретный тест
pytest tests/test_auth.py::TestRegister::test_register_success

# С покрытием кода (требует pytest-cov)
pytest --cov=main --cov-report=html
```

### Структура тестов бэкенда

- `tests/test_auth.py` - Тесты авторизации (регистрация, вход, JWT токены, пароли)
- `tests/test_websocket.py` - Тесты WebSocket соединений и игровой логики
- `tests/test_connection_manager.py` - Тесты менеджера соединений
- `conftest.py` - Общие фикстуры для тестов

### Что тестируется

1. **Авторизация:**
   - Регистрация новых пользователей
   - Вход существующих пользователей
   - Валидация токенов JWT
   - Хеширование и проверка паролей
   - Обработка ошибок (дубликаты, неверные данные)

2. **WebSocket:**
   - Подключение с валидным токеном
   - Отклонение подключений без токена
   - Движение игроков
   - Сохранение и восстановление позиций
   - Множественные игроки

3. **ConnectionManager:**
   - Подключение и отключение клиентов
   - Рассылка сообщений всем клиентам
   - Обработка ошибок при отправке

## Фронтенд тесты

### Установка зависимостей

```bash
cd frontend
npm install
```

### Запуск тестов

```bash
# Все тесты в watch режиме
npm test

# Один раз
npm test -- --run

# С UI интерфейсом
npm run test:ui

# С покрытием кода
npm run test:coverage
```

### Структура тестов фронтенда

- `src/test/AuthService.test.ts` - Тесты сервиса авторизации
- `src/test/GameScene.test.ts` - Тесты игровой сцены (с моками Phaser)
- `src/test/main.test.ts` - Интеграционные тесты основного файла
- `src/test/setup.ts` - Настройка тестового окружения

### Что тестируется

1. **AuthService:**
   - Успешный вход и регистрация
   - Обработка ошибок сети
   - Обработка невалидных ответов
   - Получение данных текущего пользователя

2. **GameScene:**
   - Инициализация сцены
   - Создание игровых объектов
   - Обработка WebSocket сообщений
   - Движение игрока
   - Выход из игры

3. **main.ts:**
   - Переключение между формами
   - Валидация форм
   - Обработка клавиатуры

## Непрерывная интеграция

Для CI/CD можно использовать следующие команды:

```bash
# Бэкенд
cd backend && pytest --junitxml=test-results.xml

# Фронтенд
cd frontend && npm test -- --run --reporter=junit --outputFile=test-results.xml
```

## Покрытие кода

### Бэкенд

```bash
pip install pytest-cov
pytest --cov=main --cov-report=term-missing --cov-report=html
```

Отчет будет в `htmlcov/index.html`

### Фронтенд

```bash
npm run test:coverage
```

Отчет будет в `coverage/` директории
