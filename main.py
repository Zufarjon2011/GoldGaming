import logging
import random
import string
import importlib
import json
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

import users_db
from game_codes import GAME_CODES
from game_links import GAME_URLS

API_TOKEN = '7919206466:AAGFvjaG8pfyq9aFMgHlVQsU3pbMEuR3LAk'
channelid = '-1002733642571'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

user_sessions = {}
HISTORY_FILE = 'gift_history.json'

def load_gift_history():
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_gift_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

gift_history = load_gift_history()

class RegisterState(StatesGroup):
    full_name = State()
    password = State()

class LoginState(StatesGroup):
    password = State()

class AddGameState(StatesGroup):
    code = State()

class GiftGameState(StatesGroup):
    game = State()
    recipient = State()

def get_main_keyboard(user=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    if user:
        keyboard.add(KeyboardButton("🚪 Выйти"))
        keyboard.add(KeyboardButton("👤 My Profile"))
        if user.games.lower() != "none":
            keyboard.add(KeyboardButton("🎮 My Games"))
            keyboard.add(KeyboardButton("➕Add Game"))
            keyboard.add(KeyboardButton("🎁 Подарить игру"))
        keyboard.add(KeyboardButton("📜 История Подарков"))
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

@dp.message_handler(lambda msg: msg.text == "📝 Зарегистрироваться")
async def register_start(message: types.Message):
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
    Password = "{password}"
    userfullname = "{full_name}"
    status = "player"
    games = "Tic Tac Toe(Default)"
    experience = "beginner"\n"""

    with open("users_db.py", "a", encoding="utf-8") as f:
        f.write("\n" + new_user_class)

    importlib.reload(users_db)
    user_class = getattr(users_db, user_code)
    user_sessions[message.from_user.id] = user_class
    await state.finish()
    await message.answer("✅ Вы успешно зарегистрированы!", reply_markup=get_main_keyboard(user_class))

@dp.message_handler(lambda msg: msg.text == "🔐 Войти")
async def login_start(message: types.Message):
    await LoginState.password.set()
    await message.answer("Введите ваш пароль:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=LoginState.password)
async def login_user(message: types.Message, state: FSMContext):
    password = message.text
    importlib.reload(users_db)
    for attr in dir(users_db):
        user_class = getattr(users_db, attr)
        if isinstance(user_class, type) and hasattr(user_class, 'Password') and user_class.Password == password:
            user_sessions[message.from_user.id] = user_class
            await state.finish()
            await message.answer("✅ Успешный вход!", reply_markup=get_main_keyboard(user_class))
            return
    await state.finish()
    await message.answer("❌ Неверный пароль.", reply_markup=get_main_keyboard())

@dp.message_handler(lambda msg: msg.text == "🚪 Выйти")
async def logout(message: types.Message):
    user_sessions.pop(message.from_user.id, None)
    await message.answer("Вы вышли из аккаунта.", reply_markup=get_main_keyboard())

@dp.message_handler(lambda msg: msg.text == "🎮 My Games")
async def my_games_handler(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    if user and user.games.lower() != "none":
        games_list = [g.strip() for g in user.games.split(",") if g.strip()]
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        for game in games_list:
            keyboard.add(KeyboardButton(game))
        keyboard.add(KeyboardButton("⬅ Назад"))
        await message.answer("🎮 Ваши игры:", reply_markup=keyboard)
    else:
        await message.answer("❌ У вас нет игр.")

@dp.message_handler(lambda msg: msg.text == "⬅ Назад")
async def back_to_main(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    await message.answer("Главное меню:", reply_markup=get_main_keyboard(user))

@dp.message_handler(lambda msg: msg.text == "👤 My Profile")
async def show_profile(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    if user:
        await message.answer(
            f"👤 <b>Full Name:</b> {user.userfullname}\n"
            f"🆔 <b>ID:</b> <code>{user.__name__}</code>\n"
            f"📛 <b>Status:</b> {user.status}\n"
            f"🎮 <b>Games:</b> {user.games}\n"
            f"📈 <b>Experience:</b> {user.experience}\n\n"
            f"❗Contact @zufar_BRO for purchasing games!",
            parse_mode=ParseMode.HTML
        )

@dp.message_handler(lambda msg: msg.text == "➕Add Game")
async def add_game_start(message: types.Message):
    await AddGameState.code.set()
    await message.answer("Введите код игры или напишите 'Отмена':", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=AddGameState.code)
async def add_game_process(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if code.lower() == "отмена":
        await state.finish()
        return await message.answer("Добавление отменено.", reply_markup=get_main_keyboard(user_sessions.get(message.from_user.id)))

    user = user_sessions.get(message.from_user.id)
    if code not in GAME_CODES:
        return await message.answer("❌ Неверный код. Попробуйте снова или напишите 'Отмена'.")

    new_game = GAME_CODES[code]
    user_class_name = user.__name__

    with open("users_db.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    inside_class = False
    for line in lines:
        if line.strip().startswith(f"class {user_class_name}"):
            inside_class = True
        if inside_class and line.strip().startswith("games ="):
            current_games = line.split("=", 1)[1].strip().strip('"')
            games = [g.strip() for g in current_games.split(",")]
            if new_game not in games:
                games.append(new_game)
            line = f'    games = "{", ".join(games)}"\n'
            inside_class = False
        new_lines.append(line)

    with open("users_db.py", "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    importlib.reload(users_db)
    user_sessions[message.from_user.id] = getattr(users_db, user_class_name)
    await state.finish()
    await message.answer(f"✅ Игра <code>{new_game}</code> добавлена!", reply_markup=get_main_keyboard(user_sessions[message.from_user.id]))

@dp.message_handler(lambda msg: msg.text == "🎁 Подарить игру")
async def gift_game_start(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    games = [g.strip() for g in user.games.split(",") if g.strip()]
    if not games:
        return await message.answer("❌ У вас нет игр для подарка.")
    await GiftGameState.game.set()
    await message.answer("Введите название игры, которую хотите подарить, или 'Отмена':")

@dp.message_handler(state=GiftGameState.game)
async def gift_game_name(message: types.Message, state: FSMContext):
    game = message.text.strip()
    if game.lower() == "отмена":
        await state.finish()
        return await message.answer("Операция отменена.", reply_markup=get_main_keyboard(user_sessions.get(message.from_user.id)))

    user = user_sessions.get(message.from_user.id)
    if game not in [g.strip() for g in user.games.split(",")]:
        return await message.answer("❌ У вас нет такой игры. Попробуйте снова или 'Отмена'.")
    await state.update_data(game=game)
    await GiftGameState.next()
    await message.answer("Введите ID получателя:")

@dp.message_handler(state=GiftGameState.recipient)
async def gift_game_recipient(message: types.Message, state: FSMContext):
    recipient_id = message.text.strip()
    if recipient_id.lower() == "отмена":
        await state.finish()
        return await message.answer("Операция отменена.", reply_markup=get_main_keyboard(user_sessions.get(message.from_user.id)))

    importlib.reload(users_db)
    try:
        recipient_class = getattr(users_db, recipient_id)
    except AttributeError:
        return await message.answer("❌ Получатель не найден. Проверьте ID или введите 'Отмена'.")

    data = await state.get_data()
    game = data['game']
    sender = user_sessions.get(message.from_user.id)
    sender_class = sender.__name__

    def update_games(user_obj, remove=None, add=None):
        class_name = user_obj.__name__
        with open("users_db.py", "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        inside = False
        for line in lines:
            if line.strip().startswith(f"class {class_name}"):
                inside = True
            if inside and line.strip().startswith("games ="):
                current = [g.strip() for g in line.split("=")[1].strip().strip('"').split(",")]
                if remove and remove in current:
                    current.remove(remove)
                if add and add not in current:
                    current.append(add)
                line = f'    games = "{", ".join(current)}"\n'
                inside = False
            new_lines.append(line)
        with open("users_db.py", "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    update_games(sender, remove=game)
    update_games(recipient_class, add=game)

    importlib.reload(users_db)
    user_sessions[message.from_user.id] = getattr(users_db, sender_class)

    gift_history.append({
        "giver": sender_class,
        "recipient": recipient_id,
        "game": game
    })
    save_gift_history(gift_history)

    await state.finish()
    await message.answer(f"🎁 Вы подарили игру <b>{game}</b> пользователю <code>{recipient_id}</code>!", parse_mode="HTML", reply_markup=get_main_keyboard(user_sessions[message.from_user.id]))

@dp.message_handler(lambda msg: msg.text == "📜 История Подарков")
async def show_gift_history(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    uid = user.__name__
    given = [h for h in gift_history if h["giver"] == uid]
    received = [h for h in gift_history if h["recipient"] == uid]

    text = "<b>🎁 История Подарков:</b>\n\n"
    text += "<u>Полученные:</u>\n"
    for h in received:
        text += f"📥 {h['game']} от <code>{h['giver']}</code>\n"

    text += "\n<u>Отправленные:</u>\n"
    for h in given:
        text += f"📤 {h['game']} → <code>{h['recipient']}</code>\n"

    if not given and not received:
        text += "Пока нет подарков."

    await message.answer(text, parse_mode="HTML")

@dp.message_handler(lambda msg: True)
async def launch_game_handler(message: types.Message):
    user = user_sessions.get(message.from_user.id)
    if not user:
        return
    games = [g.strip() for g in user.games.split(",") if g.strip()]
    text = message.text.strip()
    if text in games and text in GAME_URLS:
        game_url = GAME_URLS[text]
        inline_kb = InlineKeyboardMarkup()
        inline_kb.add(InlineKeyboardButton("▶️ Играть", url=game_url))
        await message.answer(f"🎮 {text}", reply_markup=inline_kb)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
