import sqlite3
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN="8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID=8232389772
BOT_USERNAME="ElentraChatBot"

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
reset_time INTEGER DEFAULT 0,
invites INTEGER DEFAULT 0,
coins INTEGER DEFAULT 0,
banned INTEGER DEFAULT 0
)
""")

conn.commit()

waiting=[]
active={}
editing={}
partner_setting={}

menu=ReplyKeyboardMarkup([
["🔎 Find Partner"],
["👤 Profile","✏ Edit Profile"],
["🎯 Partner Gender","🎁 Invite Friends"],
["🏆 Leaderboard","🎁 Daily Reward"],
["🚨 Report","💎 VIP"],
["⏭ Next","⛔ Stop"]
],resize_keyboard=True)

# reset daily
def reset_daily(user):

    row=cursor.execute(
    "SELECT reset_time FROM users WHERE user_id=?",
    (user,)
    ).fetchone()

    now=int(time.time())

    if now-row[0]>86400:

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

    # referral
    if context.args:

        ref=int(context.args[0])

        if ref!=user:

            cursor.execute(
            "UPDATE users SET invites=invites+1 WHERE user_id=?",
            (ref,)
            )

            conn.commit()

    await update.message.reply_text(
"👋 Welcome to ElentraChat",
reply_markup=menu
)

# profile
async def profile(update:Update):

    user=update.effective_user.id

    data=cursor.execute(
    "SELECT name,age,gender,pref,vip,invites,coins FROM users WHERE user_id=?",
    (user,)
    ).fetchone()

    await update.message.reply_text(f"""
👤 Profile

Name: {data[0]}
Age: {data[1]}
Gender: {data[2]}
Looking for: {data[3]}

VIP: {"Yes" if data[4] else "No"}
Invites: {data[5]}
Coins: {data[6]}

ID: {user}
""")

# edit profile
async def edit(update:Update):

    editing[update.effective_user.id]=True

    await update.message.reply_text(
"Send profile:\nName,Age,Gender\nExample:\nZayn,18,Male"
)

# save profile
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

    partner_setting[update.effective_user.id]=True

    await update.message.reply_text(
"Choose partner gender:\nMale / Female / Any"
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
"⚠ Daily limit reached (50 chats)\nUpgrade to VIP"
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

        await context.bot.send_message(user,"✅ Connected")
        await context.bot.send_message(partner,"✅ Connected")

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

        await context.bot.send_message(p,"Partner left")

# next
async def next_chat(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await stop(update,context)
    await find(update,context)

# invite
async def invite(update:Update):

    user=update.effective_user.id

    link=f"https://t.me/{BOT_USERNAME}?start={user}"

    await update.message.reply_text(
f"Invite friends and get VIP\n\n{link}"
    )

# leaderboard
async def leaderboard(update:Update):

    rows=cursor.execute(
    "SELECT user_id,invites FROM users ORDER BY invites DESC LIMIT 5"
    ).fetchall()

    text="🏆 Top Inviters\n\n"

    for i,r in enumerate(rows):

        text+=f"{i+1}. {r[0]} — {r[1]} invites\n"

    await update.message.reply_text(text)

# daily reward
async def reward(update:Update):

    user=update.effective_user.id

    cursor.execute(
    "UPDATE users SET coins=coins+5 WHERE user_id=?",
    (user,)
    )

    conn.commit()

    await update.message.reply_text("🎁 +5 coins")

# vip
async def vip(update:Update):

    await update.message.reply_text("""
💎 VIP Membership

Unlimited chats
Gender search

UPI:
hatmahendran267r@ybl

Send screenshot to:
@Elentraadmin001
""")

# report
async def report(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if user in active:

        partner=active[user]

        await context.bot.send_message(
        ADMIN_ID,
        f"🚨 Report\nReporter:{user}\nPartner:{partner}"
        )

        await update.message.reply_text("Report sent")

# admin commands
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

    if user in partner_setting:

        pref=update.message.text

        cursor.execute(
        "UPDATE users SET pref=? WHERE user_id=?",
        (pref,user)
        )

        conn.commit()

        partner_setting.pop(user)

        await update.message.reply_text(
        "Partner preference saved",
        reply_markup=menu
        )

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

        elif text=="⏭ Next":
            await next_chat(update,context)

        elif text=="⛔ Stop":
            await stop(update,context)

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

        elif text=="💎 VIP":
            await vip(update)

        elif text=="🚨 Report":
            await report(update,context)

app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("addvip",addvip))

app.add_handler(MessageHandler(filters.ALL,handler))

print("ElentraChat V2 running")

app.run_polling()
