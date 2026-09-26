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
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN missing! Railway Variables me BOT_TOKEN add karo."
    )

if not ADMIN_ID_RAW.isdigit():
    raise RuntimeError(
        "ADMIN_ID invalid! Railway Variables me numeric Telegram ID add karo."
    )

ADMIN_ID = int(ADMIN_ID_RAW)

DB_FILE = "name_drop.db"


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
        CREATE TABLE IF NOT EXISTS drops (
            chat_id INTEGER PRIMARY KEY,
            active INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def is_drop_active(chat_id):
    conn = sqlite3.connect(DB_FILE)

    row = conn.execute(
        "SELECT active FROM drops WHERE chat_id=?",
        (chat_id,)
    ).fetchone()

    conn.close()

    return bool(row and row[0] == 1)


def set_drop(chat_id, active):
    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        INSERT INTO drops(chat_id, active)
        VALUES (?, ?)
        ON CONFLICT(chat_id)
        DO UPDATE SET active=excluded.active
    """, (chat_id, int(active)))

    conn.commit()
    conn.close()


def add_name(chat_id, user_id, name):
    conn = sqlite3.connect(DB_FILE)

    try:
        conn.execute(
            "INSERT INTO names(chat_id,user_id,name) VALUES(?,?,?)",
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

    cursor = conn.execute(
        "UPDATE names SET name=? WHERE chat_id=? AND user_id=?",
        (name, chat_id, user_id)
    )

    conn.commit()
    result = cursor.rowcount > 0

    conn.close()

    return result


def get_names(chat_id):
    conn = sqlite3.connect(DB_FILE)

    rows = conn.execute(
        "SELECT user_id, name FROM names WHERE chat_id=? ORDER BY id",
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

def admin_panel():
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


def drop_button():
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
async def start_command(message: Message):

    if is_admin(message.from_user.id):

        await message.answer(
            "👑 <b>NAME DROP + POLL BOT</b>\n\n"
            "Bot successfully connected! ✅\n\n"
            "Group me bot add karo aur group me:\n"
            "<code>/panel</code>\n"
            "bhejo.",
            parse_mode="HTML"
        )

    else:

        await message.answer(
            "🤖 Bot active hai.\n\n"
            "Name Drop ke liye group me join karo."
        )


# =========================================================
# ADMIN PANEL
# =========================================================

@dp.message(Command("panel"))
async def panel_command(message: Message):

    if not is_admin(message.from_user.id):
        await message.answer("❌ Admin only.")
        return

    await message.answer(
        "👑 <b>NAME DROP CONTROL PANEL</b>\n\n"
        "Neeche se option choose karo 👇",
        reply_markup=admin_panel(),
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
        "🔥 <b>NAME DROP STARTED</b> 🔥\n\n"
        "Sab bande apna naam drop karo 👇\n\n"
        "Ek user sirf ek naam submit kar sakta hai.",
        reply_markup=drop_button(),
        parse_mode="HTML"
    )

    await callback.answer("Name Drop Started ✅")


# =========================================================
# STOP NAME DROP
# =========================================================

@dp.callback_query(F.data == "stop_drop")
async def stop_drop(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "❌ Admin only.",
            show_alert=True
        )
        return

    set_drop(callback.message.chat.id, False)

    await callback.message.answer(
        "🔴 <b>NAME DROP CLOSED</b> 🔒",
        parse_mode="HTML"
    )

    await callback.answer("Stopped")


# =========================================================
# USER NAME BUTTON
# =========================================================

@dp.callback_query(F.data == "drop_name")
async def drop_name(callback: CallbackQuery):

    chat_id = callback.message.chat.id

    if not is_drop_active(chat_id):
        await callback.answer(
            "❌ Name Drop abhi closed hai.",
            show_alert=True
        )
        return

    await callback.message.answer(
        "✍️ <b>Apna naam bhejo</b>\n\n"
        "Example:\n"
        "<code>Arjun</code>",
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
        await message.answer(
            "❌ Sirf text me naam bhejo."
        )
        return

    # Check that reply is to our bot's message
    try:
        me = await bot.me()

        if not message.reply_to_message.from_user:
            return

        if message.reply_to_message.from_user.id != me.id:
            return

    except Exception:
        return

    name = " ".join(message.text.strip().split())

    if not name:
        await message.answer(
            "❌ Valid naam bhejo."
        )
        return

    if len(name) > 100:
        await message.answer(
            "❌ Naam bahut bada hai. 100 characters ke andar rakho."
        )
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check whether user already submitted
    rows = get_names(chat_id)

    already_submitted = any(
        uid == user_id for uid, _ in rows
    )

    if already_submitted:

        update_name(
            chat_id,
            user_id,
            name
        )

        await message.answer(
            f"✅ Tumhara naam update ho gaya:\n\n"
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
            "📋 Abhi koi name nahi hai.",
            show_alert=True
        )

        return

    text = "📋 <b>NAME LIST</b>\n\n"

    for index, (_, name) in enumerate(rows, 1):

        text += f"{index}. {name}\n"

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
            "❌ Poll ke liye minimum 2 names chahiye.",
            show_alert=True
        )

        return

    # Remove duplicate names
    options = []
    seen = set()

    for _, name in rows:

        key = name.casefold()

        if key not in seen:

            seen.add(key)
            options.append(name)

    # Telegram poll max 10 options
    if len(options) > 10:

        await callback.answer(
            "❌ Maximum 10 poll options allowed hain.\n\n"
            f"Abhi {len(options)} unique names hain.",
            show_alert=True
        )

        return

    # Close Name Drop
    set_drop(chat_id, False)

    # Create Telegram Poll
    await callback.message.answer_poll(
        question="🔥 WHO IS THE BEST? 🔥",
        options=options,
        is_anonymous=False,
        allows_multiple_answers=False
    )

    await callback.message.answer(
        "✅ <b>POLL CREATED!</b>\n\n"
        "🗳️ Har user sirf ek option ko vote kar sakta hai.",
        parse_mode="HTML"
    )

    await callback.answer(
        "Poll Created ✅"
    )


# =========================================================
# CLEAR NAMES
# =========================================================

@dp.callback_query(F.data == "clear_names")
async def clear_names(callback: CallbackQuery):

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

    await callback.answer(
        "Cleared ✅"
    )


# =========================================================
# STATUS
# =========================================================

@dp.message(Command("status"))
async def status_command(message: Message):

    if not is_admin(message.from_user.id):
        return

    rows = get_names(message.chat.id)

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
