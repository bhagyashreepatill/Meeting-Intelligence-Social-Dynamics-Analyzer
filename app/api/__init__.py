"""API router package."""
from app.api.meetings import router as meetings_router
from app.api.action_items import router as action_items_router
from app.api.ideas import router as ideas_router
from app.api.analytics import router as analytics_router, global_analytics_router
from app.api.integrations import router as integrations_router
from app.api.attendance import router as attendance_router
from app.api.meeting_plan import router as meeting_plan_router

__all__ = [
    "meetings_router",
    "action_items_router",
    "ideas_router",
    "analytics_router",
    "global_analytics_router",
    "integrations_router",
    "attendance_router",
    "meeting_plan_router"
]
