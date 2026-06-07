from app.routers.users import router as users_router
from app.routers.servers import router as servers_router
from app.routers.payments import router as payments_router
from app.routers.subscriptions import router as subscriptions_router
from app.routers.referrals import router as referrals_router
from app.routers.admin import router as admin_router
from app.routers.health import router as health_router
from app.routers.settings import router as settings_router

__all__ = [
    "users_router",
    "servers_router",
    "payments_router",
    "subscriptions_router",
    "referrals_router",
    "admin_router",
    "health_router",
    "settings_router",
]
