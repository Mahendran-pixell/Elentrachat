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
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
coins INTEGER DEFAULT 0,
chats INTEGER DEFAULT 0,
referrals INTEGER DEFAULT 0,
last_daily INTEGER DEFAULT 0,
last_chat_day INTEGER DEFAULT 0,
chat_today INTEGER DEFAULT 0
)
""")

conn.commit()

# LEVEL SYSTEM
def get_level(chats):
    if chats >= 40:
        return "👑 Legend"
    elif chats >= 20:
        return "🔥 Chat Pro"
    elif chats >= 10:
        return "💬 Social Starter"
    else:
        return "🌱 Explorer"


# MENU
menu = ReplyKeyboardMarkup(
[
["🔎 Find Stranger","👤 Profile"],
["🎁 Daily Coins","🏆 Leaderboard"],
["👥 Invite Friends","🌍 Unlock Countries"],
["🚨 Report","ℹ️ Help"]
],
resize_keyboard=True
)

# START
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user_id,))
    conn.commit()

    await update.message.reply_text(
"""👋 Welcome to ElentraChat

✨ Anonymous random chatting
🔒 Private & Secure
⚡ Instant matching

⚠️ Please respect privacy
Do not screenshot conversations

Use menu below 👇""",
reply_markup=menu
)

# FIND CHAT
async def find(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    today = int(time.time()//86400)

    data = cursor.execute(
    "SELECT chat_today,last_chat_day FROM users WHERE user_id=?",(user_id,)
    ).fetchone()

    chats_today,last_day = data

    if today != last_day:
        chats_today = 0
        cursor.execute(
        "UPDATE users SET chat_today=0,last_chat_day=? WHERE user_id=?",
        (today,user_id)
        )
        conn.commit()

    if chats_today >= 50:
        await update.message.reply_text(
        "🚫 Daily limit reached (50 chats).\nCome back tomorrow."
        )
        return

    await update.message.reply_text("🔎 Searching for someone interesting...")
    await asyncio.sleep(1.5)

    if waiting_users:

        partner = waiting_users.pop(0)

        active_chats[user_id] = partner
        active_chats[partner] = user_id

        cursor.execute("UPDATE users SET chats=chats+1,chat_today=chat_today+1 WHERE user_id=?",(user_id,))
        cursor.execute("UPDATE users SET chats=chats+1,chat_today=chat_today+1 WHERE user_id=?",(partner,))
        conn.commit()

        chats = cursor.execute(
        "SELECT chats FROM users WHERE user_id=?",(user_id,)
        ).fetchone()[0]

        level = get_level(chats)

        await update.message.reply_text(
f"""✅ Connected!

🏆 Level: {level}
Say hi 👋"""
)

        await context.bot.send_message(
        partner,
        "✅ Connected!\nSay hi 👋"
        )

    else:
        waiting_users.append(user_id)
        await update.message.reply_text("⏳ Waiting for a stranger...")

# MESSAGE RELAY
async def handle_message(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    now = time.time()

    if user_id in message_time:
        if now-message_time[user_id] < 1:
            return

    message_time[user_id] = now

    if user_id in active_chats:

        partner = active_chats[user_id]

        try:
            await update.message.copy(chat_id=partner)
        except:
            pass


# PROFILE
async def profile(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    user = cursor.execute(
    "SELECT coins,chats,referrals FROM users WHERE user_id=?",
    (user_id,)
    ).fetchone()

    coins,chats,refs = user

    level = get_level(chats)

    await update.message.reply_text(
f"""👤 Profile

🏆 Level: {level}
💬 Chats: {chats}
🪙 Coins: {coins}
👥 Referrals: {refs}"""
)

# DAILY COINS
async def daily(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    last = cursor.execute(
    "SELECT last_daily FROM users WHERE user_id=?",(user_id,)
    ).fetchone()[0]

    now = int(time.time())

    if now-last < 86400:
        await update.message.reply_text("⏳ Come back tomorrow.")
        return

    cursor.execute(
    "UPDATE users SET coins=coins+25,last_daily=? WHERE user_id=?",
    (now,user_id)
    )
    conn.commit()

    await update.message.reply_text("🎁 You received 25 coins!")

# INVITE
async def invite(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    bot_username = context.bot.username

    link = f"https://t.me/{bot_username}?start={user_id}"

    await update.message.reply_text(
f"""👥 Invite friends

Share this link:

{link}

Earn 30 coins per referral!"""
)

# LEADERBOARD
async def leaderboard(update:Update,context:ContextTypes.DEFAULT_TYPE):

    top = cursor.execute(
    "SELECT user_id,chats FROM users ORDER BY chats DESC LIMIT 10"
    ).fetchall()

    text = "🏆 Top Users\n\n"

    rank = 1

    for u in top:
        text += f"{rank}. {u[0]} — {u[1]} chats\n"
        rank += 1

    await update.message.reply_text(text)

# COUNTRY SHOP
async def countries(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""🌍 Unlock Countries

🇷🇺 Russia — 100 coins
🇬🇧 UK — 100 coins
🇰🇷 South Korea — 120 coins
🇯🇵 Japan — 120 coins

(Coming soon)"""
)

# REPORT
async def report(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""🚨 Report System

If someone abuses chat,
send message:

/report reason"""
)

# HELP
async def help_cmd(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""ℹ️ Commands

/start — open menu
🔎 Find Stranger — chat
👤 Profile — stats
🎁 Daily Coins — reward
👥 Invite — referral
🏆 Leaderboard — top users"""
)

# BUTTON HANDLER
async def buttons(update:Update,context:ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "🎁 Daily Coins":
        await daily(update,context)

    elif text == "🏆 Leaderboard":
        await leaderboard(update,context)

    elif text == "👥 Invite Friends":
        await invite(update,context)

    elif text == "🌍 Unlock Countries":
        await countries(update,context)

    elif text == "🚨 Report":
        await report(update,context)

    elif text == "ℹ️ Help":
        await help_cmd(update,context)

    else:
        await handle_message(update,context)


# RUN BOT
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,buttons))

print("ElentraChat running...")

app.run_polling()
