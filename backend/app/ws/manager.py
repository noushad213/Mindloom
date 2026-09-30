from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, workspace_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[workspace_id].add(websocket)

    def disconnect(self, workspace_id: UUID, websocket: WebSocket) -> None:
        self._connections[workspace_id].discard(websocket)
        if not self._connections[workspace_id]:
            self._connections.pop(workspace_id, None)

    async def broadcast(self, event: dict) -> None:
        workspace_id = UUID(event["workspace_id"])
        for websocket in tuple(self._connections.get(workspace_id, ())):
            try:
                await websocket.send_json(event)
            except Exception:
                self.disconnect(workspace_id, websocket)
