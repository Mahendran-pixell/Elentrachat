import sqlite3
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID = 8232389772

# DATABASE
conn = sqlite3.connect("elentra.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
name TEXT,
age INTEGER,
country TEXT,
gender TEXT,
partner_gender TEXT,
vip INTEGER DEFAULT 0,
coins INTEGER DEFAULT 10,
agreed INTEGER DEFAULT 0
)
""")

conn.commit()

waiting_users = []
active_chats = {}

menu = ReplyKeyboardMarkup([
["🔎 Find Stranger"],
["👤 Profile","✏️ Edit Profile"],
["🎯 Partner Gender","🌍 Country"],
["💎 VIP","📜 Terms"]
],resize_keyboard=True)

terms = """
📜 Terms & Privacy

• Chats are anonymous
• Do not share personal information
• No harassment or illegal content
• Respect other users

Type /agree to continue.
"""

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user,))
    conn.commit()

    agreed = cursor.execute("SELECT agreed FROM users WHERE user_id=?",(user,)).fetchone()[0]

    if agreed == 0:
        await update.message.reply_text(terms)
        return

    await update.message.reply_text(
"👋 Welcome to ElentraChat!",
reply_markup=menu
)

# AGREE
async def agree(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("UPDATE users SET agreed=1 WHERE user_id=?",(user,))
    conn.commit()

    await update.message.reply_text("✅ Rules accepted!",reply_markup=menu)

# PROFILE
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    data = cursor.execute(
    "SELECT name,age,country,gender,partner_gender,coins,vip FROM users WHERE user_id=?",(user,)
    ).fetchone()

    name,age,country,gender,partner,coins,vip = data

    status = "VIP 💎" if vip else "Free"

    await update.message.reply_text(
f"""👤 Your Profile

Name: {name}
Age: {age}
Country: {country}
Gender: {gender}
Looking for: {partner}

Coins: {coins}
Status: {status}
"""
)

# EDIT PROFILE
async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"Send profile like:\nName,Age,Country,Gender"
)

# SAVE PROFILE
async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    try:

        name,age,country,gender = update.message.text.split(",")

        cursor.execute(
        "UPDATE users SET name=?,age=?,country=?,gender=? WHERE user_id=?",
        (name,int(age),country,gender,user)
        )

        conn.commit()

        await update.message.reply_text("✅ Profile saved")

    except:
        pass

# SET PARTNER GENDER
async def partner_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"Send preferred partner gender:\nMale / Female / Any"
)

# SAVE PARTNER
async def save_partner(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    gender = update.message.text

    cursor.execute(
    "UPDATE users SET partner_gender=? WHERE user_id=?",
    (gender,user)
    )

    conn.commit()

    await update.message.reply_text("🎯 Partner preference saved")

# FIND CHAT
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if waiting_users:

        partner = waiting_users.pop(0)

        active_chats[user] = partner
        active_chats[partner] = user

        await context.bot.send_message(user,"✅ Connected!")
        await context.bot.send_message(partner,"✅ Connected!")

    else:

        waiting_users.append(user)

        await update.message.reply_text("🔎 Searching...")

# STOP
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:

        partner = active_chats[user]

        del active_chats[user]
        del active_chats[partner]

        await context.bot.send_message(partner,"❌ Partner left")
        await update.message.reply_text("Chat ended")

# RELAY
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:

        partner = active_chats[user]

        await context.bot.copy_message(
        chat_id=partner,
        from_chat_id=user,
        message_id=update.message.message_id
        )

# VIP
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""💎 VIP

Benefits

⚡ Faster matches
🌍 Country filter
🎯 Gender filter
💬 Unlimited chats

Contact admin to activate."""
)

# ADMIN STATS
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    await update.message.reply_text(
f"""📊 Stats

Users: {total}
Waiting: {len(waiting_users)}
Active chats: {len(active_chats)//2}
"""
)

# REMINDER
async def reminder(app):

    while True:

        await asyncio.sleep(21600)

        users = cursor.execute("SELECT user_id FROM users").fetchall()

        for u in users:

            try:

                await app.bot.send_message(
                u[0],
"👋 People are waiting for you on ElentraChat!\nTap /start"
                )

            except:
                pass

async def post_init(app):
    asyncio.create_task(reminder(app))

# BUTTONS
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "✏️ Edit Profile":
        await edit(update,context)

    elif text == "🎯 Partner Gender":
        await partner_gender(update,context)

    elif text == "💎 VIP":
        await vip(update,context)

    elif text == "📜 Terms":
        await update.message.reply_text(terms)

app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("agree",agree))
app.add_handler(CommandHandler("stop",stop))
app.add_handler(CommandHandler("stats",stats))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,buttons))
app.add_handler(MessageHandler(filters.TEXT,save_profile))
app.add_handler(MessageHandler(filters.ALL,relay))

print("ElentraChat V17 running 🚀")

app.run_polling()
