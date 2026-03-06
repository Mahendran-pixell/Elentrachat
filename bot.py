import sqlite3
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID = 8232389772

# DATABASE
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
name TEXT,
age TEXT,
gender TEXT,
partner TEXT,
coins INTEGER DEFAULT 10,
invites INTEGER DEFAULT 0
)
""")

conn.commit()

# STORAGE
waiting = []
active = {}
editing = {}
setting_partner = {}

# MENU
menu = ReplyKeyboardMarkup([
["🔎 Find Stranger"],
["👤 Profile","✏ Edit Profile"],
["🎯 Partner Gender"],
["⏭ Next","⛔ Stop"],
["💎 VIP","🎁 Invite Friends"]
], resize_keyboard=True)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user,))
    conn.commit()

    await update.message.reply_text(
"""👋 Welcome to ElentraChat

Anonymous random chat bot.

Press 🔎 Find Stranger to start chatting.
""",
reply_markup=menu)

# PROFILE
async def profile(update: Update):

    user = update.effective_user.id

    data = cursor.execute(
    "SELECT name,age,gender,partner,coins FROM users WHERE user_id=?",
    (user,)
    ).fetchone()

    await update.message.reply_text(
f"""👤 Profile

Name: {data[0]}
Age: {data[1]}
Gender: {data[2]}
Looking for: {data[3]}

Coins: {data[4]}
"""
)

# EDIT PROFILE
async def edit_profile(update: Update):

    editing[update.effective_user.id] = True

    await update.message.reply_text(
"""Send profile like:

Name,Age,Gender

Example:
Zayn,18,Male
"""
)

# SAVE PROFILE
def save_profile(user,text):

    try:

        name,age,gender = text.split(",")

        cursor.execute("""
        UPDATE users
        SET name=?,age=?,gender=?
        WHERE user_id=?
        """,(name.strip(),age.strip(),gender.strip(),user))

        conn.commit()

        return True

    except:
        return False

# PARTNER GENDER
async def partner(update: Update):

    setting_partner[update.effective_user.id] = True

    await update.message.reply_text(
"Send preferred partner gender:\nMale / Female / Any"
)

# SAVE PARTNER
def save_partner(user,text):

    cursor.execute(
    "UPDATE users SET partner=? WHERE user_id=?",
    (text,user)
    )

    conn.commit()

# FIND STRANGER
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if waiting:

        partner = waiting.pop(0)

        active[user] = partner
        active[partner] = user

        await context.bot.send_message(user,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        waiting.append(user)

        fake_online = random.randint(50,200)
        fake_wait = random.randint(5,30)

        await update.message.reply_text(
f"""🔎 Searching for stranger...

👥 {fake_online} users online
💬 {fake_wait} waiting"""
)

# STOP
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active:

        partner = active[user]

        del active[user]
        del active[partner]

        await context.bot.send_message(partner,"❌ Partner left chat.")
        await update.message.reply_text("Chat ended.")

# NEXT
async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await stop(update,context)
    await find(update,context)

# VIP
async def vip(update: Update):

    await update.message.reply_text(
"""💎 VIP Membership

⚡ Faster matches
🎯 Gender filter
💬 Unlimited chats

Price

1 Month – ₹49
3 Months – ₹99
Lifetime – ₹299

UPI:
hatmahendran267r@ybl

Send screenshot to:
@Elentraadmin001
"""
)

# INVITE SYSTEM
async def invite(update: Update):

    user = update.effective_user.id

    link = f"https://t.me/ElentraChatBot?start={user}"

    await update.message.reply_text(
f"""🎁 Invite Friends

Invite 3 friends and get VIP!

Your invite link:

{link}
"""
)

# ADMIN STATS
async def stats(update: Update):

    if update.effective_user.id != ADMIN_ID:
        return

    users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    await update.message.reply_text(
f"""📊 Bot Stats

Users: {users}
Waiting: {len(waiting)}
Active chats: {len(active)//2}
"""
)

# MAIN HANDLER
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id
    text = update.message.text

    if user in editing:

        ok = save_profile(user,text)

        editing.pop(user)

        if ok:
            await update.message.reply_text("✅ Profile saved!",reply_markup=menu)
        else:
            await update.message.reply_text("❌ Format error")

        return

    if user in setting_partner:

        save_partner(user,text)

        setting_partner.pop(user)

        await update.message.reply_text("✅ Partner preference saved",reply_markup=menu)

        return

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update)

    elif text == "✏ Edit Profile":
        await edit_profile(update)

    elif text == "🎯 Partner Gender":
        await partner(update)

    elif text == "⏭ Next":
        await next_chat(update,context)

    elif text == "⛔ Stop":
        await stop(update,context)

    elif text == "💎 VIP":
        await vip(update)

    elif text == "🎁 Invite Friends":
        await invite(update)

    elif user in active:

        partner = active[user]

        await context.bot.copy_message(
        chat_id=partner,
        from_chat_id=user,
        message_id=update.message.message_id
        )

# RUN BOT
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

print("ElentraChat V19 Running")

app.run_polling()		

