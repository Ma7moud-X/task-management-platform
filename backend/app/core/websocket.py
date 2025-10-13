from fastapi import WebSocket, status
from typing import Dict, List
import json
from app.core.security import verify_access_token
from app.db.redis import redis_client

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, org_id: str, token: str):
        try:
            payload = verify_access_token(token)
            if payload.get("org_id") != org_id:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return False
        except ValueError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

        await websocket.accept()
        if org_id not in self.active_connections:
            self.active_connections[org_id] = []
        self.active_connections[org_id].append(websocket)
        return True

    def disconnect(self, websocket: WebSocket, org_id: str):
        if org_id in self.active_connections:
            self.active_connections[org_id].remove(websocket)

    async def broadcast_to_org(self, org_id: str, message: dict):
        if org_id in self.active_connections:
            disconnected = []
            for ws in self.active_connections[org_id]:
                try:
                    await ws.send_text(json.dumps(message))
                except Exception:
                    disconnected.append(ws)
            # Clean up dead connections
            for ws in disconnected:
                self.active_connections[org_id].remove(ws)

manager = ConnectionManager()