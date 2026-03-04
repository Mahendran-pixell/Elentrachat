import os
import asyncio
import sqlite3
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")

waiting_users = []
active_chats = {}
message_time = {}

# DATABASE
conn = sqlite3.connect("elentra.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY,
coins INTEGER DEFAULT 0,
chats INTEGER DEFAULT 0,
last_daily INTEGER DEFAULT 0
)
""")
conn.commit()


# LEVEL SYSTEM
def get_level(chats):
    if chats >= 30:
        return "👑 Legend"
    elif chats >= 15:
        return "🔥 Chat Pro"
    elif chats >= 5:
        return "💬 Social Starter"
    else:
        return "🌱 Explorer"


# MENU
menu_keyboard = ReplyKeyboardMarkup(
[
["🔎 Find Stranger", "👤 Profile"],
["🎁 Daily Reward", "🏆 Leaderboard"],
["ℹ️ Help"]
],
resize_keyboard=True
)


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)",(user_id,))
    conn.commit()

    await update.message.reply_text(
"""👋 Welcome to ElentraChat

✨ Talk anonymously with strangers
🔒 Private & Secure
⚡ Instant random matching

Use the menu below 👇""",
reply_markup=menu_keyboard
)


# FIND STRANGER
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    await update.message.reply_text("🔎 Searching for someone interesting...")
    await asyncio.sleep(1.5)

    if user_id in active_chats:
        await update.message.reply_text("⚠️ You are already chatting.")
        return

    if waiting_users:
        partner = waiting_users.pop(0)

        active_chats[user_id] = partner
        active_chats[partner] = user_id

        cursor.execute("UPDATE users SET chats = chats + 1 WHERE user_id=?",(user_id,))
        cursor.execute("UPDATE users SET chats = chats + 1 WHERE user_id=?",(partner,))
        conn.commit()

        chats = cursor.execute("SELECT chats FROM users WHERE user_id=?",(user_id,)).fetchone()[0]
        level = get_level(chats)

        await update.message.reply_text(
f"✅ Connected!\n🏆 Level: {level}\nSay hi 👋"
)

        await context.bot.send_message(
partner,
"✅ Connected!\nSay hi 👋"
)

    else:
        waiting_users.append(user_id)
        await update.message.reply_text("⏳ Waiting for a stranger...")


# MESSAGE RELAY
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    # Anti spam
    now = time.time()

    if user_id in message_time:
        if now - message_time[user_id] < 1:
            await update.message.reply_text("⚠️ Slow down.")
            return

    message_time[user_id] = now

    if user_id in active_chats:
        partner = active_chats[user_id]

        try:
            await update.message.copy(chat_id=partner)
        except:
            pass


# PROFILE
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    user = cursor.execute(
    "SELECT coins,chats FROM users WHERE user_id=?",(user_id,)
    ).fetchone()

    coins,chats = user
    level = get_level(chats)

    await update.message.reply_text(
f"""👤 Your Profile

🏆 Level: {level}
💬 Chats: {chats}
🪙 Coins: {coins}"""
)


# DAILY
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    last = cursor.execute(
    "SELECT last_daily FROM users WHERE user_id=?",(user_id,)
    ).fetchone()[0]

    now = int(time.time())

    if now - last < 86400:
        await update.message.reply_text("⏳ Come back tomorrow.")
        return

    cursor.execute(
    "UPDATE users SET coins = coins + 20, last_daily=? WHERE user_id=?",
    (now,user_id)
    )

    conn.commit()

    await update.message.reply_text(
"🎁 Daily reward claimed!\n🪙 +20 coins"
)


# LEADERBOARD
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    top = cursor.execute(
    "SELECT user_id,chats FROM users ORDER BY chats DESC LIMIT 5"
    ).fetchall()

    text = "🏆 Top Chatters\n\n"

    rank = 1

    for user in top:
        text += f"{rank}. {user[0]} — {user[1]} chats\n"
        rank += 1

    await update.message.reply_text(text)


# HELP
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""ℹ️ Help

/start - open menu
🔎 Find Stranger - start chat
👤 Profile - view stats
🎁 Daily Reward - get coins
🏆 Leaderboard - top users"""
)


# BUTTON HANDLER
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "🎁 Daily Reward":
        await daily(update,context)

    elif text == "🏆 Leaderboard":
        await leaderboard(update,context)

    elif text == "ℹ️ Help":
        await help_cmd(update,context)

    else:
        await handle_message(update,context)


# BUILD BOT
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,buttons))

print("Bot running...")
app.run_polling()
