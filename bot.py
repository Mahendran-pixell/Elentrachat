import sqlite3
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID = 8232389772

db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
name TEXT,
age TEXT,
gender TEXT,
pref TEXT DEFAULT 'Any'
)
""")
db.commit()

waiting_users = []
active_chats = {}
editing_profile = {}
editing_pref = {}

menu = ReplyKeyboardMarkup([
["🔎 Find Partner"],
["👤 Profile","✏ Edit Profile"],
["🎯 Partner Gender"],
["🚨 Report","💎 VIP"],
["📜 Terms","🔐 Privacy"],
["⏭ Next","⛔ Stop"]
],resize_keyboard=True)


async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id

    cursor.execute(
        "INSERT OR IGNORE INTO users(user_id) VALUES(?)",
        (user,)
    )
    db.commit()

    await update.message.reply_text(
        "👋 Welcome to ElentraChat\nAnonymous random chat bot.",
        reply_markup=menu
    )


async def profile(update:Update,context:ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id

    data = cursor.execute(
        "SELECT name,age,gender,pref FROM users WHERE user_id=?",
        (user,)
    ).fetchone()

    await update.message.reply_text(
f"""👤 Profile

Name: {data[0]}
Age: {data[1]}
Gender: {data[2]}
Looking for: {data[3]}
"""
)


async def edit(update:Update,context:ContextTypes.DEFAULT_TYPE):
    editing_profile[update.effective_user.id] = True

    await update.message.reply_text(
        "Send profile like:\nName,Age,Gender\nExample:\nAlex,18,Male"
    )


async def partner_gender(update:Update,context:ContextTypes.DEFAULT_TYPE):
    editing_pref[update.effective_user.id] = True

    await update.message.reply_text(
        "Choose partner gender:\nMale / Female / Any"
    )


def match_user(user):

    my_gender,my_pref = cursor.execute(
        "SELECT gender,pref FROM users WHERE user_id=?",
        (user,)
    ).fetchone()

    for u in waiting_users:

        if u == user:
            continue

        g,p = cursor.execute(
            "SELECT gender,pref FROM users WHERE user_id=?",
            (u,)
        ).fetchone()

        if (my_pref=="Any" or my_pref==g) and (p=="Any" or p==my_gender):

            waiting_users.remove(u)
            return u

    return None


async def find_partner(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:
        await update.message.reply_text("You are already chatting.")
        return

    partner = match_user(user)

    if partner:

        active_chats[user] = partner
        active_chats[partner] = user

        await context.bot.send_message(user,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        if user not in waiting_users:
            waiting_users.append(user)

        await update.message.reply_text("🔎 Searching for partner...")


async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user not in active_chats:
        await update.message.reply_text("You are not in a chat.")
        return

    partner = active_chats[user]

    del active_chats[user]
    del active_chats[partner]

    await context.bot.send_message(partner,"❌ Partner left chat")
    await update.message.reply_text("Chat ended")


async def next_chat(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active_chats:

        partner = active_chats[user]

        del active_chats[user]
        del active_chats[partner]

        await context.bot.send_message(partner,"❌ Partner skipped")

    await find_partner(update,context)


async def vip(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""💎 VIP Membership

Benefits:
• Unlimited chats
• Gender filter

Price: ₹49

UPI:
hatmahendran267r@ybl

Send screenshot to:
@Elentraadmin001
"""
)


async def report(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user not in active_chats:
        await update.message.reply_text("No partner to report.")
        return

    partner = active_chats[user]

    await context.bot.send_message(
        ADMIN_ID,
        f"🚨 User Report\nReporter: {user}\nPartner: {partner}"
    )

    await update.message.reply_text("Report sent to admin.")


async def terms(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""📜 Terms

• Respect other users
• No harassment
• No illegal content
• Violators will be banned
"""
)


async def privacy(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""🔐 Privacy Policy

• Chats are anonymous
• We do not store messages
• Do not share personal info
"""
)


async def handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id
    text = update.message.text

    if user in editing_profile:

        try:
            name,age,gender = text.split(",")

            cursor.execute(
                "UPDATE users SET name=?,age=?,gender=? WHERE user_id=?",
                (name.strip(),age.strip(),gender.strip(),user)
            )
            db.commit()

            editing_profile.pop(user)

            await update.message.reply_text(
                "Profile saved",reply_markup=menu
            )

        except:
            await update.message.reply_text("Format wrong")

        return


    if user in editing_pref:

        cursor.execute(
            "UPDATE users SET pref=? WHERE user_id=?",
            (text,user)
        )
        db.commit()

        editing_pref.pop(user)

        await update.message.reply_text("Preference saved")

        return


    if user in active_chats:

        partner = active_chats[user]

        await context.bot.copy_message(
            chat_id=partner,
            from_chat_id=user,
            message_id=update.message.message_id
        )
        return


    if text == "🔎 Find Partner":
        await find_partner(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "✏ Edit Profile":
        await edit(update,context)

    elif text == "🎯 Partner Gender":
        await partner_gender(update,context)

    elif text == "💎 VIP":
        await vip(update,context)

    elif text == "🚨 Report":
        await report(update,context)

    elif text == "📜 Terms":
        await terms(update,context)

    elif text == "🔐 Privacy":
        await privacy(update,context)

    elif text == "⏭ Next":
        await next_chat(update,context)

    elif text == "⛔ Stop":
        await stop(update,context)


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(MessageHandler(filters.TEXT,handler))

print("ElentraChat Stable Running")

app.run_polling()
