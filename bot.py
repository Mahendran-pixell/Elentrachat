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
chats_today INTEGER DEFAULT 0,
last_daily INTEGER DEFAULT 0,
referrals INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals(
user_id INTEGER,
ref_by INTEGER
)
""")

conn.commit()

waiting_users = []
active_chats = {}
online_users = set()

MAIN_MENU = ReplyKeyboardMarkup([
["🔎 Find Stranger","👤 Profile"],
["🎁 Daily Coins","🏆 Leaderboard"],
["🌍 Country Shop","💎 VIP"],
["👥 Invite Friends","⚠️ Report"]
],resize_keyboard=True)

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id
    online_users.add(user_id)

    args = context.args

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

        if args:
            ref = int(args[0])

            if ref != user_id:

                cursor.execute(
                "INSERT INTO referrals VALUES(?,?)",
                (user_id,ref)
                )

                cursor.execute(
                "UPDATE users SET coins = coins + 20 WHERE user_id=?",
                (ref,)
                )

                conn.commit()

    await update.message.reply_text(
"""
👋 Welcome to ElentraChat

🔐 Private anonymous chat
⚡ Instant random matching

Choose an option 👇
""",
reply_markup=MAIN_MENU)

async def find(update,context):

    user_id = update.message.chat_id

    user = cursor.execute(
    "SELECT chats_today,vip FROM users WHERE user_id=?",
    (user_id,)
    ).fetchone()

    chats_today,vip = user

    if chats_today >= 50 and vip == 0:
        await update.message.reply_text(
        "❌ Daily chat limit reached.\nUpgrade VIP for unlimited chats.")
        return

    await update.message.reply_text(
    "🔎 Searching for someone interesting...")

    await asyncio.sleep(1)

    if waiting_users:

        partner = waiting_users.pop(0)

        active_chats[user_id] = partner
        active_chats[partner] = user_id

        await update.message.reply_text("✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

        cursor.execute(
        "UPDATE users SET chats_today = chats_today + 1 WHERE user_id=?",
        (user_id,)
        )
        conn.commit()

    else:

        waiting_users.append(user_id)

        await update.message.reply_text("⏳ Waiting for a stranger...")

async def relay(update,context):

    user_id = update.message.chat_id

    if user_id in active_chats:

        partner = active_chats[user_id]

        await update.message.copy(partner)

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

        await update.message.reply_text("🔎 Searching next...")

        await find(update,context)

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
    "Chat stopped.",
    reply_markup=MAIN_MENU)

async def daily(update,context):

    user_id = update.message.chat_id

    data = cursor.execute(
    "SELECT last_daily FROM users WHERE user_id=?",
    (user_id,)
    ).fetchone()

    now = int(time.time())

    if now - data[0] < 86400:

        await update.message.reply_text(
        "❌ You already claimed daily reward.")
        return

    cursor.execute(
    "UPDATE users SET coins = coins + 20,last_daily=? WHERE user_id=?",
    (now,user_id)
    )

    conn.commit()

    await update.message.reply_text(
    "🎁 You received 20 coins!")

async def profile(update,context):

    user_id = update.message.chat_id

    user = cursor.execute(
    "SELECT coins,vip,referrals FROM users WHERE user_id=?",
    (user_id,)
    ).fetchone()

    coins,vip,refs = user

    await update.message.reply_text(
f"""
👤 Profile

💰 Coins: {coins}
💎 VIP: {"Yes" if vip else "No"}
👥 Referrals: {refs}
""")

async def invite(update,context):

    user_id = update.message.chat_id

    link = f"https://t.me/ElentraChatBot?start={user_id}"

    await update.message.reply_text(
f"""
👥 Invite Friends

Invite link:
{link}

Earn 20 coins per referral!
""")

async def shop(update,context):

    await update.message.reply_text(
"""
🌍 Country Unlock Shop

🇷🇺 Russia — 100 coins
🇬🇧 UK — 100 coins
🇰🇷 Korea — 120 coins
🇯🇵 Japan — 120 coins
""")

async def vip(update,context):

    await update.message.reply_text(
"""
💎 VIP Benefits

• Unlimited chats
• All countries unlocked
• Priority matching

Contact admin for VIP.
""")

async def report(update,context):

    await update.message.reply_text(
    "⚠️ User reported.\nAdmin will review.")

async def stats(update,context):

    if update.message.chat_id != ADMIN_ID:
        return

    total = cursor.execute(
    "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    await update.message.reply_text(
f"""
📊 Bot Statistics

👥 Total users: {total}
🟢 Online users: {len(online_users)}
💬 Active chats: {len(active_chats)//2}
""")

async def menu(update,context):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "🎁 Daily Coins":
        await daily(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "👥 Invite Friends":
        await invite(update,context)

    elif text == "🌍 Country Shop":
        await shop(update,context)

    elif text == "💎 VIP":
        await vip(update,context)

    elif text == "⚠️ Report":
        await report(update,context)

    else:
        await relay(update,context)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("next",next_chat))
app.add_handler(CommandHandler("stop",stop))
app.add_handler(CommandHandler("stats",stats))

app.add_handler(MessageHandler(filters.TEXT,menu))

print("ElentraChat V7 running...")

app.run_polling()	
	
