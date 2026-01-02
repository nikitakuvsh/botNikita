import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    InputMediaPhoto
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()

bot = Bot(os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())


# -------- STATES --------
class Form(StatesGroup):
    main_text = State()
    photos = State()
    button_text = State()
    modal_count = State()
    modal_texts = State()


# -------- START --------
@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Введи текст основного сообщения")
    await state.set_state(Form.main_text)


# -------- MAIN TEXT --------
@dp.message(Form.main_text)
async def get_main_text(message: Message, state: FSMContext):
    await state.update_data(main_text=message.text, photos=[])
    await message.answer(
        "Отправь фото для сообщения (одно или несколько)\n"
        "Когда закончишь — напиши `готово`\n"
        "Если без фото — сразу напиши `нет`"
    )
    await state.set_state(Form.photos)


# -------- PHOTOS --------
@dp.message(Form.photos)
async def get_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data["photos"]

    if message.text:
        text = message.text.lower()

        if text == "нет":
            await message.answer("Введи текст кнопки")
            await state.set_state(Form.button_text)
            return

        if text == "готово":
            if not photos:
                return await message.answer("Ты ещё не прислал ни одного фото 🙂")
            await message.answer("Введи текст кнопки")
            await state.set_state(Form.button_text)
            return

    if message.photo:
        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)
    else:
        await message.answer("Пришли фото или напиши `готово` / `нет`")


# -------- BUTTON TEXT --------
@dp.message(Form.button_text)
async def get_button_text(message: Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await message.answer("Сколько модальных окон будет?")
    await state.set_state(Form.modal_count)


# -------- MODAL COUNT --------
@dp.message(Form.modal_count)
async def get_modal_count(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Нужно число 🙂")

    await state.update_data(
        modal_count=int(message.text),
        modal_texts=[],
        current_index=0
    )

    await message.answer("Введи текст модального окна №1")
    await state.set_state(Form.modal_texts)


# -------- MODAL TEXTS --------
@dp.message(Form.modal_texts)
async def get_modal_texts(message: Message, state: FSMContext):
    data = await state.get_data()
    texts = data["modal_texts"]
    texts.append(message.text)

    await state.update_data(modal_texts=texts)

    if len(texts) < data["modal_count"]:
        await message.answer(
            f"Введи текст модального окна №{len(texts) + 1}"
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=data["button_text"],
                callback_data="open_modal"
            )]
        ]
    )

    # ---- отправка основного сообщения ----
    photos = data["photos"]

    if not photos:
        await message.answer(
            data["main_text"],
            reply_markup=keyboard
        )

    elif len(photos) == 1:
        await message.answer_photo(
            photo=photos[0],
            caption=data["main_text"],
            reply_markup=keyboard
        )

    else:
        media = [
            InputMediaPhoto(
                media=photo,
                caption=data["main_text"] if i == 0 else None
            )
            for i, photo in enumerate(photos)
        ]
        await message.answer_media_group(media)
        await message.answer(
            "⬇️",
            reply_markup=keyboard
        )


# -------- CALLBACK (MODAL) --------
@dp.callback_query(F.data == "open_modal")
async def open_modal(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data.get("current_index", 0)

    if index >= len(data["modal_texts"]):
        await callback.answer(
            "Модальные окна закончились 😎",
            show_alert=True
        )
        return

    await callback.answer(
        data["modal_texts"][index],
        show_alert=True
    )

    await state.update_data(current_index=index + 1)


# -------- RUN --------
async def main():
    print('bot started')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
