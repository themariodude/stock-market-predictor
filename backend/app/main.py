"""
FastAPI entry point.

Only /health lives here — it exists so the container has a startup path
and CI has something to assert against.

Register additional routers at the bottom of this file.
"""

import logging
import os

from fastapi import FastAPI
from sqlalchemy import create_engine, text

from app.api.stocks import router as stocks_router

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(title="Stock Market Predictor API", version="0.1.1")

DATABASE_URL = os.getenv("DATABASE_URL", "")
_engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None


@app.get("/health")
def health() -> dict:
    """Liveness probe. Used by the Docker healthcheck and by CI."""
    db_status = "unconfigured"
    if _engine is not None:
        try:
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception as exc:
            log.warning("database health check failed: %s", exc)
            db_status = "error"
    return {"status": "ok", "database": db_status}


app.include_router(stocks_router)