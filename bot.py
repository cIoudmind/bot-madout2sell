
import os
import asyncio
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


# ==============================
# НАСТРОЙКИ
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN or not ADMIN_ID:
    raise RuntimeError("Укажите BOT_TOKEN и ADMIN_ID")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())


# ==============================
# ТОВАРЫ
# ==============================

PRODUCTS = {
    "diamonds": {
        "name": "💎 Алмазы",
        "items": [
            ("160 алмазов", "99 ₽"),
            ("420 алмазов", "279 ₽"),
            ("880 алмазов", "565 ₽"),
            ("1840 алмазов", "1 099 ₽"),
            ("4800 алмазов", "2 499 ₽"),
            ("10 000 алмазов", "4 990 ₽"),
        ]
    },

    "coins": {
        "name": "🪙 Монеты",
        "items": [
            ("480 000 монет", "155 ₽"),
            ("1 200 000 монет", "355 ₽"),
            ("2 640 000 монет", "949 ₽"),
            ("7 700 000 монет", "2 499 ₽"),
            ("20 000 000 монет", "4 990 ₽"),
        ]
    },

    "pass": {
        "name": "🎟 Боевой пропуск",
        "items": [
            ("Элитный пропуск плюс", "990 ₽"),
        ]
    },

    "premium": {
        "name": "👑 Премиум",
        "items": [
            ("Премиум 7 дней", "129 ₽"),
            ("Премиум 30 дней", "565 ₽"),
            ("Премиум 90 дней", "1 199 ₽"),
        ]
    }
}


# ==============================
# СОСТОЯНИЯ
# ==============================

class Order(StatesGroup):
    waiting_game_id = State()


# ==============================
# КЛАВИАТУРЫ
# ==============================

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💎 Алмазы",
                callback_data="cat:diamonds"
            ),
            InlineKeyboardButton(
                text="🪙 Монеты",
                callback_data="cat:coins"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎟 Боевой пропуск",
                callback_data="cat:pass"
            ),
            InlineKeyboardButton(
                text="👑 Премиум",
                callback_data="cat:premium"
            )
        ]
    ])


def products_keyboard(category):
    items = PRODUCTS[category]["items"]
    keyboard = []

    for index, (name, price) in enumerate(items):
        keyboard.append([
            InlineKeyboardButton(
                text=f"{name} — {price}",
                callback_data=f"product:{category}:{index}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==============================
# СТАРТ
# ==============================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "🛒 <b>МАГАЗИН MADOUT2</b>\n\n"
        "Добро пожаловать!\n"
        "Выберите категорию товаров:",
        reply_markup=main_keyboard()
    )


# ==============================
# ВЫБОР КАТЕГОРИИ
# ==============================

@dp.callback_query(F.data.startswith("cat:"))
async def category(callback: CallbackQuery):
    category_id = callback.data.split(":")[1]

    if category_id not in PRODUCTS:
        await callback.answer("Категория не найдена")
        return

    await callback.message.edit_text(
        f"<b>{PRODUCTS[category_id]['name']}</b>\n\n"
        "Выберите нужный товар:",
        reply_markup=products_keyboard(category_id)
    )

    await callback.answer()


# ==============================
# НАЗАД В МЕНЮ
# ==============================

@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "🛒 <b>МАГАЗИН MADOUT2</b>\n\n"
        "Выберите категорию товаров:",
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ==============================
# ВЫБОР ТОВАРА
# ==============================

@dp.callback_query(F.data.startswith("product:"))
async def choose_product(
    callback: CallbackQuery,
    state: FSMContext
):
    _, category_id, index = callback.data.split(":")
    index = int(index)

    if category_id not in PRODUCTS:
        await callback.answer("Ошибка")
        return

    items = PRODUCTS[category_id]["items"]

    if index < 0 or index >= len(items):
        await callback.answer("Товар не найден")
        return

    name, price = items[index]

    await state.update_data(
        product=name,
        price=price,
        category=PRODUCTS[category_id]["name"]
    )

    await state.set_state(Order.waiting_game_id)

    await callback.message.edit_text(
        "✅ <b>Товар выбран!</b>\n\n"
        f"📦 Товар: {escape(name)}\n"
        f"💰 Цена: {escape(price)}\n\n"
        "🎮 Теперь отправьте ваш игровой ID MadOut2:"
    )

    await callback.answer()


# ==============================
# ПОЛУЧЕНИЕ ИГРОВОГО ID
# ==============================

@dp.message(Order.waiting_game_id)
async def receive_game_id(
    message: Message,
    state: FSMContext
):
    if not message.text:
        await message.answer("Отправьте игровой ID текстом.")
        return

    game_id = message.text.strip()

    if not 1 <= len(game_id) <= 64:
        await message.answer(
            "Некорректная длина ID. Попробуйте ещё раз."
        )
        return

    data = await state.get_data()

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "Не указан"
    )

    user_id = message.from_user.id

    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять заявку",
                    callback_data=f"approve:{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить заявку",
                    callback_data=f"reject:{user_id}"
                )
            ]
        ]
    )

    admin_text = (
        "📩 <b>НОВАЯ ЗАЯВКА MADOUT2</b>\n\n"
        f"📦 Категория: {escape(data['category'])}\n"
        f"🛍 Товар: {escape(data['product'])}\n"
        f"💰 Цена: {escape(data['price'])}\n\n"
        f"🎮 Игровой ID: <code>{escape(game_id)}</code>\n\n"
        "👤 <b>Покупатель:</b>\n"
        f"Имя: {escape(message.from_user.full_name)}\n"
        f"Username: {escape(username)}\n"
        f"Telegram ID: <code>{user_id}</code>"
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=admin_keyboard
        )
    except Exception:
        await message.answer(
            "Не удалось отправить заявку администратору. "
            "Попробуйте позже."
        )
        return

    await message.answer(
        "🎉 <b>Заявка успешно отправлена!</b>\n\n"
        f"📦 Товар: {escape(data['product'])}\n"
        f"💰 Цена: {escape(data['price'])}\n"
        f"🎮 Игровой ID: <code>{escape(game_id)}</code>\n\n"
        "Ожидайте ответа администратора."
    )

    await state.clear()


# ==============================
# АДМИН: ПРИНЯТЬ ЗАЯВКУ
# ==============================

@dp.callback_query(F.data.startswith("approve:"))
async def approve_order(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        f"✅ Заявка пользователя {user_id} принята."
    )

    try:
        await bot.send_message(
            user_id,
            "✅ <b>Ваша заявка принята!</b>\n\n"
            "Администратор подтвердил вашу заявку."
        )
    except Exception:
        pass

    await callback.answer("Заявка принята")


# ==============================
# АДМИН: ОТКЛОНИТЬ ЗАЯВКУ
# ==============================

@dp.callback_query(F.data.startswith("reject:"))
async def reject_order(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        f"❌ Заявка пользователя {user_id} отклонена."
    )

    try:
        await bot.send_message(
            user_id,
            "❌ <b>Ваша заявка отклонена.</b>\n\n"
            "Если у вас есть вопросы, обратитесь к администратору."
        )
    except Exception:
        pass

    await callback.answer("Заявка отклонена")


# ==============================
# ЗАПУСК
# ==============================

async def main():
    print("Бот MadOut2 запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
