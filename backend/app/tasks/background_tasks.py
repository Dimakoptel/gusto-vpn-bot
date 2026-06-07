"""
GUSTO Background Tasks — APScheduler jobs
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import async_session
from app.models import GustoSubscription, GustoServer, GustoUser, GustoPayment
from app.services import GustoX3UIClient, X3UIPanel
from app.services.notification_service import NotificationService
from app.config import settings

logger = logging.getLogger("gusto.tasks")

class BackgroundTaskManager:
    """Менеджер фоновых задач"""

    def __init__(self, bot):
        self.scheduler = AsyncIOScheduler()
        self.bot = bot
        self.notifier = NotificationService(bot)

    def start(self):
        """Запустить все задачи"""
        # Проверка истекающих подписок (каждые 10 мин)
        self.scheduler.add_job(
            self.check_expiring_subscriptions,
            IntervalTrigger(minutes=10),
            id="check_expiring",
            replace_existing=True
        )

        # Удаление истекших подписок (каждый час)
        self.scheduler.add_job(
            self.cleanup_expired_subscriptions,
            IntervalTrigger(hours=1),
            id="cleanup_expired",
            replace_existing=True
        )

        # Мониторинг серверов (каждые 2 мин)
        self.scheduler.add_job(
            self.monitor_servers,
            IntervalTrigger(minutes=2),
            id="monitor_servers",
            replace_existing=True
        )

        # Сбор статистики трафика (каждые 5 мин)
        self.scheduler.add_job(
            self.collect_traffic_stats,
            IntervalTrigger(minutes=5),
            id="collect_traffic",
            replace_existing=True
        )

        # Проверка pending платежей (каждые 5 мин)
        self.scheduler.add_job(
            self.check_pending_payments,
            IntervalTrigger(minutes=5),
            id="check_payments",
            replace_existing=True
        )

        # Бэкап базы данных (ежедневно в 3:00)
        self.scheduler.add_job(
            self.backup_database,
            "cron",
            hour=3,
            minute=0,
            id="backup_db",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("✅ Background tasks started")

    def shutdown(self):
        """Остановить задачи"""
        self.scheduler.shutdown()
        logger.info("🔒 Background tasks stopped")

    async def check_expiring_subscriptions(self):
        """Проверить подписки, истекающие через 3/1 день"""
        async with async_session() as db:
            now = datetime.utcnow()

            # За 3 дня
            days_3 = now + timedelta(days=3)
            days_3_start = days_3.replace(hour=0, minute=0, second=0)
            days_3_end = days_3.replace(hour=23, minute=59, second=59)

            result = await db.execute(
                select(GustoSubscription).where(
                    and_(
                        GustoSubscription.status == "active",
                        GustoSubscription.expires_at >= days_3_start,
                        GustoSubscription.expires_at <= days_3_end,
                        GustoSubscription.notified_3d == False  # Флаг уведомления
                    )
                )
            )
            subs_3d = result.scalars().all()

            for sub in subs_3d:
                user = await db.get(GustoUser, sub.user_id)
                if user:
                    await self.notifier.subscription_expiring_soon(
                        user.telegram_id,
                        3,
                        sub.plan.name if sub.plan else "Unknown",
                        sub.expires_at.strftime("%d.%m.%Y")
                    )
                    sub.notified_3d = True

            # За 1 день
            days_1 = now + timedelta(days=1)
            days_1_start = days_1.replace(hour=0, minute=0, second=0)
            days_1_end = days_1.replace(hour=23, minute=59, second=59)

            result = await db.execute(
                select(GustoSubscription).where(
                    and_(
                        GustoSubscription.status == "active",
                        GustoSubscription.expires_at >= days_1_start,
                        GustoSubscription.expires_at <= days_1_end,
                        GustoSubscription.notified_1d == False
                    )
                )
            )
            subs_1d = result.scalars().all()

            for sub in subs_1d:
                user = await db.get(GustoUser, sub.user_id)
                if user:
                    await self.notifier.subscription_expiring_soon(
                        user.telegram_id,
                        1,
                        sub.plan.name if sub.plan else "Unknown",
                        sub.expires_at.strftime("%d.%m.%Y")
                    )
                    sub.notified_1d = True

            await db.commit()
            logger.info(f"Checked expiring: {len(subs_3d)} (3d), {len(subs_1d)} (1d)")

    async def cleanup_expired_subscriptions(self):
        """Удалить/отключить истекшие подписки"""
        async with async_session() as db:
            now = datetime.utcnow()

            result = await db.execute(
                select(GustoSubscription).where(
                    and_(
                        GustoSubscription.status == "active",
                        GustoSubscription.expires_at < now
                    )
                )
            )
            expired = result.scalars().all()

            for sub in expired:
                # Отключить клиента в 3x-ui
                if sub.server:
                    x3ui = GustoX3UIClient(X3UIPanel(
                        host=sub.server.host,
                        port=sub.server.port,
                        api_token=sub.server.panel_api_token,
                        name=sub.server.name
                    ))

                    try:
                        await x3ui.update_client(sub.email, {"enable": False})
                        logger.info(f"Disabled client: {sub.email}")
                    except Exception as e:
                        logger.error(f"Failed to disable client {sub.email}: {e}")
                    finally:
                        await x3ui.close()

                sub.status = "expired"

                # Уведомить пользователя
                user = await db.get(GustoUser, sub.user_id)
                if user:
                    await self.notifier.subscription_expired(
                        user.telegram_id,
                        sub.plan.name if sub.plan else "Unknown"
                    )

            await db.commit()
            logger.info(f"Cleaned up {len(expired)} expired subscriptions")

    async def monitor_servers(self):
        """Мониторинг серверов (ping, CPU, online status)"""
        async with async_session() as db:
            result = await db.execute(
                select(GustoServer).where(GustoServer.is_active == True)
            )
            servers = result.scalars().all()

            for server in servers:
                x3ui = GustoX3UIClient(X3UIPanel(
                    host=server.host,
                    port=server.port,
                    api_token=server.panel_api_token,
                    name=server.name
                ))

                try:
                    # Проверить статус
                    status = await x3ui.get_server_status()

                    if status:
                        server.is_online = True
                        server.cpu_load = status.get("cpu", 0)
                        server.memory_used = status.get("mem", {}).get("current", 0)
                        server.memory_total = status.get("mem", {}).get("total", 1)
                        server.last_check = datetime.utcnow()
                    else:
                        server.is_online = False

                        # Уведомить админов
                        admin_ids = settings.ADMIN_IDS
                        for admin_id in admin_ids:
                            await self.notifier.admin_server_offline(admin_id, server.name)

                except Exception as e:
                    server.is_online = False
                    logger.error(f"Server {server.name} check failed: {e}")

                finally:
                    await x3ui.close()

            await db.commit()
            logger.info(f"Monitored {len(servers)} servers")

    async def collect_traffic_stats(self):
        """Собрать статистику трафика по подпискам"""
        async with async_session() as db:
            result = await db.execute(
                select(GustoSubscription).where(
                    GustoSubscription.status == "active"
                )
            )
            subs = result.scalars().all()

            for sub in subs:
                if not sub.server:
                    continue

                x3ui = GustoX3UIClient(X3UIPanel(
                    host=sub.server.host,
                    port=sub.server.port,
                    api_token=sub.server.panel_api_token,
                    name=sub.server.name
                ))

                try:
                    stats = await x3ui.get_client_traffic(sub.email)
                    if stats:
                        # Обновить использованный трафик
                        up = stats.get("up", 0)
                        down = stats.get("down", 0)
                        total_used = (up + down) / (1024 ** 3)  # bytes to GB

                        sub.used_gb = total_used

                        # Проверить лимит трафика
                        if sub.total_gb > 0 and total_used >= sub.total_gb:
                            sub.status = "suspended"

                            user = await db.get(GustoUser, sub.user_id)
                            if user:
                                await self.notifier.low_traffic(
                                    user.telegram_id,
                                    0,
                                    sub.total_gb,
                                    sub.plan.name if sub.plan else "Unknown"
                                )

                except Exception as e:
                    logger.error(f"Traffic collection failed for {sub.email}: {e}")

                finally:
                    await x3ui.close()

            await db.commit()
            logger.info(f"Collected traffic for {len(subs)} subscriptions")

    async def check_pending_payments(self):
        """Проверить pending платежи и активировать подписки"""
        async with async_session() as db:
            from app.services.payments import PaymentManager

            payment_manager = PaymentManager()

            result = await db.execute(
                select(GustoPayment).where(
                    and_(
                        GustoPayment.status == "pending",
                        GustoPayment.created_at > datetime.utcnow() - timedelta(hours=24)
                    )
                )
            )
            payments = result.scalars().all()

            for payment in payments:
                try:
                    result = await payment_manager.check_payment(
                        payment.method,
                        payment.provider_payment_id
                    )

                    if result and result["status"] == "success":
                        payment.status = "success"
                        payment.paid_at = datetime.utcnow()

                        # Активировать подписку
                        if payment.subscription_id:
                            sub = await db.get(GustoSubscription, payment.subscription_id)
                            if sub and sub.status == "pending":
                                sub.status = "active"
                                sub.started_at = datetime.utcnow()

                                # Уведомить пользователя
                                user = await db.get(GustoUser, payment.user_id)
                                if user:
                                    await self.notifier.payment_success(
                                        user.telegram_id,
                                        sub.plan.name if sub.plan else "Unknown",
                                        float(payment.amount),
                                        sub.config_link or ""
                                    )

                        # Обработать рефералку
                        from app.services.referral_engine import GustoReferralEngine
                        ref_engine = GustoReferralEngine(db)
                        await ref_engine.process_payment(payment)

                except Exception as e:
                    logger.error(f"Payment check failed {payment.id}: {e}")

            await db.commit()
            logger.info(f"Checked {len(payments)} pending payments")

    async def backup_database(self):
        """Бэкап базы данных"""
        import subprocess
        import os

        backup_dir = "/app/backups"
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/gusto_backup_{timestamp}.sql"

        try:
            # pg_dump
            db_url = settings.DATABASE_URL
            result = subprocess.run(
                ["pg_dump", "-f", backup_file, db_url],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                logger.info(f"✅ Backup created: {backup_file}")

                # Upload to S3 (optional)
                if settings.BACKUP_S3_BUCKET:
                    await self._upload_to_s3(backup_file)

                # Cleanup old backups (keep 30 days)
                await self._cleanup_old_backups(backup_dir, days=30)
            else:
                logger.error(f"Backup failed: {result.stderr}")

        except Exception as e:
            logger.error(f"Backup error: {e}")

    async def _upload_to_s3(self, file_path: str):
        """Upload backup to S3"""
        import boto3

        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.BACKUP_S3_ENDPOINT,
                aws_access_key_id=settings.BACKUP_S3_KEY,
                aws_secret_access_key=settings.BACKUP_S3_SECRET
            )

            key = os.path.basename(file_path)
            s3.upload_file(file_path, settings.BACKUP_S3_BUCKET, key)
            logger.info(f"✅ Backup uploaded to S3: {key}")

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")

    async def _cleanup_old_backups(self, backup_dir: str, days: int = 30):
        """Удалить старые бэкапы"""
        import os
        from pathlib import Path

        cutoff = datetime.utcnow() - timedelta(days=days)

        for file in Path(backup_dir).glob("gusto_backup_*.sql"):
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if mtime < cutoff:
                file.unlink()
                logger.info(f"🗑️ Removed old backup: {file.name}")
