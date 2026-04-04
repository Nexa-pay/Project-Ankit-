import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import os
import pymongo
from datetime import datetime
import uuid
import urllib.parse

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "@Nexapayz") 
MONGO_URI = os.getenv("MONGO_URI")

try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0")) 
except (ValueError, TypeError):
    OWNER_ID = 0

if not BOT_TOKEN or not MONGO_URI or OWNER_ID == 0:
    print("❌ ERROR: Missing Environment Variables!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- DATABASE SETUP ---
client = pymongo.MongoClient(MONGO_URI)
db = client["panel_store_db"]

users_col = db["users"]
admins_col = db["admins"]
settings_col = db["settings"]
products_col = db["products"]
plans_col = db["plans"]
logs_col = db["logs"]

pending_inputs = {}

# --- INITIALIZE SETTINGS ---
default_welcome = (
    "🔥 ━━ **PANEL STORE FREE FIRE** ━━ 🔥\n"
    "*Powered by Nexapayz*\n\n"
    "💥 Yo **{name}**, Welcome!!\n\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "❓ **Why our store is trusted?**\n"
    "↳ Direct deals with every mod developer\n"
    "↳ Instant delivery after payment\n"
    "↳ **5% discount** on your 2nd & every extra purchase\n"
    "↳ Guaranteed discounted prices"
)

if not settings_col.find_one({"_id": "config"}):
    settings_col.insert_one({
        "_id": "config",
        "welcome_msg": default_welcome,
        "bot_token": "HIDDEN",
        "upi_id": "your_upi_id@okhdfcbank",
        "min_deposit": 100,
        "max_deposit": 2000,
        "referral_percent": 20,
        "maintenance": False,
        "reseller_fee": 999,
        "support_link": "https://t.me/Nexapayz",
        "pay_proof_link": "https://t.me/Nexapayz",
        "tutorial_link": "https://youtube.com"
    })

if not admins_col.find_one({"user_id": OWNER_ID}):
    admins_col.insert_one({"user_id": OWNER_ID, "role": "owner"})

# --- UTILITIES ---
def is_admin(user_id):
    return admins_col.find_one({"user_id": user_id}) is not None

def check_force_join(user_id):
    if user_id == OWNER_ID or is_admin(user_id): return True 
    try:
        status = bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def safe_edit_text(text, chat_id, message_id, markup):
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    except:
        try: bot.delete_message(chat_id, message_id)
        except: pass
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def validate_url(url):
    if not url or not url.startswith("http"): return "https://t.me/Nexapayz"
    return url

# --- KEYBOARDS ---
def user_main_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🛍 Shop Now"))
    markup.row(KeyboardButton("📦 Orders"), KeyboardButton("👤 Profile"))
    markup.row(KeyboardButton("💰 Add Balance"), KeyboardButton("🎁 Referral"))
    markup.row(KeyboardButton("🆘 Support"), KeyboardButton("❓ How to Use"))
    if user_id == OWNER_ID or is_admin(user_id):
        markup.add(KeyboardButton("⚙️ Admin Panel"))
    return markup

def admin_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📦 Product Management"))
    markup.add(KeyboardButton("📅 Plan Management"))
    markup.add(KeyboardButton("🔑 Key Management"))
    markup.add(KeyboardButton("👥 User Management"))
    markup.add(KeyboardButton("💰 Deposit Requests"))
    markup.add(KeyboardButton("🎟 Coupon Management"))
    markup.add(KeyboardButton("🎟 Promo Codes"))
    markup.add(KeyboardButton("🔑 Reseller Keys"))
    markup.add(KeyboardButton("⭐ Reseller Management"))
    markup.add(KeyboardButton("📢 Broadcast"))
    markup.add(KeyboardButton("✉️ Custom DM"))
    markup.add(KeyboardButton("⚙️ Settings"))
    markup.add(KeyboardButton("⬅️ Back to Main"))
    return markup

# --- CORE HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not check_force_join(message.from_user.id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 Join Channel", url=validate_url(f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@', '')}")))
        markup.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_join"))
        bot.send_message(message.chat.id, "🛑 **Access Denied**\n\nYou must join our official channel to use this bot.", reply_markup=markup, parse_mode="Markdown")
        return

    user = users_col.find_one({"user_id": message.from_user.id})
    if not user:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("📱 Share My Number", request_contact=True))
        bot.send_message(message.chat.id, "👋 **Welcome to PANEL STORE FREE FIRE!**\n\nTo continue, please share your phone number by tapping the button below.", reply_markup=markup, parse_mode="Markdown")
    else:
        main_menu(message.chat.id, user_first_name=message.from_user.first_name)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if not users_col.find_one({"user_id": message.from_user.id}):
        join_date = datetime.now().strftime("%d %b %Y")
        users_col.insert_one({
            "user_id": message.from_user.id, 
            "first_name": message.from_user.first_name,
            "phone": message.contact.phone_number,
            "balance": 0.0,
            "type": "CUSTOMER",
            "orders": [], 
            "referrals": 0,
            "date": join_date
        })
    bot.send_message(message.chat.id, "✅ Number Verified Successfully!", reply_markup=telebot.types.ReplyKeyboardRemove())
    main_menu(message.chat.id, user_first_name=message.from_user.first_name)

