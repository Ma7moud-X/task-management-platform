from fastapi import FastAPI, Depends
from app.db.session import get_db
from sqlalchemy import text
from app.api.auth import router as auth_router

# Import models so SQLAlchemy relationships are registered
from app.models import user, organization

app = FastAPI(title="Task Manager API")

app.include_router(auth_router)


@app.get("/")
async def health_check(db=Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}

