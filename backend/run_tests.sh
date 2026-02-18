#!/bin/bash
# Скрипт для запуска тестов бэкенда

echo "Установка зависимостей для тестов..."
pip install -q -r test_requirements.txt

echo ""
echo "Запуск тестов бэкенда..."
pytest -v
