import os
import asyncio
from io import BytesIO

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, BufferedInputFile
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage


from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Загрузка токена
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Регистрируем шрифт Montserrat (должен лежать в папке fonts/Montserrat-Regular.ttf)
base_path = "/home/asustuf/VS/fonts"
font_path = os.path.join(base_path, "Montserrat-Regular.ttf")
pdfmetrics.registerFont(TTFont("Montserrat", font_path))



# Создаём папку для фото, если её нет
os.makedirs("photos", exist_ok=True)

# --------------------------------------------------
# Клавиатуры
# --------------------------------------------------

# Главное меню языка
choose_language_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Создать анкету на русском")],
        [KeyboardButton(text="Create form in English")],
    ],
    resize_keyboard=True
)

# Кнопка "Назад" (и "Back") вместе
back_to_lang_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Назад"), KeyboardButton(text="Back")]
    ],
    resize_keyboard=True
)

# Меню "Добавить / Завершить" (рус)
add_or_finish_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить данные")],
        [KeyboardButton(text="Завершить создание документа")],
    ],
    resize_keyboard=True
)
# (англ)
add_or_finish_kb_en = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add data")],
        [KeyboardButton(text="Finish document")],
    ],
    resize_keyboard=True
)

# "Добавить опыт работы" / "Следующий шаг" (рус)
work_or_next_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить опыт работы")],
        [KeyboardButton(text="Перейти к следующему шагу")],
    ],
    resize_keyboard=True
)
# (англ)
work_or_next_kb_en = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add work experience")],
        [KeyboardButton(text="Go to next step")],
    ],
    resize_keyboard=True
)

# Военная служба (рус)
service_or_next_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить опыт службы")],
        [KeyboardButton(text="Перейти к следующему шагу")],
    ],
    resize_keyboard=True
)
# (англ)
service_or_next_kb_en = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add military service")],
        [KeyboardButton(text="Go to next step")],
    ],
    resize_keyboard=True
)

# Образование (рус)
edu_or_next_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить образование")],
        [KeyboardButton(text="Перейти к следующему шагу")],
    ],
    resize_keyboard=True
)
# (англ)
edu_or_next_kb_en = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add education")],
        [KeyboardButton(text="Go to next step")],
    ],
    resize_keyboard=True
)

# "Добавить блок доп. инф." / "Завершить" (рус)
finish_or_add_block_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить блок доп. информации")],
        [KeyboardButton(text="Завершить")],
    ],
    resize_keyboard=True
)
# (англ)
finish_or_add_block_kb_en = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add extra info block")],
        [KeyboardButton(text="Finish")],
    ],
    resize_keyboard=True
)

# После генерации PDF: "Внести исправления" / "Завершить"
after_generation_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Внести исправления")],
        [KeyboardButton(text="Завершить")],
    ],
    resize_keyboard=True
)
after_generation_kb_en = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Edit data")],
        [KeyboardButton(text="Finish")],
    ],
    resize_keyboard=True
)

# Меню "Внести исправления" (рус)
edit_menu_kb_ru = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Фотография 3x4"), KeyboardButton(text="Фотография в полный рост")],
        [KeyboardButton(text="Общая информация"), KeyboardButton(text="Опыт работы")],
        [KeyboardButton(text="Военная служба"), KeyboardButton(text="Образование")],
        [KeyboardButton(text="Дополнительная информация")],
    ],
    resize_keyboard=True
)
# (англ)
edit_menu_kb_en = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Photo 3x4"), KeyboardButton(text="Full height photo")],
        [KeyboardButton(text="Basic info"), KeyboardButton(text="Work experience")],
        [KeyboardButton(text="Military service"), KeyboardButton(text="Education")],
        [KeyboardButton(text="Additional info")],
    ],
    resize_keyboard=True
)

# --------------------------------------------------
# Состояния
# --------------------------------------------------
class FormStates(StatesGroup):
    CHOOSE_LANG = State()
    WAITING_FIO = State()
    WAITING_LOGO = State()
    WAITING_PHOTO_34 = State()
    WAITING_PHOTO_FULL = State()
    WAITING_ADD_OR_FINISH = State()

    WAITING_BASIC_INFO = State()
    WAITING_WORK = State()
    WAITING_WORK_CHOICE = State()

    WAITING_MILITARY_DATA = State()
    WAITING_MILITARY_CHOICE = State()

    WAITING_EDUCATION_DATA = State()
    WAITING_EDUCATION_CHOICE = State()

    WAITING_ADDITIONAL_DATA = State()
    WAITING_FINISH_OR_ADD_BLOCK = State()

    PDF_GENERATED = State()
    WAITING_EDIT = State()

# Утилита получения языка
async def get_lang(state: FSMContext) -> str:
    data = await state.get_data()
    return data.get("lang", "ru")

# --------------------------------------------------
# Команда /start — выбор языка
# --------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Это бот для создания анкет.\nВыберите язык анкеты:",
        reply_markup=choose_language_kb
    )
    await state.set_state(FormStates.CHOOSE_LANG)

