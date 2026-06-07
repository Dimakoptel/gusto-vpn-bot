"""Subscription Service — активация, продление, управление подписками"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.subscription import GustoSubscription, SubscriptionStatus
from app.models.user import GustoUser
from app.models.server import GustoServer
from app.models.plan import GustoPlan
from app.models.payment import GustoPayment, PaymentStatus
from app.services.x3ui_client import GustoX3UIClient, X3UIPanel
from app.services.config_service import ConfigService
from app.services.notification_service import NotificationService

logger = logging.getLogger("gusto.subscriptions")

class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notify = NotificationService(db)

    async def create_pending(self, user_id: int, plan_id: int, country_code: str = "RU") -> Dict[str, Any]:
        """Создать подписку в статусе PENDING (до оплаты)"""
        # Get user
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get plan
        result = await self.db.execute(select(GustoPlan).where(GustoPlan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan or not plan.is_active:
            raise ValueError(f"Plan {plan_id} not found or inactive")

        # Select server via Smart Router
        server = await self._select_server(country_code, plan.is_premium)
        if not server:
            raise ValueError("No available servers")

        # Generate unique email
        email = f"user{user_id}_{uuid.uuid4().hex[:8]}@gusto.vpn"
        client_uuid = str(uuid.uuid4())

        # Create subscription record
        subscription = GustoSubscription(
            user_id=user_id,
            plan_id=plan_id,
            server_id=server.id,
            email=email,
            uuid=client_uuid,
            protocol=plan.protocol,
            security=plan.security,
            total_gb=plan.traffic_gb,
            used_gb=0,
            device_limit=plan.device_limit,
            ip_limit=plan.ip_limit,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=plan.duration_days),
            status=SubscriptionStatus.PENDING,
            config_link="",
            config_json={}
        )
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)

        return {
            "subscription_id": subscription.id,
            "email": email,
            "uuid": client_uuid,
            "plan": {
                "id": plan.id,
                "name": plan.display_name,
                "price": plan.price,
                "traffic_gb": plan.traffic_gb,
                "duration_days": plan.duration_days
            },
            "server": {
                "id": server.id,
                "name": server.display_name or server.name,
                "host": server.host,
                "flag": server.flag_emoji
            }
        }

    async def activate_after_payment(self, payment: GustoPayment) -> Dict[str, Any]:
        """Активировать подписку после успешной оплаты — КЛЮЧЕВАЯ ФУНКЦИЯ!"""
        logger.info(f"🚀 Activating subscription for payment #{payment.id}")

        # Get subscription
        result = await self.db.execute(
            select(GustoSubscription).where(GustoSubscription.id == payment.subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.error(f"❌ Subscription not found for payment #{payment.id}")
            raise ValueError("Subscription not found")

        if subscription.status != SubscriptionStatus.PENDING:
            logger.warning(f"⚠️ Subscription #{subscription.id} already activated (status: {subscription.status})")
            return {"status": "already_active", "subscription_id": subscription.id}

        # Get plan and server
        result = await self.db.execute(select(GustoPlan).where(GustoPlan.id == subscription.plan_id))
        plan = result.scalar_one_or_none()

        result = await self.db.execute(select(GustoServer).where(GustoServer.id == subscription.server_id))
        server = result.scalar_one_or_none()

        if not plan or not server:
            logger.error(f"❌ Plan or server not found for subscription #{subscription.id}")
            raise ValueError("Plan or server not found")

        # Create client in 3x-ui
        try:
            panel = X3UIPanel(
                host=server.host,
                port=server.port,
                api_token=server.panel_api_token,
                name=server.name
            )
            x3ui = GustoX3UIClient(panel)

            # Determine inbound ID based on protocol
            inbound_id = server.vless_inbound_id if subscription.protocol == "vless" else                         server.trojan_inbound_id if subscription.protocol == "trojan" else                         server.ss_inbound_id or 1

            # Create client in 3x-ui
            client_result = await x3ui.create_client(
                inbound_ids=[inbound_id],
                email=subscription.email,
                total_gb=subscription.total_gb,
                expiry_days=plan.duration_days,
                uuid_str=subscription.uuid,
                enable=True,
                tg_id=subscription.user_id,
                ip_limit=subscription.ip_limit,
                flow=server.reality_short_id or "xtls-rprx-vision"
            )

            if not client_result:
                raise RuntimeError("Failed to create client in 3x-ui")

            # Generate config link
            if subscription.protocol == "vless":
                config_link = x3ui.generate_vless_link(
                    client_uuid=subscription.uuid,
                    host=server.host,
                    port=server.port,
                    remark=f"GUSTO-{server.name}",
                    public_key=server.reality_public_key or "",
                    short_id=server.reality_short_id or "",
                    server_name=server.host
                )
            elif subscription.protocol == "trojan":
                config_link = x3ui.generate_trojan_link(
                    password=subscription.uuid,
                    host=server.host,
                    port=server.port,
                    remark=f"GUSTO-{server.name}"
                )
            else:
                config_link = x3ui.generate_vmess_link({
                    "v": "2", "ps": f"GUSTO-{server.name}",
                    "add": server.host, "port": str(server.port),
                    "id": subscription.uuid, "aid": "0",
                    "scy": "auto", "net": "tcp", "type": "none",
                    "host": "", "path": "", "tls": "reality"
                })

            await x3ui.close()

            # Update subscription
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.config_link = config_link
            subscription.config_json = {
                "protocol": subscription.protocol,
                "uuid": subscription.uuid,
                "server": server.host,
                "port": server.port,
                "inbound_id": inbound_id,
                "email": subscription.email,
                "public_key": server.reality_public_key,
                "short_id": server.reality_short_id
            }
            subscription.started_at = datetime.utcnow()
            subscription.expires_at = datetime.utcnow() + timedelta(days=plan.duration_days)

            await self.db.commit()
            await self.db.refresh(subscription)

            # Process referral
            await self._process_referral(payment)

            # Send notification
            await self.notify.payment_success(
                user_id=subscription.user_id,
                amount=float(payment.amount),
                plan_name=plan.display_name,
                config_link=config_link,
                server_name=server.display_name or server.name
            )

            logger.info(f"✅ Subscription #{subscription.id} activated successfully!")

            return {
                "status": "activated",
                "subscription_id": subscription.id,
                "config_link": config_link,
                "email": subscription.email,
                "expires_at": subscription.expires_at.isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Failed to activate subscription #{subscription.id}: {e}")
            # Mark payment for retry
            payment.status = PaymentStatus.PENDING
            await self.db.commit()
            raise

    async def renew_subscription(self, subscription_id: int, plan_id: int, payment: GustoPayment) -> Dict[str, Any]:
        """Продлить подписку через bulkAdjust"""
        result = await self.db.execute(
            select(GustoSubscription).where(GustoSubscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise ValueError("Subscription not found")

        result = await self.db.execute(select(GustoPlan).where(GustoPlan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan:
            raise ValueError("Plan not found")

        result = await self.db.execute(select(GustoServer).where(GustoServer.id == subscription.server_id))
        server = result.scalar_one_or_none()
        if not server:
            raise ValueError("Server not found")

        # Use bulkAdjust to add days and traffic
        try:
            panel = X3UIPanel(
                host=server.host,
                port=server.port,
                api_token=server.panel_api_token,
                name=server.name
            )
            x3ui = GustoX3UIClient(panel)

            add_bytes = int(plan.traffic_gb * 1073741824)  # GB to bytes

            await x3ui.bulk_adjust_clients(
                emails=[subscription.email],
                add_days=plan.duration_days,
                add_bytes=add_bytes
            )

            await x3ui.close()

            # Update subscription
            subscription.expires_at = subscription.expires_at + timedelta(days=plan.duration_days)
            subscription.total_gb = subscription.total_gb + plan.traffic_gb
            subscription.status = SubscriptionStatus.ACTIVE

            await self.db.commit()
            await self.db.refresh(subscription)

            await self.notify.subscription_renewed(
                user_id=subscription.user_id,
                plan_name=plan.display_name,
                new_expiry=subscription.expires_at
            )

            return {
                "status": "renewed",
                "subscription_id": subscription.id,
                "new_expires_at": subscription.expires_at.isoformat(),
                "new_total_gb": float(subscription.total_gb)
            }

        except Exception as e:
            logger.error(f"❌ Failed to renew subscription #{subscription.id}: {e}")
            raise

    async def _select_server(self, country_code: str, is_premium: bool = False) -> Optional[GustoServer]:
        """Smart Router — выбор лучшего сервера"""
        from sqlalchemy import and_, or_

        query = select(GustoServer).where(
            and_(
                GustoServer.is_active == True,
                GustoServer.is_online == True,
                GustoServer.total_users < GustoServer.max_users
            )
        )

        if is_premium:
            query = query.where(GustoServer.is_premium == True)

        # Prefer servers with target country
        if country_code:
            query = query.where(
                or_(
                    GustoServer.country_code == country_code,
                    GustoServer.target_countries.contains([country_code])
                )
            )

        # Order by load (CPU + user ratio)
        query = query.order_by(
            (GustoServer.cpu_load * 0.35 + 
             (GustoServer.total_users / GustoServer.max_users) * 0.30 +
             GustoServer.memory_used * 0.20).asc()
        )

        result = await self.db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def _process_referral(self, payment: GustoPayment) -> None:
        """Обработать реферальные начисления"""
        result = await self.db.execute(
            select(GustoUser).where(GustoUser.id == payment.user_id)
        )
        user = result.scalar_one_or_none()
        if not user or not user.referred_by:
            return

        # Get referral config
        ref_config = await ConfigService.get_many([
            "REFERRAL_ENABLED", "REFERRAL_LEVEL_1", 
            "REFERRAL_LEVEL_2", "REFERRAL_LEVEL_3"
        ])

        if not ref_config.get("REFERRAL_ENABLED", True):
            return

        # Process 3 levels
        levels = [
            (user.referred_by, float(ref_config.get("REFERRAL_LEVEL_1", 0.30))),
        ]

        # Level 2
        result = await self.db.execute(
            select(GustoUser).where(GustoUser.id == user.referred_by)
        )
        referrer = result.scalar_one_or_none()
        if referrer and referrer.referred_by:
            levels.append((referrer.referred_by, float(ref_config.get("REFERRAL_LEVEL_2", 0.15))))

            # Level 3
            result = await self.db.execute(
                select(GustoUser).where(GustoUser.id == referrer.referred_by)
            )
            referrer2 = result.scalar_one_or_none()
            if referrer2 and referrer2.referred_by:
                levels.append((referrer2.referred_by, float(ref_config.get("REFERRAL_LEVEL_3", 0.05))))

        # Apply commissions
        for ref_id, percent in levels:
            commission = float(payment.amount) * percent
            await self.db.execute(
                update(GustoUser)
                .where(GustoUser.id == ref_id)
                .values(
                    referral_balance=GustoUser.referral_balance + Decimal(str(commission)),
                    total_earned=GustoUser.total_earned + Decimal(str(commission))
                )
            )

            await self.notify.referral_earned(
                user_id=ref_id,
                amount=commission,
                level=levels.index((ref_id, percent)) + 1,
                from_user=payment.user_id
            )

        await self.db.commit()

    async def deactivate_expired(self) -> List[int]:
        """Деактивировать истекшие подписки"""
        result = await self.db.execute(
            select(GustoSubscription).where(
                and_(
                    GustoSubscription.status == SubscriptionStatus.ACTIVE,
                    GustoSubscription.expires_at < datetime.utcnow()
                )
            )
        )
        expired = result.scalars().all()

        deactivated = []
        for sub in expired:
            sub.status = SubscriptionStatus.EXPIRED
            deactivated.append(sub.id)

            # Delete from 3x-ui
            try:
                result = await self.db.execute(
                    select(GustoServer).where(GustoServer.id == sub.server_id)
                )
                server = result.scalar_one_or_none()
                if server:
                    panel = X3UIPanel(
                        host=server.host,
                        port=server.port,
                        api_token=server.panel_api_token,
                        name=server.name
                    )
                    x3ui = GustoX3UIClient(panel)
                    await x3ui.delete_client(sub.email)
                    await x3ui.close()
            except Exception as e:
                logger.error(f"Failed to delete client {sub.email}: {e}")

            await self.notify.subscription_expired(sub.user_id, sub.email)

        await self.db.commit()
        return deactivated

    async def update_traffic_stats(self) -> None:
        """Обновить статистику трафика из 3x-ui"""
        result = await self.db.execute(
            select(GustoSubscription).where(
                GustoSubscription.status == SubscriptionStatus.ACTIVE
            )
        )
        subscriptions = result.scalars().all()

        for sub in subscriptions:
            try:
                result = await self.db.execute(
                    select(GustoServer).where(GustoServer.id == sub.server_id)
                )
                server = result.scalar_one_or_none()
                if not server:
                    continue

                panel = X3UIPanel(
                    host=server.host,
                    port=server.port,
                    api_token=server.panel_api_token,
                    name=server.name
                )
                x3ui = GustoX3UIClient(panel)

                traffic = await x3ui.get_client_traffic(sub.email)
                if traffic:
                    # Convert bytes to GB
                    upload_gb = traffic.get("up", 0) / 1073741824
                    download_gb = traffic.get("down", 0) / 1073741824
                    sub.used_gb = upload_gb + download_gb

                    # Check IPs for antifraud
                    ips = await x3ui.get_client_ips(sub.email)
                    sub.unique_ips_24h = len(ips)
                    sub.last_ip_check = datetime.utcnow()

                await x3ui.close()

            except Exception as e:
                logger.error(f"Failed to update traffic for {sub.email}: {e}")

        await self.db.commit()
