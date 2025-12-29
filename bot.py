import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# ================== إعدادات ==================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN not found")

ADMIN_ID = 642912725

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.txt")
SUBJECTS_DIR = os.path.join(BASE_DIR, "subjects")

# ================== المواد ==================
TERM1_SUBJECTS = [
    "أساسيات التمريض عملي",
    "أساسيات التمريض نظري",
    "الأحياء الدقيقة",
    "التخدير والإنعاش عملي 1",
    "التخدير والإنعاش نظري 1",
    "التشريح 1 عملي",
    "التشريح 1 نظري",
    "المصطلحات الطبية",
    "فيزيولوجيا 1",
    "معدات التخدير عملي",
    "معدات التخدير نظري",
    "مهارات التواصل"
]

TERM2_SUBJECTS = [
    "أدوية التخدير",
    "التخدير والإنعاش 2",
    "المراقبة السريرية",
    "الإسعافات الأولية",
    "الوبائيات والعدوى",
    "أخلاقيات المهنة",
    "علم وظائف الأعضاء 2"
]

# ================== مستخدمين ==================
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return [line.strip().split("|") for line in f if line.strip()]

def save_user(user):
    users = load_users()
    if not any(u[0] == user[0] for u in users):
        with open(USERS_FILE, "a", encoding="utf-8") as f:
            f.write("|".join(user) + "\n")

def remove_user(uid):
    users = [u for u in load_users() if u[0] != str(uid)]
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        for u in users:
            f.write("|".join(u) + "\n")

def is_approved(uid):
    return uid == ADMIN_ID or any(u[0] == str(uid) for u in load_users())

# ================== كيبورد ==================
start_kb = ReplyKeyboardMarkup(resize_keyboard=True)
start_kb.add("ابدأ")

admin_kb = ReplyKeyboardMarkup(resize_keyboard=True)
admin_kb.add("📊 إحصائيات", "🚫 طرد مستخدم")
admin_kb.add("📢 رسالة جماعية")
admin_kb.add("ابدأ")

term_kb = ReplyKeyboardMarkup(resize_keyboard=True)
term_kb.add("📘 الفصل الأول", "📗 الفصل الثاني")
term_kb.add("🔙 رجوع")

def subjects_kb(subjects):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for s in subjects:
        kb.add(s)
    kb.add("🔙 رجوع")
    return kb

# ================== START ==================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    if not is_approved(message.from_user.id):
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{message.from_user.id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{message.from_user.id}")
        )
        await bot.send_message(
            ADMIN_ID,
            f"طلب جديد:\n👤 {message.from_user.full_name}\n🔗 @{message.from_user.username}\n🆔 {message.from_user.id}",
            reply_markup=kb
        )
        await message.answer("⏳ تم إرسال طلبك للموافقة")
        return

    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 لوحة الأدمن", reply_markup=admin_kb)
    else:
        await message.answer("أهلاً بك 👋", reply_markup=start_kb)

# ================== موافقة ==================
@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve(call: types.CallbackQuery):
    uid = call.data.split("_")[1]
    user = await bot.get_chat(uid)
    save_user([uid, user.full_name, user.username or "—"])
    await bot.send_message(uid, "✅ تمت الموافقة، أرسل /start")
    await call.message.edit_text("✅ تمت الموافقة")

@dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
async def reject(call: types.CallbackQuery):
    uid = call.data.split("_")[1]
    await bot.send_message(uid, "❌ تم رفض طلبك")
    await call.message.edit_text("❌ تم الرفض")

# ================== اختيار الفصل ==================
@dp.message_handler(lambda m: m.text == "ابدأ")
async def choose_term(message: types.Message):
    await message.answer("اختر الفصل:", reply_markup=term_kb)

@dp.message_handler(lambda m: m.text == "📘 الفصل الأول")
async def term1(message: types.Message):
    await message.answer("مواد الفصل الأول:", reply_markup=subjects_kb(TERM1_SUBJECTS))

@dp.message_handler(lambda m: m.text == "📗 الفصل الثاني")
async def term2(message: types.Message):
    await message.answer("مواد الفصل الثاني:", reply_markup=subjects_kb(TERM2_SUBJECTS))

# ================== إرسال الملفات ==================
@dp.message_handler(lambda m: m.text in TERM1_SUBJECTS + TERM2_SUBJECTS)
async def send_files(message: types.Message):
    term = "term1" if message.text in TERM1_SUBJECTS else "term2"
    path = os.path.join(SUBJECTS_DIR, term, message.text)

    if not os.path.exists(path):
        await message.answer("❌ لا يوجد ملفات لهذه المادة")
        return

    for file in os.listdir(path):
        fp = os.path.join(path, file)
        if file.lower().endswith(".pdf"):
            await message.answer_document(open(fp, "rb"))
        else:
            await message.answer_photo(open(fp, "rb"))

# ================== رجوع ==================
@dp.message_handler(lambda m: m.text == "🔙 رجوع")
async def back(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 لوحة الأدمن", reply_markup=admin_kb)
    else:
        await message.answer("🏠 القائمة الرئيسية", reply_markup=start_kb)

# ================== إحصائيات ==================
@dp.message_handler(lambda m: m.text == "📊 إحصائيات" and m.from_user.id == ADMIN_ID)
async def stats(message: types.Message):
    users = load_users()
    text = f"👥 العدد: {len(users)}\n\n"
    for u in users:
        text += f"👤 {u[1]}\n🔗 @{u[2]}\n🆔 {u[0]}\n──────\n"
    await message.answer(text, reply_markup=admin_kb)

# ================== طرد ==================
@dp.message_handler(lambda m: m.text == "🚫 طرد مستخدم" and m.from_user.id == ADMIN_ID)
async def ask_id(message: types.Message):
    await message.answer("أرسل ID المستخدم")

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text.isdigit())
async def kick_user(message: types.Message):
    remove_user(message.text)
    await message.answer("✅ تم الطرد – سيُطلب منه موافقة جديدة", reply_markup=admin_kb)

# ================== رسالة جماعية ==================
@dp.message_handler(lambda m: m.text == "📢 رسالة جماعية" and m.from_user.id == ADMIN_ID)
async def broadcast(message: types.Message):
    await message.answer("أرسل الرسالة")

    @dp.message_handler(lambda m: m.from_user.id == ADMIN_ID)
    async def send_all(msg: types.Message):
        for u in load_users():
            try:
                await bot.send_message(u[0], msg.text)
            except:
                pass
        await msg.answer("✅ تم الإرسال", reply_markup=admin_kb)

# ================== Render ==================
class Dummy(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Dummy).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