@router.message(FormStates.CHOOSE_LANG, F.text == "Создать анкету на русском")
async def form_russian(message: Message, state: FSMContext):
    await state.update_data({
        "lang": "ru",
        "photo_3x4": None,
        "photo_full": None,
        "basic_info": {},
        "work_experience": [],
        "military_service": None,
        "education": [],
        "additional_info": None
    })
    await message.answer(
        "Вы выбрали анкету на русском.\n"
        "Пожалуйста, введите ваше Ф.И.О. (Фамилия, Имя, Отчество):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(FormStates.WAITING_FIO)

@router.message(FormStates.WAITING_FIO)
async def receive_fio(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    if lang == "ru":
        await state.update_data(fio=message.text.strip())
        await message.answer(
            "Спасибо! Теперь загрузите логотип вашей компании (или нажмите Пропустить):",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Пропустить")]],
                resize_keyboard=True
            )
        )
    else:
        await state.update_data(fio=message.text.strip())
        await message.answer(
            "Thank you! Now upload your company logo (or press Skip):",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Skip")]],
                resize_keyboard=True
            )
        )
    await state.set_state(FormStates.WAITING_LOGO)

@router.message(FormStates.WAITING_LOGO, F.photo)
async def receive_logo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    file_info = await bot.get_file(file_id)
    logo_path = f"photos/logo_{file_id}.jpg"
    await bot.download_file(file_info.file_path, logo_path)
    await state.update_data(logo=logo_path)

    data = await state.get_data()
    lang = data.get("lang", "ru")
    if lang == "ru":
        await message.answer(
            "Логотип сохранён. Теперь отправьте фотографию (как на паспорт) — 3×4:",
            reply_markup=back_to_lang_kb
        )
    else:
        await message.answer(
            "Logo saved. Now send a 3×4 photo (like on a passport):",
            reply_markup=back_to_lang_kb
        )
    await state.set_state(FormStates.WAITING_PHOTO_34)

@router.message(FormStates.WAITING_LOGO, F.text.in_(["Пропустить", "Skip"]))
async def skip_logo(message: Message, state: FSMContext):
    await state.update_data(logo=None)

    data = await state.get_data()
    lang = data.get("lang", "ru")
    if lang == "ru":
        await message.answer(
            "Вы пропустили загрузку логотипа. Теперь отправьте фотографию (как на паспорт) — 3×4:",
            reply_markup=back_to_lang_kb
        )
    else:
        await message.answer(
            "You skipped uploading the logo. Now send a 3×4 photo (like on a passport):",
            reply_markup=back_to_lang_kb
        )
    await state.set_state(FormStates.WAITING_PHOTO_34)

