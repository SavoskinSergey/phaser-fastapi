import pytest
from unittest.mock import AsyncMock, MagicMock
from api.websocket_handlers import ConnectionManager


class TestConnectionManager:
    """Тесты для ConnectionManager"""
    
    def test_init(self):
        """Проверка инициализации менеджера"""
        manager = ConnectionManager()
        assert manager.active_connections == {}
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Проверка подключения"""
        manager = ConnectionManager()
        websocket = AsyncMock()
        user_id = "user123"
        
        await manager.connect(user_id, websocket)
        
        assert user_id in manager.active_connections
        assert manager.active_connections[user_id] == websocket
        websocket.accept.assert_called_once()
    
    def test_disconnect(self):
        """Проверка отключения"""
        manager = ConnectionManager()
        websocket = MagicMock()
        user_id = "user123"
        
        manager.active_connections[user_id] = websocket
        manager.disconnect(user_id)
        
        assert user_id not in manager.active_connections
    
    def test_disconnect_nonexistent(self):
        """Отключение несуществующего соединения"""
        manager = ConnectionManager()
        # Не должно быть ошибки
        manager.disconnect("nonexistent")
        assert len(manager.active_connections) == 0
    
    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Проверка рассылки сообщений"""
        manager = ConnectionManager()
        
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        manager.active_connections["user1"] = ws1
        manager.active_connections["user2"] = ws2
        
        message = {"type": "test", "data": "hello"}
        await manager.broadcast(message)
        
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_broadcast_with_error(self):
        """Проверка рассылки при ошибке отправки"""
        manager = ConnectionManager()
        
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json.side_effect = Exception("Connection error")
        
        manager.active_connections["user1"] = ws1
        manager.active_connections["user2"] = ws2
        
        message = {"type": "test"}
        # Не должно быть исключения
        await manager.broadcast(message)
        
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_empty(self):
        """Рассылка при отсутствии соединений"""
        manager = ConnectionManager()
        
        message = {"type": "test"}
        # Не должно быть ошибки
        await manager.broadcast(message)
