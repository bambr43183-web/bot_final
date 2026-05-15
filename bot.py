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
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Можно вставить токен прямо в кавычках
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 123456789))  # замените на свой id
DB_NAME = "users.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot=bot)

# ================= БАЗА ДАННЫХ =================
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
    clan TEXT,
    username TEXT,
    status TEXT
)
""")
conn.commit()

# ================= FSM =================
class Form(StatesGroup):
    name = State()
    age = State()
    birth = State()
    city = State()
    nickname = State()
    game_id = State()
    clan = State()

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
    await message.answer("Ваше ігрове ID:")
    await state.set_state(Form.game_id)

# ================= ВИБІР КЛАНУ =================
@dp.message(Form.game_id)
async def get_game_id(message: Message, state: FSMContext):
    await state.update_data(game_id=message.text)

    text = (
        "В який саме клан Ви бажаєте вступити?\n"
        "Ознайомтесь з вимогами до кожного клану:\n\n"

        "『HH』Academy (13+)\n"
        "K/D:\n"
        "- Для хлопців: 4+ на 100 матчів\n"
        "- Для дівчат: 3+ на 100 матчів\n\n"

        "『HH』Team (18+)\n"
        "K/D:\n"
        "- Для хлопців: 6+ на 100матчів\n"
        "- Для дівчат: 4.5+ на 100матчів\n\n"

        "『HH』ЕSportsTeam (16+)\n"
        "K/D:\n"
        "Для дівчат: Classic Game - 8+ | Ultimate Royale - 1.4+\n"
        "Для хлопців: Classic Game 10+ | Ultimate Royale -1.5+\n\n"

        "⬇️ Оберіть клан:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Аcademy (13+)", callback_data="clan:Академ")],
        [InlineKeyboardButton(text="2️⃣ Основний (18+)", callback_data="clan:Основний (18+)")],
        [InlineKeyboardButton(text="4️⃣ ESport`s Team (16+)", callback_data="clan:ESports")]
    ])

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(Form.clan)

# ================= ОБРОБКА ВИБОРУ =================
@dp.callback_query(Form.clan)
async def choose_clan(callback: CallbackQuery, state: FSMContext):
    clan_name = callback.data.split(":")[1]
    await state.update_data(clan=clan_name)

    # Якщо ESports — одразу повідомлення про перевірку
    if clan_name == "ESports":
        await callback.message.answer(
            "Запрошуємо Вас на перевірку!\n\n"
            "Для того, щоб узгодити дату та час перевірки зв'яжіться з "
            "Лідером Клану ESports @WAZOVSKIJ, "
            "або його заступником (перевіряючим) @zeVS_045"
        )

    data = await state.get_data()
    username = callback.from_user.username or "немає"

    cursor.execute(
        "INSERT INTO forms (tg_id, name, age, birth, city, nickname, game_id, clan, username, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (callback.from_user.id, data['name'], data['age'], data['birth'],
         data['city'], data['nickname'], data['game_id'],
         clan_name, username, "pending")
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
        f"ID: {data['game_id']}\n"
        f"Клан: {clan_name}\n"
        f"Telegram: @{username}"
    )

    keyboard_admin = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Прийняти", callback_data=f"accept:{form_id}"),
        InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject:{form_id}")
    ]])

    await bot.send_message(ADMIN_CHAT_ID, text, reply_markup=keyboard_admin)
    await callback.message.answer("Анкету надіслано. Очікуйте рішення адміністраторів ⏳")
    await state.clear()
    await callback.answer()

# ================= CALLBACK (РІШЕННЯ) =================
@dp.callback_query()
async def decision(callback: CallbackQuery):
    action, form_id = callback.data.split(":")
    cursor.execute("SELECT tg_id, nickname, game_id, clan FROM forms WHERE id=?", (form_id,))
    result = cursor.fetchone()

    if not result:
        await callback.answer("Анкета не знайдена!", show_alert=True)
        return

    user_id, nickname, game_id, clan = result

    # ===== ХТО НАТИСНУВ КНОПКУ =====
    admin_username = callback.from_user.username
    admin_fullname = callback.from_user.full_name

    if admin_username:
        admin_text = f"@{admin_username}"
    else:
        admin_text = admin_fullname

    if action == "accept":
        status = "accepted"

        await bot.send_message(user_id, "✅ Вітаємо! Вас ПРИЙНЯТО в клан!")

        instruction_text = (
            "📌 Одразу після входу в чат ти зобовʼязаний додати:\n"
            f"1️⃣ Своє ігрове ID: {game_id}\n"
            "2️⃣ Нік — окреме повідомлення\n\n"
            "Окремо в чаті:\n"
            "+ник (свій нік)\n"
            "+звание (свій ID)"
        )

        # ===== КНОПКИ ДЛЯ КОЖНОГО КЛАНУ =====
        if clan == "Академ":
            keyboard_chat = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Чат Академ", url="https://t.me/+w7gOGc5vXL83M2Ey")],
                [InlineKeyboardButton(text="Спільний чат", url="https://t.me/+0aldXdWy3EZiMWEy")]
            ])

        elif clan == "Основний (18+)":
            keyboard_chat = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Чат Основний (18+)", url="https://t.me/+ED7Kh0C57QgzMzhi")],
                [InlineKeyboardButton(text="Спільний чат", url="https://t.me/+0aldXdWy3EZiMWEy")]
            ])
    
        elif clan == "ESports":
            keyboard_chat = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Чат ESports", url="https://t.me/+5cPx8LzQLhsxYzEy")],
                [InlineKeyboardButton(text="Спільний чат", url="https://t.me/+0aldXdWy3EZiMWEy")]
            ])

        await bot.send_message(user_id, instruction_text, reply_markup=keyboard_chat)

        # ===== ОНОВЛЮЄМО ПОВІДОМЛЕННЯ В АДМІН-ЧАТІ =====
        await callback.message.edit_text(
            callback.message.text + f"\n\n✅ Прийнято адміністратором {admin_text}"
        )

    else:
        status = "rejected"

        await bot.send_message(user_id, "❌ На жаль, вас ВІДХИЛЕНО.")

        await callback.message.edit_text(
            callback.message.text + f"\n\n❌ Відхилено адміністратором {admin_text}"
        )

    cursor.execute("UPDATE forms SET status=? WHERE id=?", (status, form_id))
    conn.commit()
    await callback.answer()

# ================= RUN =================
async def main():
    print("Бот запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())











