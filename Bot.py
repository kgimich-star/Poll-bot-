import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# user_id -> submitted name
names = {}

waiting_for_name = set()


def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="➕ Start Name Drop",
                callback_data="start_drop"
            )],
            [InlineKeyboardButton(
                text="📋 Name List",
                callback_data="name_list"
            )],
            [InlineKeyboardButton(
                text="📊 Create Poll",
                callback_data="create_poll"
            )],
            [InlineKeyboardButton(
                text="🗑 Clear Names",
                callback_data="clear_names"
            )],
        ]
    )


@dp.message(Command("start"))
async def start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "👑 Admin Panel\n\nName Drop + Poll Bot",
            reply_markup=admin_keyboard()
        )
    else:
        await message.answer(
            "🔥 NAME DROP 🔥\n\n"
            "Apna naam submit karne ke liye button ka use karo.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="➕ Drop Your Name",
                        callback_data="drop_name"
                    )]
                ]
            )
        )


@dp.callback_query(F.data == "drop_name")
async def drop_name(callback: CallbackQuery):
    waiting_for_name.add(callback.from_user.id)

    await callback.message.answer(
        "✍️  naam bhej.\n\n"
        "Example: ᴳᵒᵈﾒRαϝƚααɾ"
    )

    await callback.answer()


@dp.message()
async def receive_name(message: Message):
    user_id = message.from_user.id

    if user_id not in waiting_for_name:
        return

    name = message.text.strip()

    if not name:
        await message.answer("❌ Valid naam bhejo.")
        return

    if len(name) > 50:
        await message.answer("❌ Naam 50 characters se chhota rakho.")
        return

    # Same user dobara naam submit nahi kar sakta
    if user_id in names:
        await message.answer(
            f"⚠️ Tumhara naam already submitted hai:\n\n"
            f"👤 {names[user_id]}"
        )
        waiting_for_name.discard(user_id)
        return

    names[user_id] = name
    waiting_for_name.discard(user_id)

    await message.answer(
        f"✅ Name submitted!\n\n"
        f"👤 {name}"
    )


@dp.callback_query(F.data == "start_drop")
async def start_drop(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    await callback.message.answer(
        "🔥 NAME DROP STARTED 🔥\n\n"
        "Sab apna naam drop karo gnduuu 👇",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="➕ Drop Your Name",
                    callback_data="drop_name"
                )]
            ]
        )
    )

    await callback.answer("Started")


@dp.callback_query(F.data == "name_list")
async def name_list(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    if not names:
        await callback.message.answer("📋 Abhi koi name submit nahi hua.")
        await callback.answer()
        return

    text = "📋 NAME LIST\n\n"

    for i, name in enumerate(names.values(), 1):
        text += f"{i}. {name}\n"

    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data == "create_poll")
async def create_poll(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    if not names:
        await callback.answer(
            "❌ Pehle names collect karo.",
            show_alert=True
        )
        return

    # Duplicate names remove, order preserve
    options = list(dict.fromkeys(names.values()))

    # Telegram polls have a limited number of options.
    if len(options) < 2:
        await callback.answer(
            "❌ Poll ke liye kam se kam 2 unique names chahiye.",
            show_alert=True
        )
        return

    if len(options) > 10:
        await callback.answer(
            "❌ Telegram poll mein maximum 10 options rakho.",
            show_alert=True
        )
        return

    await callback.message.answer_poll(
        question="🔥 KON WIN KAREGA PAII? 🔥",
        options=options,
        is_anonymous=False,
        allows_multiple_answers=False
    )

    await callback.answer("📊 Poll created!")


@dp.callback_query(F.data == "clear_names")
async def clear_names(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    names.clear()
    waiting_for_name.clear()

    await callback.message.answer("🗑 All submitted names cleared.")
    await callback.answer("Cleared")


async def main():
    print("🤖 Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
