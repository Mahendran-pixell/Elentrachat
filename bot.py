import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"

db = sqlite3.connect("users.db",check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
name TEXT,
age TEXT
)
""")
db.commit()

waiting = []
active = {}
editing = {}

menu = ReplyKeyboardMarkup([
["🔎 Find Partner"],
["👤 Profile","✏ Edit Profile"],
["⏭ Next","⛔ Stop"]
],resize_keyboard=True)


async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    cursor.execute(
        "INSERT OR IGNORE INTO users(user_id) VALUES(?)",
        (uid,)
    )
    db.commit()

    await update.message.reply_text(
        "👋 Welcome to ElentraChat\nAnonymous random chat.",
        reply_markup=menu
    )


async def profile(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    data = cursor.execute(
        "SELECT name,age FROM users WHERE user_id=?",
        (uid,)
    ).fetchone()

    await update.message.reply_text(
f"""👤 Your Profile

Name: {data[0]}
Age: {data[1]}
"""
)


async def edit_profile(update:Update,context:ContextTypes.DEFAULT_TYPE):

    editing[update.effective_user.id] = True

    await update.message.reply_text(
        "Send profile like:\nName,Age\nExample:\nAlex,18"
    )


def match(user):

    for u in waiting:

        if u != user:
            waiting.remove(u)
            return u

    return None


async def find(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    if uid in active:
        await update.message.reply_text("You are already chatting.")
        return

    partner = match(uid)

    if partner:

        active[uid] = partner
        active[partner] = uid

        await context.bot.send_message(uid,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        if uid not in waiting:
            waiting.append(uid)

        await update.message.reply_text("🔎 Searching for partner...")


async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    if uid in waiting:
        waiting.remove(uid)

    if uid not in active:
        await update.message.reply_text("You are not in a chat.")
        return

    partner = active[uid]

    del active[uid]
    del active[partner]

    await context.bot.send_message(partner,"❌ Partner left chat")
    await update.message.reply_text("Chat ended.")


async def next_chat(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    if uid in active:

        partner = active[uid]

        del active[uid]
        del active[partner]

        await context.bot.send_message(partner,"❌ Partner skipped")

    await find(update,context)


async def message_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id
    text = update.message.text

    if uid in editing:

        try:

            name,age = text.split(",")

            cursor.execute(
                "UPDATE users SET name=?,age=? WHERE user_id=?",
                (name.strip(),age.strip(),uid)
            )
            db.commit()

            editing.pop(uid)

            await update.message.reply_text(
                "Profile saved",
                reply_markup=menu
            )

        except:
            await update.message.reply_text("Format wrong")

        return


    if uid in active:

        partner = active[uid]

        await context.bot.copy_message(
            chat_id=partner,
            from_chat_id=uid,
            message_id=update.message.message_id
        )

        return


    if text == "🔎 Find Partner":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "✏ Edit Profile":
        await edit_profile(update,context)

    elif text == "⏭ Next":
        await next_chat(update,context)

    elif text == "⛔ Stop":
        await stop(update,context)


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(MessageHandler(filters.TEXT,message_handler))

print("ElentraChat Core Running")

app.run_polling()