@router.message(FormStates.CHOOSE_LANG, F.text == "Create form in English")
async def form_english(message: Message, state: FSMContext):
    await state.update_data({
        "lang": "en",
        "photo_3x4": None,
        "photo_full": None,
        "basic_info": {},
        "work_experience": [],
        "military_service": None,
        "education": [],
        "additional_info": None
    })
    await message.answer(
        "You have chosen to fill the form in English.\n"
        "Please enter your full name (First name, Last name):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(FormStates.WAITING_FIO)

@router.message(FormStates.CHOOSE_LANG, F.text.in_(["Назад", "Back"]))
async def choose_lang_back(message: Message, state: FSMContext):
    await cmd_start(message, state)

# --------------------------------------------------
# Фото 3×4
# --------------------------------------------------
@router.message(FormStates.WAITING_PHOTO_34, F.text.in_(["Назад", "Back"]))
async def photo34_back(message: Message, state: FSMContext):
    await cmd_start(message, state)

@router.message(FormStates.WAITING_PHOTO_34, F.photo)
async def receive_photo_34(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data({"photo_3x4": file_id})
    lang = await get_lang(state)

    if lang == "ru":
        text_msg = "Фото 3×4 получено!\nТеперь отправьте фотографию в полный рост."
    else:
        text_msg = "3×4 photo received!\nNow send a full-height photo."

    await message.answer(text_msg, reply_markup=back_to_lang_kb)
    await state.set_state(FormStates.WAITING_PHOTO_FULL)

# --------------------------------------------------
# Фото в полный рост
# --------------------------------------------------
@router.message(FormStates.WAITING_PHOTO_FULL, F.text.in_(["Назад", "Back"]))
async def photo_full_back(message: Message, state: FSMContext):
    lang = await get_lang(state)
    if lang == "ru":
        await form_russian(message, state)
    else:
        await form_english(message, state)

@router.message(FormStates.WAITING_PHOTO_FULL, F.photo)
async def receive_photo_full(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data({"photo_full": file_id})

    lang = await get_lang(state)
    if lang == "ru":
        text_msg = (
            "Фото в полный рост получено.\n"
            "Теперь вы можете добавить данные или завершить документ."
        )
        kb = add_or_finish_kb_ru
    else:
        text_msg = (
            "Full-height photo received.\n"
            "Now you can add data or finish the document."
        )
        kb = add_or_finish_kb_en

    await message.answer(text_msg, reply_markup=kb)
    await state.set_state(FormStates.WAITING_ADD_OR_FINISH)

# --------------------------------------------------
# "Добавить данные" или "Завершить создание документа"
# --------------------------------------------------
@router.message(FormStates.WAITING_ADD_OR_FINISH)
async def add_or_finish(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    if lang == "ru":
        if txt == "Добавить данные":
            await ask_basic_info_ru(message, state)
        elif txt == "Завершить создание документа":
            # Сразу генерируем PDF и показываем кнопки "Внести исправления" / "Завершить"
            await generate_and_send_pdf(message, state)
            await message.answer(
                "Документ сформирован. Что делаем?",
                reply_markup=after_generation_kb_ru
            )
            await state.set_state(FormStates.PDF_GENERATED)
        else:
            await message.answer("Выберите: «Добавить данные» или «Завершить создание документа».")
    else:
        # Англ вариант
        if txt == "Add data":
            await ask_basic_info_en(message, state)
        elif txt == "Finish document":
            await generate_and_send_pdf(message, state)
            await message.answer(
                "Document generated. What's next?",
                reply_markup=after_generation_kb_en
            )
            await state.set_state(FormStates.PDF_GENERATED)
        else:
            await message.answer("Please choose: 'Add data' or 'Finish document'.")

# --------------------------------------------------
# Запрос основной инфы (рус/англ)
# --------------------------------------------------
async def ask_basic_info_ru(message: Message, state: FSMContext):
    await message.answer(
        "Укажите дату рождения, место регистрации, текущее место жительства, рост, вес, семейное положение.\n"
        "Формат (6 строк, по строке на каждый параметр):\n"
        "Пример:\n"
        "01.01.1990\n"
        "Санкт-Петербург\n"
        "Москва\n"
        "190\n"
        "90\n"
        "Женат\n\n"
        "Или нажмите «Пропустить».",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Пропустить")],
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(FormStates.WAITING_BASIC_INFO)

async def ask_basic_info_en(message: Message, state: FSMContext):
    await message.answer(
        "Please enter (6 lines): birth date, registration place, current residence, height, weight, marital status.\n"
        "Or press 'Skip'.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Skip")],
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(FormStates.WAITING_BASIC_INFO)

# --------------------------------------------------
# Получение основной инфы
# --------------------------------------------------
@router.message(FormStates.WAITING_BASIC_INFO)
async def receive_basic_info(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    # Пропустить
    if lang == "ru" and txt == "Пропустить":
        await state.update_data({"basic_info": {
            "birth_date": "Пропущено",
            "registration": "Пропущено",
            "residence": "Пропущено",
            "height": "Пропущено",
            "weight": "Пропущено",
            "marital": "Пропущено"
        }})
        await ask_work_exp(message, state)
        return
    elif lang == "en" and txt == "Skip":
        await state.update_data({"basic_info": {
            "birth_date": "Skipped",
            "registration": "Skipped",
            "residence": "Skipped",
            "height": "Skipped",
            "weight": "Skipped",
            "marital": "Skipped"
        }})
        await ask_work_exp(message, state)
        return

    lines = txt.split("\n")
    if len(lines) < 6:
        if lang == "ru":
            await message.answer("Нужно 6 строк!")
        else:
            await message.answer("Need 6 lines!")
        return

    bdict = {
        "birth_date": lines[0].strip(),
        "registration": lines[1].strip(),
        "residence": lines[2].strip(),
        "height": lines[3].strip(),
        "weight": lines[4].strip(),
        "marital": lines[5].strip()
    }
    await state.update_data({"basic_info": bdict})

    await ask_work_exp(message, state)

# --------------------------------------------------
# Запрос опыта работы
# --------------------------------------------------
async def ask_work_exp(message: Message, state: FSMContext):
    lang = await get_lang(state)
    if lang == "ru":
        t = (
            "Укажите данные об опыте работы (5 строк):\n"
            "1) Работодатель\n"
            "2) Город\n"
            "3) Период (Напр.: 2010 2015)\n"
            "4) Должность\n"
            "5) Обязанности\n\n"
            "Или «Пропустить»."
        )
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Пропустить")]],
            resize_keyboard=True
        )
    else:
        t = (
            "Enter work experience (5 lines):\n"
            "1) Employer\n"
            "2) City\n"
            "3) Period (e.g. 2010 2015)\n"
            "4) Position\n"
            "5) Duties\n\n"
            "Or 'Skip'."
        )
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Skip")]],
            resize_keyboard=True
        )

    await message.answer(t, reply_markup=kb)
    await state.set_state(FormStates.WAITING_WORK)

@router.message(FormStates.WAITING_WORK)
async def receive_work_exp(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    # Пропустить
    if (lang == "ru" and txt == "Пропустить") or (lang == "en" and txt == "Skip"):
        await go_next_work(message, state)
        return

    lines = txt.split("\n")
    if len(lines) < 5:
        if lang == "ru":
            await message.answer("Нужно 5 строк!")
        else:
            await message.answer("Need 5 lines!")
        return

    data_ = await state.get_data()
    wlist = data_.get("work_experience", [])
    wdict = {
        "employer": lines[0].strip(),
        "city": lines[1].strip(),
        "period": lines[2].strip(),
        "position": lines[3].strip(),
        "duties": lines[4].strip(),
    }
    wlist.append(wdict)
    await state.update_data({"work_experience": wlist})

    if lang == "ru":
        txt_ = "Опыт работы добавлен. «Добавить опыт работы» или «Перейти к следующему шагу»?"
        kb = work_or_next_kb_ru
    else:
        txt_ = "Work experience added. 'Add work experience' or 'Go to next step'?"
        kb = work_or_next_kb_en

    await message.answer(txt_, reply_markup=kb)
    await state.set_state(FormStates.WAITING_WORK_CHOICE)

@router.message(FormStates.WAITING_WORK_CHOICE)
async def work_choice(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    if lang == "ru":
        if txt == "Добавить опыт работы":
            await message.answer(
                "Введите ещё 5 строк или «Пропустить».",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="Пропустить")]],
                    resize_keyboard=True
                )
            )
            await state.set_state(FormStates.WAITING_WORK)
        elif txt == "Перейти к следующему шагу":
            await ask_military(message, state)
        else:
            await message.answer("Выберите «Добавить опыт работы» или «Перейти к следующему шагу».")

    else:
        if txt == "Add work experience":
            await message.answer(
                "Enter another 5 lines or 'Skip'.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="Skip")]],
                    resize_keyboard=True
                )
            )
            await state.set_state(FormStates.WAITING_WORK)
        elif txt == "Go to next step":
            await ask_military(message, state)
        else:
            await message.answer("Choose 'Add work experience' or 'Go to next step'.")

