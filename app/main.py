"""Main FastAPI application entry point for Meeting Intelligence & Social Dynamics Analyzer."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.utils.config import settings
from app.utils.logging import logger
from app.database.database import init_db
from app.api import (
    meetings_router,
    action_items_router,
    ideas_router,
    analytics_router,
    global_analytics_router,
    integrations_router,
    attendance_router,
    meeting_plan_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database tables and pre-load demo meeting if needed."""
    logger.info("Initializing %s...", settings.app_name)
    init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down application.")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Analyze how conversations, ideas, decisions, participation, and actions evolve throughout meetings.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(meetings_router)
app.include_router(action_items_router)
app.include_router(ideas_router)
app.include_router(analytics_router)
app.include_router(global_analytics_router)
app.include_router(integrations_router)
app.include_router(attendance_router)
app.include_router(meeting_plan_router)


@app.get("/api/health", tags=["system"])
def health_check():
    """Health check endpoint verifying system and demo mode status."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "demo_mode": settings.demo_mode,
        "env": settings.app_env
    }


# Mount Frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend index.html not yet built"}
