from fastapi import FastAPI, Depends
from app.db.session import get_db
from sqlalchemy import text
from app.api.auth import router as auth_router
from app.api.task import router as tasks_router
from app.api.websocket import router as websocket_router
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from contextlib import asynccontextmanager

# Setup structured logging
setup_logging(log_level=settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up", extra={"event": "startup"})
    yield
    # Shutdown
    logger.info("Application shutting down", extra={"event": "shutdown"})


app = FastAPI(title="Task Manager API", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(websocket_router)

@app.get("/health")
async def health_check(db=Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        logger.info("Health check passed", extra={"status": "ok"})
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        raise
