from fastapi import APIRouter, WebSocket, Query
from app.core.websocket import manager
from app.db.redis import redis_client
import asyncio
import json

router = APIRouter()

@router.websocket("/ws/{org_id}")
async def websocket_endpoint(websocket: WebSocket, org_id: str, token: str = Query(...)):
    # Connect and validate
    connected = await manager.connect(websocket, org_id, token)
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