def main_menu(chat_id, message_id=None, user_first_name="User"):
    config = settings_col.find_one({"_id": "config"}) or {}
    support_link = validate_url(config.get("support_link", "https://t.me/Nexapayz"))
    pay_proof_link = validate_url(config.get("pay_proof_link", "https://t.me/Nexapayz"))
    
    welcome_template = config.get("welcome_msg", default_welcome)
    text = welcome_template.replace("{name}", user_first_name)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Shop Now", callback_data="shop_menu"))
    markup.row(InlineKeyboardButton("📦 My Orders", callback_data="my_orders"), InlineKeyboardButton("👤 Profile", callback_data="my_profile"))
    markup.row(InlineKeyboardButton("↗️ Pay Proof", url=pay_proof_link), InlineKeyboardButton("❓ How to Use", callback_data="how_to_use"))
    markup.row(InlineKeyboardButton("💬 Support", url=support_link), InlineKeyboardButton("🎁 Referral", callback_data="my_referral"))
    
    if message_id: safe_edit_text(text, chat_id, message_id, markup)
    else: bot.send_message(chat_id, text, reply_markup=user_main_keyboard(chat_id), parse_mode="Markdown")

# --- BOTTOM MENU ROUTER (Users) ---
@bot.message_handler(func=lambda message: message.text in ["🛍 Shop Now", "📦 Orders", "👤 Profile", "💰 Add Balance", "🎁 Referral", "❓ How to Use", "🆘 Support"])
def user_menu_handler(message):
    chat_id = message.chat.id
    config = settings_col.find_one({"_id": "config"}) or {}
    
    if message.text == "🛍 Shop Now":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📱 Android", callback_data="shop_Android"))
        markup.add(InlineKeyboardButton("🍎 iOS", callback_data="shop_iOS"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        bot.send_message(chat_id, "🔥 **Choose your device category:**", reply_markup=markup, parse_mode="Markdown")

    elif message.text == "👤 Profile":
        user = users_col.find_one({"user_id": chat_id}) or {}
        phone = user.get("phone", "Not Provided")
        date = user.get("date")
        if not date or date == "Unknown":
            date = datetime.now().strftime("%d %b %Y")
            users_col.update_one({"user_id": chat_id}, {"$set": {"date": date}})
            
        orders_count = len(user.get("orders", []))
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{chat_id}"
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 **YOUR PROFILE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 **Name:** {message.from_user.first_name}\n"
            f"🆔 **User ID:** `{chat_id}`\n"
            f"📱 **Phone:** `+{phone.replace('+', '')}`\n"
            f"📅 **Member Since:** {date}\n"
            f"🛒 **Total Orders:** {orders_count}\n\n"
            f"🔗 **Your Referral Link:**\n"
            f"`{ref_link}`\n"
            "Share → friend buys → you earn rewards!\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🛒 Shop Now", callback_data="shop_menu"), InlineKeyboardButton("📦 My Orders", callback_data="my_orders"))
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
        
    elif message.text == "📦 Orders":
        user = users_col.find_one({"user_id": chat_id})
        orders = user.get("orders", []) if user else []
        
        text = "━━━━━━━━━━━━━━━━━━━━\n📦 **MY ORDERS (last 10)**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if not orders:
            text += "You have no previous orders.\n\n"
        else:
            for i, o in enumerate(reversed(orders[-10:]), 1):
                status = o.get("status", "Pending")
                icon = "⏳" if status == "Pending" else ("✅" if "Approved" in status else "🚫")
                # Fix for old vs new database entries
                plan_name = o.get("plan_name", o.get("name", "Product"))
                price = o.get("price", 0)
                days = o.get("days", "N/A")
                
                text += f"{i}. {icon} **{plan_name}**\n   ⏱ {days} Days • 💰 ₹{price} • {status}\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🛒 Shop Again", callback_data="shop_menu"))
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

    elif message.text == "🎁 Referral":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{chat_id}"
        text = (
            "🎁 **REFERRAL PROGRAM**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📢 **How it works:**\n"
            "↳ Share your link with friends\n"
            "↳ When they complete their **1st order**, you earn rewards!\n\n"
            "📊 **Your Stats:**\n"
            "👥 **Total Referrals:** 0\n"
            "✅ **Rewarded Referrals:** 0\n\n"
            f"🔗 **Your Referral Link:**\n`{ref_link}`\n\n"
            "_Tap the link to copy and share!_"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")

    elif message.text == "❓ How to Use":
        tutorial = validate_url(config.get("tutorial_link", "https://youtube.com"))
        text = (
            "📖 **How to Buy — Panel Store Free Fire**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Tap 🛒 **Shop Now**\n"
            "2️⃣ Choose **Android** or **iOS**\n"
            "3️⃣ Pick your product & plan\n"
            "4️⃣ Scan the UPI QR or copy UPI ID\n"
            "5️⃣ Pay the **exact** amount shown\n"
            "6️⃣ Tap ✅ **I Have Paid**\n"
            "7️⃣ Enter your UPI registered name\n"
            "8️⃣ Sit back — your panel key arrives shortly! 🚀\n\n"
            "⚠️ _Always pay the exact amount. Partial payments will NOT be detected._"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("▶️ Watch Tutorial on YouTube", url=tutorial))
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

    elif message.text == "🆘 Support":
        support_link = validate_url(config.get("support_link", "https://t.me/Nexapayz"))
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💬 Contact Support", url=support_link))
        bot.send_message(chat_id, "🆘 **Need Help?**\n\nClick the button below to message our support team directly.", reply_markup=markup, parse_mode="Markdown")

    elif message.text == "💰 Add Balance":
        bot.send_message(chat_id, "💰 **Add Balance**\n\nThis automated wallet feature is currently being integrated.\n\nTo add balance manually, please contact 🆘 **Support**.", parse_mode="Markdown")

# --- ADMIN BOTTOM MENU ROUTER ---
@bot.message_handler(func=lambda message: message.text == "⚙️ Admin Panel")
def enter_admin_panel(message):
    if not (message.from_user.id == OWNER_ID or is_admin(message.from_user.id)): return
    bot.send_message(message.chat.id, "🔐 **Admin Panel Unlocked**\n\nSelect an option below:", reply_markup=admin_main_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "⬅️ Back to Main")
def back_to_main(message):
    send_welcome(message)

@bot.message_handler(func=lambda message: message.text in ["📦 Product Management", "📅 Plan Management", "⚙️ Settings"])
def admin_menu_handler(message):
    if not (message.from_user.id == OWNER_ID or is_admin(message.from_user.id)): return
    chat_id = message.chat.id

    if message.text == "📦 Product Management":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add Product", callback_data="prod_add"))
        markup.add(InlineKeyboardButton("❌ Delete Product", callback_data="prod_delete"))
        markup.add(InlineKeyboardButton("⬅️ Close", callback_data="close_menu"))
        bot.send_message(chat_id, "📦 **PRODUCTS**\n\nActions:", reply_markup=markup, parse_mode="Markdown")

    elif message.text == "📅 Plan Management":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add Plan", callback_data="plan_add"))
        markup.add(InlineKeyboardButton("❌ Delete Plan", callback_data="plan_delete"))
        markup.add(InlineKeyboardButton("⬅️ Close", callback_data="close_menu"))
        bot.send_message(chat_id, "📅 **PLANS**\n\nActions:", reply_markup=markup, parse_mode="Markdown")

    elif message.text == "⚙️ Settings":
        config = settings_col.find_one({"_id": "config"})
        text = (
            "⚙️ **SETTINGS**\n\n"
            f"**Welcome Msg:** `{config.get('welcome_msg', '')[:15]}...`\n"
            f"**UPI ID:** `{config.get('upi_id')}`\n"
            f"**Min Dep:** ₹{config.get('min_deposit')} | **Max:** ₹{config.get('max_deposit')}\n"
            f"**Ref %:** {config.get('referral_percent')}%\n"
            f"**Maintenance:** {'ON 🔴' if config.get('maintenance') else 'OFF 🟢'}"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 Welcome Msg", callback_data="set_welcome"))
        markup.add(InlineKeyboardButton("💳 UPI ID", callback_data="set_upi"))
        markup.add(InlineKeyboardButton("🔗 Change Links", callback_data="admin_links"))
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- INLINE CALLBACK ROUTER ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    config = settings_col.find_one({"_id": "config"}) or {}

    if call.data == "close_menu":
        bot.delete_message(chat_id, msg_id)

    elif call.data == "check_join":
        if check_force_join(call.from_user.id):
            bot.delete_message(chat_id, msg_id)
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)
            
    elif call.data == "main_menu":
        main_menu(chat_id, msg_id, call.from_user.first_name)

    # --- INLINE UI SECTIONS ---
    elif call.data == "my_orders":
        user = users_col.find_one({"user_id": chat_id})
        orders = user.get("orders", []) if user else []
        text = "━━━━━━━━━━━━━━━━━━━━\n📦 **MY ORDERS (last 10)**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if not orders:
            text += "You have no previous orders.\n\n"
        else:
            for i, o in enumerate(reversed(orders[-10:]), 1):
                status = o.get("status", "Pending")
                icon = "⏳" if status == "Pending" else ("✅" if "Approved" in status else "🚫")
                plan_name = o.get("plan_name", o.get("name", "Product"))
                price = o.get("price", 0)
                days = o.get("days", "N/A")
                text += f"{i}. {icon} **{plan_name}**\n   ⏱ {days} Days • 💰 ₹{price} • {status}\n"
        text += "━━━━━━━━━━━━━━━━━━━━"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🛒 Shop Again", callback_data="shop_menu"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    elif call.data == "my_profile":
        user = users_col.find_one({"user_id": chat_id}) or {}
        phone = user.get("phone", "Not Provided")
        date = user.get("date")
        if not date or date == "Unknown":
            date = datetime.now().strftime("%d %b %Y")
            users_col.update_one({"user_id": chat_id}, {"$set": {"date": date}})
        orders_count = len(user.get("orders", []))
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{chat_id}"
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 **YOUR PROFILE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 **Name:** {call.from_user.first_name}\n"
            f"🆔 **User ID:** `{chat_id}`\n"
            f"📱 **Phone:** `+{phone.replace('+', '')}`\n"
            f"📅 **Member Since:** {date}\n"
            f"🛒 **Total Orders:** {orders_count}\n\n"
            f"🔗 **Your Referral Link:**\n"
            f"`{ref_link}`\n"
            "Share → friend buys → you earn rewards!\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🛒 Shop Now", callback_data="shop_menu"), InlineKeyboardButton("📦 My Orders", callback_data="my_orders"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    elif call.data == "my_referral":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{chat_id}"
        text = (
            "🎁 **REFERRAL PROGRAM**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📢 **How it works:**\n"
            "↳ Share your link with friends\n"
            "↳ When they complete their **1st order**, you earn rewards!\n\n"
            "📊 **Your Stats:**\n"
            "👥 **Total Referrals:** 0\n"
            "✅ **Rewarded Referrals:** 0\n\n"
            f"🔗 **Your Referral Link:**\n`{ref_link}`\n\n"
            "_Tap the link to copy and share!_"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)
        
    elif call.data == "how_to_use":
        tutorial = validate_url(config.get("tutorial_link", "https://youtube.com"))
        text = (
            "📖 **How to Buy — Panel Store Free Fire**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Tap 🛒 **Shop Now**\n"
            "2️⃣ Choose **Android** or **iOS**\n"
            "3️⃣ Pick your product & plan\n"
            "4️⃣ Scan the UPI QR or copy UPI ID\n"
            "5️⃣ Pay the **exact** amount shown\n"
            "6️⃣ Tap ✅ **I Have Paid**\n"
            "7️⃣ Enter your UPI registered name\n"
            "8️⃣ Sit back — your panel key arrives shortly! 🚀\n\n"
            "⚠️ _Always pay the exact amount. Partial payments will NOT be detected._"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("▶️ Watch Tutorial on YouTube", url=tutorial))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    # --- PRODUCT MANAGEMENT ---
    elif call.data == "prod_add":
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "📝 **Add Product**\n\nEnter product name:")
        bot.register_next_step_handler(msg, step_prod_name)

    elif call.data == "prod_delete":
        products = list(products_col.find())
        if not products: return bot.answer_callback_query(call.id, "No products exist.", show_alert=True)
        markup = InlineKeyboardMarkup()
        for p in products: markup.add(InlineKeyboardButton(f"❌ {p['name']}", callback_data=f"delprod_{p['_id']}"))
        safe_edit_text("Select product to delete:", chat_id, msg_id, markup)

    elif call.data.startswith("delprod_"):
        pid = call.data.split("_")[1]
        products_col.delete_one({"_id": pid})
        plans_col.delete_many({"product_id": pid})
        safe_edit_text("✅ Product deleted.", chat_id, msg_id, None)

    # --- PLAN MANAGEMENT ---
    elif call.data == "plan_add":
        products = list(products_col.find())
        if not products: return bot.answer_callback_query(call.id, "Create a Product first!", show_alert=True)
        markup = InlineKeyboardMarkup()
        for p in products: markup.add(InlineKeyboardButton(p["name"], callback_data=f"addplan_{p['_id']}"))
        safe_edit_text("Select Product to add plan to:", chat_id, msg_id, markup)

    elif call.data.startswith("addplan_"):
        pid = call.data.split("_")[1]
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "📝 **Add Plan**\n\nEnter plan duration in days (Numbers only, e.g. 7):")
        bot.register_next_step_handler(msg, step_plan_days, pid)

    # --- SHOPPING DYNAMICS ---
    elif call.data == "shop_menu":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📱 Android", callback_data="shop_Android"))
        markup.add(InlineKeyboardButton("🍎 iOS", callback_data="shop_iOS"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text("🔥 **Choose your device category:**", chat_id, msg_id, markup)

    elif call.data.startswith("shop_"):
        category = call.data.replace("shop_", "")
        products = list(products_col.find({"category": category}))
        markup = InlineKeyboardMarkup()
        for p in products:
            markup.add(InlineKeyboardButton(p["name"], callback_data=f"list_{p['_id']}"))
        markup.add(InlineKeyboardButton("⬅️ Back to Categories", callback_data="shop_menu"))
        icon = "📱" if category == "Android" else "🍎"
        safe_edit_text(f"🛒 **PANEL STORE — {icon} {category}**\n\nChoose a product 👇", chat_id, msg_id, markup)

    elif call.data.startswith("list_"):
        prod_id = call.data.replace("list_", "")
        p = products_col.find_one({"_id": prod_id})
        plans = list(plans_col.find({"product_id": prod_id}))
        
        markup = InlineKeyboardMarkup()
        if not plans:
            markup.add(InlineKeyboardButton("⬅️ Back", callback_data=f"shop_{p['category']}"))
            safe_edit_text(f"🏷 **{p['name']}**\n\n_{p['desc']}_\n\n*No plans available yet.*", chat_id, msg_id, markup)
            return

        for plan in plans:
            markup.add(InlineKeyboardButton(f"{plan['days']} Day{'s' if int(plan['days'])>1 else ''} — ₹{plan['price']}", callback_data=f"buy_plan_{plan['_id']}"))
        markup.add(InlineKeyboardButton("⬅️ Back to Shop", callback_data=f"shop_{p['category']}"))
        safe_edit_text(f"🏷 **{p['name']}**\n\n_{p['desc']}_\n\nChoose a plan 👇", chat_id, msg_id, markup)

    # --- DYNAMIC CHECKOUT ---
    elif call.data.startswith("buy_plan_"):
        plan_id = call.data.replace("buy_plan_", "")
        plan = plans_col.find_one({"_id": plan_id})
        if not plan: return bot.answer_callback_query(call.id, "Plan not found!", show_alert=True)
        
        p = products_col.find_one({"_id": plan["product_id"]})
        upi_id = config.get("upi_id", "error@upi")
        
        text = (
            f"🔥 **ORDER CREATED**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏷 **Product:** {p['name']}\n"
            f"⏱ **Duration:** {plan['days']} Day{'s' if int(plan['days']) > 1 else ''}\n"
            f"💰 **Amount:** ₹{plan['price']}\n"
            f"🔖 **UPI ID:** `{upi_id}`\n\n"
            f"📲 *Scan the QR above to pay*\n"
            f"⚠️ **Pay EXACTLY ₹{plan['price']}**\n"
            f"⏰ Expires in 5 minutes"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ I Have Paid", callback_data=f"paid_{plan_id}"))
        markup.add(InlineKeyboardButton("❌ Cancel", callback_data="close_menu"))
        
        bot.delete_message(chat_id, msg_id)
        
        # GENERATE DYNAMIC QR
        upi_url = f"upi://pay?pa={upi_id}&pn=PanelStore&am={plan['price']}&cu=INR"
        qr_link = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(upi_url)}"
        
        try: bot.send_photo(chat_id, qr_link, caption=text, reply_markup=markup, parse_mode="Markdown")
        except: bot.send_message(chat_id, text + "\n\n*(QR Error. Please pay using UPI ID directly)*", reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("paid_"):
        plan_id = call.data.replace("paid_", "")
        bot.delete_message(chat_id, msg_id) 
        msg = bot.send_message(chat_id, "✅ **Payment Initiated**\n\nPlease type your **UPI registered name** exactly as it appears in your payment app:\n\n_Example: RAHUL SHARMA_", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_upi_name, plan_id)

    # --- ADMIN ORDER APPROVAL ---
    elif call.data.startswith("approve_") or call.data.startswith("reject_"):
        if not (call.from_user.id == OWNER_ID or is_admin(call.from_user.id)):
            return bot.answer_callback_query(call.id, "Unauthorized Access", show_alert=True)
            
        parts = call.data.split("_")
        action = parts[0]
        user_id = int(parts[1])
        order_id = parts[2]
        
        user = users_col.find_one({"user_id": user_id})
        target_order = next((o for o in user.get("orders", []) if o.get("order_id") == order_id), None) if user else None
        
        if not target_order or target_order.get("status") != "Pending Verification":
            bot.answer_callback_query(call.id, "Order was already processed!", show_alert=True)
            bot.edit_message_caption(f"{call.message.caption}\n\n🔒 **PROCESSED ALREADY**", chat_id=chat_id, message_id=msg_id, parse_mode="Markdown")
            return
            
        new_status = "Approved ✅" if action == "approve" else "Cancelled 🚫"
        
        users_col.update_one(
            {"user_id": user_id, "orders.order_id": order_id},
            {"$set": {"orders.$.status": new_status}}
        )
        
        bot.edit_message_caption(f"{call.message.caption}\n\n**Status:** {new_status} (by {call.from_user.first_name})", chat_id=chat_id, message_id=msg_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, f"Order {new_status}")
        
        if action == "approve":
            bot.send_message(user_id, f"✅ **Payment Approved!**\n\nYour order for `{target_order['plan_name']}` was verified. The admin will DM your key shortly.", parse_mode="Markdown")
        else:
            bot.send_message(user_id, f"❌ **Payment Rejected!**\n\nYour order for `{target_order['plan_name']}` could not be verified.", parse_mode="Markdown")

    # --- SETTINGS CALLBACKS ---
    elif call.data == "set_welcome":
        msg = bot.send_message(chat_id, "Send your new Welcome Message.\nUse `{name}` and `{prod_count}` for dynamic text.")
        bot.register_next_step_handler(msg, lambda m: settings_col.update_one({"_id": "config"}, {"$set": {"welcome_msg": m.text}}))
    elif call.data == "set_upi":
        msg = bot.send_message(chat_id, "Send your exact UPI ID:")
        bot.register_next_step_handler(msg, lambda m: settings_col.update_one({"_id": "config"}, {"$set": {"upi_id": m.text.strip()}}))
    elif call.data == "admin_links":
        msg = bot.send_message(chat_id, "Send new links separated by a space:\n`Support Proof Tutorial`\nExample:\n`https://t.me/sup https://t.me/prf https://youtu.be/x`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_links)

# --- CREATION STEP HANDLERS ---
def step_prod_name(message):
    pending_inputs[message.chat.id] = {"name": message.text}
    msg = bot.send_message(message.chat.id, "Enter product category (Android or iOS):")
    bot.register_next_step_handler(msg, step_prod_cat)

def step_prod_cat(message):
    cat = message.text.strip()
    if cat not in ["Android", "iOS"]:
        bot.send_message(message.chat.id, "❌ Cancelled. Category must be exactly `Android` or `iOS`.", parse_mode="Markdown")
        return
    pending_inputs[message.chat.id]["cat"] = cat
    msg = bot.send_message(message.chat.id, "Enter product description:")
    bot.register_next_step_handler(msg, step_prod_desc)

def step_prod_desc(message):
    data = pending_inputs.pop(message.chat.id)
    prod_id = str(uuid.uuid4())[:6]
    products_col.insert_one({
        "_id": prod_id,
        "name": data["name"],
        "category": data["cat"],
        "desc": message.text
    })
    bot.send_message(message.chat.id, f"✅ Product **{data['name']}** added to {data['cat']} successfully!", parse_mode="Markdown")

def step_plan_days(message, prod_id):
    try:
        days = int(message.text)
        pending_inputs[message.chat.id] = {"days": days}
        msg = bot.send_message(message.chat.id, "Enter price in ₹ (Numbers only):")
        bot.register_next_step_handler(msg, step_plan_price, prod_id)
    except:
        bot.send_message(message.chat.id, "❌ Days must be a number. Cancelled.")

def step_plan_price(message, prod_id):
    try:
        price = int(message.text)
        data = pending_inputs.pop(message.chat.id)
        plan_id = str(uuid.uuid4())[:8]
        p = products_col.find_one({"_id": prod_id})
        
        name = f"{p['name']} {data['days']} Day{'s' if data['days']>1 else ''}"
        plans_col.insert_one({
            "_id": plan_id,
            "product_id": prod_id,
            "name": name,
            "days": data["days"],
            "price": price
        })
        bot.send_message(message.chat.id, f"✅ Plan **{name}** for ₹{price} added successfully!", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ Price must be a valid number. Cancelled.")

def process_links(message):
    try:
        sup, prf, tut = message.text.split()
        settings_col.update_one({"_id": "config"}, {"$set": {"support_link": sup, "pay_proof_link": prf, "tutorial_link": tut}})
        bot.send_message(message.chat.id, "✅ Links updated successfully!")
    except:
        bot.send_message(message.chat.id, "❌ Error. Send exactly 3 valid links separated by spaces.")

# --- CHECKOUT FLOW ---
def process_upi_name(message, plan_id):
    pending_inputs[message.chat.id] = {"upi_name": message.text, "plan_id": plan_id}
    msg = bot.send_message(message.chat.id, "📸 **Almost done!**\nPlease send the **Screenshot** of your successful payment now.", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_payment_screenshot)

def process_payment_screenshot(message):
    chat_id = message.chat.id
    if not message.photo:
        msg = bot.send_message(chat_id, "❌ Please send a valid screenshot photo.")
        bot.register_next_step_handler(msg, process_payment_screenshot)
        return
        
    data = pending_inputs.pop(chat_id)
    plan = plans_col.find_one({"_id": data["plan_id"]})
    p = products_col.find_one({"_id": plan["product_id"]})
    if not plan: return
    
    order_id = str(uuid.uuid4())[:8].upper()
    new_order = {
        "order_id": order_id,
        "plan_name": plan["name"],
        "days": plan["days"],
        "price": plan["price"],
        "status": "Pending Verification",
        "upi_name": data["upi_name"],
        "date": datetime.now().strftime("%d %b %Y")
    }
    
    users_col.update_one({"user_id": chat_id}, {"$push": {"orders": new_order}})
    bot.send_message(chat_id, "⏳ **Screenshot Received!**\n\nYour payment is being verified by admins.", parse_mode="Markdown")
    
    admin_caption = (
        f"🔔 **NEW PAYMENT ALERT**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** `{chat_id}` (@{message.from_user.username})\n"
        f"📛 **UPI Name:** `{data['upi_name']}`\n"
        f"📦 **Item:** {plan['name']}\n"
        f"💰 **Amount:** ₹{plan['price']}\n"
        f"🔖 **Order ID:** `{order_id}`\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("✅ Approve", callback_data=f"approve_{chat_id}_{order_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}_{order_id}"))
    
    bot.send_photo(OWNER_ID, message.photo[-1].file_id, caption=admin_caption, reply_markup=markup, parse_mode="Markdown")

print("Bot is starting... Loading Environment Variables...")
bot.infinity_polling(skip_pending=True)
