"""
GUSTO VPN Bot — Telegram Interface
Быстрый. Безопасный. Без границ.
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gusto.bot")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Main Menu
MAIN_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy")],
    [InlineKeyboardButton(text="👤 Мой кабинет", callback_data="account")],
    [InlineKeyboardButton(text="👥 Партнерка", callback_data="referral")],
    [InlineKeyboardButton(text="❓ Помощь", callback_data="support")],
])

PLANS_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚡ GUSTO Базовый — 299₽", callback_data="plan:basic")],
    [InlineKeyboardButton(text="🚀 GUSTO Про — 599₽", callback_data="plan:pro")],
    [InlineKeyboardButton(text="👑 GUSTO Макс — 999₽", callback_data="plan:max")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="main")],
])

PAYMENT_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💎 CryptoBot", callback_data="pay:crypto")],
    [InlineKeyboardButton(text="💳 ЮKassa", callback_data="pay:yookassa")],
    [InlineKeyboardButton(text="💵 FreeKassa", callback_data="pay:freekassa")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="buy")],
])

ACCOUNT_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📊 Мои подписки", callback_data="subs")],
    [InlineKeyboardButton(text="🔑 Получить конфиг", callback_data="config")],
    [InlineKeyboardButton(text="🔄 Продлить", callback_data="renew")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="main")],
])


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """GUSTO Welcome"""
    await message.answer(
        f"🚀 <b>Добро пожаловать в GUSTO VPN!</b>

"
        f"Привет, {message.from_user.first_name}! 👋

"
        f"<b>Что такое GUSTO?</b>
"
        f"• ⚡ Максимальная скорость (XTLS-Reality)
"
        f"• 🌍 10+ серверов в Европе и Азии
"
        f"• 🔒 Военное шифрование
"
        f"• 📱 До 5 устройств
"
        f"• 💰 Оплата картой, криптой, СБП

"
        f"<i>Быстрый. Безопасный. Без границ.</i>

"
        f"Выберите действие 👇",
        reply_markup=MAIN_KB
    )


@dp.callback_query(F.data == "buy")
async def cb_buy(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 <b>GUSTO Тарифы</b>

"
        "Все тарифы включают:
"
        "• ⚡ VLESS + Reality (обход DPI)
"
        "• 🔄 Smart Router (автовыбор сервера)
"
        "• 📱 3-5 устройств
"
        "• 🛡️ GUSTO Shield (антифрод)
"
        "• 💬 Поддержка 24/7

"
        "<i>⭐ Популярный выбор — GUSTO Про</i>",
        reply_markup=PLANS_KB
    )


@dp.callback_query(F.data.startswith("plan:"))
async def cb_plan(callback: CallbackQuery):
    plan = callback.data.split(":")[1]
    prices = {"basic": 299, "pro": 599, "max": 999}
    await callback.message.edit_text(
        f"✅ <b>GUSTO {plan.upper()}</b>

"
        f"Сумма: <b>{prices.get(plan, 599)}₽</b>

"
        f"Выберите способ оплаты:",
        reply_markup=PAYMENT_KB
    )


@dp.callback_query(F.data.startswith("pay:"))
async def cb_payment(callback: CallbackQuery):
    method = callback.data.split(":")[1]
    methods = {"crypto": "CryptoBot", "yookassa": "ЮKassa", "freekassa": "FreeKassa"}
    await callback.message.edit_text(
        f"🏦 <b>Оплата через {methods.get(method)}</b>

"
        f"Счет создан! Оплатите и конфигурация придет автоматически.

"
        f"<i>GUSTO — Быстрый. Безопасный. Без границ.</i>"
    )


@dp.callback_query(F.data == "account")
async def cb_account(callback: CallbackQuery):
    await callback.message.edit_text(
        "👤 <b>Мой GUSTO</b>

"
        "├ ID: <code>12345</code>
"
        "├ Подписки: 1 активная
"
        "├ 💰 Баланс: 0.00₽
"
        "├ 👥 Рефералов: 0
"
        "└ 🏆 Ачивок: 0

"
        "<code>https://t.me/gustovpn_bot?start=ref_abc123</code>",
        reply_markup=ACCOUNT_KB
    )


@dp.callback_query(F.data == "config")
async def cb_config(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔑 <b>Ваша GUSTO конфигурация</b>

"
        "📡 Сервер: GUSTO-NL-1 🇳🇱
"
        "🔒 Протокол: VLESS + Reality
"
        "📅 Действует до: 2024-12-31
"
        "📊 Трафик: 12.5 / 100 GB

"
        "<code>vless://uuid@host:443?security=reality...</code>

"
        "<b>Как подключить:</b>
"
        "1. Скачайте V2RayNG (Android) или Streisand (iOS)
"
        "2. Отсканируйте QR или вставьте ссылку
"
        "3. Готово! 🚀"
    )


@dp.callback_query(F.data == "referral")
async def cb_referral(callback: CallbackQuery):
    await callback.message.edit_text(
        "🤝 <b>GUSTO Партнерка</b>

"
        "Приглашайте друзей и зарабатывайте!

"
        "<b>Уровни комиссии:</b>
"
        "• 🥇 1 уровень: <b>30%</b>
"
        "• 🥈 2 уровень: <b>15%</b>
"
        "• 🥉 3 уровень: <b>5%</b>

"
        "<b>Ваша ссылка:</b>
"
        "<code>https://t.me/gustovpn_bot?start=ref_abc123</code>

"
        "Минимум для вывода: 500₽"
    )


@dp.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery):
    await callback.message.edit_text(
        "❓ <b>GUSTO Support</b>

"
        "Если нужна помощь:
"
        "• Пишите: @gusto_support
"
        "• Или напишите сюда

"
        "<i>GUSTO — Быстрый. Безопасный. Без границ.</i>"
    )


@dp.callback_query(F.data == "main")
async def cb_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "🚀 <b>GUSTO VPN</b>

"
        "Выберите действие 👇",
        reply_markup=MAIN_KB
    )


async def main():
    logger.info("🚀 GUSTO Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
