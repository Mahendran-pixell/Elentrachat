import sqlite3
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN="8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID=8232389772

BAD_WORDS=["spam","scam","abuse"]

conn=sqlite3.connect("users.db",check_same_thread=False)
cursor=conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
gender TEXT,
partner TEXT DEFAULT 'Any',
vip INTEGER DEFAULT 0,
daily_chats INTEGER DEFAULT 0,
last_reset INTEGER DEFAULT 0
)
""")

conn.commit()

waiting=[]
active={}

menu=ReplyKeyboardMarkup([
["🔎 Find Stranger"],
["🎯 Partner Gender"],
["⏭ Next","⛔ Stop"],
["💎 VIP"]
],resize_keyboard=True)

# RESET DAILY LIMIT
def reset_daily(user):

    last=cursor.execute(
        "SELECT last_reset FROM users WHERE user_id=?",(user,)
    ).fetchone()[0]

    now=int(time.time())

    if now-last>86400:

        cursor.execute(
        "UPDATE users SET daily_chats=0,last_reset=? WHERE user_id=?",
        (now,user)
        )
        conn.commit()

# START
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    cursor.execute(
    "INSERT OR IGNORE INTO users(user_id,last_reset) VALUES(?,?)",
    (user,int(time.time()))
    )
    conn.commit()

    await update.message.reply_text(
    "👋 Welcome to ElentraChat",
    reply_markup=menu
    )

# SET PARTNER
async def partner(update:Update):

    await update.message.reply_text(
    "Send preferred partner gender:\nMale / Female / Any"
    )

# MATCHING
def match(user):

    gender=cursor.execute(
    "SELECT gender FROM users WHERE user_id=?",(user,)
    ).fetchone()[0]

    pref=cursor.execute(
    "SELECT partner FROM users WHERE user_id=?",(user,)
    ).fetchone()[0]

    for p in waiting:

        g=cursor.execute(
        "SELECT gender FROM users WHERE user_id=?",(p,)
        ).fetchone()[0]

        pr=cursor.execute(
        "SELECT partner FROM users WHERE user_id=?",(p,)
        ).fetchone()[0]

        if (pref=="Any" or pref==g) and (pr=="Any" or pr==gender):

            waiting.remove(p)
            return p

    return None

# FIND
async def find(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    reset_daily(user)

    data=cursor.execute(
    "SELECT daily_chats,vip FROM users WHERE user_id=?",(user,)
    ).fetchone()

    if not data[1] and data[0]>=50:

        await update.message.reply_text(
        "⚠️ Daily limit reached (50 chats)\nCome back tomorrow or buy VIP"
        )
        return

    partner=match(user)

    if partner:

        active[user]=partner
        active[partner]=user

        cursor.execute(
        "UPDATE users SET daily_chats=daily_chats+1 WHERE user_id=?",
        (user,)
        )
        conn.commit()

        await context.bot.send_message(user,"✅ Connected")
        await context.bot.send_message(partner,"✅ Connected")

    else:

        waiting.append(user)

        await update.message.reply_text(
        f"🔎 Searching...\n👥 Users online: {len(waiting)+len(active)}"
        )

# STOP
async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if user in active:

        p=active[user]

        del active[user]
        del active[p]

        await context.bot.send_message(p,"Partner left chat")

# VIP
async def vip(update:Update):

    await update.message.reply_text(
"""💎 VIP Membership

Unlimited chats

UPI:
hatmahendran267r@ybl

Send payment screenshot
@Elentraadmin001
"""
)

# MESSAGE HANDLER
async def handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if update.message.text:

        text=update.message.text.lower()

        for w in BAD_WORDS:

            if w in text:

                await update.message.reply_text(
                "⚠️ Message blocked by moderation"
                )
                return

    if user in active:

        p=active[user]

        msg=await context.bot.copy_message(
        chat_id=p,
        from_chat_id=user,
        message_id=update.message.message_id
        )

        # self destruct photo
        if update.message.photo:

            await context.job_queue.run_once(
            lambda c: c.bot.delete_message(p,msg.message_id),
            10
            )

    elif update.message.text=="🔎 Find Stranger":
        await find(update,context)

    elif update.message.text=="⛔ Stop":
        await stop(update,context)

    elif update.message.text=="⏭ Next":
        await stop(update,context)
        await find(update,context)

    elif update.message.text=="💎 VIP":
        await vip(update)

    elif update.message.text=="🎯 Partner Gender":
        await partner(update)

app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(MessageHandler(filters.ALL,handler))

print("ElentraChat V24 running")

app.run_polling()
