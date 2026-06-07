"""
GUSTO VPN Bot Tests — pytest suite
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Test Smart Router
@pytest.mark.asyncio
async def test_smart_router_selects_best_server():
    from app.services.smart_router import GustoSmartRouter

    router = GustoSmartRouter()

    # Mock servers
    servers = [
        MagicMock(
            id=1, host="server1.ru", port=2053, cpu_load=0.8,
            memory_used=80, memory_total=100, total_users=100, max_users=200,
            is_premium=True, target_countries=["RU"]
        ),
        MagicMock(
            id=2, host="server2.ru", port=2053, cpu_load=0.3,
            memory_used=30, memory_total=100, total_users=50, max_users=200,
            is_premium=False, target_countries=["RU"]
        )
    ]

    with patch('app.services.smart_router.GustoSmartRouter._check_latency', 
               return_value=50.0):
        result = await router.find_best("RU", servers)

        assert result is not None
        assert result.server.id == 2  # Less loaded server

# Test Anti-Fraud
@pytest.mark.asyncio
async def test_antifraud_detects_sharing():
    from app.services.antifraud import GustoAntiFraud

    antifraud = GustoAntiFraud()

    # Mock subscription with many unique IPs
    sub = MagicMock()
    sub.unique_ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4", "5.5.5.5"]

    result = await antifraud.check_sharing(sub, 5)

    assert result["action"] == "rotate"
    assert result["score"] > 0.5

# Test 3x-ui Client
@pytest.mark.asyncio
async def test_x3ui_client_uses_bearer_token():
    from app.services.x3ui_client import GustoX3UIClient, X3UIPanel

    panel = X3UIPanel(
        host="test.ru", port=2053, api_token="test_token_123", name="Test"
    )

    client = GustoX3UIClient(panel)

    assert client.headers["Authorization"] == "Bearer test_token_123"
    assert "Bearer" in client.headers["Authorization"]

# Test Payment Providers
@pytest.mark.asyncio
async def test_cryptobot_creates_invoice():
    from app.services.payments import CryptoBotPayment

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "ok": True,
            "result": {
                "invoice_id": "123",
                "pay_url": "https://pay.crypt.bot/123",
                "amount": "100.00",
                "asset": "USDT"
            }
        }

        provider = CryptoBotPayment("test_token")
        result = await provider.create_payment(
            amount=100.0,
            description="Test",
            order_id="test_123"
        )

        assert result is not None
        assert result["provider"] == "cryptobot"
        assert result["pay_url"] == "https://pay.crypt.bot/123"

@pytest.mark.asyncio
async def test_yookassa_creates_payment():
    from app.services.payments import YooKassaPayment

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "id": "test_payment",
            "status": "pending",
            "amount": {"value": "100.00", "currency": "RUB"},
            "confirmation": {
                "confirmation_url": "https://yookassa.ru/pay/test"
            }
        }

        provider = YooKassaPayment("shop_id", "secret_key")
        result = await provider.create_payment(
            amount=100.0,
            description="Test",
            order_id="test_123"
        )

        assert result is not None
        assert result["provider"] == "yookassa"
        assert result["pay_url"] == "https://yookassa.ru/pay/test"

# Test Referral Engine
@pytest.mark.asyncio
async def test_referral_calculates_commission():
    from app.services.referral_engine import GustoReferralEngine

    with patch('app.services.referral_engine.GustoReferralEngine._get_referral_chain') as mock_chain:
        mock_chain.return_value = [
            {"level": 1, "user_id": 2, "telegram_id": 222},
            {"level": 2, "user_id": 3, "telegram_id": 333}
        ]

        engine = GustoReferralEngine(None)
        commissions = await engine._calculate_commissions(1000.0, 1)

        assert len(commissions) == 2
        assert commissions[0]["amount"] == 300.0  # 30%
        assert commissions[1]["amount"] == 150.0  # 15%

# Test Notification Service
@pytest.mark.asyncio
async def test_notification_sends_message():
    from app.services.notification_service import NotificationService

    mock_bot = AsyncMock()
    service = NotificationService(mock_bot)

    result = await service.send_notification(123456, "Test message")

    assert result is True
    mock_bot.send_message.assert_called_once()

# Test Background Tasks
@pytest.mark.asyncio
async def test_cleanup_expired_subscriptions():
    from app.tasks.background_tasks import BackgroundTaskManager

    with patch('app.tasks.background_tasks.async_session') as mock_session:
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db

        # Mock expired subscriptions
        mock_sub = MagicMock()
        mock_sub.status = "active"
        mock_sub.expires_at = datetime.utcnow() - timedelta(days=1)
        mock_sub.email = "test@test.com"
        mock_sub.server = MagicMock(
            host="test.ru", port=2053, panel_api_token="token"
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_sub]
        mock_db.execute.return_value = mock_result

        manager = BackgroundTaskManager(AsyncMock())
        await manager.cleanup_expired_subscriptions()

        assert mock_sub.status == "expired"

# Integration Tests
@pytest.mark.asyncio
async def test_full_purchase_flow():
    """E2E тест: покупка подписки"""
    # This would require full integration setup
    # Mock all external services
    pass
