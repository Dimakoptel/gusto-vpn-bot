from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import users_router, servers_router, payments_router
from app.routers import subscriptions_router, referrals_router, admin_router, health_router
from app.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="GUSTO VPN API",
    description="Быстрый. Безопасный. Без границ.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(servers_router, prefix="/api/servers", tags=["Servers"])
app.include_router(payments_router, prefix="/api/payments", tags=["Payments"])
app.include_router(subscriptions_router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(referrals_router, prefix="/api/referrals", tags=["Referrals"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(health_router, prefix="", tags=["Health"])


@app.get("/")
async def root():
    return {
        "name": "GUSTO VPN API",
        "version": "1.0.0",
        "tagline": "Быстрый. Безопасный. Без границ.",
        "status": "operational"
    }
