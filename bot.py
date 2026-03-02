import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")

waiting_users = []
active_chats = {}

# START COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id

    if user_id in active_chats:
        await update.message.reply_text("⚠️ You are already connected. Use /next to skip.")
        return

    if user_id in waiting_users:
        await update.message.reply_text("⏳ Still waiting for a stranger...")
        return

    if waiting_users:
        partner = waiting_users.pop(0)

        active_chats[user_id] = partner
        active_chats[partner] = user_id

        await update.message.reply_text("✅ Connected to a stranger! Say hi 👋")
        await context.bot.send_message(partner, "✅ Connected to a stranger! Say hi 👋")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("⏳ Waiting for a stranger...")

# NEXT COMMAND (Skip)
async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id

    if user_id in active_chats:
        partner = active_chats.pop(user_id)
        active_chats.pop(partner, None)

        await context.bot.send_message(partner, "⚠️ Stranger disconnected.")

    await start(update, context)

# STOP COMMAND
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id

    if user_id in active_chats:
        partner = active_chats.pop(user_id)
        active_chats.pop(partner, None)

        await context.bot.send_message(partner, "⚠️ Stranger disconnected.")
        await update.message.reply_text("❌ You disconnected.")
    else:
        await update.message.reply_text("⚠️ You are not connected.")

# MESSAGE HANDLER
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id

    if user_id in active_chats:
        partner = active_chats[user_id]
        try:
            await update.message.copy(chat_id=partner)
        except:
            await update.message.reply_text("⚠️ Failed to send message.")
    else:
        await update.message.reply_text("⚠️ Type /start to find a stranger.")

# ONLINE COUNT
async def online(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_online = len(waiting_users) + len(active_chats)
    await update.message.reply_text(f"👥 Users online: {total_online}")

# BUILD APP
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("next", next_chat))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CommandHandler("online", online))
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

app.run_polling()
