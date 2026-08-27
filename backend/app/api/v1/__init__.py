"""v1 API routers."""

from fastapi import APIRouter

from app.api.v1 import inbox, webhook

router = APIRouter(prefix="/api/v1")
router.include_router(inbox.router)
router.include_router(webhook.router)

__all__ = ["router"]
