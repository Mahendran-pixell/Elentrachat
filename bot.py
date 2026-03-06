import sqlite3
import random
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN="8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID=8232389772

conn=sqlite3.connect("users.db",check_same_thread=False)
cursor=conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
name TEXT,
age TEXT,
gender TEXT,
partner TEXT,
coins INTEGER DEFAULT 10,
invites INTEGER DEFAULT 0,
last_reward INTEGER DEFAULT 0,
accepted INTEGER DEFAULT 0,
banned INTEGER DEFAULT 0
)
""")

conn.commit()

waiting=[]
active={}
editing={}
setting_partner={}
last_msg={}

menu=ReplyKeyboardMarkup([
["🔎 Find Stranger"],
["👤 Profile","✏ Edit Profile"],
["🎯 Partner Gender"],
["⏭ Next","⛔ Stop"],
["💎 VIP","🎁 Invite Friends"],
["🎁 Daily Reward","🏆 Leaderboard"],
["📜 Terms","❓ Help"]
],resize_keyboard=True)

TERMS_TEXT="""
📜 Terms & Privacy

• Chats are anonymous
• Do not share personal information
• No harassment or illegal content
• Respect other users
• Admin may ban abusive users

Type /agree to continue.
"""

HELP_TEXT="""
❓ ElentraChat Help

🔎 Find Stranger — start chat
⏭ Next — skip partner
⛔ Stop — end chat
👤 Profile — view profile
✏ Edit Profile — update profile
🎯 Partner Gender — choose preference
🎁 Invite Friends — earn VIP
🎁 Daily Reward — collect coins
"""

# START
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id
    args=context.args

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user,))
    conn.commit()

    accepted=cursor.execute(
    "SELECT accepted FROM users WHERE user_id=?",(user,)
    ).fetchone()[0]

    if not accepted:
        await update.message.reply_text(TERMS_TEXT)
        return

    await update.message.reply_text("👋 Welcome to ElentraChat",reply_markup=menu)

# AGREE
async def agree(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    cursor.execute("UPDATE users SET accepted=1 WHERE user_id=?",(user,))
    conn.commit()

    await update.message.reply_text("✅ Rules accepted!",reply_markup=menu)

# PROFILE
async def profile(update:Update):

    user=update.effective_user.id

    data=cursor.execute(
    "SELECT name,age,gender,partner,coins,invites FROM users WHERE user_id=?",
    (user,)
    ).fetchone()

    await update.message.reply_text(
f"""👤 Profile

Name: {data[0]}
Age: {data[1]}
Gender: {data[2]}
Looking for: {data[3]}

Coins: {data[4]}
Invites: {data[5]}
"""
)

# EDIT PROFILE
async def edit_profile(update:Update):

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

# PARTNER
async def partner(update:Update):

    setting_partner[update.effective_user.id]=True

    await update.message.reply_text(
"Send preferred partner gender:\nMale / Female / Any"
)

def save_partner(user,text):

    cursor.execute(
    "UPDATE users SET partner=? WHERE user_id=?",
    (text,user)
    )

    conn.commit()

# FIND
async def find(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if waiting:

        partner=waiting.pop(0)

        active[user]=partner
        active[partner]=user

        await context.bot.send_message(user,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        waiting.append(user)

        await update.message.reply_text(
f"""🔎 Searching...

👥 {random.randint(120,300)} users online
💬 {random.randint(10,40)} waiting"""
)

# STOP
async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if user in active:

        partner=active[user]

        del active[user]
        del active[partner]

        await context.bot.send_message(partner,"❌ Partner left chat.")
        await update.message.reply_text("Chat ended.")

# NEXT
async def next_chat(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await stop(update,context)
    await find(update,context)

# VIP
async def vip(update:Update):

    await update.message.reply_text(
"""💎 VIP Membership

1 Month – ₹49
3 Months – ₹99
Lifetime – ₹299

UPI:
hatmahendran267r@ybl

Send screenshot to:
@Elentraadmin001
"""
)

# INVITE
async def invite(update:Update):

    user=update.effective_user.id
    link=f"https://t.me/ElentraChatBot?start={user}"

    await update.message.reply_text(
f"""🎁 Invite Friends

Invite 3 friends → VIP

Your link:
{link}
"""
)

# DAILY
async def reward(update:Update):

    user=update.effective_user.id

    last=cursor.execute(
    "SELECT last_reward FROM users WHERE user_id=?",
    (user,)
    ).fetchone()[0]

    now=int(time.time())

    if now-last<86400:
        await update.message.reply_text("❌ Come back tomorrow")
        return

    cursor.execute(
    "UPDATE users SET coins=coins+5,last_reward=? WHERE user_id=?",
    (now,user)
    )
    conn.commit()

    await update.message.reply_text("🎁 Daily reward +5 coins")

# LEADERBOARD
async def leaderboard(update:Update):

    top=cursor.execute(
    "SELECT user_id,invites FROM users ORDER BY invites DESC LIMIT 5"
    ).fetchall()

    text="🏆 Top Inviters\n\n"

    for i,u in enumerate(top):
        text+=f"{i+1}. {u[0]} — {u[1]} invites\n"

    await update.message.reply_text(text)

# HANDLER
async def handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id
    text=update.message.text

    now=time.time()

    if user in last_msg and now-last_msg[user]<1:
        await update.message.reply_text("⚠️ Slow down!")
        return

    last_msg[user]=now

    if user in editing:

        ok=save_profile(user,text)
        editing.pop(user)

        if ok:
            await update.message.reply_text("✅ Profile saved",reply_markup=menu)

        return

    if user in setting_partner:

        save_partner(user,text)
        setting_partner.pop(user)

        await update.message.reply_text("✅ Partner saved",reply_markup=menu)
        return

    if text=="🔎 Find Stranger":
        await find(update,context)

    elif text=="👤 Profile":
        await profile(update)

    elif text=="✏ Edit Profile":
        await edit_profile(update)

    elif text=="🎯 Partner Gender":
        await partner(update)

    elif text=="⏭ Next":
        await next_chat(update,context)

    elif text=="⛔ Stop":
        await stop(update,context)

    elif text=="💎 VIP":
        await vip(update)

    elif text=="🎁 Invite Friends":
        await invite(update)

    elif text=="🎁 Daily Reward":
        await reward(update)

    elif text=="🏆 Leaderboard":
        await leaderboard(update)

    elif text=="📜 Terms":
        await update.message.reply_text(TERMS_TEXT)

    elif text=="❓ Help":
        await update.message.reply_text(HELP_TEXT)

    elif user in active:

        partner=active[user]

        await context.bot.copy_message(
        chat_id=partner,
        from_chat_id=user,
        message_id=update.message.message_id
        )

app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("agree",agree))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handler))

print("ElentraChat V22 running")

app.run_polling()