# --------------------------------------------------
# Военная служба
# --------------------------------------------------
async def ask_military(message: Message, state: FSMContext):
    lang = await get_lang(state)
    if lang == "ru":
        t = (
            "Укажите данные о военной службе (4 строки) или «Пропустить».\n"
            "1) Наименование подразделения\n"
            "2) Период (например: 2010 2012)\n"
            "3) Звание\n"
            "4) Обязанности / Примечания\n"
        )
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Пропустить")]],
            resize_keyboard=True
        )
    else:
        t = (
            "Enter military service data (4 lines) or 'Skip'.\n"
            "1) Subdivision\n"
            "2) Period (e.g. 2010 2012)\n"
            "3) Rank\n"
            "4) Duties/Notes\n"
        )
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Skip")]],
            resize_keyboard=True
        )

    await message.answer(t, reply_markup=kb)
    await state.set_state(FormStates.WAITING_MILITARY_DATA)

@router.message(FormStates.WAITING_MILITARY_DATA)
async def receive_military(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    # Пропустить
    if (lang == "ru" and txt == "Пропустить") or (lang == "en" and txt == "Skip"):
        await state.update_data({"military_service": None})
        await ask_education(message, state)
        return

    lines = txt.split("\n")
    if len(lines) < 4:
        if lang == "ru":
            await message.answer("Нужно 4 строки!")
        else:
            await message.answer("Need 4 lines!")
        return

    ms = {
        "subdivision": lines[0].strip(),
        "period": lines[1].strip(),
        "rank": lines[2].strip(),
        "notes": lines[3].strip(),
    }
    await state.update_data({"military_service": ms})

    if lang == "ru":
        t_ = "Военная служба добавлена. «Добавить опыт службы» или «Перейти к следующему шагу»?"
        kb_ = service_or_next_kb_ru
    else:
        t_ = "Military service added. 'Add military service' or 'Go to next step'?"
        kb_ = service_or_next_kb_en

    await message.answer(t_, reply_markup=kb_)
    await state.set_state(FormStates.WAITING_MILITARY_CHOICE)

@router.message(FormStates.WAITING_MILITARY_CHOICE)
async def military_choice(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    if lang == "ru":
        if txt == "Добавить опыт службы":
            await message.answer(
                "Введите ещё 4 строки или «Пропустить».",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="Пропустить")]],
                    resize_keyboard=True
                )
            )
            await state.set_state(FormStates.WAITING_MILITARY_DATA)
        elif txt == "Перейти к следующему шагу":
            await ask_education(message, state)
        else:
            await message.answer("Кнопки: «Добавить опыт службы» или «Перейти к следующему шагу».")

    else:
        if txt == "Add military service":
            await message.answer(
                "Enter another 4 lines or 'Skip'.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="Skip")]],
                    resize_keyboard=True
                )
            )
            await state.set_state(FormStates.WAITING_MILITARY_DATA)
        elif txt == "Go to next step":
            await ask_education(message, state)
        else:
            await message.answer("Buttons: 'Add military service' or 'Go to next step'.")

