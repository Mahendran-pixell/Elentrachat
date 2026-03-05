import sqlite3
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID = 123456789

# DATABASE
conn = sqlite3.connect("elentra.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
agreed INTEGER DEFAULT 0
)
""")
conn.commit()

waiting_users = []
active_chats = {}

# MENU
menu_keyboard = [
["🔎 Find Stranger"],
["👤 Profile","💎 Premium"],
["📜 Terms","ℹ️ Help"]
]

menu = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

# TERMS
terms_text = """
📜 ElentraChat Terms & Rules

🔒 Privacy
• Chats are anonymous
• Do not share personal information

🚫 Forbidden
• Spam
• Harassment
• Illegal content

⚠️ Safety
• Do not send sensitive photos

By using ElentraChat you agree to these rules.

Type /agree to continue.
"""

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user,))
    conn.commit()

    agreed = cursor.execute("SELECT agreed FROM users WHERE user_id=?",(user,)).fetchone()[0]

    if agreed == 0:
        await update.message.reply_text(terms_text)
        return

    await update.message.reply_text(
"""👋 Welcome to ElentraChat

✨ Anonymous random chat
🔒 Private & secure""",
reply_markup=menu
)

# AGREE
async def agree(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("UPDATE users SET agreed=1 WHERE user_id=?",(user,))
    conn.commit()

    await update.message.reply_text(
"✅ Thanks for accepting the rules.\n\nYou can now start chatting!",
reply_markup=menu
)

# FIND
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:
        return

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

# STOP
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:

        partner = active_chats[user]

        del active_chats[user]
        del active_chats[partner]

        await context.bot.send_message(partner,"❌ Your partner disconnected.")
        await update.message.reply_text("Chat ended.")

# RELAY
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:

        partner = active_chats[user]

        await context.bot.copy_message(
            chat_id=partner,
            from_chat_id=user,
            message_id=update.message.message_id
        )

# PROFILE
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""👤 Profile

Status: Free user

Upgrade to 💎 Premium for faster matches."""
)

# PREMIUM
async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""💎 Premium

✨ Faster matching
💬 Unlimited chats
🚀 Priority queue

Contact admin to activate."""
)

# TERMS BUTTON
async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(terms_text)

# HELP
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""ℹ️ Help

🔎 Find Stranger → Start chat
/stop → End chat

Stay respectful and enjoy chatting!"""
)

# ADMIN STATS
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

# REMINDER LOOP
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

# START REMINDER
async def post_init(app):
    asyncio.create_task(reminder_loop(app))

# BUTTON HANDLER
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "💎 Premium":
        await premium(update,context)

    elif text == "📜 Terms":
        await terms(update,context)

    elif text == "ℹ️ Help":
        await help_cmd(update,context)

# APP
app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("agree",agree))
app.add_handler(CommandHandler("stop",stop))
app.add_handler(CommandHandler("stats",stats))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,buttons))
app.add_handler(MessageHandler(filters.ALL,relay))

print("ElentraChat V15 ULTRA running 🚀")

app.run_polling()		

