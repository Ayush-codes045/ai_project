import json
import asyncio
from fastapi import WebSocket
from models.schemas import AgentEvent


class ConnectionManager:
    """Manages WebSocket connections for real-time agent updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        async with self._lock:
            if task_id not in self.active_connections:
                self.active_connections[task_id] = []
            self.active_connections[task_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, task_id: str):
        async with self._lock:
            if task_id in self.active_connections:
                if websocket in self.active_connections[task_id]:
                    self.active_connections[task_id].remove(websocket)
                if not self.active_connections[task_id]:
                    del self.active_connections[task_id]

    async def send_event(self, task_id: str, event: AgentEvent):
        """Broadcast an event to all connected clients for a task."""
        if task_id not in self.active_connections:
            return

        message = json.dumps(event.model_dump(), default=str)
        disconnected = []

        for connection in self.active_connections.get(task_id, []):
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn, task_id)


manager = ConnectionManager()