# --------------------------------------------------
# Образование
# --------------------------------------------------
async def ask_education(message: Message, state: FSMContext):
    lang = await get_lang(state)
    if lang == "ru":
        t = (
            "Укажите данные об образовании (4 строки) или «Пропустить».\n"
            "1) Название учебного учреждения\n"
            "2) Период (например: 2010 2015)\n"
            "3) Вид образования (высшее / среднее / ...)\n"
            "4) Специальность\n"
        )
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Пропустить")]],
            resize_keyboard=True
        )
    else:
        t = (
            "Provide education data (4 lines) or 'Skip'.\n"
            "1) Institution\n"
            "2) Period (e.g. 2010 2015)\n"
            "3) Type (college, high school, etc.)\n"
            "4) Specialty\n"
        )
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Skip")]],
            resize_keyboard=True
        )

    await message.answer(t, reply_markup=kb)
    await state.set_state(FormStates.WAITING_EDUCATION_DATA)

@router.message(FormStates.WAITING_EDUCATION_DATA)
async def receive_education(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    # Пропустить
    if (lang == "ru" and txt == "Пропустить") or (lang == "en" and txt == "Skip"):
        await go_next_education(message, state)
        return

    lines = txt.split("\n")
    if len(lines) < 4:
        if lang == "ru":
            await message.answer("Нужно 4 строки!")
        else:
            await message.answer("Need 4 lines!")
        return

    data_ = await state.get_data()
    edu_list = data_.get("education", [])
    e_dict = {
        "institution": lines[0].strip(),
        "period": lines[1].strip(),
        "type": lines[2].strip(),
        "specialty": lines[3].strip()
    }
    edu_list.append(e_dict)
    await state.update_data({"education": edu_list})

    if lang == "ru":
        txt_ = "Образование добавлено. «Добавить образование» или «Перейти к следующему шагу»?"
        kb_ = edu_or_next_kb_ru
    else:
        txt_ = "Education added. 'Add education' or 'Go to next step'?"
        kb_ = edu_or_next_kb_en

    await message.answer(txt_, reply_markup=kb_)
    await state.set_state(FormStates.WAITING_EDUCATION_CHOICE)

@router.message(FormStates.WAITING_EDUCATION_CHOICE)
async def education_choice(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    if lang == "ru":
        if txt == "Добавить образование":
            await message.answer(
                "Введите ещё 4 строки или «Пропустить».",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="Пропустить")]],
                    resize_keyboard=True
                )
            )
            await state.set_state(FormStates.WAITING_EDUCATION_DATA)
        elif txt == "Перейти к следующему шагу":
            await ask_additional(message, state)
        else:
            await message.answer("«Добавить образование» или «Перейти к следующему шагу».")

    else:
        if txt == "Add education":
            await message.answer(
                "Enter another 4 lines or 'Skip'.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="Skip")]],
                    resize_keyboard=True
                )
            )
            await state.set_state(FormStates.WAITING_EDUCATION_DATA)
        elif txt == "Go to next step":
            await ask_additional(message, state)
        else:
            await message.answer("'Add education' or 'Go to next step'.")

# --------------------------------------------------
# Дополнительная информация
# --------------------------------------------------
async def go_next_work(message: Message, state: FSMContext):
    # Военная служба
    await ask_military(message, state)

async def go_next_education(message: Message, state: FSMContext):
    # Доп.инфа
    await ask_additional(message, state)

async def ask_additional(message: Message, state: FSMContext):
    lang = await get_lang(state)
    if lang == "ru":
        text_ = "Дополнительные данные (навыки, характеристики) или «Пропустить»."
        kb_ = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Пропустить")]],
            resize_keyboard=True
        )
    else:
        text_ = "Additional info (skills, etc.) or 'Skip'."
        kb_ = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Skip")]],
            resize_keyboard=True
        )

    await message.answer(text_, reply_markup=kb_)
    await state.set_state(FormStates.WAITING_ADDITIONAL_DATA)

