import os
import json
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler,
    ContextTypes, filters
)
from ollama import Client
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
BOT_TOKEN = os.getenv("BOT_TOKEN")

ollama_client = Client(host=OLLAMA_HOST)

HISTORY_FILE = "chat_history.json"

# تحميل الذاكرة من ملف json
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}

# حفظ الذاكرة إلى ملف json
def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)

chat_memory = load_history()

async def reset_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_memory.pop(user_id, None)
    save_history(chat_memory)
    await update.message.reply_text("🧠 تم مسح سجل المحادثة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    text = message.text

    if update.message.chat.type in ['group', 'supergroup']:
        bot_username = (await context.bot.get_me()).username
        if f"@{bot_username}" not in text:
            return
        text = text.replace(f"@{bot_username}", "").strip()

    user_id = str(update.effective_user.id)
    history = chat_memory.get(user_id, [])
    history.append({"role": "user", "content": text})

    if len(history) > 4:
        history = history[-4:]

    try:
        response = ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "أنت مساعد ذكي، تحلل وتشرح باختصار وعمق."}
            ] + history
        )
        reply = response['message']['content']
        await message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        history.append({"role": "assistant", "content": reply})
        chat_memory[user_id] = history
        save_history(chat_memory)

    except Exception as e:
        await message.reply_text("⚠️ حدث خطأ أثناء الاتصال بـ Ollama.")
        print(f"[❌] Error: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("reset", reset_history))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("[✅] Bot is running...")
    app.run_polling()

