import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
# CHANNEL_ID = -1001828619345
CHANNEL_ID = -1003458597245


bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# -------- STATES --------
class Form(StatesGroup):
    password = State()
    choose_post = State()
    # канал
    main_text = State()
    photo = State()
    button_text = State()
    modal_text = State()
    confirm_post = State()
    # реклама
    ad_text = State()
    ad_photo = State()
    ad_button = State()
    ad_link = State()

# -------- глобальное хранение --------
modal_texts = {}         # для кнопок в канале
user_modal_text = {}     # для предпросмотра у пользователя
authorized_users = set()

PASSWORD = "BVx14b8S0eP6H"
DELAY = 0.3  # задержка для стабильности

# -------- START --------
@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    await asyncio.sleep(DELAY)
    if message.from_user.id in authorized_users:
        await message.answer(
            "Привет! Какой пост вы хотите создать?\n1️⃣ В канал\n2️⃣ Рекламный пост"
        )
        await state.set_state(Form.choose_post)
    else:
        await message.answer("Введите пароль для доступа к боту:")
        await state.set_state(Form.password)

@dp.message(Form.password)
async def check_password(message: Message, state: FSMContext):
    if message.text != PASSWORD:
        await asyncio.sleep(DELAY)
        await message.answer("❌ Неверный пароль. Доступ запрещён.")
        await state.clear()
        return

    authorized_users.add(message.from_user.id)
    await state.clear()
    await asyncio.sleep(DELAY)
    await message.answer(
        "✅ Пароль принят.\nКакой пост вы хотите создать?\n1️⃣ В канал\n2️⃣ Рекламный пост"
    )
    await state.set_state(Form.choose_post)

# -------- ВЫБОР ПОСТА --------
@dp.message(Form.choose_post)
async def choose_post(message: Message, state: FSMContext):
    text = message.text.lower()
    await asyncio.sleep(DELAY)
    if "1" in text or "канал" in text:
        await message.answer("Введите текст основного сообщения для канала:")
        await state.set_state(Form.main_text)
    elif "2" in text or "реклам" in text:
        await message.answer("Введите текст рекламного поста:")
        await state.set_state(Form.ad_text)
    else:
        await message.answer("Выберите 1️⃣ или 2️⃣")

# -------- КАНАЛ: MAIN TEXT --------
@dp.message(Form.main_text)
async def get_main_text(message: Message, state: FSMContext):
    await state.update_data(main_text=message.text)
    await asyncio.sleep(DELAY)
    await message.answer("Отправь фото (одно) или напиши `нет` если без фото:")
    await state.set_state(Form.photo)

# -------- КАНАЛ: PHOTO --------
@dp.message(Form.photo)
async def get_photo(message: Message, state: FSMContext):
    if message.text and message.text.lower() == "нет":
        await state.update_data(photo=None)
    elif message.photo:
        await state.update_data(photo=message.photo[-1].file_id)
    else:
        await asyncio.sleep(DELAY)
        await message.answer("Пришли фото или напиши `нет`")
        return
    await asyncio.sleep(DELAY)
    await message.answer("Введи текст кнопки:")
    await state.set_state(Form.button_text)

# -------- КАНАЛ: BUTTON TEXT --------
@dp.message(Form.button_text)
async def get_button_text(message: Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await asyncio.sleep(DELAY)
    await message.answer("Введи текст модального окна:")
    await state.set_state(Form.modal_text)

# -------- КАНАЛ: MODAL TEXT --------
@dp.message(Form.modal_text)
async def get_modal_text(message: Message, state: FSMContext):
    await state.update_data(modal_text=message.text)
    user_modal_text[message.from_user.id] = message.text  # для предпросмотра
    data = await state.get_data()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=data["button_text"], callback_data="show_modal_user")]]
    )
    photo = data.get("photo")

    await asyncio.sleep(DELAY)
    if not photo:
        await message.answer(f"Вот как будет выглядеть пост:\n\n{data['main_text']}", reply_markup=keyboard)
    else:
        await message.answer_photo(photo=photo, caption=data['main_text'], reply_markup=keyboard)

    await asyncio.sleep(DELAY)
    await message.answer("Опубликовать пост? (да/нет)")
    await state.set_state(Form.confirm_post)

# -------- КАНАЛ: CONFIRM POST --------
@dp.message(Form.confirm_post)
async def confirm_post(message: Message, state: FSMContext):
    text = message.text.lower()
    if text != "да":
        await asyncio.sleep(DELAY)
        await message.answer("Пост отменён. Вы можете начать заново /start")
        await state.clear()
        return

    data = await state.get_data()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=data["button_text"], callback_data="show_modal")]]
    )
    photo = data.get("photo")

    if not photo:
        msg = await bot.send_message(CHANNEL_ID, data["main_text"], reply_markup=keyboard)
    else:
        msg = await bot.send_photo(CHANNEL_ID, photo, caption=data["main_text"], reply_markup=keyboard)

    modal_texts[msg.message_id] = data["modal_text"]
    await asyncio.sleep(DELAY)
    await message.answer("Пост отправлен в канал ✅")
    await state.clear()

# -------- РЕКЛАМНЫЙ ПОСТ --------
@dp.message(Form.ad_text)
async def ad_text(message: Message, state: FSMContext):
    await state.update_data(ad_text=message.text)
    await asyncio.sleep(DELAY)
    await message.answer("Отправьте фото для рекламного поста (или напишите `нет`)")
    await state.set_state(Form.ad_photo)

@dp.message(Form.ad_photo)
async def ad_photo(message: Message, state: FSMContext):
    if message.text and message.text.lower() == "нет":
        await state.update_data(ad_photo=None)
    elif message.photo:
        await state.update_data(ad_photo=message.photo[-1].file_id)
    else:
        await asyncio.sleep(DELAY)
        await message.answer("Пришлите фото или напишите `нет`")
        return
    await asyncio.sleep(DELAY)
    await message.answer("Введите текст кнопки для рекламного поста:")
    await state.set_state(Form.ad_button)

@dp.message(Form.ad_button)
async def ad_button(message: Message, state: FSMContext):
    await state.update_data(ad_button=message.text)
    await asyncio.sleep(DELAY)
    await message.answer("Введите ссылку на канал или приглашение для кнопки:")
    await state.set_state(Form.ad_link)

@dp.message(Form.ad_link)
async def ad_link(message: Message, state: FSMContext):
    await state.update_data(ad_link=message.text)
    data = await state.get_data()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=data["ad_button"], url=data["ad_link"])]]
    )
    await asyncio.sleep(DELAY)
    if data.get("ad_photo"):
        await message.answer_photo(photo=data["ad_photo"], caption=data["ad_text"], reply_markup=keyboard)
    else:
        await message.answer(data["ad_text"], reply_markup=keyboard)
    await asyncio.sleep(DELAY)
    await message.answer("Рекламный пост готов ✅ Можно пересылать")
    await state.clear()

# -------- CALLBACKS --------
@dp.callback_query(F.data == "show_modal_user")
async def show_modal_user(callback: CallbackQuery):
    text = user_modal_text.get(callback.from_user.id, "Текст модального окна не найден")
    await callback.answer(text, show_alert=True)

@dp.callback_query(F.data == "show_modal")
async def show_modal(callback: CallbackQuery):
    text = modal_texts.get(callback.message.message_id, "Текст модального окна не найден")
    await callback.answer(text, show_alert=True)

# -------- RUN --------
async def main():
    print("bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
