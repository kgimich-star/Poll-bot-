import asyncio
import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ForceReply,
)
from aiogram.exceptions import TelegramUnauthorizedError


# =========================================================
# RAILWAY VARIABLES
# BOT_TOKEN = BotFather API token
# ADMIN_ID  = Your numeric Telegram ID
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_TEXT = os.getenv("ADMIN_ID", "").strip()

print("🚀 Starting Name Drop Bot...")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN Railway Variables me missing hai!")

if not ADMIN_ID_TEXT.isdigit():
    raise RuntimeError(
        "❌ ADMIN_ID Railway Variables me numeric Telegram ID honi chahiye!"
    )

ADMIN_ID = int(ADMIN_ID_TEXT)

print("✅ Railway variables loaded")


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# =========================================================
# BOT
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_FILE = "name_drop.db"


# =========================================================
# DATABASE
# =========================================================

def init_db():
    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS names (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(chat_id, user_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS drop_status (
            chat_id INTEGER PRIMARY KEY,
            active INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def set_drop(chat_id, active):
    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        INSERT INTO drop_status(chat_id, active)
        VALUES (?, ?)
        ON CONFLICT(chat_id)
        DO UPDATE SET active=excluded.active
    """, (chat_id, int(active)))

    conn.commit()
    conn.close()


def is_drop_active(chat_id):
    conn = sqlite3.connect(DB_FILE)

    row = conn.execute(
        "SELECT active FROM drop_status WHERE chat_id=?",
        (chat_id,)
    ).fetchone()

    conn.close()

    return bool(row and row[0] == 1)


def add_name(chat_id, user_id, name):
    conn = sqlite3.connect(DB_FILE)

    try:
        conn.execute(
            """
            INSERT INTO names(chat_id, user_id, name)
            VALUES (?, ?, ?)
            """,
            (chat_id, user_id, name)
        )

        conn.commit()
        result = True

    except sqlite3.IntegrityError:
        result = False

    conn.close()

    return result


def update_name(chat_id, user_id, name):
    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        UPDATE names
        SET name=?
        WHERE chat_id=? AND user_id=?
        """,
        (name, chat_id, user_id)
    )

    conn.commit()
    conn.close()


def get_names(chat_id):
    conn = sqlite3.connect(DB_FILE)

    rows = conn.execute(
        """
        SELECT user_id, name
        FROM names
        WHERE chat_id=?
        ORDER BY id
        """,
        (chat_id,)
    ).fetchall()

    conn.close()

    return rows


def clear_names(chat_id):
    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        "DELETE FROM names WHERE chat_id=?",
        (chat_id,)
    )

    conn.commit()
    conn.close()


# =========================================================
# KEYBOARDS
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🟢 Start Name Drop",
                    callback_data="start_drop"
                ),

                InlineKeyboardButton(
                    text="🔴 Stop",
                    callback_data="stop_drop"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📋 Name List",
                    callback_data="name_list"
                ),

                InlineKeyboardButton(
                    text="📊 Create Poll",
                    callback_data="create_poll"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🗑 Clear Names",
                    callback_data="clear_names"
                )
            ]

        ]
    )


def drop_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ DROP YOUR NAME",
                    callback_data="drop_name"
                )
            ]
        ]
    )


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


# =========================================================
# START
# =========================================================

@dp.message(Command("start"))
async def start(message: Message):

    if is_admin(message.from_user.id):

        await message.answer(
            "👑 <b>NAME DROP + POLL BOT</b>\n\n"
            "✅ Bot is working!\n\n"
            "Group me bot add karo.\n"
            "Phir group me <code>/panel</code> bhejo.",
            parse_mode="HTML"
        )

    else:

        await message.answer(
            "👋 Hello!\n\n"
            "Name Drop ke liye group me join karo."
        )


# =========================================================
# PANEL
# =========================================================

