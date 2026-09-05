from fastapi import APIRouter

from app.api.v1.endpoints import auth, example_items, health, portal

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(auth.profile_router, tags=["profile"])
api_router.include_router(auth.admin_router, tags=["admin-users"])
api_router.include_router(portal.router, tags=["portal"])
api_router.include_router(example_items.router, tags=["example-items"])
