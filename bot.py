import sqlite3
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 8232389772

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
vip INTEGER DEFAULT 0,
chats_today INTEGER DEFAULT 0,
last_reset INTEGER DEFAULT 0
)
""")

waiting_users = []
active_chats = {}
online_users = set()

DAILY_LIMIT = 50


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id
    online_users.add(user_id)

    cursor.execute(
        "INSERT OR IGNORE INTO users(id,last_reset) VALUES(?,?)",
        (user_id, int(time.time()))
    )
    conn.commit()

    keyboard = [
        ["🔍 Find Stranger", "👤 Profile"],
        ["💎 VIP", "🏆 Leaderboard"],
        ["👥 Invite Friends", "ℹ️ Help"]
    ]

    await update.message.reply_text(
        "👋 Welcome to ElentraChat\n\nAnonymous random chat\n\nChoose an option",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# DAILY LIMIT
def check_limit(user_id):

    data = cursor.execute(
        "SELECT chats_today,last_reset,vip FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    chats_today, last_reset, vip = data

    now = int(time.time())

    if now - last_reset > 86400:
        cursor.execute(
            "UPDATE users SET chats_today=0,last_reset=? WHERE id=?",
            (now, user_id)
        )
        conn.commit()
        chats_today = 0

    if vip == 1:
        return True

    if chats_today >= DAILY_LIMIT:
        return False

    cursor.execute(
        "UPDATE users SET chats_today=chats_today+1 WHERE id=?",
        (user_id,)
    )
    conn.commit()

    return True


# FIND CHAT
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    if not check_limit(user_id):

        await update.message.reply_text(
            "⚠️ Daily limit reached (50 chats).\n\n💎 Buy VIP for unlimited chats."
        )
        return

    if waiting_users:

        partner = waiting_users.pop(0)

        active_chats[user_id] = partner
        active_chats[partner] = user_id

        await context.bot.send_message(user_id, "✅ Connected! Say hi 👋")
        await context.bot.send_message(partner, "✅ Connected! Say hi 👋")

    else:

        waiting_users.append(user_id)

        await update.message.reply_text("⏳ Waiting for stranger...")


# STOP CHAT
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    if user_id in active_chats:

        partner = active_chats.pop(user_id)

        if partner in active_chats:
            active_chats.pop(partner)

        await context.bot.send_message(
            partner,
            "⚠️ Stranger disconnected."
        )

        await update.message.reply_text("Chat ended.")


# MESSAGE FORWARD
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    if user_id in active_chats:

        partner = active_chats[user_id]

        await context.bot.send_message(
            partner,
            update.message.text
        )


# VIP INFO
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
💎 VIP Membership

Benefits:
♾ Unlimited chats
⚡ Faster matching
🌍 Future country unlock

Price: ₹99 / month

Send payment screenshot to:
@yourusername
"""

    await update.message.reply_text(text)


# ADMIN STATS
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != ADMIN_ID:
        return

    total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    vip = cursor.execute("SELECT COUNT(*) FROM users WHERE vip=1").fetchone()[0]

    online = len(online_users)
    active = len(active_chats) // 2

    await update.message.reply_text(f"""
📊 Bot Stats

👥 Total Users: {total}
🟢 Online Users: {online}
💬 Active Chats: {active}
💎 VIP Users: {vip}
""")


# ADMIN ADD VIP
async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != ADMIN_ID:
        return

    user = int(context.args[0])

    cursor.execute(
        "UPDATE users SET vip=1 WHERE id=?",
        (user,)
    )
    conn.commit()

    await update.message.reply_text("VIP activated")


# BUTTON HANDLER
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🔍 Find Stranger":
        await find(update, context)

    elif text == "💎 VIP":
        await vip(update, context)


# RUN BOT
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("addvip", addvip))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, buttons))
app.add_handler(MessageHandler(filters.TEXT, relay))

print("ElentraChat V10 running...")

if __name__ == "__main__":
    app.run_polling()
