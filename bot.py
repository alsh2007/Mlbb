import os
import json
import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import openai

# ======== إعدادات البوت ========
BOT_TOKEN = os.getenv("BOT_TOKEN")  # خلي التوكن بالـEnv بدل ما تكتبه بالكود
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# ======== ذاكرة المحادثة ========
memory = {}

# ======== قاعدة بيانات الأبطال ========
DB_FILE = "heroes_db.json"

def load_heroes_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_heroes_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

heroes_db = load_heroes_db()

# ======== تحديث الأبطال تلقائي ========
def update_heroes_db():
    url = "https://liquipedia.net/mobilelegends/api.php?action=parse&page=List_of_Heroes&format=json"  # مثال API
    try:
        res = requests.get(url, timeout=10).json()
        new_heroes = {}  
        for hero_name in res.get("heroes", []):
            new_heroes[hero_name] = {
                "role": "Unknown",
                "counters": [],
                "tips": ""
            }
        heroes_db.update(new_heroes)
        save_heroes_db(heroes_db)
        print(f"تم تحديث قاعدة الأبطال: {len(new_heroes)} أبطال جدد")
    except Exception as e:
        print(f"خطأ بالتحديث: {e}")

# ======== البحث في قاعدة الأبطال ========
def get_hero_info(hero_name):
    return heroes_db.get(hero_name.strip().title(), None)

# ======== تحليل الصور ========
async def analyze_photo(file_path):
    try:
        with open(file_path, "rb") as f:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "حلل هذه الصورة من Mobile Legends وحدد اسم البطل وأفضل الكاونترات والنصائح."}
                ],
                files=[{"name": "screenshot.png", "file": f}]
            )
        return response.choices[0].message.content
    except Exception as e:
        return f"خطأ بتحليل الصورة: {e}"

# ======== معالجة الرسائل ========
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # جروبات → رد فقط عند المنشن
    if update.message.chat.type in ["group", "supergroup"]:
        if not context.bot.id in [ent.user.id for ent in update.message.entities if ent.type == "mention"]:
            return

    # ذاكرة محادثة ساعة
    if user_id not in memory:
        memory[user_id] = []
    memory[user_id] = [msg for msg in memory[user_id] if datetime.now() - msg["time"] < timedelta(hours=1)]

    # ==== إذا الصورة موجودة ====
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        file_path = f"temp_{user_id}.jpg"
        await file.download_to_drive(file_path)
        analysis = await analyze_photo(file_path)
        await update.message.reply_text(analysis)
        memory[user_id].append({"text": analysis, "time": datetime.now()})
        os.remove(file_path)
        return

    # ==== إذا نص ====
    text = update.message.text or ""
    memory[user_id].append({"text": text, "time": datetime.now()})

    # البحث في قاعدة الأبطال
    hero_info = get_hero_info(text)
    if hero_info:
        reply = f"البطل: {text.title()}\nالدور: {hero_info['role']}\nكاونترات: {', '.join(hero_info['counters'])}\nنصائح: {hero_info['tips']}"
        await update.message.reply_text(reply)
        return

    # أي سؤال عام → الذكاء الاصطناعي
    conversation = "\n".join([msg["text"] for msg in memory[user_id]])
    prompt = f"أنت مساعد ذكي للعبة Mobile Legends. اللاعب كتب: {text}\nالسياق السابق: {conversation}\nجاوب باختصار ودقيق:"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        await update.message.reply_text(response.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text(f"صار خطأ: {e}")

# ======== بدء البوت ========
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("هلو! أنا بوت مساعد Mobile Legends. أسألني عن أي بطل أو أرسل صورة!")

# ======== تشغيل البوت ========
update_heroes_db()  # تحديث عند التشغيل
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

print("البوت شغال مع تحليل الصور والنصوص 😎")
app.run_polling()
