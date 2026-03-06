import sqlite3
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
gender TEXT DEFAULT 'unknown',
pref TEXT DEFAULT 'any',
vip INTEGER DEFAULT 0,
daily INTEGER DEFAULT 0,
reset_time INTEGER DEFAULT 0
)
""")

conn.commit()

waiting = []
active = {}

BAD_WORDS = ["spam","scam","abuse"]

menu = ReplyKeyboardMarkup(
[
["🔎 Find Partner"],
["⚙ Settings"],
["⏭ Next","⛔ Stop"],
["💎 VIP"]
],
resize_keyboard=True
)

# reset daily chat count
def reset_daily(user):
    row = cursor.execute("SELECT reset_time FROM users WHERE user_id=?",(user,)).fetchone()
    if not row:
        return

    last = row[0]
    now = int(time.time())

    if now - last > 86400:
        cursor.execute("UPDATE users SET daily=0, reset_time=? WHERE user_id=?",(now,user))
        conn.commit()

# start
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute(
        "INSERT OR IGNORE INTO users(user_id,reset_time) VALUES(?,?)",
        (user,int(time.time()))
    )

    conn.commit()

    await update.message.reply_text(
        "👋 Welcome to ElentraChat\n\nPress 🔎 Find Partner",
        reply_markup=menu
    )

# settings
async def settings(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    data = cursor.execute(
        "SELECT gender,pref FROM users WHERE user_id=?",
        (user,)
    ).fetchone()

    await update.message.reply_text(
f"""⚙ Your Settings

Gender: {data[0]}
Looking for: {data[1]}

Send:
male
female
any
"""
)

# match system
def match(user):

    my_gender = cursor.execute(
        "SELECT gender FROM users WHERE user_id=?",(user,)
    ).fetchone()[0]

    my_pref = cursor.execute(
        "SELECT pref FROM users WHERE user_id=?",(user,)
    ).fetchone()[0]

    for u in waiting:

        g = cursor.execute("SELECT gender FROM users WHERE user_id=?",(u,)).fetchone()[0]
        p = cursor.execute("SELECT pref FROM users WHERE user_id=?",(u,)).fetchone()[0]

        if (my_pref=="any" or my_pref==g) and (p=="any" or p==my_gender):

            waiting.remove(u)
            return u

    return None

# find partner
async def find(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    reset_daily(user)

    data = cursor.execute(
        "SELECT daily,vip FROM users WHERE user_id=?",
        (user,)
    ).fetchone()

    if not data[1] and data[0] >= 50:

        await update.message.reply_text(
            "⚠ Daily chat limit reached (50)\nCome back tomorrow."
        )

        return

    partner = match(user)

    if partner:

        active[user] = partner
        active[partner] = user

        cursor.execute(
            "UPDATE users SET daily=daily+1 WHERE user_id=?",
            (user,)
        )

        conn.commit()

        await context.bot.send_message(user,"✅ Connected!")
        await context.bot.send_message(partner,"✅ Connected!")

    else:

        waiting.append(user)

        await update.message.reply_text(
            f"🔎 Searching...\nWaiting users: {len(waiting)}"
        )

# stop chat
async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active:

        p = active[user]

        del active[user]
        del active[p]

        await context.bot.send_message(p,"❌ Partner left")

# next
async def next_chat(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await stop(update,context)
    await find(update,context)

# vip
async def vip(update:Update):

    await update.message.reply_text(
"""💎 VIP Membership

Unlimited chats

UPI:
hatmahendran267r@ybl

Send screenshot to admin.
"""
)

# message handler
async def handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if update.message.text:

        text = update.message.text.lower()

        if text in ["male","female","any"]:

            cursor.execute(
                "UPDATE users SET pref=? WHERE user_id=?",
                (text,user)
            )

            conn.commit()

            await update.message.reply_text("Preference saved")

            return

        for w in BAD_WORDS:

            if w in text:
                await update.message.reply_text("⚠ Message blocked")
                return

    if user in active:

        partner = active[user]

        msg = await context.bot.copy_message(
            chat_id=partner,
            from_chat_id=user,
            message_id=update.message.message_id
        )

        # self destruct photo
        if update.message.photo:

            await context.job_queue.run_once(
                lambda c: c.bot.delete_message(partner,msg.message_id),
                10
            )

    else:

        if update.message.text == "🔎 Find Partner":
            await find(update,context)

        elif update.message.text == "⛔ Stop":
            await stop(update,context)

        elif update.message.text == "⏭ Next":
            await next_chat(update,context)

        elif update.message.text == "⚙ Settings":
            await settings(update,context)

        elif update.message.text == "💎 VIP":
            await vip(update)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(MessageHandler(filters.ALL,handler))

print("ElentraChat V24 running")

app.run_polling()
