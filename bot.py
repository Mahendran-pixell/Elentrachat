import sqlite3
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID = 123456789

# Database
conn = sqlite3.connect("elentra.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
premium INTEGER DEFAULT 0
)
""")

conn.commit()

waiting_users = []
active_chats = {}

menu_keyboard = [
["🔎 Find Stranger"],
["👤 Profile","💎 Premium"],
["📊 Stats","ℹ️ Help"]
]

menu = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user,))
    conn.commit()

    await update.message.reply_text(
"""👋 Welcome to ElentraChat

✨ Anonymous chat
🔒 Private conversations
🔥 Meet new people instantly

Choose an option below 👇""",
reply_markup=menu
)

# Find Stranger
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in waiting_users:
        return

    await update.message.reply_text("🔎 Searching for someone interesting...")

    if waiting_users:

        partner = waiting_users.pop(0)

        active_chats[user] = partner
        active_chats[partner] = user

        await context.bot.send_message(user,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        waiting_users.append(user)

        await update.message.reply_text("⏳ Waiting for a partner...")

        context.application.create_task(wait_messages(user,context))

# Waiting engagement messages
async def wait_messages(user,context):

    await asyncio.sleep(15)

    if user in waiting_users:
        await context.bot.send_message(
        user,
"""🔥 Many people are chatting right now!

💎 Premium users get priority matching."""
)

    await asyncio.sleep(20)

    if user in waiting_users:
        await context.bot.send_message(
        user,
"""🎁 Special Offer

Upgrade to Premium and unlock:

✨ Faster matching
💬 Unlimited chats
🌍 Country filters

Press 💎 Premium"""
)

# Stop Chat
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:

        partner = active_chats[user]

        del active_chats[user]
        del active_chats[partner]

        await context.bot.send_message(partner,"❌ Your partner disconnected.")
        await update.message.reply_text("Chat ended.")

    else:
        await update.message.reply_text("You are not in a chat.")

# Relay messages
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:

        partner = active_chats[user]

        await context.bot.copy_message(
        chat_id=partner,
        from_chat_id=user,
        message_id=update.message.message_id
        )

# Profile
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    data = cursor.execute(
    "SELECT premium FROM users WHERE user_id=?",(user,)
    ).fetchone()

    premium = "Yes 💎" if data[0] else "No"

    await update.message.reply_text(
f"""👤 Your Profile

Premium: {premium}

Upgrade to unlock more features."""
)

# Premium
async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""💎 Premium Subscription

✨ Unlimited chats
⚡ Faster matches
🌍 Country filters
🚫 No limits

Price: $2 / month

Contact admin to activate."""
)

# Stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    waiting = len(waiting_users)
    chats = len(active_chats)//2

    await update.message.reply_text(
f"""📊 Bot Stats

Users: {total}
Waiting: {waiting}
Active chats: {chats}"""
)

# Button handler
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "💎 Premium":
        await premium(update,context)

    elif text == "📊 Stats":
        await stats(update,context)

    elif text == "ℹ️ Help":
        await update.message.reply_text(
"""Use 🔎 Find Stranger to start chatting.

Type /stop to leave a chat."""
)

# App
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("stop",stop))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,buttons))
app.add_handler(MessageHandler(filters.ALL,relay))

print("ElentraChat V12 running 🚀")

app.run_polling()	

