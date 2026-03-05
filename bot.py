import os
import asyncio
import sqlite3
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8232389772

boys_queue = []
girls_queue = []
random_queue = []

active_chats = {}
online_users = set()

photo_timer = {}

conn = sqlite3.connect("elentra.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
name TEXT,
age INTEGER,
country TEXT,
gender TEXT,
looking TEXT,
coins INTEGER DEFAULT 0,
chats INTEGER DEFAULT 0,
last_daily INTEGER DEFAULT 0
)
""")

conn.commit()

main_menu = ReplyKeyboardMarkup([
["🔎 Find Stranger","👤 Profile"],
["🎁 Daily Coins","⏱ Photo Timer"],
["🌍 Country Filter","ℹ️ Help"]
],resize_keyboard=True)

gender_menu = ReplyKeyboardMarkup([
["👦 Boy","👧 Girl","🌍 Random"]
],resize_keyboard=True)

timer_menu = ReplyKeyboardMarkup([
["5 sec","10 sec","20 sec"]
],resize_keyboard=True)

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id
    online_users.add(user_id)

    user = cursor.execute(
    "SELECT name FROM users WHERE user_id=?",(user_id,)
    ).fetchone()

    if not user:
        cursor.execute("INSERT INTO users(user_id) VALUES(?)",(user_id,))
        conn.commit()

        await update.message.reply_text(
        "Welcome! Let's setup your profile.\nSend your name:")
        context.user_data["setup"]="name"
        return

    await update.message.reply_text(
    "👋 Welcome to ElentraChat",
    reply_markup=main_menu)

async def setup_profile(update,context):

    user_id = update.message.chat_id
    step = context.user_data.get("setup")

    if step=="name":
        cursor.execute("UPDATE users SET name=? WHERE user_id=?",
        (update.message.text,user_id))
        conn.commit()

        await update.message.reply_text("Send your age:")
        context.user_data["setup"]="age"
        return

    if step=="age":
        cursor.execute("UPDATE users SET age=? WHERE user_id=?",
        (update.message.text,user_id))
        conn.commit()

        await update.message.reply_text("Your country?")
        context.user_data["setup"]="country"
        return

    if step=="country":
        cursor.execute("UPDATE users SET country=? WHERE user_id=?",
        (update.message.text,user_id))
        conn.commit()

        await update.message.reply_text("Your gender? (boy/girl)")
        context.user_data["setup"]="gender"
        return

    if step=="gender":
        cursor.execute("UPDATE users SET gender=? WHERE user_id=?",
        (update.message.text,user_id))
        conn.commit()

        await update.message.reply_text("Looking for? (boy/girl/random)")
        context.user_data["setup"]="looking"
        return

    if step=="looking":
        cursor.execute("UPDATE users SET looking=? WHERE user_id=?",
        (update.message.text,user_id))
        conn.commit()

        context.user_data["setup"]=None

        await update.message.reply_text(
        "Profile saved!",
        reply_markup=main_menu)

async def find(update,context):

    await update.message.reply_text(
    "Who do you want to chat with?",
    reply_markup=gender_menu)

async def match_user(user_id,queue,update,context):

    await update.message.reply_text("Searching...")
    await asyncio.sleep(1)

    if queue:
        partner=queue.pop(0)

        active_chats[user_id]=partner
        active_chats[partner]=user_id

        await update.message.reply_text(
        "Connected! Say hi 👋")

        await context.bot.send_message(
        partner,"Connected! Say hi 👋")

    else:
        queue.append(user_id)
        await update.message.reply_text(
        "Waiting for stranger...")

async def relay(update,context):

    user_id = update.message.chat_id

    if user_id in active_chats:

        partner = active_chats[user_id]

        try:
            msg = await update.message.copy(chat_id=partner)

            if update.message.photo:

                timer = photo_timer.get(user_id,5)

                await asyncio.sleep(timer)

                await context.bot.delete_message(
                chat_id=partner,
                message_id=msg.message_id)

        except:
            pass

async def next_chat(update,context):

    user_id = update.message.chat_id

    if user_id in active_chats:

        partner = active_chats[user_id]

        active_chats.pop(user_id,None)
        active_chats.pop(partner,None)

        await context.bot.send_message(
        partner,"Stranger skipped.")

        await update.message.reply_text(
        "Searching next...")

async def stop_chat(update,context):

    user_id = update.message.chat_id

    if user_id in active_chats:

        partner = active_chats[user_id]

        active_chats.pop(user_id,None)
        active_chats.pop(partner,None)

        await context.bot.send_message(
        partner,"Stranger disconnected.")

        await update.message.reply_text(
        "Chat ended.",
        reply_markup=main_menu)

async def timer(update,context):

    await update.message.reply_text(
    "Choose photo auto-delete timer",
    reply_markup=timer_menu)

async def timer_set(update,context):

    user_id=update.message.chat_id
    text=update.message.text

    if text=="5 sec":
        photo_timer[user_id]=5

    if text=="10 sec":
        photo_timer[user_id]=10

    if text=="20 sec":
        photo_timer[user_id]=20

    await update.message.reply_text(
    f"Photo timer set: {photo_timer[user_id]} sec",
    reply_markup=main_menu)

async def stats(update,context):

    if update.message.chat_id != ADMIN_ID:
        return

    total = cursor.execute(
    "SELECT COUNT(*) FROM users").fetchone()[0]

    online = len(online_users)
    active = len(active_chats)//2

    await update.message.reply_text(
f"""
Bot Stats

Total users: {total}
Online users: {online}
Active chats: {active}
""")

async def buttons(update,context):

    if context.user_data.get("setup"):
        await setup_profile(update,context)
        return

    text = update.message.text
    user_id = update.message.chat_id

    if text=="🔎 Find Stranger":
        await find(update,context)

    elif text=="👦 Boy":
        await match_user(user_id,girls_queue,update,context)

    elif text=="👧 Girl":
        await match_user(user_id,boys_queue,update,context)

    elif text=="🌍 Random":
        await match_user(user_id,random_queue,update,context)

    elif text=="⏱ Photo Timer":
        await timer(update,context)

    elif text in ["5 sec","10 sec","20 sec"]:
        await timer_set(update,context)

    else:
        await relay(update,context)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("next",next_chat))
app.add_handler(CommandHandler("stop",stop_chat))
app.add_handler(CommandHandler("stats",stats))

app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO,buttons))

print("ElentraChat V6 running")

app.run_polling()	

