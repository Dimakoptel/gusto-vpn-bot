"""Background Tasks — APScheduler"""
import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.database import async_session_maker
from app.services.config_service import ConfigService
from app.services.subscription_service import SubscriptionService
from app.services.notification_service import NotificationService
from app.services.x3ui_client import GustoX3UIClient, X3UIPanel
from app.models.server import GustoServer
from app.models.subscription import GustoSubscription, SubscriptionStatus
from sqlalchemy import select, and_

logger = logging.getLogger("gusto.background")

scheduler = AsyncIOScheduler()

async def check_expired_subscriptions():
    """Проверить и деактивировать истекшие подписки"""
    async with async_session_maker() as db:
        service = SubscriptionService(db)
        try:
            deactivated = await service.deactivate_expired()
            if deactivated:
                logger.info(f"✅ Deactivated {len(deactivated)} expired subscriptions")
        except Exception as e:
            logger.error(f"❌ Error checking expired subscriptions: {e}")

async def delete_expired_subscriptions():
    """Удалить подписки, истекшие более 7 дней назад"""
    async with async_session_maker() as db:
        try:
            cutoff = datetime.utcnow() - timedelta(days=7)
            result = await db.execute(
                select(GustoSubscription).where(
                    and_(
                        GustoSubscription.status == SubscriptionStatus.EXPIRED,
                        GustoSubscription.expires_at < cutoff
                    )
                )
            )
            to_delete = result.scalars().all()
            for sub in to_delete:
                await db.delete(sub)
            await db.commit()
            if to_delete:
                logger.info(f"✅ Deleted {len(to_delete)} old expired subscriptions")
        except Exception as e:
            logger.error(f"❌ Error deleting expired subscriptions: {e}")

async def monitor_servers():
    """Мониторинг серверов (ping, статус)"""
    async with async_session_maker() as db:
        try:
            result = await db.execute(
                select(GustoServer).where(GustoServer.is_active == True)
            )
            servers = result.scalars().all()

            for server in servers:
                try:
                    panel = X3UIPanel(
                        host=server.host,
                        port=server.port,
                        api_token=server.panel_api_token,
                        name=server.name
                    )
                    x3ui = GustoX3UIClient(panel)

                    # Get server status
                    status = await x3ui.get_server_status()
                    if status:
                        server.is_online = True
                        server.cpu_load = status.get("cpu", 0)
                        server.memory_used = status.get("mem", {}).get("current", 0) / 1073741824
                        server.memory_total = status.get("mem", {}).get("total", 1) / 1073741824
                        server.network_in = status.get("netTraffic", {}).get("sent", 0)
                        server.network_out = status.get("netTraffic", {}).get("recv", 0)
                        server.total_users = status.get("xray", {}).get("inbounds", 0)
                        server.last_ping = datetime.utcnow()
                        server.consecutive_fails = 0
                    else:
                        server.consecutive_fails += 1
                        if server.consecutive_fails >= 3:
                            server.is_online = False
                            notify = NotificationService(db)
                            await notify.admin_server_offline(
                                server.name, server.host, "No response"
                            )

                    await x3ui.close()
                except Exception as e:
                    server.consecutive_fails += 1
                    if server.consecutive_fails >= 3:
                        server.is_online = False
                        notify = NotificationService(db)
                        await notify.admin_server_offline(server.name, server.host, str(e))
                    logger.error(f"❌ Server {server.name} check failed: {e}")

            await db.commit()
        except Exception as e:
            logger.error(f"❌ Error monitoring servers: {e}")

async def update_traffic_stats():
    """Обновить статистику трафика"""
    async with async_session_maker() as db:
        service = SubscriptionService(db)
        try:
            await service.update_traffic_stats()
            logger.info("✅ Traffic stats updated")
        except Exception as e:
            logger.error(f"❌ Error updating traffic stats: {e}")

async def check_low_traffic():
    """Проверить пользователей с малым трафиком"""
    async with async_session_maker() as db:
        try:
            config_service = ConfigService(db)
            notify_config = await config_service.get_notification_config()
            threshold = notify_config.get("low_traffic_gb", 5.0)

            result = await db.execute(
                select(GustoSubscription).where(
                    and_(
                        GustoSubscription.status == SubscriptionStatus.ACTIVE,
                        GustoSubscription.total_gb - GustoSubscription.used_gb < threshold
                    )
                )
            )
            low_traffic = result.scalars().all()

            notify = NotificationService(db)
            for sub in low_traffic:
                remaining = sub.total_gb - sub.used_gb
                await notify.low_traffic(sub.user_id, sub.email, remaining)

            if low_traffic:
                logger.info(f"✅ Notified {len(low_traffic)} users about low traffic")
        except Exception as e:
            logger.error(f"❌ Error checking low traffic: {e}")