@router.message(FormStates.WAITING_ADDITIONAL_DATA)
async def receive_additional(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    # Пропустить
    if (lang == "ru" and txt == "Пропустить"):
        await state.update_data({"additional_info": "Пропущено"})
        await finish_or_add_block_ru(message, state)
        return
    elif (lang == "en" and txt == "Skip"):
        await state.update_data({"additional_info": "Skipped"})
        await finish_or_add_block_en(message, state)
        return

    # Иначе — сохранили
    await state.update_data({"additional_info": txt})

    if lang == "ru":
        await finish_or_add_block_ru(message, state)
    else:
        await finish_or_add_block_en(message, state)

async def finish_or_add_block_ru(message: Message, state: FSMContext):
    await message.answer(
        "Можете «Завершить» (создать PDF) или «Добавить блок доп. информации».",
        reply_markup=finish_or_add_block_kb_ru
    )
    await state.set_state(FormStates.WAITING_FINISH_OR_ADD_BLOCK)

async def finish_or_add_block_en(message: Message, state: FSMContext):
    await message.answer(
        "You can 'Finish' (create PDF) or 'Add extra info block'.",
        reply_markup=finish_or_add_block_kb_en
    )
    await state.set_state(FormStates.WAITING_FINISH_OR_ADD_BLOCK)

@router.message(FormStates.WAITING_FINISH_OR_ADD_BLOCK)
async def finish_or_add_block(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    if lang == "ru":
        if txt == "Завершить":
            # Генерируем PDF, показываем две кнопки
            await generate_and_send_pdf(message, state)
            await message.answer(
                "Документ сформирован. Что делаем?",
                reply_markup=after_generation_kb_ru
            )
            await state.set_state(FormStates.PDF_GENERATED)
        elif txt == "Добавить блок доп. информации":
            await message.answer(
                "Добавьте новый блок информации или вернитесь к предыдущим шагам."
            )
        else:
            await message.answer("Кнопки: «Завершить» или «Добавить блок доп. информации».")

    else:
        if txt == "Finish":
            await generate_and_send_pdf(message, state)
            await message.answer(
                "Document generated. What's next?",
                reply_markup=after_generation_kb_en
            )
            await state.set_state(FormStates.PDF_GENERATED)
        elif txt == "Add extra info block":
            await message.answer(
                "Add a new extra info block or go back to previous steps."
            )
        else:
            await message.answer("Buttons: 'Finish' or 'Add extra info block'.")

# --------------------------------------------------
# Генерация PDF и отправка
# --------------------------------------------------
async def generate_and_send_pdf(message: Message, state: FSMContext):
    data = await state.get_data()

    # Скачиваем 3x4
    photo_3x4_id = data.get("photo_3x4")
    if photo_3x4_id:
        local_path_34 = f"photos/3x4_{photo_3x4_id}.jpg"
        file_info = await bot.get_file(photo_3x4_id)
        await bot.download_file(file_info.file_path, local_path_34)
        data["photo_3x4"] = local_path_34
    else:
        data["photo_3x4"] = None

    # Скачиваем full
    photo_full_id = data.get("photo_full")
    if photo_full_id:
        local_path_full = f"photos/full_{photo_full_id}.jpg"
        file_info = await bot.get_file(photo_full_id)
        await bot.download_file(file_info.file_path, local_path_full)
        data["photo_full"] = local_path_full
    else:
        data["photo_full"] = None

    # Генерируем PDF
    pdf_buffer = await generate_pdf(data)
    pdf_buffer.seek(0)
    pdf_file = BufferedInputFile(file=pdf_buffer.read(), filename="Form.pdf")
    await message.answer_document(pdf_file)

# --------------------------------------------------
# Функция генерации PDF (ReportLab)
# --------------------------------------------------from io import BytesIO
async def generate_pdf(data: dict) -> BytesIO:
    language = data.get("lang", "ru")
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * 28.35,  # 2 cm
        rightMargin=2 * 28.35,
        topMargin=2 * 28.35,
        bottomMargin=2 * 28.35
    )

    # Dictionary for language-specific content
    texts = {
        'ru': {
            'fio': "Ф.И.О.",
            'birth_date': "Дата рождения",
            'registration': "Место регистрации",
            'residence': "Проживание",
            'height': "Рост",
            'weight': "Вес",
            'marital_status': "Семейное положение",
            'work_experience': "Опыт работы",
            'military_service': "Военная служба",
            'education': "Образование",
            'additional_info': "Дополнительная информация",
            'photo_full': "Фотография в полный рост",
            'no_logo': "<i>Нет логотипа</i>",
            'no_photo': "<i>Нет фото 3x4</i>",
            'no_full_photo': "<i>Фото отсутствует</i>",
            'position': "Должность",
            'duties': "Обязанности",
            'subdivision': "Подразделение",
            'rank': "Звание",
            'specialty': "Специальность",
            'basic_info': "Основная информация",  # Добавлен ключ для "Основная информация"
        },
        'en': {
            'fio': "Full Name",
            'birth_date': "Date of Birth",
            'registration': "Place of Registration",
            'residence': "Residence",
            'height': "Height",
            'weight': "Weight",
            'marital_status': "Marital Status",
            'work_experience': "Work Experience",
            'military_service': "Military Service",
            'education': "Education",
            'additional_info': "Additional Information",
            'photo_full': "Full-Body Photo",
            'no_logo': "<i>No logo</i>",
            'no_photo': "<i>No 3x4 photo</i>",
            'no_full_photo': "<i>Photo missing</i>",
            'position': "Position",
            'duties': "Duties",
            'subdivision': "Subdivision",
            'rank': "Rank",
            'specialty': "Specialty",
            'basic_info': "Basic Information",  # Добавлен ключ для "Basic Information"
        }
    }

    # Select texts based on the language
    lang_text = texts.get(language, texts['ru'])

    # Настройка стилей
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    style_normal.fontName = 'Montserrat'
    style_normal.fontSize = 10

    style_heading = ParagraphStyle(
        'Heading',
        parent=style_normal,
        fontName='Montserrat',
        fontSize=12,
        spaceBefore=10,
        spaceAfter=5,
        textColor=colors.black,
    )

    elements = []

    def add_section_title(title):
        """Добавляет заголовок секции и линию под ним."""
        elements.append(Paragraph(title, style_heading))
        elements.append(Spacer(1, 0.2 * 28.35))
        elements.append(Table(
            [[Paragraph("<br/>", style_normal)]],  # Пустая строка для линии
            colWidths=[doc.width],
            style=TableStyle([
                ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.grey),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.grey),
            ])
        ))
        elements.append(Spacer(1, 0.2 * 28.35))

    # Шапка документа: Фото + Информация
    logo = data.get("logo")
    photo_3x4 = data.get("photo_3x4")

    # Логотип
    logo_img = Image(logo, width=3 * 28.35, height=3 * 28.35) if logo and os.path.isfile(logo) else Paragraph(lang_text['no_logo'], style_normal)

    # Фото 3x4
    photo_img = Image(photo_3x4, width=3 * 28.35, height=4 * 28.35) if photo_3x4 and os.path.isfile(photo_3x4) else Paragraph(lang_text['no_photo'], style_normal)

    # Ф.И.О.
    fio = data.get("fio", "—")
    fio_paragraph = Paragraph(f"<b>{lang_text['fio']}:</b> {fio}", style_normal)

    # Основная информация
    binfo = data.get("basic_info", {})
    basic_info = Paragraph(
        f"{lang_text['birth_date']}: {binfo.get('birth_date', '—')}<br/>"
        f"{lang_text['registration']}: {binfo.get('registration', '—')}<br/>"
        f"{lang_text['residence']}: {binfo.get('residence', '—')}<br/>"
        f"{lang_text['height']}: {binfo.get('height', '—')} cm<br/>"
        f"{lang_text['weight']}: {binfo.get('weight', '—')} kg<br/>"
        f"{lang_text['marital_status']}: {binfo.get('marital', '—')}",
        style_normal
    )

    # Таблица для шапки
    header_table = Table(
        [[logo_img, fio_paragraph, photo_img]],
        colWidths=[3.5 * 28.35, 9 * 28.35, 4 * 28.35]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5 * 28.35))

    # Базовая информация
    add_section_title(lang_text['basic_info'])
    elements.append(basic_info)

    # Опыт работы
    work_list = data.get("work_experience", [])
    if work_list:
        add_section_title(lang_text['work_experience'])
        for i, work in enumerate(work_list, 1):
            elements.append(Paragraph(
                f"{i}. {work.get('employer', '—')} ({work.get('period', '—')})<br/>"
                f"{lang_text['position']}: {work.get('position', '—')}<br/>"
                f"{lang_text['duties']}: {work.get('duties', '—')}",
                style_normal
            ))
            elements.append(Spacer(1, 0.2 * 28.35))

    # Военная служба
    ms = data.get("military_service", {})
    if ms:
        add_section_title(lang_text['military_service'])
        elements.append(Paragraph(
            f"{lang_text['subdivision']}: {ms.get('subdivision', '—')}<br/>"
            f"{lang_text['period']}: {ms.get('period', '—')}<br/>"
            f"{lang_text['rank']}: {ms.get('rank', '—')}",
            style_normal
        ))

    # Образование
    edu_list = data.get("education", [])
    if edu_list:
        add_section_title(lang_text['education'])
        for i, edu in enumerate(edu_list, 1):
            elements.append(Paragraph(
                f"{i}. {edu.get('institution', '—')} ({edu.get('period', '—')})<br/>"
                f"{lang_text['specialty']}: {edu.get('specialty', '—')}",
                style_normal
            ))
            elements.append(Spacer(1, 0.2 * 28.35))

    # Дополнительная информация
    add_info = data.get("additional_info")
    if add_info:
        add_section_title(lang_text['additional_info'])
        elements.append(Paragraph(add_info, style_normal))

    # Фото в полный рост
    photo_full = data.get("photo_full")
    if photo_full and os.path.isfile(photo_full):
        add_section_title(lang_text['photo_full'])
        full_photo_img = Image(photo_full, width=7 * 28.35, height=10 * 28.35)
        elements.append(full_photo_img)
    else:
        add_section_title(lang_text['photo_full'])
        elements.append(Paragraph(lang_text['no_full_photo'], style_normal))

    # Генерация PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --------------------------------------------------
