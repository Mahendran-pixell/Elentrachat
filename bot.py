import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID = 8232389772

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
name TEXT,
age TEXT,
gender TEXT,
country TEXT,
partner TEXT
)
""")

waiting = []
active = {}

menu = ReplyKeyboardMarkup([
["🔎 Find Stranger"],
["👤 Profile", "💎 VIP"]
], resize_keyboard=True)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user,))
    conn.commit()

    await update.message.reply_text(
"""👋 Welcome to ElentraChat

Use menu to start chatting""",
reply_markup=menu)

# PROFILE
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    data = cursor.execute(
    "SELECT name,age,gender,country,partner FROM users WHERE user_id=?",
    (user,)
    ).fetchone()

    await update.message.reply_text(
f"""👤 Profile

Name: {data[0]}
Age: {data[1]}
Gender: {data[2]}
Country: {data[3]}
Looking for: {data[4]}
"""
)

# VIP
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""💎 VIP Membership

1 Month VIP – ₹49
3 Months VIP – ₹99
Lifetime – ₹299

UPI Payment:
hatmahendran267r@ybl

After payment send screenshot to:
@Elentraadmin001
"""
)

# FIND STRANGER
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if waiting:

        partner = waiting.pop(0)

        active[user] = partner
        active[partner] = user

        await context.bot.send_message(user,"✅ Connected! Say hi")
        await context.bot.send_message(partner,"✅ Connected! Say hi")

    else:

        waiting.append(user)

        await update.message.reply_text("🔎 Searching for partner...")

# STOP
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active:

        partner = active[user]

        del active[user]
        del active[partner]

        await context.bot.send_message(partner,"❌ Partner left chat")
        await update.message.reply_text("Chat ended")

# NEXT
async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await stop(update,context)
    await find(update,context)

# RELAY MESSAGES
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active:

        partner = active[user]

        await context.bot.copy_message(
        chat_id=partner,
        from_chat_id=user,
        message_id=update.message.message_id
        )

# ADMIN STATS
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    await update.message.reply_text(
f"""📊 Bot Stats

Users: {users}
Waiting: {len(waiting)}
Active chats: {len(active)//2}
"""
)

# BUTTONS
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "💎 VIP":
        await vip(update,context)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("next", next_chat))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CommandHandler("stats", stats))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, buttons))
app.add_handler(MessageHandler(filters.ALL, relay))

print("ElentraChat running")

app.run_polling()
