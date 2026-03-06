import sqlite3
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN="8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID=8232389772
BOT_USERNAME="ElentraChatBot"

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
reset_time INTEGER DEFAULT 0,
invites INTEGER DEFAULT 0,
coins INTEGER DEFAULT 0
)
""")

db.commit()

waiting=[]
active={}
editing={}
pref_edit={}
last_msg={}

menu=ReplyKeyboardMarkup([
["🔎 Find Partner"],
["👤 Profile","✏ Edit Profile"],
["🎯 Partner Gender","🎁 Invite Friends"],
["🏆 Leaderboard","🎁 Daily Reward"],
["🚨 Report","💎 VIP"],
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

    if now-data[0] > 86400:

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

    if context.args:

        ref=int(context.args[0])

        if ref!=uid:

            cursor.execute(
            "UPDATE users SET invites=invites+1 WHERE user_id=?",
            (ref,)
            )

            db.commit()

    await update.message.reply_text(
"👋 Welcome to ElentraChat",
reply_markup=menu
)

async def profile(update:Update):

    uid=update.effective_user.id

    d=cursor.execute(
    "SELECT name,age,gender,pref,vip,invites,coins FROM users WHERE user_id=?",
    (uid,)
    ).fetchone()

    await update.message.reply_text(f"""
👤 Profile

Name: {d[0]}
Age: {d[1]}
Gender: {d[2]}
Looking for: {d[3]}

VIP: {"Yes" if d[4] else "No"}
Invites: {d[5]}
Coins: {d[6]}

ID: {uid}
""")

async def edit(update:Update):

    editing[update.effective_user.id]=True

    await update.message.reply_text(
"Send profile:\nName,Age,Gender\nExample:\nAlex,18,Male"
)

async def partner(update:Update):

    pref_edit[update.effective_user.id]=True

    await update.message.reply_text(
"Choose partner gender:\nMale / Female / Any"
)

def find_match(uid):

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

    d=cursor.execute(
    "SELECT daily,vip FROM users WHERE user_id=?",
    (uid,)
    ).fetchone()

    if not d[1] and d[0]>=50:

        await update.message.reply_text(
"⚠ 50 chats limit reached today"
        )

        return

    partner=find_match(uid)

    if partner:

        active[uid]=partner
        active[partner]=uid

        cursor.execute(
        "UPDATE users SET daily=daily+1 WHERE user_id=?",
        (uid,)
        )

        db.commit()

        await context.bot.send_message(uid,"✅ Connected")
        await context.bot.send_message(partner,"✅ Connected")

    else:

        waiting.append(uid)

        await update.message.reply_text(
f"🔎 Searching...\n👥 Online: {len(waiting)+len(active)}"
        )

async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id

    if uid in active:

        p=active[uid]

        del active[uid]
        del active[p]

        await context.bot.send_message(p,"Partner left")

async def next_chat(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await stop(update,context)
    await find(update,context)

async def invite(update:Update):

    uid=update.effective_user.id

    link=f"https://t.me/{BOT_USERNAME}?start={uid}"

    await update.message.reply_text(
f"Invite friends:\n{link}"
)

async def leaderboard(update:Update):

    rows=cursor.execute(
    "SELECT user_id,invites FROM users ORDER BY invites DESC LIMIT 5"
    ).fetchall()

    text="🏆 Top Inviters\n\n"

    for i,r in enumerate(rows):

        text+=f"{i+1}. {r[0]} — {r[1]}\n"

    await update.message.reply_text(text)

async def reward(update:Update):

    uid=update.effective_user.id

    cursor.execute(
    "UPDATE users SET coins=coins+5 WHERE user_id=?",
    (uid,)
    )

    db.commit()

    await update.message.reply_text("🎁 +5 coins")

async def vip(update:Update):

    await update.message.reply_text("""
💎 VIP

Unlimited chats
Gender search

UPI:
hatmahendran267r@ybl

Send screenshot to:
@Elentraadmin001
""")

async def report(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id

    if uid in active:

        p=active[uid]

        await context.bot.send_message(
        ADMIN_ID,
        f"🚨 Report\nReporter:{uid}\nPartner:{p}"
        )

async def handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id
    text=update.message.text

    if uid in editing:

        try:

            n,a,g=text.split(",")

            cursor.execute(
            "UPDATE users SET name=?,age=?,gender=? WHERE user_id=?",
            (n,a,g,uid)
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

        await update.message.reply_text("Preference saved")

        return

    if uid in active:

        if time.time()-last_msg.get(uid,0)<1:
            return

        last_msg[uid]=time.time()

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
        await edit(update)

    elif text=="🎯 Partner Gender":
        await partner(update)

    elif text=="🎁 Invite Friends":
        await invite(update)

    elif text=="🏆 Leaderboard":
        await leaderboard(update)

    elif text=="🎁 Daily Reward":
        await reward(update)

    elif text=="🚨 Report":
        await report(update,context)

    elif text=="💎 VIP":
        await vip(update)

    elif text=="⏭ Next":
        await next_chat(update,context)

    elif text=="⛔ Stop":
        await stop(update,context)

app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(MessageHandler(filters.ALL,handler))

print("ElentraChat V3 running")

app.run_polling()
