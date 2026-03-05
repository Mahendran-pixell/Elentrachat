import sqlite3
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN="8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID=8232389772

conn=sqlite3.connect("elentra.db",check_same_thread=False)
cursor=conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
name TEXT,
age INTEGER,
country TEXT,
gender TEXT,
partner_gender TEXT,
coins INTEGER DEFAULT 10,
vip INTEGER DEFAULT 0,
agreed INTEGER DEFAULT 0
)
""")

conn.commit()

waiting=[]
active={}
user_state={}

menu=ReplyKeyboardMarkup([
["🔎 Find Stranger"],
["👤 Profile","✏️ Edit Profile"],
["🎯 Partner Gender","🌍 Country"],
["💎 VIP","📜 Terms"]
],resize_keyboard=True)

terms="""
📜 Terms & Privacy

• Chats are anonymous
• No harassment
• No illegal content
• Respect other users

Type /agree to continue.
"""

# START
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user,))
    conn.commit()

    agreed=cursor.execute("SELECT agreed FROM users WHERE user_id=?",(user,)).fetchone()[0]

    if agreed==0:
        await update.message.reply_text(terms)
        return

    await update.message.reply_text("👋 Welcome to ElentraChat!",reply_markup=menu)

# AGREE
async def agree(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    cursor.execute("UPDATE users SET agreed=1 WHERE user_id=?",(user,))
    conn.commit()

    await update.message.reply_text("✅ Rules accepted!",reply_markup=menu)

# PROFILE
async def profile(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    data=cursor.execute(
    "SELECT name,age,country,gender,partner_gender,coins,vip FROM users WHERE user_id=?",
    (user,)
    ).fetchone()

    name,age,country,gender,partner,coins,vip=data

    status="VIP 💎" if vip else "Free"

    await update.message.reply_text(
f"""👤 Profile

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
async def edit_profile(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_state[update.effective_user.id]="edit"

    await update.message.reply_text(
"Send profile like:\nName,Age,Country,Gender"
)

# PARTNER GENDER
async def partner(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_state[update.effective_user.id]="partner"

    await update.message.reply_text(
"Send preferred partner gender:\nMale / Female / Any"
)

# COUNTRY
async def country(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_state[update.effective_user.id]="country"

    await update.message.reply_text("Send your country")

# FIND
async def find(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if waiting:

        partner=waiting.pop(0)

        active[user]=partner
        active[partner]=user

        await context.bot.send_message(user,"✅ Connected!")
        await context.bot.send_message(partner,"✅ Connected!")

    else:

        waiting.append(user)

        await update.message.reply_text("🔎 Searching...")

# STOP
async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id

    if user in active:

        partner=active[user]

        del active[user]
        del active[partner]

        await context.bot.send_message(partner,"❌ Partner left")
        await update.message.reply_text("Chat ended")

# MESSAGE HANDLER
async def handle_message(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id
    text=update.message.text

    # PROFILE SAVE
    if user_state.get(user)=="edit":

        try:
            name,age,country,gender=text.split(",")

            cursor.execute(
            "UPDATE users SET name=?,age=?,country=?,gender=? WHERE user_id=?",
            (name,int(age),country,gender,user)
            )

            conn.commit()

            await update.message.reply_text("✅ Profile saved")

        except:
            await update.message.reply_text("❌ Format incorrect")

        user_state[user]=None
        return

    # PARTNER GENDER
    if user_state.get(user)=="partner":

        cursor.execute(
        "UPDATE users SET partner_gender=? WHERE user_id=?",
        (text,user)
        )

        conn.commit()

        await update.message.reply_text("🎯 Partner preference saved")

        user_state[user]=None
        return

    # COUNTRY
    if user_state.get(user)=="country":

        cursor.execute(
        "UPDATE users SET country=? WHERE user_id=?",
        (text,user)
        )

        conn.commit()

        await update.message.reply_text("🌍 Country saved")

        user_state[user]=None
        return

    # CHAT RELAY
    if user in active:

        partner=active[user]

        await context.bot.copy_message(
        chat_id=partner,
        from_chat_id=user,
        message_id=update.message.message_id
        )

# VIP
async def vip(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""💎 VIP

Benefits

⚡ Faster matches
🌍 Country filter
🎯 Gender filter
💬 Unlimited chats

Contact admin to activate."""
)

# BUTTONS
async def buttons(update:Update,context:ContextTypes.DEFAULT_TYPE):

    text=update.message.text

    if text=="🔎 Find Stranger":
        await find(update,context)

    elif text=="👤 Profile":
        await profile(update,context)

    elif text=="✏️ Edit Profile":
        await edit_profile(update,context)

    elif text=="🎯 Partner Gender":
        await partner(update,context)

    elif text=="🌍 Country":
        await country(update,context)

    elif text=="💎 VIP":
        await vip(update,context)

    elif text=="📜 Terms":
        await update.message.reply_text(terms)

app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("agree",agree))
app.add_handler(CommandHandler("stop",stop))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,buttons))
app.add_handler(MessageHandler(filters.TEXT,handle_message))

print("ElentraChat V17 FIX running 🚀")

app.run_polling()
