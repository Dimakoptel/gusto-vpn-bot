from .users import router as users_router
from .servers import router as servers_router
from .payments import router as payments_router
from .subscriptions import router as subscriptions_router
from .referrals import router as referrals_router
from .admin import router as admin_router
from .health import router as health_router

__all__ = [
    "users_router", "servers_router", "payments_router",
    "subscriptions_router", "referrals_router", "admin_router", "health_router"
]
