"""Background Tasks — APScheduler
Проверка подписок, удаление истекших, мониторинг серверов, сбор трафика, бэкап
"""
import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.database import async_session_maker
from app.services.subscription_service import SubscriptionService
from app.services.notification_service import NotificationService
from app.services.x3ui_client import GustoX3UIClient, X3UIPanel
from app.models.server import GustoServer
from app.models.subscription import GustoSubscription, SubscriptionStatus
from sqlalchemy import select, update

logger = logging.getLogger("gusto.tasks")
scheduler = AsyncIOScheduler()

async def check_expiring_subscriptions():
    """Проверить подписки, истекающие через 3/1/0 дней"""
    async with async_session_maker() as db:
        notify = NotificationService(db)

        now = datetime.utcnow()

        # 3 days before expiry
        three_days = now + timedelta(days=3)
        result = await db.execute(
            select(GustoSubscription).where(
                GustoSubscription.status == SubscriptionStatus.ACTIVE,
                GustoSubscription.expires_at <= three_days,
                GustoSubscription.expires_at > now + timedelta(days=2)
            )
        )
        for sub in result.scalars().all():
            await notify.subscription_expiring_soon(sub.user_id, sub.email, days=3)

        # 1 day before expiry
        one_day = now + timedelta(days=1)
        result = await db.execute(
            select(GustoSubscription).where(
                GustoSubscription.status == SubscriptionStatus.ACTIVE,
                GustoSubscription.expires_at <= one_day,
                GustoSubscription.expires_at > now
            )
        )
        for sub in result.scalars().all():
            await notify.subscription_expiring_soon(sub.user_id, sub.email, days=1)

        # Today expired
        result = await db.execute(
            select(GustoSubscription).where(
                GustoSubscription.status == SubscriptionStatus.ACTIVE,
                GustoSubscription.expires_at <= now
            )
        )
        for sub in result.scalars().all():
            await notify.subscription_expired(sub.user_id, sub.email)

        logger.info(f"✅ Checked expiring subscriptions at {now}")

async def cleanup_expired_subscriptions():
    """Деактивировать истекшие подписки и удалить из 3x-ui"""
    async with async_session_maker() as db:
        service = SubscriptionService(db)
        deactivated = await service.deactivate_expired()
        logger.info(f"✅ Deactivated {len(deactivated)} expired subscriptions")

async def monitor_servers():
    """Проверить доступность серверов (TCP ping)"""
    async with async_session_maker() as db:
        result = await db.execute(select(GustoServer).where(GustoServer.is_active == True))
        servers = result.scalars().all()

        for server in servers:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                await asyncio.get_event_loop().run_in_executor(None, sock.connect, (server.host, server.port))
                sock.close()

                server.is_online = True
                server.last_ping = datetime.utcnow()
                server.ping_ms = 50  # Placeholder

            except Exception as e:
                server.is_online = False
                server.consecutive_fails = (server.consecutive_fails or 0) + 1
                logger.warning(f"⚠️ Server {server.name} ({server.host}) offline: {e}")

                # Notify admins if server is down
                if server.consecutive_fails >= 3:
                    notify = NotificationService(db)
                    await notify.admin_server_offline(server.name, server.host, str(e))

        await db.commit()
        logger.info(f"✅ Monitored {len(servers)} servers")

async def collect_traffic_stats():
    """Обновить статистику трафика из 3x-ui"""
    async with async_session_maker() as db:
        service = SubscriptionService(db)
        await service.update_traffic_stats()
        logger.info("✅ Traffic stats updated")

async def check_pending_payments():
    """Проверить просроченные платежи"""
    async with async_session_maker() as db:
        from app.models.payment import GustoPayment, PaymentStatus

        now = datetime.utcnow()
        result = await db.execute(
            select(GustoPayment).where(
                GustoPayment.status == PaymentStatus.PENDING,
                GustoPayment.created_at < now - timedelta(hours=1)
            )
        )
        expired = result.scalars().all()

        for payment in expired:
            payment.status = PaymentStatus.FAILED
            logger.info(f"⏳ Payment #{payment.id} expired (created at {payment.created_at})")

        await db.commit()
        logger.info(f"✅ Checked {len(expired)} expired payments")

async def backup_database():
    """Бэкап PostgreSQL (если запущен в Docker)"""
    import subprocess
    import os
    from datetime import datetime

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_dir = "/backups"
    os.makedirs(backup_dir, exist_ok=True)

    filename = f"{backup_dir}/gusto_backup_{timestamp}.sql.gz"

    try:
        # This assumes we're in the Docker container with pg_dump available
        # In production, use S3 upload
        subprocess.run([
            "pg_dump", "-h", "postgres", "-U", "gusto", "gusto_vpn", "|", "gzip", ">", filename
        ], shell=True, check=True, env={**os.environ, "PGPASSWORD": os.getenv("DB_PASSWORD", "gusto_secret_2024")})

        logger.info(f"✅ Database backup created: {filename}")

        # Cleanup old backups (keep 30 days)
        subprocess.run([
            "find", backup_dir, "-name", "gusto_backup_*.sql.gz", "-mtime", "+30", "-delete"
        ], check=False)

    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")

async def start_scheduler():
    """Запустить планировщик фоновых задач"""
    scheduler.add_job(
        check_expiring_subscriptions,
        trigger=IntervalTrigger(minutes=10),
        id="check_expiring",
        replace_existing=True
    )

    scheduler.add_job(
        cleanup_expired_subscriptions,
        trigger=IntervalTrigger(hours=1),
        id="cleanup_expired",
        replace_existing=True
    )

    scheduler.add_job(
        monitor_servers,
        trigger=IntervalTrigger(minutes=2),
        id="monitor_servers",
        replace_existing=True
    )

    scheduler.add_job(
        collect_traffic_stats,
        trigger=IntervalTrigger(minutes=5),
        id="collect_traffic",
        replace_existing=True
    )

    scheduler.add_job(
        check_pending_payments,
        trigger=IntervalTrigger(minutes=5),
        id="check_payments",
        replace_existing=True
    )

    scheduler.add_job(
        backup_database,
        trigger=CronTrigger(hour=3, minute=0),
        id="backup_db",
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ Background scheduler started with 6 jobs")

async def stop_scheduler():
    """Остановить планировщик"""
    scheduler.shutdown()
    logger.info("✅ Background scheduler stopped")
