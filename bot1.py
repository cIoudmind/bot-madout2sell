
import os
import asyncio
import aiosqlite

from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


# =====================================
# НАСТРОЙКИ
# =====================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB_NAME = "madout.db"

if not BOT_TOKEN or not ADMIN_ID:
    raise RuntimeError("Не указаны BOT_TOKEN или ADMIN_ID")


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())


# =====================================
# ТОВАРЫ
# =====================================

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


# =====================================
# СОСТОЯНИЯ
# =====================================

class Order(StatesGroup):
    waiting_game_id = State()


# =====================================
# SQLITE: СОЗДАНИЕ БАЗЫ
# =====================================

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                category TEXT NOT NULL,
                product TEXT NOT NULL,
                price TEXT NOT NULL,
                game_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_user
            ON orders(user_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_status
            ON orders(status)
        """)

        await db.commit()

    print("SQLite база данных подключена!")
    print("Файл базы:", os.path.abspath(DB_NAME))


# =====================================
# КЛАВИАТУРЫ
# =====================================

def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
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
            ],
            [
                InlineKeyboardButton(
                    text="📦 Мои заявки",
                    callback_data="myorders"
                )
            ]
        ]
    )


def products_keyboard(category):
    keyboard = []

    for index, (name, price) in enumerate(
        PRODUCTS[category]["items"]
    ):
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


def admin_keyboard(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"approve:{order_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject:{order_id}"
                )
            ]
        ]
    )


# =====================================
# СТАРТ
# =====================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "🛒 <b>MADOUT2 SHOP</b>\n\n"
        "Добро пожаловать в магазин!\n\n"
        "Выберите нужную категорию:",
        reply_markup=main_keyboard()
    )


# =====================================
# ПРОВЕРКА ID
# =====================================

@dp.message(Command("id"))
async def show_id(message: Message):
    await message.answer(
        f"Ваш Telegram ID:\n"
        f"<code>{message.from_user.id}</code>"
    )


# =====================================
# ВЫБОР КАТЕГОРИИ
# =====================================

@dp.callback_query(F.data.startswith("cat:"))
async def category(callback: CallbackQuery):
    category_id = callback.data.split(":")[1]

    if category_id not in PRODUCTS:
        await callback.answer("Категория не найдена")
        return

    await callback.message.edit_text(
        f"<b>{PRODUCTS[category_id]['name']}</b>\n\n"
        "Выберите товар:",
        reply_markup=products_keyboard(category_id)
    )

    await callback.answer()


# =====================================
# НАЗАД
# =====================================

@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "🛒 <b>MADOUT2 SHOP</b>\n\n"
        "Выберите категорию:",
        reply_markup=main_keyboard()
    )

    await callback.answer()


# =====================================
# ВЫБОР ТОВАРА
# =====================================

@dp.callback_query(F.data.startswith("product:"))
async def choose_product(
    callback: CallbackQuery,
    state: FSMContext
):
    try:
        _, category_id, index = callback.data.split(":")
        index = int(index)

        if category_id not in PRODUCTS:
            raise ValueError

        items = PRODUCTS[category_id]["items"]

        if index < 0 or index >= len(items):
            raise ValueError

    except ValueError:
        await callback.answer("Товар не найден", show_alert=True)
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
        "🎮 Отправьте свой игровой ID MadOut2:"
    )

    await callback.answer()


# =====================================
# СОЗДАНИЕ ЗАЯВКИ В SQLITE
# =====================================

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
        await message.answer("Проверьте игровой ID и отправьте снова.")
        return

    data = await state.get_data()

    username = message.from_user.username or "Не указан"
    full_name = message.from_user.full_name
    user_id = message.from_user.id

    # Сохраняем заявку в SQLite

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            INSERT INTO orders (
                user_id,
                username,
                full_name,
                category,
                product,
                price,
                game_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            username,
            full_name,
            data["category"],
            data["product"],
            data["price"],
            game_id
        ))

        order_id = cursor.lastrowid
        await db.commit()

    # Отправляем заявку администратору

    admin_text = (
        "📩 <b>НОВАЯ ЗАЯВКА MADOUT2</b>\n\n"
        f"🆔 Номер заявки: <code>#{order_id}</code>\n\n"
        f"📂 Категория: {escape(data['category'])}\n"
        f"📦 Товар: {escape(data['product'])}\n"
        f"💰 Цена: {escape(data['price'])}\n\n"
        f"🎮 Игровой ID: <code>{escape(game_id)}</code>\n\n"
        "👤 <b>Покупатель:</b>\n"
        f"Имя: {escape(full_name)}\n"
        f"Username: @{escape(username)}\n"
        f"Telegram ID: <code>{user_id}</code>\n\n"
        "⏳ Статус: Ожидает рассмотрения"
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=admin_keyboard(order_id)
        )

    except Exception as e:
        print("Ошибка отправки админу:", e)

        await message.answer(
            f"⚠️ Заявка #{order_id} сохранена в базе, "
            "но не удалось уведомить администратора. "
            "Свяжитесь с поддержкой."
        )

        await state.clear()
        return

    await message.answer(
        "🎉 <b>Заявка успешно создана!</b>\n\n"
        f"🆔 Номер: <code>#{order_id}</code>\n"
        f"📦 Товар: {escape(data['product'])}\n"
        f"💰 Цена: {escape(data['price'])}\n"
        f"🎮 Игровой ID: <code>{escape(game_id)}</code>\n\n"
        "⏳ Ожидайте ответа администратора.",
        reply_markup=main_keyboard()
    )

    await state.clear()


# =====================================
# МОИ ЗАЯВКИ
# =====================================

@dp.message(Command("myorders"))
async def my_orders_command(message: Message):
    await show_orders(message.from_user.id, message)


@dp.callback_query(F.data == "myorders")
async def my_orders_callback(callback: CallbackQuery):
    await show_orders(callback.from_user.id, callback.message)
    await callback.answer()


async def show_orders(user_id, message):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT id, product, price, status, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (user_id,))

        orders = await cursor.fetchall()

    if not orders:
        await message.answer("📦 У вас пока нет заявок.")
        return

    status_names = {
        "pending": "⏳ Ожидает",
        "accepted": "✅ Принята",
        "rejected": "❌ Отклонена"
    }

    text = "📦 <b>ВАШИ ПОСЛЕДНИЕ ЗАЯВКИ</b>\n\n"

    for order in orders:
        order_id, product, price, status, created_at = order

        text += (
            f"🆔 Заявка #{order_id}\n"
            f"📦 {escape(product)}\n"
            f"💰 {escape(price)}\n"
            f"📌 {status_names.get(status, status)}\n"
            f"🕒 {created_at}\n\n"
        )

    await message.answer(text)


# =====================================
# АДМИН: СТАТИСТИКА
# =====================================

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа!")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT
                COUNT(*),
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END)
            FROM orders
        """)

        total, pending, accepted, rejected = await cursor.fetchone()

    total = total or 0
    pending = pending or 0
    accepted = accepted or 0
    rejected = rejected or 0

    await message.answer(
        "⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"📦 Всего заявок: {total}\n"
        f"⏳ Ожидают: {pending}\n"
        f"✅ Приняты: {accepted}\n"
        f"❌ Отклонены: {rejected}\n\n"
        f"👑 Ваш ID: <code>{message.from_user.id}</code>"
    )


