from fastapi import APIRouter

from app.presentation.routers.health import router as health_router
from app.presentation.routers.v1.users import router as users_router

api = APIRouter()
api.include_router(health_router)

# Add all v1 routers here
routers = (users_router,)
for router in routers:
    api.include_router(router, prefix="/v1")
