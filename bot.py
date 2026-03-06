import sqlite3
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
country TEXT,
gender TEXT,
partner TEXT
)
""")

conn.commit()

waiting = []
active = {}
editing = {}

menu = ReplyKeyboardMarkup([
["🔎 Find Stranger"],
["👤 Profile","✏️ Edit Profile"],
["💎 VIP"]
], resize_keyboard=True)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)",(user,))
    conn.commit()

    await update.message.reply_text(
"👋 Welcome to ElentraChat",
reply_markup=menu)

# PROFILE
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    data = cursor.execute(
    "SELECT name,age,country,gender FROM users WHERE user_id=?",
    (user,)
    ).fetchone()

    await update.message.reply_text(
f"""👤 Profile

Name: {data[0]}
Age: {data[1]}
Country: {data[2]}
Gender: {data[3]}
"""
)

# EDIT PROFILE
async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id
    editing[user] = True

    await update.message.reply_text(
"""Send profile like:

Name,Age,Country,Gender

Example:
Zayn,18,India,Male"""
)

# SAVE PROFILE
async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user not in editing:
        return

    try:

        name,age,country,gender = update.message.text.split(",")

        cursor.execute("""
        UPDATE users
        SET name=?,age=?,country=?,gender=?
        WHERE user_id=?
        """,(name.strip(),age.strip(),country.strip(),gender.strip(),user))

        conn.commit()

        del editing[user]

        await update.message.reply_text("✅ Profile saved!")

    except:

        await update.message.reply_text("❌ Format wrong. Use:\nName,Age,Country,Gender")

# FIND STRANGER
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if waiting:

        partner = waiting.pop(0)

        active[user] = partner
        active[partner] = user

        await context.bot.send_message(user,"✅ Connected!")
        await context.bot.send_message(partner,"✅ Connected!")

    else:

        waiting.append(user)

        await update.message.reply_text("🔎 Searching for partner...")

# STOP
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in active:

        partner = active[user]

        del active[user]
        del active[partner]

        await context.bot.send_message(partner,"❌ Partner left")

# NEXT
async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await stop(update,context)
    await find(update,context)

# RELAY
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user in editing:
        await save_profile(update,context)
        return

    if user in active:

        partner = active[user]

        await context.bot.copy_message(
        chat_id=partner,
        from_chat_id=user,
        message_id=update.message.message_id
        )

# VIP
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""💎 VIP

1 Month – ₹49
3 Months – ₹99
Lifetime – ₹299

UPI:
hatmahendran267r@ybl

Send screenshot to:
@Elentraadmin001
"""
)

# BUTTONS
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🔎 Find Stranger":
        await find(update,context)

    elif text == "👤 Profile":
        await profile(update,context)

    elif text == "✏️ Edit Profile":
        await edit_profile(update,context)

    elif text == "💎 VIP":
        await vip(update,context)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("next", next_chat))
app.add_handler(CommandHandler("stop", stop))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, buttons))
app.add_handler(MessageHandler(filters.ALL, relay))

print("Bot running")

app.run_polling()