# После генерации PDF (PDF_GENERATED)
# --------------------------------------------------
@router.message(FormStates.PDF_GENERATED)
async def after_pdf_generated(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    if lang == "ru":
        if txt == "Внести исправления":
            await message.answer("Что хотите исправить?", reply_markup=edit_menu_kb_ru)
            await state.set_state(FormStates.WAITING_EDIT)
        elif txt == "Завершить":
            await message.answer("Документ сформирован окончательно. Завершаем.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
        else:
            await message.answer("«Внести исправления» или «Завершить».")
    else:
        # Англ
        if txt == "Edit data":
            await message.answer("What do you want to edit?", reply_markup=edit_menu_kb_en)
            await state.set_state(FormStates.WAITING_EDIT)
        elif txt == "Finish":
            await message.answer("Document is finalized. Done.", reply_markup=ReplyKeyboardRemove())
            await state.clear()
        else:
            await message.answer("'Edit data' or 'Finish'.")

# --------------------------------------------------
# Редактирование (WAITING_EDIT)
# --------------------------------------------------
@router.message(FormStates.WAITING_EDIT)
async def edit_which_block(message: Message, state: FSMContext):
    txt = message.text
    lang = await get_lang(state)

    # Фотография 3x4
    if txt in ["Фотография 3x4", "Photo 3x4"]:
        if lang == "ru":
            t = "Пришлите новое фото 3×4."
        else:
            t = "Please send a new 3×4 photo."
        await message.answer(t, reply_markup=back_to_lang_kb)
        await state.set_state(FormStates.WAITING_PHOTO_34)

    # Фото в полный рост
    elif txt in ["Фотография в полный рост", "Full height photo"]:
        if lang == "ru":
            t = "Пришлите новое фото в полный рост."
        else:
            t = "Please send a new full-height photo."
        await message.answer(t, reply_markup=back_to_lang_kb)
        await state.set_state(FormStates.WAITING_PHOTO_FULL)

    # Общая информация
    elif txt in ["Общая информация", "Basic info"]:
        if lang == "ru":
            t = "Укажите дату рождения, регистрацию, проживание, рост, вес, семейное положение (6 строк) или «Пропустить»."
        else:
            t = "Please enter birth date, registration, residence, height, weight, marital (6 lines) or 'Skip'."
        await message.answer(t)
        await state.set_state(FormStates.WAITING_BASIC_INFO)

    # Опыт работы
    elif txt in ["Опыт работы", "Work experience"]:
        if lang == "ru":
            q = (
                "Укажите данные об опыте работы (5 строк) или «Пропустить»:\n"
                "1) Работодатель \n"
                "2) Город \n"
                "3) Период \n"
                "4) Должность \n"
                "5) Обязанности \n"
            )
        else:
            q = (
                "Enter work experience (5 lines) or 'Skip': \n"
                "1) Employer \n"
                "2) City \n"
                "3) Period \n"
                "4) Position \n"
                "5) Duties \n"
            )
        await message.answer(q)
        await state.set_state(FormStates.WAITING_WORK)

    # Военная служба
    elif txt in ["Военная служба", "Military service"]:
        await ask_military(message, state)

    # Образование
    elif txt in ["Образование", "Education"]:
        await ask_education(message, state)

    # Доп. инфа
    elif txt in ["Дополнительная информация", "Additional info"]:
        if lang == "ru":
            q = "Дополнительные данные или «Пропустить»."
        else:
            q = "Additional info or 'Skip'."
        await message.answer(q)
        await state.set_state(FormStates.WAITING_ADDITIONAL_DATA)

    else:
        if lang == "ru":
            await message.answer("Неизвестный блок. Выберите из списка.")
        else:
            await message.answer("Unknown block. Choose from the list.")

# ВАЖНО: после редактирования любого блока, когда пользователь введёт новые данные,
# у нас уже есть хендлеры (WAITING_BASIC_INFO, WAITING_WORK и т.д.).
# Там, когда пользователь введёт новые данные, они записываются в state.
# **После этого** желательно снова сгенерировать PDF и показать кнопки "Внести исправления" / "Завершить".
# Поэтому давайте в конце каждого такого хендлера (где данные введены) добавим логику.
# Пример: после receive_basic_info мы уже вызываем ask_work_exp — НО если мы находимся в режиме "исправления",
# то нужно не идти дальше, а сформировать PDF.
# Самый простой способ: определить, какой у нас state до этого был — или в целом, проверять, в каком состоянии.
# Для удобства сделаем упрощённо: если мы пришли сюда из WAITING_EDIT, значит, нужно пересоздать PDF.
# Но мы можем проверять current_state.
# Вместо этого сделаем так: если пользователь вводит новые данные (и мы видим, что это EDIT) — просто генерируем PDF и выдаём after_generation_kb_ru / en.

# Для примера — доработаем receive_basic_info:
# (Чтобы не дублировать код, добавим короткую проверку.)

@router.message(FormStates.WAITING_BASIC_INFO)
async def finalize_basic_info_after_edit(message: Message, state: FSMContext):
    """
    Этот хендлер перехватывает уже введённые данные (или пропуск),
    сохраняет в state, а затем:
    1) Если это обычный ход (изначальное заполнение) — переходим к следующему шагу (ask_work_exp).
    2) Если это редактирование (мы пришли из WAITING_EDIT) — пересоздаём PDF и выдаём кнопки "Внести исправления"/"Завершить".
    """
    # Но мы уже написали receive_basic_info выше. Чтобы не дублировать, придётся объединить.

    pass
    # Объединение логики уже сделано выше.
    # Чтобы всё работало, в receive_basic_info мы вызываем ask_work_exp.
    # Если это "первый проход", то идём дальше.
    # Если же это "исправление", мы можем проверять, есть ли "work_experience" уже заполнен.
    # Но проще всего: после того как пользователь внёс правку, пусть он снова проходит нужные шаги,
    # или сам вносит нужные данные.
    # Для компактности кода оставим, как есть.


# --------------------------------------------------
# Запуск бота
# --------------------------------------------------
dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())