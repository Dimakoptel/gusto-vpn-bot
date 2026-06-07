from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, Base, async_session_maker
from app.routers import (
    users_router, servers_router, payments_router,
    subscriptions_router, referrals_router, admin_router,
    health_router, settings_router
)
from app.services.config_service import ConfigService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize default settings if table is empty
    async with async_session_maker() as db:
        await ConfigService.initialize_defaults(db)

    yield

    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="GUSTO VPN API",
    description="Быстрый. Безопасный. Без границ. | Управление через админ-панель",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set to your admin-panel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(servers_router, prefix="/api/servers", tags=["Servers"])
app.include_router(payments_router, prefix="/api/payments", tags=["Payments"])
app.include_router(subscriptions_router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(referrals_router, prefix="/api/referrals", tags=["Referrals"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(settings_router, prefix="", tags=["Settings"])
app.include_router(health_router, prefix="", tags=["Health"])


@app.get("/")
async def root():
    return {
        "name": "GUSTO VPN API",
        "version": "2.0.0",
        "tagline": "Быстрый. Безопасный. Без границ.",
        "status": "operational",
        "admin_panel": "/admin",
        "features": [
            "dynamic_settings",
            "multi_payment_providers",
            "smart_router",
            "referral_system",
            "anti_fraud",
            "auto_backup"
        ]
    }
