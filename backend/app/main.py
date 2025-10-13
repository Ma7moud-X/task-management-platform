from fastapi import FastAPI, Depends
from app.db.session import get_db
from sqlalchemy import text
from app.api.auth import router as auth_router
from app.api.task import router as tasks_router
from app.api.websocket import router as websocket_router

app = FastAPI(title="Task Manager API")

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(websocket_router)

@app.get("/health")
async def health_check(db=Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}

