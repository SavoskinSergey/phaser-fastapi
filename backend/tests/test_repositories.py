"""Unit-тесты репозиториев: инвентарь, задания на карте, лог выполненных заданий."""
import pytest
from sqlalchemy.orm import Session

from infrastructure.database.models import UserModel, UserInventoryModel, MapTaskModel, TaskCompletionModel
from infrastructure.repositories import (
    SqlAlchemyInventoryRepository,
    SqlAlchemyMapTaskRepository,
    SqlAlchemyTaskCompletionRepository,
)


@pytest.fixture
def user_id(db_session: Session) -> str:
    u = UserModel(
        username="repouser",
        email="repouser@example.com",
        hashed_password="hash",
        balance_points=0,
        balance_mana=0,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return str(u.id)


class TestInventoryRepository:
    def test_ensure_user_rows_creates_three_types(self, db_session: Session, user_id: str):
        repo = SqlAlchemyInventoryRepository(db_session)
        repo.ensure_user_rows(user_id)
        items = repo.get_by_user(user_id)
        assert 1 in items
        assert 2 in items
        assert 3 in items
        assert items[1] >= 0
        assert items[2] >= 0
        assert items[3] >= 0

    def test_add_quantity_increases_count(self, db_session: Session, user_id: str):
        repo = SqlAlchemyInventoryRepository(db_session)
        repo.ensure_user_rows(user_id)
        qty = repo.add_quantity(user_id, 1, 3)
        assert qty == 3
        assert repo.get_by_user(user_id)[1] == 3
        qty2 = repo.add_quantity(user_id, 1, 2)
        assert qty2 == 5

    def test_has_at_least(self, db_session: Session, user_id: str):
        repo = SqlAlchemyInventoryRepository(db_session)
        repo.ensure_user_rows(user_id)
        repo.add_quantity(user_id, 1, 2)
        repo.add_quantity(user_id, 2, 1)
        assert repo.has_at_least(user_id, {1: 2, 2: 1, 3: 0}) is True
        assert repo.has_at_least(user_id, {1: 3, 2: 0, 3: 0}) is False
        assert repo.has_at_least(user_id, {1: 1, 2: 1, 3: 1}) is False

    def test_deduct(self, db_session: Session, user_id: str):
        repo = SqlAlchemyInventoryRepository(db_session)
        repo.ensure_user_rows(user_id)
        repo.add_quantity(user_id, 1, 5)
        repo.add_quantity(user_id, 2, 3)
        repo.deduct(user_id, {1: 2, 2: 1, 3: 0})
        items = repo.get_by_user(user_id)
        assert items[1] == 3
        assert items[2] == 2
        assert items[3] == 0


class TestMapTaskRepository:
    def test_create_and_get_all(self, db_session: Session):
        repo = SqlAlchemyMapTaskRepository(db_session)
        task = repo.create(3, 4)
        assert "id" in task
        assert task["tile_x"] == 3
        assert task["tile_y"] == 4
        assert task["required_type_1"] + task["required_type_2"] + task["required_type_3"] == 3
        all_tasks = repo.get_all()
        assert len(all_tasks) >= 1
        assert any(t["tile_x"] == 3 and t["tile_y"] == 4 for t in all_tasks)

    def test_get_by_tile(self, db_session: Session):
        repo = SqlAlchemyMapTaskRepository(db_session)
        repo.create(5, 6)
        t = repo.get_by_tile(5, 6)
        assert t is not None
        assert t["tile_x"] == 5
        assert t["tile_y"] == 6
        assert repo.get_by_tile(99, 99) is None

    def test_delete_by_tile_returns_task(self, db_session: Session):
        repo = SqlAlchemyMapTaskRepository(db_session)
        repo.create(7, 8)
        deleted = repo.delete_by_tile(7, 8)
        assert deleted is not None
        assert deleted["tile_x"] == 7
        assert repo.get_by_tile(7, 8) is None


class TestTaskCompletionRepository:
    def test_log_and_get_recent(self, db_session: Session, user_id: str):
        repo = SqlAlchemyTaskCompletionRepository(db_session)
        repo.log(user_id, 25, 1, 2)
        repo.log(user_id, 40, 2, 3)
        recent = repo.get_recent_by_user(user_id, limit=10)
        assert len(recent) == 2
        assert recent[0]["reward_points"] == 40
        assert recent[0]["reward_item_1"] == 2
        assert recent[1]["reward_points"] == 25
        assert "completed_at" in recent[0]
