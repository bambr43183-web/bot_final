```python
import asyncio
import os
import re
import sqlite3
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))  # чат адмінів
DB_NAME = "users.db"

bot = Bot(token=8404813322:AAHW1xd6eoo2SduUTAkYJ1dFaEFlXxxgiR0)
dp = Dispatcher()

# ================= БАЗА ДАНИХ =================
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER,
    name TEXT,
    age TEXT,
    birth TEXT,
    city TEXT,
    nickname TEXT,
    game_id TEXT,
    username TEXT,
    status TEXT
)
"""
)
conn.commit()

# ================= FSM =================
class Form(StatesGroup):
    name = State()
    age = State()
    birth = State()
    city = State()
    nickname = State()
    game_id = State()

# ================= START =================
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Привіт!\nНапиши /form щоб заповнити анкету.")

# ================= FORM =================
@dp.message(Command("form"))
async def form_start(message: Message, state: FSMContext):
    await message.answer("Введіть ім'я:")
    await state.set_state(Form.name)

@dp.message(Form.name)
async def get_name(message: Message, state: FSMContext):
    if not re.match(r"^[A-Za-zА-Яа-яЇїІіЄєҐґ\s-]+$", message.text):
        await message.answer("Тільки літери. Спробуйте ще раз:")
        return
    await state.update_data(name=message.text)
    await message.answer("Вік:")
    await state.set_state(Form.age)

@dp.message(Form.age)
async def get_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Вік має бути числом:")
        return
    await state.update_data(age=message.text)
    await message.answer("Дата народження (дд.мм.рррр):")
    await state.set_state(Form.birth)

@dp.message(Form.birth)
async def get_birth(message: Message, state: FSMContext):
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", message.text):
        await message.answer("Формат дд.мм.рррр")
        return
    await state.update_data(birth=message.text)
    await message.answer("Місто проживання:")
    await state.set_state(Form.city)

@dp.message(Form.city)
async def get_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Нік в грі:")
    await state.set_state(Form.nickname)

@dp.message(Form.nickname)
async def get_nickname(message: Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await message.answer("ID в грі:")
    await state.set_state(Form.game_id)

@dp.message(Form.game_id)
async def finish_form(message: Message, state: FSMContext):
    data = await state.get_data()
    username = message.from_user.username or "немає"

    cursor.execute(
        "INSERT INTO forms (tg_id, name, age, birth, city, nickname, game_id, username, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (message.from_user.id, data['name'], data['age'], data['birth'], data['city'], data['nickname'], message.text, username, "pending")
    )
    conn.commit()

    form_id = cursor.lastrowid

    text = (
        "📝 НОВА АНКЕТА\n\n"
        f"Імʼя: {data['name']}\n"
        f"Вік: {data['age']}\n"
        f"Дата народження: {data['birth']}\n"
        f"Місто: {data['city']}\n"
        f"Нік: {data['nickname']}\n"
        f"ID: {message.text}\n"
        f"Telegram: @{username}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Прийняти", callback_data=f"accept:{form_id}"),
            InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject:{form_id}")
        ]
    ])

    await bot.send_message(ADMIN_CHAT_ID, text, reply_markup=keyboard)
    await message.answer("Анкету надіслано. Очікуйте рішення адміністраторів ⏳")
    await state.clear()

# ================= CALLBACK =================
@dp.callback_query()
async def decision(callback: CallbackQuery):
    action, form_id = callback.data.split(":")

    cursor.execute("SELECT tg_id FROM forms WHERE id=?", (form_id,))
    user_id = cursor.fetchone()[0]

    if action == "accept":
        status = "accepted"
        await bot.send_message(user_id, "✅ Вітаємо! Вас ПРИЙНЯТО в клан!")
        await callback.message.edit_text(callback.message.text + "\n\n✅ Прийнято")
    else:
        status = "rejected"
        await bot.send_message(user_id, "❌ На жаль, вас ВІДХИЛЕНО.")
        await callback.message.edit_text(callback.message.text + "\n\n❌ Відхилено")

    cursor.execute("UPDATE forms SET status=? WHERE id=?", (status, form_id))
    conn.commit()
    await callback.answer()

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```



