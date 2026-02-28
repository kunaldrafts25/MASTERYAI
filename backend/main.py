import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.config import settings
from backend.logging_config import setup_logging
from backend.services.knowledge_graph import knowledge_graph
from backend.services.career_service import career_service
from backend.routes import session, learner, career, graph, topics, analytics
from backend.auth.routes import router as auth_router

setup_logging(getattr(settings, "log_level", "INFO"))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting up — dynamic mode (no static data pre-loaded)")
    # Concepts are generated on-the-fly when a user picks a topic.
    # Career roles are generated on demand.
    # Tests load static seed data via conftest.py.

    try:
        from backend.db.database import db
        from backend.services.cache import cache
        if settings.database_url.startswith("postgresql"):
            await db.connect()
        await cache.connect()
    except Exception as e:
        logger.warning("optional services failed to start: %s — running in sqlite-only mode", e)

    yield

    logger.info("shutting down")
    try:
        from backend.db.database import db
        from backend.services.cache import cache
        await cache.disconnect()
        await db.disconnect()
    except Exception:
        pass


app = FastAPI(
    title="MasteryAI",
    version="1.0.0",
    description="AI-Powered Learning & Career Intelligence Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from backend.middleware import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)
except Exception:
    pass

app.include_router(auth_router)
app.include_router(session.router)
app.include_router(learner.router)
app.include_router(career.router)
app.include_router(graph.router)
app.include_router(topics.router)
app.include_router(analytics.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.get("/api/v1/health")
async def health():
    from backend.services.llm_client import llm_client
    return {
        "status": "ok",
        "concepts_loaded": len(knowledge_graph.concepts),
        "roles_loaded": len(career_service.roles),
        "llm": llm_client.get_stats(),
    }
