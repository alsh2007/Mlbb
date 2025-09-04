import os
import json
import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# ======== إعدادات البوت ========
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")  # خد API مجاني من Hugging Face

# ======== ذاكرة المحادثة ========
memory = {}

# ======== قاعدة بيانات الأبطال ========
DB_FILE = "heroes_db.json"

def load_heroes_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

heroes_db = load_heroes_db()

# ======== البحث في قاعدة الأبطال ========
def get_hero_info(hero_name):
    return heroes_db.get(hero_name.strip().title(), None)

# ======== محادثة ذكية باستخدام Hugging Face ========
def chat_with_hf(prompt):
    url = "https://api-inference.huggingface.co/models/gpt2"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": prompt}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        res_json = response.json()
        if isinstance(res_json, list) and "generated_text" in res_json[0]:
            return res_json[0]["generated_text"]
        return "معليش، ما قدرت أفهم سؤالك 😅"
    except Exception as e:
        return f"صار خطأ بالمحادثة: {e}"

# ======== معالجة الرسائل ========
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # ذاكرة محادثة ساعة
    if user_id not in memory:
        memory[user_id] = []
    memory[user_id] = [msg for msg in memory[user_id] if datetime.now() - msg["time"] < timedelta(hours=1)]

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
    reply = chat_with_hf(prompt)
    await update.message.reply_text(reply)

# ======== بدء البوت ========
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("هلو! أنا بوت مساعد Mobile Legends. أسألني عن أي بطل أو أرسل نص!")

# ======== تشغيل البوت ========
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

print("البوت شغال على Hugging Face بدون OpenAI 😎")
app.run_polling()
