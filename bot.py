from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import os

# ================== الإعدادات ==================
TOKEN = os.getenv("TOKEN")
ADMIN_ID = 1188982651  # ID الأدمن

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUBJECTS_DIR = os.path.join(BASE_DIR, "subjects")
USERS_FILE = os.path.join(BASE_DIR, "users.txt")

# ================== المستخدمين ==================
def get_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return [u.strip() for u in f if u.strip()]

def is_approved(uid):
    return uid == ADMIN_ID or str(uid) in get_users()

def approve_user(uid):
    if str(uid) not in get_users():
        with open(USERS_FILE, "a", encoding="utf-8") as f:
            f.write(str(uid) + "\n")

def remove_user(uid):
    users = [u for u in get_users() if u != str(uid)]
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        for u in users:
            f.write(u + "\n")

# ================== الكيبورد ==================
start_kb = ReplyKeyboardMarkup(resize_keyboard=True)
start_kb.add("ابدأ")

semester_kb = ReplyKeyboardMarkup(resize_keyboard=True)
semester_kb.add("📘 فصل أول", "📗 فصل ثاني")
semester_kb.add("🔙 رجوع")

admin_kb = ReplyKeyboardMarkup(resize_keyboard=True)
admin_kb.add("ابدأ")
admin_kb.add("📊 إحصائيات", "🚫 إخراج مستخدم")
admin_kb.add("📢 رسالة جماعية")

# ================== متغير الجلسة ==================
user_semester = {}

# ================== start ==================
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("👑 لوحة الأدمن", reply_markup=admin_kb)
        return

    if not is_approved(msg.from_user.id):
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{msg.from_user.id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{msg.from_user.id}")
        )
        await bot.send_message(
            ADMIN_ID,
            f"طلب دخول:\n{msg.from_user.full_name}\n{msg.from_user.id}",
            reply_markup=kb
        )
        await msg.answer("⏳ بانتظار الموافقة")
        return

    await msg.answer("أهلاً 👋", reply_markup=start_kb)

# ================== الموافقة ==================
@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve(call: types.CallbackQuery):
    uid = int(call.data.split("_")[1])
    approve_user(uid)
    await bot.send_message(uid, "✅ تمت الموافقة، أرسل /start")
    await call.message.edit_text("تمت الموافقة")

@dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
async def reject(call: types.CallbackQuery):
    uid = int(call.data.split("_")[1])
    await bot.send_message(uid, "❌ تم الرفض")
    await call.message.edit_text("تم الرفض")

# ================== ابدأ ==================
@dp.message_handler(lambda m: m.text == "ابدأ")
async def choose_semester(msg: types.Message):
    await msg.answer("اختر الفصل الدراسي:", reply_markup=semester_kb)

# ================== اختيار الفصل ==================
@dp.message_handler(lambda m: m.text in ["📘 فصل أول", "📗 فصل ثاني"])
async def semester_selected(msg: types.Message):
    semester = "فصل أول" if "أول" in msg.text else "فصل ثاني"
    user_semester[msg.from_user.id] = semester

    folder = os.path.join(SUBJECTS_DIR, semester)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    for s in os.listdir(folder):
        kb.add(s)

    kb.add("🔙 رجوع")
    await msg.answer(f"📚 مواد {semester}:", reply_markup=kb)

# ================== إرسال الملفات ==================
@dp.message_handler(lambda m: m.from_user.id in user_semester)
async def send_files(msg: types.Message):
    semester = user_semester[msg.from_user.id]
    subject_path = os.path.join(SUBJECTS_DIR, semester, msg.text)

    if not os.path.exists(subject_path):
        return

    files = os.listdir(subject_path)
    if not files:
        await msg.answer("❌ لا يوجد ملفات")
        return

    for file in files:
        with open(os.path.join(subject_path, file), "rb") as f:
            await msg.answer_document(f)

# ================== رجوع ==================
@dp.message_handler(lambda m: m.text == "🔙 رجوع")
async def go_back(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("👑 لوحة الأدمن", reply_markup=admin_kb)
    else:
        await msg.answer("أهلاً 👋", reply_markup=start_kb)

# ================== إحصائيات ==================
@dp.message_handler(lambda m: m.text == "📊 إحصائيات" and m.from_user.id == ADMIN_ID)
async def stats(msg: types.Message):
    users = get_users()
    text = f"📊 عدد المستخدمين: {len(users)}\n\n"

    for uid in users:
        try:
            chat = await bot.get_chat(int(uid))
            username = f"@{chat.username}" if chat.username else "بدون"
            text += f"👤 {chat.full_name}\n🔗 {username}\n🆔 {uid}\n\n"
        except:
            text += f"🆔 {uid}\n\n"

    await msg.answer(text, reply_markup=admin_kb)

# ================== إخراج ==================
@dp.message_handler(lambda m: m.text == "🚫 إخراج مستخدم" and m.from_user.id == ADMIN_ID)
async def ask_delete(msg: types.Message):
    await msg.answer("أرسل ID المستخدم")

@dp.message_handler(lambda m: m.text.isdigit() and m.from_user.id == ADMIN_ID)
async def delete_user(msg: types.Message):
    remove_user(msg.text)
    await msg.answer("✅ تم إخراج المستخدم", reply_markup=admin_kb)

# ================== رسالة جماعية ==================
@dp.message_handler(lambda m: m.text == "📢 رسالة جماعية" and m.from_user.id == ADMIN_ID)
async def ask_broadcast(msg: types.Message):
    await msg.answer("✍️ أرسل الرسالة")

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.reply_to_message is None)
async def broadcast(msg: types.Message):
    sent = 0
    for uid in get_users():
        try:
            await bot.send_message(int(uid), msg.text)
            sent += 1
        except:
            pass
    await msg.answer(f"✅ تم الإرسال إلى {sent} مستخدم")

# ================== تشغيل ==================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
