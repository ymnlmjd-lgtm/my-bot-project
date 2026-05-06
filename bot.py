import os
import telebot
import sqlite3
import requests
import re
import asyncio
import edge_tts
import subprocess
from gtts import gTTS
from telebot import types
from flask import Flask
from threading import Thread

# --- 1. إعداد خادم البقاء حياً ---
app = Flask('')
@app.route('/')
def home(): return "I am alive!"

def run(): app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- 2. الإعدادات ---
TOKEN = "ZFpY8689609657:AAHN5Gqb0rwXi52zweHJ34LecR5vFgehuMI"
CH_ID = -1003982280092  
CH_LINK = 'https://t.me/+TWfwB6wfdNw5YWVk'
bot = telebot.TeleBot(API_TOKEN)
VOICE = "ar-EG-SalmaNeural"
POINTS_FOR_MINING = 20 

# قاعدة البيانات
conn = sqlite3.connect('users_data.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, points INTEGER, referrals INTEGER, invited_by INTEGER)''')
conn.commit()

# --- 3. الدوال البرمجية ---

def get_user(user_id):
    cursor.execute("SELECT points, referrals, invited_by FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO users VALUES (?, 0, 0, NULL)", (user_id,))
        conn.commit()
        return (0, 0, None)
    return res

def check_sub(user_id):
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'creator', 'administrator']
    except: return False

def fetch_numbers():
    try:
        url = "https://receive-smss.com/"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10).text
        nums = re.findall(r'\+\d{10,15}', res)
        return list(set(nums))[:10]
    except: return ["+12025550123", "+447700900123"]

async def create_voice(text, filename):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(filename)

def text_to_video(text, filename):
    audio_file = f"temp_{filename}.mp3"
    gTTS(text=text, lang='ar').save(audio_file)
    command = [
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=720x1280:d=5',
        '-i', audio_file, '-c:v', 'libx264', '-tune', 'stillimage', 
        '-c:a', 'aac', '-pix_fmt', 'yuv420p', '-shortest', filename
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(audio_file): os.remove(audio_file)

def main_menu(user_id):
    p, _, _ = get_user(user_id)
    mine_status = "✅" if p >= POINTS_FOR_MINING else "🔒"
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton(f"📸 تلغيم صورة {mine_status}"),
        types.KeyboardButton("📱 جلب أرقام وهمية"),
        types.KeyboardButton("🎙️ تحويل نص لصوت"),
        types.KeyboardButton("🎬 تحويل نص لفيديو"),
        types.KeyboardButton("👤 إحصائياتي"),
        types.KeyboardButton("🔗 رابط الدعوة")
    )
    return markup

# --- 4. معالجة الرسائل ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        inviter_id = int(args[1])
        p, r, invited_by = get_user(user_id)
        if invited_by is None and inviter_id != user_id:
            cursor.execute("UPDATE users SET points = points + 5, referrals = referrals + 1 WHERE user_id = ?", (inviter_id,))
            cursor.execute("UPDATE users SET invited_by = ? WHERE user_id = ?", (inviter_id, user_id))
            conn.commit()

    if not check_sub(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("انضم للقناة أولاً 📢", url=CH_LINK))
        bot.send_message(message.chat.id, "⚠️ اشترك بالقناة لتفعيل البوت!", reply_markup=markup)
        return
    bot.send_message(message.chat.id, "أهلاً بالقيادة! 🦅 البوت جاهز للعمل.", reply_markup=main_menu(user_id))

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    user_id = message.from_user.id
    if not check_sub(user_id): return
    p, r, _ = get_user(user_id)

    if message.text == "📱 جلب أرقام وهمية":
        bot.send_message(message.chat.id, "📡 جاري سحب الأرقام...")
        nums = fetch_numbers()
        bot.send_message(message.chat.id, "✅ الأرقام المتاحة:\n\n" + "\n".join([f"`{n}`" for n in nums]), parse_mode="Markdown")

    elif message.text == "🎙️ تحويل نص لصوت":
        msg = bot.send_message(message.chat.id, "أرسل النص لتحويله لبصمة صوتية:")
        bot.register_next_step_handler(msg, process_voice)

    elif message.text == "🎬 تحويل نص لفيديو":
        msg = bot.send_message(message.chat.id, "أرسل النص لتحويله لفيديو:")
        bot.register_next_step_handler(msg, process_video)

    elif "تلغيم صورة" in message.text:
        if p < POINTS_FOR_MINING:
            bot.send_message(message.chat.id, f"🔒 تحتاج {POINTS_FOR_MINING} نقطة. لديك {p}.")
        else:
            bot.send_message(message.chat.id, "🛠️ أرسل رابط التتبع (Link) للبدء.")

    elif message.text == "👤 إحصائياتي":
        bot.send_message(message.chat.id, f"📊 إحصائياتك:\n💰 النقاط: {p}\n👥 الإحالات: {r}")

    elif message.text == "🔗 رابط الدعوة":
        link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.send_message(message.chat.id, f"🎁 رابط دعوتك (5 نقاط لكل إحالة):\n{link}")

def process_voice(message):
    if not message.text: return
    file_path = f"v_{message.from_user.id}.mp3"
    try:
        bot.send_message(message.chat.id, "⏳ جاري التوليد...")
        asyncio.run(create_voice(message.text, file_path))
        with open(file_path, "rb") as audio: bot.send_voice(message.chat.id, audio)
        os.remove(file_path)
    except: bot.send_message(message.chat.id, "❌ خطأ في الصوت")

def process_video(message):
    if not message.text: return
    video_path = f"vid_{message.from_user.id}.mp4"
    try:
        bot.send_message(message.chat.id, "⏳ جاري معالجة الفيديو...")
        text_to_video(message.text, video_path)
        with open(video_path, "rb") as video: bot.send_video(message.chat.id, video)
        os.remove(video_path)
    except: bot.send_message(message.chat.id, "❌ خطأ في الفيديو")

# --- 5. التشغيل ---
if __name__ == "__main__":
    keep_alive()
    print("🚀 البوت يعمل الآن بكامل الميزات يا قيادة!")
    bot.infinity_polling()
