@echo off
REM Скрипт для запуска тестов фронтенда (Windows)

echo Установка зависимостей...
call npm install

echo.
echo Запуск тестов фронтенда...
call npm test -- --run
