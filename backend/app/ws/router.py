import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Workspace
from app.services.auth import valid_share
from app.services.events import envelope, latest_seq


router = APIRouter()


@router.websocket("/ws/workspaces/{workspace_id}")
async def workspace_socket(websocket: WebSocket, workspace_id: UUID, share: str | None = None, db: Session = Depends(get_db)) -> None:
    if db.get(Workspace, workspace_id) is None:
        await websocket.close(code=4404)
        return
    if share is not None and (link := valid_share(db, share)) is None:
        await websocket.close(code=4403)
        return
    if share is not None and link.workspace_id != workspace_id:
        await websocket.close(code=4403)
        return
    db.rollback()  # Do not hold a read transaction for the lifetime of the socket.
    manager = websocket.app.state.ws_manager
    await manager.connect(workspace_id, websocket)
    try:
        seq = latest_seq(db, workspace_id)
        db.rollback()
        await websocket.send_json(envelope("hello", workspace_id, seq, {"seq": seq}))
        while True:
            try:
                await asyncio.wait_for(websocket.receive_json(), timeout=25)
            except asyncio.TimeoutError:
                current_seq = latest_seq(db, workspace_id)
                db.rollback()
                await websocket.send_json(envelope("ping", workspace_id, current_seq, {}))
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(workspace_id, websocket)