async def check_expiring_subscriptions():
    """Уведомить о скором истечении подписки"""
    async with async_session_maker() as db:
        try:
            config_service = ConfigService(db)
            notify_config = await config_service.get_notification_config()

            now = datetime.utcnow()
            notify = NotificationService(db)

            # 3 days
            if notify_config.get("expiry_3days", True):
                in_3_days = now + timedelta(days=3)
                result = await db.execute(
                    select(GustoSubscription).where(
                        and_(
                            GustoSubscription.status == SubscriptionStatus.ACTIVE,
                            GustoSubscription.expires_at.between(now, in_3_days),
                            GustoSubscription.notified_3days == False
                        )
                    )
                )
                for sub in result.scalars().all():
                    await notify.subscription_expiring_soon(sub.user_id, sub.email, 3)
                    sub.notified_3days = True

            # 1 day
            if notify_config.get("expiry_1day", True):
                in_1_day = now + timedelta(days=1)
                result = await db.execute(
                    select(GustoSubscription).where(
                        and_(
                            GustoSubscription.status == SubscriptionStatus.ACTIVE,
                            GustoSubscription.expires_at.between(now, in_1_day),
                            GustoSubscription.notified_1day == False
                        )
                    )
                )
                for sub in result.scalars().all():
                    await notify.subscription_expiring_soon(sub.user_id, sub.email, 1)
                    sub.notified_1day = True

            # Today
            if notify_config.get("expiry_today", True):
                in_1_hour = now + timedelta(hours=1)
                result = await db.execute(
                    select(GustoSubscription).where(
                        and_(
                            GustoSubscription.status == SubscriptionStatus.ACTIVE,
                            GustoSubscription.expires_at.between(now, in_1_hour),
                            GustoSubscription.notified_today == False
                        )
                    )
                )
                for sub in result.scalars().all():
                    await notify.subscription_expiring_soon(sub.user_id, sub.email, 0)
                    sub.notified_today = True

            await db.commit()
        except Exception as e:
            logger.error(f"❌ Error checking expiring subscriptions: {e}")

async def process_payments():
    """Проверить незавершенные платежи (fallback)"""
    async with async_session_maker() as db:
        try:
            from app.models.payment import GustoPayment, PaymentStatus
            result = await db.execute(
                select(GustoPayment).where(
                    and_(
                        GustoPayment.status == PaymentStatus.PENDING,
                        GustoPayment.created_at < datetime.utcnow() - timedelta(hours=1)
                    )
                )
            )
            stale = result.scalars().all()
            for payment in stale:
                payment.status = PaymentStatus.FAILED
            await db.commit()
            if stale:
                logger.info(f"✅ Marked {len(stale)} stale payments as failed")
        except Exception as e:
            logger.error(f"❌ Error processing payments: {e}")

async def daily_backup():
    """Ежедневный бэкап (запускается через docker-compose)"""
    logger.info("📦 Daily backup triggered")
    # Backup logic handled by docker-compose backup service

async def start_scheduler():
    """Запустить все background tasks"""
    scheduler.add_job(
        check_expired_subscriptions,
        trigger=IntervalTrigger(minutes=5),
        id="check_expired",
        replace_existing=True
    )
    scheduler.add_job(
        delete_expired_subscriptions,
        trigger=IntervalTrigger(hours=1),
        id="delete_expired",
        replace_existing=True
    )
    scheduler.add_job(
        monitor_servers,
        trigger=IntervalTrigger(minutes=2),
        id="monitor_servers",
        replace_existing=True
    )
    scheduler.add_job(
        update_traffic_stats,
        trigger=IntervalTrigger(minutes=10),
        id="update_traffic",
        replace_existing=True
    )
    scheduler.add_job(
        check_low_traffic,
        trigger=IntervalTrigger(hours=6),
        id="check_low_traffic",
        replace_existing=True
    )
    scheduler.add_job(
        check_expiring_subscriptions,
        trigger=IntervalTrigger(minutes=30),
        id="check_expiring",
        replace_existing=True
    )
    scheduler.add_job(
        process_payments,
        trigger=IntervalTrigger(minutes=15),
        id="process_payments",
        replace_existing=True
    )
    scheduler.add_job(
        daily_backup,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_backup",
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ Background scheduler started with 7 jobs")

async def stop_scheduler():
    """Остановить scheduler"""
    scheduler.shutdown()
    logger.info("✅ Background scheduler stopped")
