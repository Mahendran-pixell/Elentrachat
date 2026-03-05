import sqlite3
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID = 123456789

conn = sqlite3.connect("elentra.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY
)
""")

conn.commit()

waiting_users = []
active_chats = {}

menu_keyboard = [
["🔎 Find Stranger"],
["👤 Profile","💎 Premium"],
["ℹ️ Help"]
]

menu = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

# start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)",(user,))
    conn.commit()

    await update.message.reply_text(
"""👋 Welcome to ElentraChat

✨ Anonymous random chat
🔒 Private & secure

Choose an option 👇""",
reply_markup=menu
)

# find partner
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if waiting_users:

        partner = waiting_users.pop(0)

        active_chats[user] = partner
        active_chats[partner] = user

        await context.bot.send_message(user,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        waiting_users.append(user)

        await update.message.reply_text("🔎 Searching for someone interesting...")
        await update.message.reply_text("⏳ Waiting for partner...")

        asyncio.create_task(wait_messages(user,context))

# waiting engagement
async def wait_messages(user,context):

    await asyncio.sleep(15)

    if user in waiting_users:
        await context.bot.send_message(
        user,
"""👀 Someone else is searching too...

💎 Premium users get faster matches."""
)

    await asyncio.sleep(20)

    if user in waiting_users:
        await context.bot.send_message(
        user,
"""🔥 Many people are chatting right now!

Tap 🔎 Find Stranger to meet them."""
)

# stop chat
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:

        partner = active_chats[user]

        del active_chats[user]
        del active_chats[partner]

        await context.bot.send_message(partner,"❌ Your partner disconnected.")

        await update.message.reply_text("Chat ended.")

# relay messages
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:

        partner = active_chats[user]

        await context.bot.copy_message(
        chat_id=partner,
        from_chat_id=user,
        message_id=update.message.message_id
        )

# profile
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""👤 Your Profile

Status: Free user

Upgrade to 💎 Premium for faster matches."""
)

# premium page
async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""💎 Premium Subscription

✨ Faster matching
💬 Unlimited chats
🌍 Future filters

Contact admin to activate."""
)

# admin stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    await update.message.reply_text(
f"""📊 Bot Stats

Users: {total}
Waiting: {len(waiting_users)}
Active chats: {len(active_chats)//2}"""
)

# reminder broadcast
async def reminder_loop(app):

    while True:

        await asyncio.sleep(21600)

        users = cursor.execute("SELECT user_id FROM users").fetchall()

        for u in users:

            try:

                await app.bot.send_message(
                u[0],
"""👋 Hey!

💬 People are waiting for you on ElentraChat.

🔥 Someone interesting might be online now!

Tap /start to chat."""
)

            except:
                pass

# buttons
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "💎 Premium":
        await premium(update,context)

    elif text == "ℹ️ Help":
        await update.message.reply_text(
"Use 🔎 Find Stranger to start chatting.\nType /stop to leave chat."
)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("stop",stop))
app.add_handler(CommandHandler("stats",stats))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,buttons))
app.add_handler(MessageHandler(filters.ALL,relay))

app.create_task(reminder_loop(app))

print("ElentraChat V14 running 🚀")

app.run_polling()