@dp.message(Command("panel"))
async def panel(message: Message):

    if not is_admin(message.from_user.id):

        await message.answer("❌ Admin only.")
        return

    await message.answer(
        "👑 <b>NAME DROP PANEL</b>\n\n"
        "Action select karo 👇",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# START NAME DROP
# =========================================================

@dp.callback_query(F.data == "start_drop")
async def start_drop(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "❌ Admin only.",
            show_alert=True
        )
        return

    chat_id = callback.message.chat.id

    set_drop(chat_id, True)

    await callback.message.answer(
        "🔥 <b>NAME DROP STARTED!</b> 🔥\n\n"
        "Sab bande neeche button dabakar apna naam drop karo 👇\n\n"
        "⚠️ Ek user = ek name",
        reply_markup=drop_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer("Started ✅")


# =========================================================
# STOP
# =========================================================

@dp.callback_query(F.data == "stop_drop")
async def stop_drop(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "❌ Admin only.",
            show_alert=True
        )
        return

    set_drop(
        callback.message.chat.id,
        False
    )

    await callback.message.answer(
        "🔴 <b>NAME DROP CLOSED</b>",
        parse_mode="HTML"
    )

    await callback.answer("Stopped")


# =========================================================
# DROP NAME BUTTON
# =========================================================

@dp.callback_query(F.data == "drop_name")
async def drop_name(callback: CallbackQuery):

    chat_id = callback.message.chat.id

    if not is_drop_active(chat_id):

        await callback.answer(
            "❌ Name Drop closed hai.",
            show_alert=True
        )
        return

    await callback.message.answer(
        "✍️ <b>Apna naam reply karke bhejo:</b>\n\n"
        "Example: <code>Arjun</code>",
        reply_markup=ForceReply(
            selective=True,
            input_field_placeholder="Apna naam..."
        ),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# RECEIVE NAME
# =========================================================

@dp.message(F.reply_to_message)
async def receive_name(message: Message):

    if not is_drop_active(message.chat.id):
        return

    if not message.text:
        return

    reply = message.reply_to_message

    if not reply or not reply.from_user:
        return

    try:

        me = await bot.get_me()

        if reply.from_user.id != me.id:
            return

    except Exception:

        return

    name = " ".join(
        message.text.strip().split()
    )

    if not name:
        return

    if len(name) > 100:

        await message.answer(
            "❌ Name 100 characters ke andar rakho."
        )

        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    rows = get_names(chat_id)

    already = any(
        uid == user_id
        for uid, _ in rows
    )

    if already:

        update_name(
            chat_id,
            user_id,
            name
        )

        await message.answer(
            f"✅ Naam update ho gaya:\n\n"
            f"👤 <b>{name}</b>",
            parse_mode="HTML"
        )

    else:

        add_name(
            chat_id,
            user_id,
            name
        )

        await message.answer(
            f"✅ <b>Name Added!</b>\n\n"
            f"👤 {name}",
            parse_mode="HTML"
        )


# =========================================================
# NAME LIST
# =========================================================

@dp.callback_query(F.data == "name_list")
async def name_list(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "❌ Admin only.",
            show_alert=True
        )

        return

    rows = get_names(
        callback.message.chat.id
    )

    if not rows:

        await callback.answer(
            "📋 Koi name nahi hai.",
            show_alert=True
        )

        return

    text = "📋 <b>NAME LIST</b>\n\n"

    for i, (_, name) in enumerate(rows, 1):

        text += f"{i}. {name}\n"

    text += f"\n👥 Total: {len(rows)}"

    await callback.message.answer(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# CREATE POLL
# =========================================================

@dp.callback_query(F.data == "create_poll")
async def create_poll(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "❌ Admin only.",
            show_alert=True
        )

        return

    chat_id = callback.message.chat.id

    rows = get_names(chat_id)

    if len(rows) < 2:

        await callback.answer(
            "❌ Minimum 2 names chahiye.",
            show_alert=True
        )

        return

    options = []
    seen = set()

    for _, name in rows:

        key = name.casefold()

        if key not in seen:

            seen.add(key)
            options.append(name)

    if len(options) > 10:

        await callback.answer(
            "❌ Telegram poll me maximum 10 options hain.",
            show_alert=True
        )

        return

    set_drop(chat_id, False)

    await callback.message.answer_poll(
        question="🔥 WHO IS THE BEST? 🔥",
        options=options,
        is_anonymous=False,
        allows_multiple_answers=False
    )

    await callback.message.answer(
        "✅ <b>POLL CREATED!</b>\n\n"
        "🗳️ Har user sirf ek vote de sakta hai.",
        parse_mode="HTML"
    )

    await callback.answer("Poll Created ✅")


# =========================================================
# CLEAR NAMES
# =========================================================

@dp.callback_query(F.data == "clear_names")
async def clear_names_callback(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "❌ Admin only.",
            show_alert=True
        )

        return

    clear_names(
        callback.message.chat.id
    )

    await callback.message.answer(
        "🗑 <b>All names cleared!</b>",
        parse_mode="HTML"
    )

    await callback.answer("Cleared ✅")


# =========================================================
# STATUS
# =========================================================

@dp.message(Command("status"))
async def status(message: Message):

    if not is_admin(message.from_user.id):
        return

    rows = get_names(
        message.chat.id
    )

    active = is_drop_active(
        message.chat.id
    )

    state = "🟢 OPEN" if active else "🔴 CLOSED"

    await message.answer(
        f"📊 <b>STATUS</b>\n\n"
        f"Name Drop: {state}\n"
        f"👥 Names: {len(rows)}",
        parse_mode="HTML"
    )


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def help_command(message: Message):

    await message.answer(
        "🤖 <b>Name Drop + Poll Bot</b>\n\n"
        "/panel — Admin Panel\n"
        "/status — Status\n"
        "/help — Help",
        parse_mode="HTML"
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    init_db()

    print("🔍 Checking Telegram connection...")

    try:

        me = await bot.get_me()

        print(
            f"✅ BOT CONNECTED: @{me.username}"
        )

        print(
            f"🆔 BOT ID: {me.id}"
        )

    except TelegramUnauthorizedError:

        print("❌ BOT TOKEN INVALID!")

        raise

    # IMPORTANT:
    # Remove old webhook before polling
    print("🧹 Removing old webhook...")

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    print("✅ Webhook removed")

    print(
        "🚀 BOT IS RUNNING..."
    )

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    asyncio.run(main())
