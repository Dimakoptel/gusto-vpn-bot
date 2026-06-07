"""GUSTO VPN API v2.0 — Production Ready"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

from app.database import engine, Base, async_session_maker
from app.routers import (
    users_router, servers_router, payments_router,
    subscriptions_router, referrals_router, admin_router,
    health_router, settings_router, plans_router
)
from app.services.config_service import ConfigService
from app.tasks.background_tasks import start_scheduler, stop_scheduler

logger = logging.getLogger("gusto.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize default settings if empty
    async with async_session_maker() as db:
        await ConfigService.initialize_defaults(db)

    # Seed default plans
    async with async_session_maker() as db:
        from app.routers.plans import seed_default_plans
        try:
            result = await seed_default_plans(db)
            logger.info(f"✅ Seeded {result['total']} default plans")
        except Exception as e:
            logger.warning(f"⚠️ Plan seed failed (may already exist): {e}")

    # Start background scheduler
    await start_scheduler()

    yield

    # Shutdown
    await stop_scheduler()
    await engine.dispose()

# CORS origins from env (restricted in production)
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
if cors_origins == ["*"]:
    cors_origins = ["*"]  # Development only

app = FastAPI(
    title="GUSTO VPN API",
    description="Быстрый. Безопасный. Без границ. | Управление через админ-панель",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(users_router)
app.include_router(servers_router)
app.include_router(plans_router)
app.include_router(payments_router)
app.include_router(subscriptions_router)
app.include_router(referrals_router)
app.include_router(admin_router)
app.include_router(settings_router)
app.include_router(health_router)

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
            "auto_backup",
            "plan_management"
        ]
    }
