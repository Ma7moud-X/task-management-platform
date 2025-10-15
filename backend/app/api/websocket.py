from fastapi import APIRouter, WebSocket, Query, Cookie
from typing import Optional
from app.core.websocket import manager
from app.db.redis import redis_client
import json

router = APIRouter()

@router.websocket("/ws/{org_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    org_id: str, 
    token: Optional[str] = Query(None),
    access_token: Optional[str] = Cookie(None)
):
    # Try to get token from query param first, then from cookie
    auth_token = token or access_token
    if not auth_token:
        await websocket.close(code=1008, reason="No token provided")
        return
    
    # Connect and validate
    connected = await manager.connect(websocket, org_id, auth_token)
    if not connected:
        return

    # Subscribe to Redis channel for this org
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"org:{org_id}:tasks")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await websocket.send_text(json.dumps(data))
                except Exception:
                    pass  # ignore malformed
    except Exception:
        pass
    finally:
        await pubsub.unsubscribe(f"org:{org_id}:tasks")
        manager.disconnect(websocket, org_id)