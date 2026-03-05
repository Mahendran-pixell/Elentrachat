import os
import sqlite3
import asyncio
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8232389772

conn = sqlite3.connect("elentra.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
coins INTEGER DEFAULT 50,
vip INTEGER DEFAULT 0,
likes INTEGER DEFAULT 0,
reports INTEGER DEFAULT 0,
banned INTEGER DEFAULT 0
)
""")

conn.commit()

waiting_users = []
active_chats = {}

MAIN_MENU = ReplyKeyboardMarkup([
["🔎 Find Stranger","👤 Profile"],
["🎁 Daily Coins","🏆 Leaderboard"],
["👥 Invite Friends","⚠️ Report"]
],resize_keyboard=True)

RATING_MENU = ReplyKeyboardMarkup([
["👍 Good User","👎 Bad User"]
],resize_keyboard=True)

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    user = cursor.execute(
    "SELECT user_id FROM users WHERE user_id=?",
    (user_id,)
    ).fetchone()

    if not user:
        cursor.execute(
        "INSERT INTO users(user_id) VALUES(?)",
        (user_id,)
        )
        conn.commit()

    banned = cursor.execute(
    "SELECT banned FROM users WHERE user_id=?",
    (user_id,)
    ).fetchone()[0]

    if banned:
        await update.message.reply_text("🚫 You are banned.")
        return

    await update.message.reply_text(
"""
👋 Welcome to ElentraChat V8

🔐 Anonymous chat
⚡ Instant matching

Choose option 👇
""",
reply_markup=MAIN_MENU)

async def find(update,context):

    user_id = update.message.chat_id

    await update.message.reply_text(
    "🔎 Searching for someone interesting...")

    await asyncio.sleep(1)

    if waiting_users:

        partner = waiting_users.pop(0)

        active_chats[user_id] = partner
        active_chats[partner] = user_id

        await update.message.reply_text("✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        waiting_users.append(user_id)

        await update.message.reply_text("⏳ Waiting for stranger...")

async def relay(update,context):

    user_id = update.message.chat_id

    if user_id in active_chats:

        partner = active_chats[user_id]

        try:
            await update.message.copy(partner)
        except:
            pass

async def next_chat(update,context):

    user_id = update.message.chat_id

    if user_id in active_chats:

        partner = active_chats[user_id]

        active_chats.pop(user_id,None)
        active_chats.pop(partner,None)

        await context.bot.send_message(
        partner,
        "⚠️ Stranger skipped."
        )

        await update.message.reply_text(
        "⭐ Rate the user",
        reply_markup=RATING_MENU)

async def stop(update,context):

    user_id = update.message.chat_id

    if user_id in active_chats:

        partner = active_chats[user_id]

        active_chats.pop(user_id,None)
        active_chats.pop(partner,None)

        await context.bot.send_message(
        partner,
        "⚠️ Stranger disconnected."
        )

    await update.message.reply_text(
    "⭐ Rate the user",
    reply_markup=RATING_MENU)

async def rating(update,context):

    user_id = update.message.chat_id
    text = update.message.text

    if text == "👍 Good User":

        cursor.execute(
        "UPDATE users SET likes = likes + 1 WHERE user_id=?",
        (user_id,)
        )

    if text == "👎 Bad User":

        cursor.execute(
        "UPDATE users SET reports = reports + 1 WHERE user_id=?",
        (user_id,)
        )

    conn.commit()

    await update.message.reply_text(
    "Thanks for feedback!",
    reply_markup=MAIN_MENU)

async def profile(update,context):

    user_id = update.message.chat_id

    data = cursor.execute(
    "SELECT coins,vip,likes,reports FROM users WHERE user_id=?",
    (user_id,)
    ).fetchone()

    coins,vip,likes,reports = data

    await update.message.reply_text(
f"""
👤 Profile

💰 Coins: {coins}
💎 VIP: {"Yes" if vip else "No"}
👍 Likes: {likes}
👎 Reports: {reports}
""")

async def report(update,context):

    user_id = update.message.chat_id

    await context.bot.send_message(
    ADMIN_ID,
f"⚠️ Report received from user {user_id}")

    await update.message.reply_text(
    "Report sent to admin.")

async def stats(update,context):

    if update.message.chat_id != ADMIN_ID:
        return

    total = cursor.execute(
    "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    banned = cursor.execute(
    "SELECT COUNT(*) FROM users WHERE banned=1"
    ).fetchone()[0]

    await update.message.reply_text(
f"""
📊 Bot Stats

👥 Total users: {total}
🚫 Banned users: {banned}
💬 Active chats: {len(active_chats)//2}
""")

async def ban(update,context):

    if update.message.chat_id != ADMIN_ID:
        return

    user = int(context.args[0])

    cursor.execute(
    "UPDATE users SET banned=1 WHERE user_id=?",
    (user,)
    )

    conn.commit()

    await update.message.reply_text(
    f"User {user} banned.")

async def unban(update,context):

    if update.message.chat_id != ADMIN_ID:
        return

    user = int(context.args[0])

    cursor.execute(
    "UPDATE users SET banned=0 WHERE user_id=?",
    (user,)
    )

    conn.commit()

    await update.message.reply_text(
    f"User {user} unbanned.")

async def broadcast(update,context):

    if update.message.chat_id != ADMIN_ID:
        return

    msg = " ".join(context.args)

    users = cursor.execute(
    "SELECT user_id FROM users"
    ).fetchall()

    count = 0

    for u in users:
        try:
            await context.bot.send_message(u[0],msg)
            count += 1
        except:
            pass

    await update.message.reply_text(
    f"Broadcast sent to {count} users.")

async def menu(update,context):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "⚠️ Report":
        await report(update,context)

    elif text in ["👍 Good User","👎 Bad User"]:
        await rating(update,context)

    else:
        await relay(update,context)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("next",next_chat))
app.add_handler(CommandHandler("stop",stop))
app.add_handler(CommandHandler("stats",stats))
app.add_handler(CommandHandler("ban",ban))
app.add_handler(CommandHandler("unban",unban))
app.add_handler(CommandHandler("broadcast",broadcast))

app.add_handler(MessageHandler(filters.TEXT,menu))

print("ElentraChat V8 running")

app.run_polling()	

