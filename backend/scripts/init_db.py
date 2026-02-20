"""
Создание таблиц в БД (PostgreSQL).
Запуск из корня backend: python -m scripts.init_db
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database.connection import engine, Base
from infrastructure.database import models  # noqa: F401

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Таблицы созданы.")
