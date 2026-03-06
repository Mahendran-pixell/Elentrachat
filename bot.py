import sqlite3
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN="8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN="@Elentraadmin001"
ADMIN_ID=8232389772

conn=sqlite3.connect("users.db",check_same_thread=False)
cursor=conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
name TEXT,
age TEXT,
gender TEXT,
pref TEXT DEFAULT 'Any',
vip INTEGER DEFAULT 0,
daily INTEGER DEFAULT 0,
reset_time INTEGER DEFAULT 0
)
""")

conn.commit()

waiting=[]
active={}
editing={}

menu=ReplyKeyboardMarkup([
["🔎 Find Partner"],
["👤 Profile","✏ Edit Profile"],
["🎯 Partner Gender"],
["⏭ Next","⛔ Stop"],
["💎 VIP"]
],resize_keyboard=True)

# reset daily
def reset_daily(user):

    row=cursor.execute(
    "SELECT reset_time FROM users WHERE user_id=?",
    (user,)
    ).fetchone()

    if not row:
        return

    last=row[0]
    now=int(time.time())

    if now-last>86400:

        cursor.execute(
        "UPDATE users SET daily=0,reset_time=? WHERE user_id=?",
        (now,user)
        )

        conn.commit()

# start
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    cursor.execute(
    "INSERT OR IGNORE INTO users(user_id,reset_time) VALUES(?,?)",
    (user,int(time.time()))
    )

    conn.commit()

    await update.message.reply_text(
"""👋 Welcome to ElentraChat

Anonymous random chat.

Press 🔎 Find Partner to start.
""",
reply_markup=menu
)

# profile
async def profile(update:Update):

    user=update.effective_user.id

    data=cursor.execute(
    "SELECT name,age,gender,pref,vip FROM users WHERE user_id=?",
    (user,)
    ).fetchone()

    await update.message.reply_text(f"""
👤 Your Profile

Name: {data[0]}
Age: {data[1]}
Gender: {data[2]}
Looking for: {data[3]}

VIP: {"Yes" if data[4] else "No"}
ID: {user}
""")

# edit profile
async def edit(update:Update):

    editing[update.effective_user.id]=True

    await update.message.reply_text(
"Send profile like:\nName,Age,Gender\nExample:\nZayn,18,Male"
)

def save_profile(user,text):

    try:

        name,age,gender=text.split(",")

        cursor.execute(
        "UPDATE users SET name=?,age=?,gender=? WHERE user_id=?",
        (name.strip(),age.strip(),gender.strip(),user)
        )

        conn.commit()

        return True

    except:
        return False

# partner gender
async def partner(update:Update):

    await update.message.reply_text(
"Send preferred partner gender:\nMale / Female / Any"
)

# match
def match(user):

    my_gender=cursor.execute(
    "SELECT gender FROM users WHERE user_id=?",
    (user,)
    ).fetchone()[0]

    my_pref=cursor.execute(
    "SELECT pref FROM users WHERE user_id=?",
    (user,)
    ).fetchone()[0]

    for u in waiting:

        g=cursor.execute(
        "SELECT gender FROM users WHERE user_id=?",
        (u,)
        ).fetchone()[0]

        p=cursor.execute(
        "SELECT pref FROM users WHERE user_id=?",
        (u,)
        ).fetchone()[0]

        if (my_pref=="Any" or my_pref==g) and (p=="Any" or p==my_gender):

            waiting.remove(u)
            return u

    return None

# find partner
async def find(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    reset_daily(user)

    data=cursor.execute(
    "SELECT daily,vip FROM users WHERE user_id=?",
    (user,)
    ).fetchone()

    if not data[1] and data[0]>=50:

        await update.message.reply_text(
"⚠ Daily limit reached (50 chats)\nUpgrade to VIP."
        )
        return

    partner=match(user)

    if partner:

        active[user]=partner
        active[partner]=user

        cursor.execute(
        "UPDATE users SET daily=daily+1 WHERE user_id=?",
        (user,)
        )

        conn.commit()

        await context.bot.send_message(user,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        waiting.append(user)

        await update.message.reply_text(
f"🔎 Searching...\nWaiting users: {len(waiting)}"
        )

# stop
async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if user in active:

        p=active[user]

        del active[user]
        del active[p]

        await context.bot.send_message(p,"❌ Partner left")

# next
async def next_chat(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await stop(update,context)
    await find(update,context)

# vip info
async def vip(update:Update):

    await update.message.reply_text(f"""
💎 VIP Membership

Unlimited chats
Gender search

Price:
1 Month – ₹49
Lifetime – ₹299

UPI:
hatmahendran267r@ybl

Send payment screenshot to:
{ADMIN}
""")

# admin add vip
async def addvip(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id!=ADMIN_ID:
        return

    uid=int(context.args[0])

    cursor.execute(
    "UPDATE users SET vip=1 WHERE user_id=?",
    (uid,)
    )

    conn.commit()

    await update.message.reply_text("VIP activated")

# message handler
async def handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if user in editing:

        ok=save_profile(user,update.message.text)
        editing.pop(user)

        if ok:
            await update.message.reply_text("Profile saved",reply_markup=menu)

        return

    text=update.message.text

    if user in active:

        p=active[user]

        await context.bot.copy_message(
        chat_id=p,
        from_chat_id=user,
        message_id=update.message.message_id
        )

    else:

        if text=="🔎 Find Partner":
            await find(update,context)

        elif text=="⛔ Stop":
            await stop(update,context)

        elif text=="⏭ Next":
            await next_chat(update,context)

        elif text=="👤 Profile":
            await profile(update)

        elif text=="✏ Edit Profile":
            await edit(update)

        elif text=="💎 VIP":
            await vip(update)

        elif text=="🎯 Partner Gender":
            await partner(update)

app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("addvip",addvip))
app.add_handler(MessageHandler(filters.ALL,handler))

print("ElentraChat V1 running")

app.run_polling()
