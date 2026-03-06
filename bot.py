import sqlite3
import random
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID = 8232389772

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
name TEXT,
age TEXT,
gender TEXT,
partner TEXT DEFAULT 'Any',
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
set_partner={}
photo_timer={}

menu = ReplyKeyboardMarkup([
["🔎 Find Stranger"],
["👤 Profile","✏ Edit Profile"],
["🎯 Partner Gender"],
["⏭ Next","⛔ Stop"],
["🚨 Report"],
["💎 VIP","🎁 Invite Friends"],
["🎁 Daily Reward","🏆 Leaderboard"],
["📜 Terms","❓ Help"]
], resize_keyboard=True)

TERMS = """
📜 Terms & Privacy

• Chats are anonymous
• Do not share personal info
• No illegal content
• Respect users

Type /agree to continue
"""

HELP = """
❓ Help

🔎 Find Stranger → start chat
⏭ Next → skip partner
⛔ Stop → end chat
👤 Profile → view profile
✏ Edit Profile → update profile
🎯 Partner Gender → preference
🚨 Report → report partner
"""

# START
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user,))
    conn.commit()

    accepted=cursor.execute(
        "SELECT accepted FROM users WHERE user_id=?",(user,)
    ).fetchone()[0]

    if not accepted:
        await update.message.reply_text(TERMS)
        return

    await update.message.reply_text(
        "👋 Welcome to ElentraChat",
        reply_markup=menu
    )

# AGREE
async def agree(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    cursor.execute(
        "UPDATE users SET accepted=1 WHERE user_id=?",(user,)
    )
    conn.commit()

    await update.message.reply_text(
        "✅ Rules accepted",
        reply_markup=menu
    )

# PROFILE
async def profile(update:Update):

    user=update.effective_user.id

    data=cursor.execute(
        "SELECT name,age,gender,partner,coins FROM users WHERE user_id=?",
        (user,)
    ).fetchone()

    await update.message.reply_text(f"""
👤 Profile

Name: {data[0]}
Age: {data[1]}
Gender: {data[2]}
Looking for: {data[3]}

Coins: {data[4]}
""")

# EDIT PROFILE
async def edit_profile(update:Update):

    editing[update.effective_user.id]=True

    await update.message.reply_text(
        "Send profile:\nName,Age,Gender\nExample:\nZayn,18,Male"
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

# PARTNER GENDER
async def partner(update:Update):

    set_partner[update.effective_user.id]=True

    await update.message.reply_text(
        "Choose partner gender:\nMale / Female / Any"
    )

def save_partner(user,text):

    cursor.execute(
        "UPDATE users SET partner=? WHERE user_id=?",
        (text,user)
    )
    conn.commit()

# MATCHING SYSTEM
def match(user):

    user_gender=cursor.execute(
        "SELECT gender FROM users WHERE user_id=?",(user,)
    ).fetchone()[0]

    user_pref=cursor.execute(
        "SELECT partner FROM users WHERE user_id=?",(user,)
    ).fetchone()[0]

    for p in waiting:

        g=cursor.execute(
            "SELECT gender FROM users WHERE user_id=?",(p,)
        ).fetchone()[0]

        pref=cursor.execute(
            "SELECT partner FROM users WHERE user_id=?",(p,)
        ).fetchone()[0]

        if user_pref=="Any" or user_pref==g:
            if pref=="Any" or pref==user_gender:

                waiting.remove(p)
                return p

    return None

# FIND
async def find(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    partner=match(user)

    if partner:

        active[user]=partner
        active[partner]=user

        await context.bot.send_message(user,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        waiting.append(user)

        await update.message.reply_text(
f"""🔎 Searching...

👥 {random.randint(120,300)} users online
💬 {len(waiting)} waiting
"""
)

# STOP
async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if user in active:

        partner=active[user]

        del active[user]
        del active[partner]

        await context.bot.send_message(partner,"❌ Partner left chat")
        await update.message.reply_text("Chat ended")

# NEXT
async def next_chat(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await stop(update,context)
    await find(update,context)

# REPORT
async def report(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if user not in active:
        return

    partner=active[user]

    await context.bot.send_message(
        ADMIN_ID,
        f"🚨 Report\nReporter:{user}\nPartner:{partner}"
    )

    await update.message.reply_text("Report sent to admin")

# VIP
async def vip(update:Update):

    await update.message.reply_text("""
💎 VIP Membership

1 Month – ₹49
3 Months – ₹99
Lifetime – ₹299

UPI:
hatmahendran267r@ybl

Send screenshot:
@Elentraadmin001
""")

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
async def daily(update:Update):

    user=update.effective_user.id

    last=cursor.execute(
        "SELECT last_reward FROM users WHERE user_id=?",
        (user,)
    ).fetchone()[0]

    now=int(time.time())

    if now-last<86400:
        await update.message.reply_text("Come tomorrow")
        return

    cursor.execute(
        "UPDATE users SET coins=coins+5,last_reward=? WHERE user_id=?",
        (now,user)
    )
    conn.commit()

    await update.message.reply_text("🎁 +5 coins")

# PHOTO TIMER
async def send_photo_timer(context,chat,msg):
    await context.bot.delete_message(chat,msg)

# MESSAGE HANDLER
async def handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if user in editing:

        ok=save_profile(user,update.message.text)
        editing.pop(user)

        if ok:
            await update.message.reply_text(
                "Profile saved",
                reply_markup=menu
            )
        return

    if user in set_partner:

        save_partner(user,update.message.text)
        set_partner.pop(user)

        await update.message.reply_text(
            "Partner preference saved",
            reply_markup=menu
        )
        return

    text=update.message.text

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

    elif text=="🚨 Report":
        await report(update,context)

    elif text=="💎 VIP":
        await vip(update)

    elif text=="🎁 Invite Friends":
        await invite(update)

    elif text=="🎁 Daily Reward":
        await daily(update)

    elif text=="📜 Terms":
        await update.message.reply_text(TERMS)

    elif text=="❓ Help":
        await update.message.reply_text(HELP)

    elif user in active:

        partner=active[user]

        msg=await context.bot.copy_message(
            chat_id=partner,
            from_chat_id=user,
            message_id=update.message.message_id
        )

        # photo self destruct
        if update.message.photo:

            context.job_queue.run_once(
                lambda c: c.bot.delete_message(partner,msg.message_id),
                10
            )

app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("agree",agree))

app.add_handler(MessageHandler(filters.ALL,handler))

print("ElentraChat V23 running")

app.run_polling()
