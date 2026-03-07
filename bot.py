import sqlite3
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN="8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID=8232389772

db=sqlite3.connect("users.db",check_same_thread=False)
cursor=db.cursor()

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

db.commit()

waiting=[]
active={}
editing={}
pref_edit={}

menu=ReplyKeyboardMarkup([
["🔎 Find Partner"],
["👤 Profile","✏ Edit Profile"],
["🎯 Partner Gender"],
["💎 VIP"],
["⏭ Next","⛔ Stop"]
],resize_keyboard=True)

def reset_daily(uid):

    data=cursor.execute(
    "SELECT reset_time FROM users WHERE user_id=?",
    (uid,)
    ).fetchone()

    if not data:
        return

    now=int(time.time())

    if now-data[0]>86400:

        cursor.execute(
        "UPDATE users SET daily=0,reset_time=? WHERE user_id=?",
        (now,uid)
        )

        db.commit()

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id

    cursor.execute(
    "INSERT OR IGNORE INTO users(user_id,reset_time) VALUES(?,?)",
    (uid,int(time.time()))
    )

    db.commit()

    await update.message.reply_text(
"👋 Welcome to ElentraChat\n\nAnonymous random chat bot.",
reply_markup=menu
)

async def profile(update:Update):

    uid=update.effective_user.id

    data=cursor.execute(
    "SELECT name,age,gender,pref,vip FROM users WHERE user_id=?",
    (uid,)
    ).fetchone()

    await update.message.reply_text(f"""
👤 Profile

Name: {data[0]}
Age: {data[1]}
Gender: {data[2]}
Looking for: {data[3]}

VIP: {"Yes" if data[4] else "No"}
""")

async def edit_profile(update:Update):

    editing[update.effective_user.id]=True

    await update.message.reply_text(
"Send profile like:\nName,Age,Gender\nExample:\nAlex,18,Male"
)

async def partner_gender(update:Update):

    pref_edit[update.effective_user.id]=True

    await update.message.reply_text(
"Choose partner gender:\nMale / Female / Any"
)

def match_user(uid):

    my=cursor.execute(
    "SELECT gender,pref FROM users WHERE user_id=?",
    (uid,)
    ).fetchone()

    for u in waiting:

        g,p=cursor.execute(
        "SELECT gender,pref FROM users WHERE user_id=?",
        (u,)
        ).fetchone()

        if (my[1]=="Any" or my[1]==g) and (p=="Any" or p==my[0]):

            waiting.remove(u)
            return u

    return None

async def find(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id

    reset_daily(uid)

    data=cursor.execute(
    "SELECT daily,vip FROM users WHERE user_id=?",
    (uid,)
    ).fetchone()

    if not data[1] and data[0]>=50:

        await update.message.reply_text(
"⚠ Daily limit reached (50 chats)"
        )

        return

    partner=match_user(uid)

    if partner:

        active[uid]=partner
        active[partner]=uid

        cursor.execute(
        "UPDATE users SET daily=daily+1 WHERE user_id=?",
        (uid,)
        )

        db.commit()

        await context.bot.send_message(uid,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        waiting.append(uid)

        await update.message.reply_text("🔎 Searching for partner...")

async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id

    if uid in active:

        p=active[uid]

        del active[uid]
        del active[p]

        await context.bot.send_message(p,"❌ Partner left chat")

        await update.message.reply_text("Chat ended")

async def next_chat(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await stop(update,context)
    await find(update,context)

async def vip(update:Update):

    await update.message.reply_text("""
💎 VIP Membership

Benefits:
• Unlimited chats
• Gender filter

Price:
₹49

UPI:
hatmahendran267r@ybl

Send screenshot to:
@Elentraadmin001
""")

async def addvip(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id!=ADMIN_ID:
        return

    uid=int(context.args[0])

    cursor.execute(
    "UPDATE users SET vip=1 WHERE user_id=?",
    (uid,)
    )

    db.commit()

    await update.message.reply_text("VIP activated")

async def handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id
    text=update.message.text

    if uid in editing:

        try:

            name,age,gender=text.split(",")

            cursor.execute(
            "UPDATE users SET name=?,age=?,gender=? WHERE user_id=?",
            (name.strip(),age.strip(),gender.strip(),uid)
            )

            db.commit()

            editing.pop(uid)

            await update.message.reply_text("Profile saved",reply_markup=menu)

        except:

            await update.message.reply_text("Format wrong")

        return

    if uid in pref_edit:

        cursor.execute(
        "UPDATE users SET pref=? WHERE user_id=?",
        (text,uid)
        )

        db.commit()

        pref_edit.pop(uid)

        await update.message.reply_text(
        "Preference saved",
        reply_markup=menu
        )

        return

    if uid in active:

        p=active[uid]

        await context.bot.copy_message(
        chat_id=p,
        from_chat_id=uid,
        message_id=update.message.message_id
        )

        return

    if text=="🔎 Find Partner":
        await find(update,context)

    elif text=="👤 Profile":
        await profile(update)

    elif text=="✏ Edit Profile":
        await edit_profile(update)

    elif text=="🎯 Partner Gender":
        await partner_gender(update)

    elif text=="💎 VIP":
        await vip(update)

    elif text=="⏭ Next":
        await next_chat(update,context)

    elif text=="⛔ Stop":
        await stop(update,context)

app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("addvip",addvip))

app.add_handler(MessageHandler(filters.ALL,handler))

print("ElentraChat Basic running")

app.run_polling()
