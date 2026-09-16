"""
FastAPI entry point.

Platform note: created so the container has a startup path and CI has
something to assert against. Only /health lives here.

Member 3 owns the stock endpoints — register routers at the bottom.
Response shapes belong in docs/api-contract.md.
"""
import logging
import os

from fastapi import FastAPI
from sqlalchemy import create_engine, text

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


# Member 3: register routers here, e.g.
# from app.api.stocks import router as stocks_router
# app.include_router(stocks_router)
