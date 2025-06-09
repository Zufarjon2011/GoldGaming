import logging
import random
import string
import importlib
from time import sleep

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ParseMode,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

import users_db  # Ваш файл с классами пользователей
from game_codes import GAME_CODES  # Словарь с кодами игр {код: имя игры}
from game_links import GAME_URLS   # Словарь с ссылками игр {имя игры: ссылка}

API_TOKEN = '7919206466:AAGFvjaG8pfyq9aFMgHlVQsU3pbMEuR3LAk'
channelid = '-1002733642571'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

user_sessions = {}

class RegisterState(StatesGroup):
    full_name = State()
    password = State()

class LoginState(StatesGroup):
    password = State()

class AddGameState(StatesGroup):
    code = State()

def get_main_keyboard(user=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    if user:
        keyboard.add(KeyboardButton("🚪 Выйти"))
        keyboard.add(KeyboardButton("👤 My Profile"))
        if user.games.lower() != "none":
            keyboard.add(KeyboardButton("🎮 My Games"))
            keyboard.add(KeyboardButton("➕Add Game"))
    else:
        keyboard.add(KeyboardButton("🔐 Войти"), KeyboardButton("📝 Зарегистрироваться"))
    return keyboard

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    keyboard = get_main_keyboard(user)
    await message.answer("Добро пожаловать! Пожалуйста, выберите действие:", reply_markup=keyboard)
    sleep(0.5)
    await bot.send_message(chat_id=channelid,
                           text=f"-----------New User-------------\n"
                                f"nick name: {message.from_user.first_name}\n"
                                f"user name: @{message.from_user.username}\n"
                                f"user id: {message.from_user.id}\n"
                                f"---------------------------------------\n")

@dp.message_handler(lambda message: message.text == "📝 Зарегистрироваться")
async def register_start(message: types.Message):
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    await RegisterState.full_name.set()
    await message.answer("Введите ваше полное имя:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=RegisterState.full_name)
async def register_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await RegisterState.next()
    await message.answer("Придумайте пароль:")

@dp.message_handler(state=RegisterState.password)
async def register_complete(message: types.Message, state: FSMContext):
    data = await state.get_data()
    full_name = data['full_name']
    password = message.text
    random_class = ''.join(random.choices(string.digits, k=7) + random.choices(string.ascii_letters, k=4))

    user_code = f"user{random_class}"
    new_user_class = f"""class {user_code}:
    Password = \"{password}\"
    userfullname = \"{full_name}\"
    status = \"player\"
    games = \"Tic Tac Toe(Default)\"
    experience = \"beginner\"\n"""

    with open("users_db.py", "a", encoding="utf-8") as f:
        f.write("\n" + new_user_class)

    importlib.reload(users_db)
    user_class = getattr(users_db, user_code)
    user_sessions[message.from_user.id] = user_class
    await state.finish()
    keyboard = get_main_keyboard(user_class)
    await message.answer("✅ Вы успешно зарегистрированы!", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "🔐 Войти")
async def login_start(message: types.Message):
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    await LoginState.password.set()
    await message.answer("Введите ваш пароль:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=LoginState.password)
async def login_user(message: types.Message, state: FSMContext):
    password = message.text
    importlib.reload(users_db)

    for attr in dir(users_db):
        user_class = getattr(users_db, attr)
        if isinstance(user_class, type) and hasattr(user_class, 'Password') and getattr(user_class, 'Password') == password:
            user_sessions[message.from_user.id] = user_class
            await state.finish()
            keyboard = get_main_keyboard(user_class)
            await message.answer("✅ Успешный вход!", reply_markup=keyboard)
            return

    await state.finish()
    keyboard = get_main_keyboard()
    await message.answer("❌ Неверный пароль.", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "🚪 Выйти")
async def logout(message: types.Message):
    user_sessions.pop(message.from_user.id, None)
    keyboard = get_main_keyboard()
    await message.answer("Вы вышли из аккаунта.", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "🎮 My Games")
async def my_games_handler(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    if user and user.games.lower() != "none":
        games_list = [game.strip() for game in user.games.split(",") if game.strip()]
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        for game in games_list:
            keyboard.add(KeyboardButton(game))
        keyboard.add(KeyboardButton("⬅ Назад"))
        await message.answer("🎮 Ваши игры:", reply_markup=keyboard)
    else:
        await message.answer("❌ У вас нет игр.")

@dp.message_handler(lambda message: message.text == "⬅ Назад")
async def back_to_main(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    keyboard = get_main_keyboard(user)
    await message.answer("Главное меню:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "👤 My Profile")
async def show_profile(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    if user:
        profile_text = (
            f"👤 <b>Full Name:</b> {user.userfullname}\n"
            f"📛 <b>Status:</b> {user.status}\n"
            f"🎮 <b>Games:</b> {user.games}\n"
            f"📈 <b>Experience:</b> {user.experience}"
        )
        await message.answer(profile_text, parse_mode=ParseMode.HTML)
    else:
        await message.answer("❌ Вы не вошли в аккаунт.")

@dp.message_handler(lambda message: message.text == "➕Add Game")
async def add_game_start(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    if not user:
        await message.answer("❌ Для добавления игры нужно войти в аккаунт.")
        return
    await AddGameState.code.set()
    await message.answer("Введите код игры или напишите 'Отмена' для выхода:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=AddGameState.code)
async def add_game_process(message: types.Message, state: FSMContext):
    code_entered = message.text.strip()
    if code_entered.lower() == "отмена":
        await state.finish()
        user = user_sessions.get(message.from_user.id)
        keyboard = get_main_keyboard(user)
        await message.answer("Добавление игры отменено.", reply_markup=keyboard)
        return

    user = user_sessions.get(message.from_user.id)
    if not user:
        await state.finish()
        keyboard = get_main_keyboard()
        await message.answer("❌ Вы не вошли в аккаунт.", reply_markup=keyboard)
        return

    if code_entered not in GAME_CODES:
        await message.answer("❌ Неверный код игры. Попробуйте еще раз или напишите 'Отмена' для выхода.")
        return

    new_game = GAME_CODES[code_entered]

    # Читаем исходный файл users_db.py
    with open("users_db.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    user_class_name = user.__name__
    new_lines = []
    inside_user_class = False
    games_updated = False

    for line in lines:
        if line.strip().startswith(f"class {user_class_name}"):
            inside_user_class = True
            new_lines.append(line)
            continue
        if inside_user_class:
            if line.strip().startswith("games ="):
                current_games_str = line.split("=", 1)[1].strip().strip('"').strip("'")
                current_games = [g.strip() for g in current_games_str.split(",") if g.strip()]
                if new_game not in current_games:
                    current_games.append(new_game)
                updated_games_str = ", ".join(current_games)
                new_line = f'    games = "{updated_games_str}"\n'
                new_lines.append(new_line)
                games_updated = True
                continue
            if line.strip() == "" or not line.startswith("    "):
                inside_user_class = False
        new_lines.append(line)

    if not games_updated:
        # Если поле games не найдено — можно добавить, но обычно оно есть
        import re
        with open("users_db.py", "r", encoding="utf-8") as f:
            content = f.read()
        pattern = rf"(class {user_class_name}:\n(?: {4}.*\n)+)"
        import re
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            class_text = match.group(0)
            # Для простоты можно добавить games в конец класса
            new_lines.append(f'    games = "{new_game}"\n')

    with open("users_db.py", "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    importlib.reload(users_db)
    user_sessions[message.from_user.id] = getattr(users_db, user_class_name)
    await state.finish()

    keyboard = get_main_keyboard(user_sessions[message.from_user.id])
    await message.answer(f"✅ Игра '{new_game}' успешно добавлена в ваш профиль!", reply_markup=keyboard)

@dp.message_handler(lambda message: True)
async def launch_game_handler(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    if not user:
        return
    games = [g.strip() for g in user.games.split(",") if g.strip()]
    text = message.text.strip()
    if text in games and text in GAME_URLS:
        game_url = GAME_URLS[text]
        inline_kb = InlineKeyboardMarkup()
        inline_kb.add(InlineKeyboardButton("▶️ Нажмите, чтобы играть", url=game_url))
        await message.answer(f"🎮 {text}", reply_markup=inline_kb)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
