import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637048210:AAHxkLGOHMQfUEjeGqUuLRD2hK11-GKQwGk"
ADMIN_ID = 8232389772

waiting = []
active = {}

menu = ReplyKeyboardMarkup(
[
["🔎 Find Stranger"],
["⏭ Next","⛔ Stop"],
["🚨 Report","📜 Terms"]
],
resize_keyboard=True
)

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "👋 Welcome to ElentraChat\nAnonymous random chat.",
        reply_markup=menu
    )


def match(user):

    for u in waiting:

        if u != user:

            waiting.remove(u)
            return u

    return None


async def find(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active:
        await update.message.reply_text("You are already chatting.")
        return

    partner = match(user)

    if partner:

        active[user] = partner
        active[partner] = user

        await context.bot.send_message(user,"✅ Connected! Say hi 👋")
        await context.bot.send_message(partner,"✅ Connected! Say hi 👋")

    else:

        if user not in waiting:
            waiting.append(user)

        await update.message.reply_text("🔎 Searching for stranger...")


async def stop(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in waiting:
        waiting.remove(user)

    if user not in active:
        await update.message.reply_text("You are not in a chat.")
        return

    partner = active[user]

    del active[user]
    del active[partner]

    await context.bot.send_message(partner,"❌ Partner left chat")
    await update.message.reply_text("Chat ended.")


async def next_chat(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active:

        partner = active[user]

        del active[user]
        del active[partner]

        await context.bot.send_message(partner,"❌ Partner skipped")

    await find(update,context)


async def report(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user not in active:
        await update.message.reply_text("No partner to report.")
        return

    partner = active[user]

    await context.bot.send_message(
        ADMIN_ID,
        f"🚨 Report\nReporter: {user}\nPartner: {partner}"
    )

    await update.message.reply_text("Report sent to admin.")


async def terms(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""📜 Terms & Conditions

• Be respectful
• No harassment
• No illegal content
• Violators will be banned
"""
)


async def handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id
    text = update.message.text

    if user in active:

        partner = active[user]

        await context.bot.copy_message(
            chat_id=partner,
            from_chat_id=user,
            message_id=update.message.message_id
        )

        return


    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "⏭ Next":
        await next_chat(update,context)

    elif text == "⛔ Stop":
        await stop(update,context)

    elif text == "🚨 Report":
        await report(update,context)

    elif text == "📜 Terms":
        await terms(update,context)


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(MessageHandler(filters.TEXT,handler))

print("ElentraChat Core Running")

app.run_polling()
