import os
import sqlite3
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# --- SETTINGS ---
TOKEN = "8198720512:AAFi8tCWwyjFdzKgqzIS6rPdTNfWw0gOcFw" 
CH_ID = "http://t.me/cashhub_CH_bot"           
BOT_USERNAME = "cashhub_CH_bot"   
PORT = int(os.environ.get("PORT", 5000))

app = Flask(__name__)

# --- DATABASE LOGIC ---
def get_db_connection():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, 
                  referred_by INTEGER, last_bonus TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_or_create_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        conn.commit()
        user = (user_id, 0, None, None)
    conn.close()
    return user

# --- BOT COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    user = get_or_create_user(user_id)

    # Referral System
    if args and args[0].isdigit() and not user[2] and int(args[0]) != user_id:
        ref_id = int(args[0])
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (ref_id, user_id))
        c.execute("UPDATE users SET balance = balance + 5 WHERE user_id = ?", (ref_id,))
        conn.commit()
        conn.close()
        try:
            await context.bot.send_message(ref_id, "🎁 You got +5 coins! Someone joined using your link.")
        except: pass

    # Dashboard Button
    web_url = f"https://{request.host}/?id={user_id}" if request.host else "Deploy first to see link"
    keyboard = [
   InlineKeyboardButton("📱 Open Dashboard", url=f"https://cash-bot-69mn.onrender.com/?id={user_id}"),
   [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{CH_ID.replace('@','')}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Hello! Welcome to the Earning Bot.\n\n💰 Balance: {user[1]} Coins\n🎁 Daily Bonus: /bonus\n\nClick below to open your wallet:",
        reply_markup=reply_markup
    )

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_or_create_user(user_id)
    now = datetime.now()

    if user[3] and datetime.strptime(user[3], '%Y-%m-%d %H:%M:%S') > now - timedelta(days=1):
        await update.message.reply_text("❌ Bonus already claimed! Try again in 24h.")
        return

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + 2, last_bonus = ? WHERE user_id = ?", 
              (now.strftime('%Y-%m-%d %H:%M:%S'), user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Success! +2 Coins added to your wallet.")

# --- WEB SERVER ROUTES ---
@app.route('/')
def index():
    user_id = request.args.get('id')
    if not user_id: return "Access Denied: Please use the bot."
    user = get_or_create_user(int(user_id))
    return render_template('index.html', user=user, bot_username=BOT_USERNAME)

def run_bot():
    token = TOKEN
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bonus", bonus))
    application.run_polling()

if __name__ == '__main__':
    # Threading use karke bot aur flask ek sath chalenge
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=PORT)

