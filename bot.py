import sqlite3
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID = 8232389772

# DATABASE
conn = sqlite3.connect("elentra.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
gender TEXT,
country TEXT,
vip INTEGER DEFAULT 0,
coins INTEGER DEFAULT 10,
agreed INTEGER DEFAULT 0
)
""")
conn.commit()

waiting_users = []
active_chats = {}

menu_keyboard = [
["🔎 Find Stranger"],
["👤 Profile","💎 VIP"],
["🌍 Set Country","👦 Gender"],
["📜 Terms","ℹ️ Help"]
]

menu = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

terms = """
📜 ElentraChat Rules

🔒 Privacy
Chats are anonymous.

🚫 Forbidden
Spam
Harassment
Illegal content

⚠️ Safety
Do not share personal info.

Type /agree to continue.
"""

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user,))
    conn.commit()

    agreed = cursor.execute("SELECT agreed FROM users WHERE user_id=?",(user,)).fetchone()[0]

    if agreed == 0:
        await update.message.reply_text(terms)
        return

    await update.message.reply_text(
"👋 Welcome to ElentraChat!",
reply_markup=menu
)

# AGREE TERMS
async def agree(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("UPDATE users SET agreed=1 WHERE user_id=?",(user,))
    conn.commit()

    await update.message.reply_text(
"✅ Rules accepted. Start chatting!",
reply_markup=menu
)

# FIND STRANGER
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if waiting_users:

        partner = waiting_users.pop(0)

        active_chats[user] = partner
        active_chats[partner] = user

        await context.bot.send_message(user,"✅ Connected!")
        await context.bot.send_message(partner,"✅ Connected!")

    else:

        waiting_users.append(user)

        await update.message.reply_text("🔎 Searching for someone...")

# STOP CHAT
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:

        partner = active_chats[user]

        del active_chats[user]
        del active_chats[partner]

        await context.bot.send_message(partner,"❌ Partner left chat")
        await update.message.reply_text("Chat ended")

# RELAY MESSAGES
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

    user = update.effective_user.id

    data = cursor.execute(
        "SELECT coins,vip FROM users WHERE user_id=?",(user,)
    ).fetchone()

    coins,vip = data

    status = "VIP 💎" if vip else "Free"

    await update.message.reply_text(
f"""👤 Profile

Status: {status}
Coins: {coins}"""
)

# VIP PAGE
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""💎 VIP Membership

Benefits:

⚡ Faster matches
💬 Unlimited chats
🎯 Filters

Contact admin to activate."""
)

# SET COUNTRY
async def set_country(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"🌍 Send your country name."
)

# SET GENDER
async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"👦 Send your gender (male/female)"
)

# HELP
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""ℹ️ Help

🔎 Find Stranger → chat
/stop → leave chat"""
)

# TERMS BUTTON
async def show_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(terms)

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
"""👋 Someone is waiting for you on ElentraChat!

💬 New people joined today.

Tap /start to chat."""
)

            except:
                pass

# POST INIT
async def post_init(app):
    asyncio.create_task(reminder_loop(app))

# BUTTON HANDLER
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "💎 VIP":
        await vip(update,context)

    elif text == "🌍 Set Country":
        await set_country(update,context)

    elif text == "👦 Gender":
        await gender(update,context)

    elif text == "📜 Terms":
        await show_terms(update,context)

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

print("ElentraChat V16 running 🚀")

app.run_polling()
