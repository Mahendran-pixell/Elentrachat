import sqlite3
import time
from telegram import *
from telegram.ext import *

TOKEN="YOUR_TOKEN"
ADMIN_ID=8232389772

conn=sqlite3.connect("users.db",check_same_thread=False)
cursor=conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
vip INTEGER DEFAULT 0,
coins INTEGER DEFAULT 0,
chats_today INTEGER DEFAULT 0,
last_reset INTEGER DEFAULT 0
)
""")

waiting_users=[]
active_chats={}
online_users=set()

DAILY_LIMIT=50


async def start(update,context):
    user_id=update.message.chat_id
    online_users.add(user_id)

    cursor.execute("INSERT OR IGNORE INTO users(id,last_reset) VALUES(?,?)",(user_id,int(time.time())))
    conn.commit()

    keyboard=[
        ["🔍 Find Stranger","👤 Profile"],
        ["🎁 Daily Coins","🏆 Leaderboard"],
        ["👥 Invite Friends","💎 VIP"],
        ["⚠️ Report"]
    ]

    await update.message.reply_text(
    "👋 Welcome to ElentraChat\n\nChoose an option",
    reply_markup=ReplyKeyboardMarkup(keyboard,resize_keyboard=True)
    )


def check_limit(user_id):

    data=cursor.execute(
    "SELECT chats_today,last_reset,vip FROM users WHERE id=?",(user_id,)
    ).fetchone()

    chats,last_reset,vip=data

    now=int(time.time())

    if now-last_reset>86400:
        cursor.execute("UPDATE users SET chats_today=0,last_reset=? WHERE id=?",(now,user_id))
        conn.commit()
        chats=0

    if vip:
        return True

    if chats>=DAILY_LIMIT:
        return False

    cursor.execute("UPDATE users SET chats_today=chats_today+1 WHERE id=?",(user_id,))
    conn.commit()

    return True


async def find(update,context):

    user_id=update.message.chat_id

    if not check_limit(user_id):
        await update.message.reply_text(
        "⚠️ Daily limit reached (50 chats).\nBuy VIP for unlimited chats."
        )
        return

    if waiting_users:
        partner=waiting_users.pop(0)

        active_chats[user_id]=partner
        active_chats[partner]=user_id

        await context.bot.send_message(user_id,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:
        waiting_users.append(user_id)
        await update.message.reply_text("⏳ Waiting for stranger...")


async def stop(update,context):

    user_id=update.message.chat_id

    if user_id in active_chats:
        partner=active_chats.pop(user_id)

        if partner in active_chats:
            active_chats.pop(partner)

        await context.bot.send_message(partner,"⚠️ Stranger disconnected")

        await update.message.reply_text("⭐ Rate the user")


async def message(update,context):

    user_id=update.message.chat_id

    if user_id in active_chats:
        partner=active_chats[user_id]

        await context.bot.send_message(
        partner,
        update.message.text
        )


async def vip(update,context):

    text="""
💎 VIP Membership

Benefits:
🌍 Unlock all countries
⚡ Faster matching
♾ Unlimited chats
💰 Double coins

Price: ₹99/month

Send payment screenshot to:
@yourusername
"""

    await update.message.reply_text(text)


async def stats(update,context):

    if update.message.from_user.id!=ADMIN_ID:
        return

    total=cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    vip=cursor.execute("SELECT COUNT(*) FROM users WHERE vip=1").fetchone()[0]

    online=len(online_users)
    active=len(active_chats)//2

    await update.message.reply_text(f"""
📊 Bot Statistics

👥 Total users: {total}
🟢 Online users: {online}
💬 Active chats: {active}
💎 VIP users: {vip}
""")


async def addvip(update,context):

    if update.message.from_user.id!=ADMIN_ID:
        return

    user=int(context.args[0])

    cursor.execute("UPDATE users SET vip=1 WHERE id=?",(user,))
    conn.commit()

    await update.message.reply_text("VIP activated")


async def buttons(update,context):

    text=update.message.text

    if text=="🔍 Find Stranger":
        await find(update,context)

    elif text=="💎 VIP":
        await vip(update,context)


app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("stop",stop))
app.add_handler(CommandHandler("stats",stats))
app.add_handler(CommandHandler("addvip",addvip))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,buttons))
app.add_handler(MessageHandler(filters.TEXT,message))

print("ElentraChat V10 Running...")

app.run_polling()	

