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
    logger.info("starting up")

    # Load seed knowledge graph so select_next_concept has concepts to offer.
    # New topics are still generated on-the-fly; this just provides the base set.
    try:
        knowledge_graph.load()
        logger.info("knowledge graph loaded: %d concepts", len(knowledge_graph.concepts))
    except Exception as e:
        logger.warning("knowledge graph load failed: %s — concepts will be generated on demand", e)

    try:
        career_service.load()
        logger.info("career roles loaded: %d roles", len(career_service.roles))
    except Exception as e:
        logger.warning("career roles load failed: %s — career features will be limited", e)

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

import os
_cors_origins = list(settings.cors_origins)
_frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")
if _frontend_url and _frontend_url not in _cors_origins:
    _cors_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from backend.middleware import RateLimitMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
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
    from backend.agents.orchestrator import orchestrator
    from backend.services.cache import cache

    redis_ok = False
    try:
        if cache._redis:
            await cache._redis.ping()
            redis_ok = True
    except Exception:
        pass

    return {
        "status": "ok",
        "version": app.version,
        "services": {
            "redis": "connected" if redis_ok else "unavailable",
            "database": "postgresql" if settings.database_url.startswith("postgresql") else "sqlite",
        },
        "active_sessions": len(orchestrator.active_sessions),
        "concepts_loaded": len(knowledge_graph.concepts),
        "roles_loaded": len(career_service.roles),
        "llm": llm_client.get_stats(),
    }