# =====================================
# ОБРАБОТКА РЕШЕНИЯ АДМИНА
# =====================================

async def process_order(
    callback: CallbackQuery,
    new_status: str
):
    # Проверяем администратора

    print("ID нажавшего:", callback.from_user.id)
    print("ID администратора:", ADMIN_ID)

    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа!", show_alert=True)
        return

    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный номер заявки")
        return

    # Меняем статус только если заявка ожидает решения

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            UPDATE orders
            SET status = ?
            WHERE id = ? AND status = 'pending'
        """, (new_status, order_id))

        await db.commit()

        if cursor.rowcount == 0:
            await callback.answer(
                "Заявка уже обработана или не найдена.",
                show_alert=True
            )
            return

        cursor = await db.execute("""
            SELECT user_id, product, price
            FROM orders
            WHERE id = ?
        """, (order_id,))

        order = await cursor.fetchone()

    if not order:
        await callback.answer("Заявка не найдена")
        return

    user_id, product, price = order

    if new_status == "accepted":
        status_text = "✅ ПРИНЯТА"

        user_text = (
            f"✅ <b>Ваша заявка #{order_id} принята!</b>\n\n"
            f"📦 Товар: {escape(product)}\n"
            f"💰 Цена: {escape(price)}\n\n"
            "Администратор подтвердил вашу заявку."
        )

    else:
        status_text = "❌ ОТКЛОНЕНА"

        user_text = (
            f"❌ <b>Ваша заявка #{order_id} отклонена.</b>\n\n"
            "Если у вас есть вопросы, обратитесь к администратору."
        )

    # Убираем кнопки с заявки

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"Заявка #{order_id}: {status_text}"
    )

    # Уведомляем покупателя

    try:
        await bot.send_message(user_id, user_text)
    except Exception as e:
        print("Не удалось уведомить пользователя:", e)

    await callback.answer("Статус заявки обновлён")


@dp.callback_query(F.data.startswith("approve:"))
async def approve_order(callback: CallbackQuery):
    await process_order(callback, "accepted")


@dp.callback_query(F.data.startswith("reject:"))
async def reject_order(callback: CallbackQuery):
    await process_order(callback, "rejected")


# =====================================
# ЗАПУСК
# =====================================

async def main():
    await init_db()

    print("================================")
    print("MADOUT2 SHOP ЗАПУЩЕН")
    print("ADMIN_ID:", ADMIN_ID)
    print("================================")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
