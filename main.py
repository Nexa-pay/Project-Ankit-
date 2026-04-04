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
keys_col = db["keys"]
promos_col = db["promos"]
logs_col = db["logs"]

pending_inputs = {}

# --- INITIALIZE SETTINGS ---
default_welcome = (
    "💎 ━━ **PANEL STORE FREE FIRE** ━━ 💎\n"
    "✨ *Powered by Nexapayz*\n\n"
    "🚀 Yo **{name}**, Welcome!!\n\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "👑 **Why our store is trusted?**\n"
    "↳ Direct deals with every mod developer\n"
    "↳ Instant delivery after payment\n"
    "↳ **5% discount** on your 2nd & every extra purchase\n"
    "↳ Guaranteed discounted prices"
)

if not settings_col.find_one({"_id": "config"}):
    settings_col.insert_one({
        "_id": "config",
        "welcome_msg": default_welcome,
        "welcome_image": "", 
        "upi_id": "your_upi_id@okhdfcbank",
        "whatsapp_num": "+919876543210",
        "min_deposit": 100,
        "max_deposit": 5000,
        "support_link": "https://t.me/Nexapayz",
        "pay_proof_link": "https://t.me/Nexapayz",
        "tutorial_link": "https://youtube.com"
    })

if not admins_col.find_one({"user_id": OWNER_ID}):
    admins_col.insert_one({"user_id": OWNER_ID, "role": "owner"})

# --- CRASH-PROOF UTILITIES ---
def is_admin(user_id):
    if user_id == OWNER_ID: return True
    return admins_col.find_one({"user_id": user_id}) is not None

def check_force_join(user_id):
    if is_admin(user_id): return True 
    try:
        status = bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def safe_edit_text(text, chat_id, message_id, markup, image=None):
    try:
        if image:
            bot.edit_message_caption(caption=text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        try: bot.delete_message(chat_id, message_id)
        except: pass
        
        if image:
            try: bot.send_photo(chat_id, image, caption=text, reply_markup=markup, parse_mode="Markdown")
            except: bot.send_message(chat_id, text + "\n\n*(Error loading banner image)*", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def validate_url(url):
    if not url or not str(url).startswith("http"):
        return "https://t.me/Nexapayz"
    return str(url).strip()

# --- KEYBOARDS ---
def user_main_keyboard(user_id):
    if is_admin(user_id):
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("⚙️ Admin Panel"))
        return markup
    return telebot.types.ReplyKeyboardRemove()

def admin_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("📦 Product Management"), KeyboardButton("📅 Plan Management"))
    markup.row(KeyboardButton("🔑 Key Management"), KeyboardButton("👥 User Management"))
    markup.row(KeyboardButton("💰 Deposit Requests"), KeyboardButton("🎟 Promo Codes"))
    markup.row(KeyboardButton("⭐ Reseller Management"), KeyboardButton("🎟 Coupon Management"))
    markup.row(KeyboardButton("📢 Broadcast"), KeyboardButton("✉️ Custom DM"))
    markup.row(KeyboardButton("🔑 Reseller Keys"), KeyboardButton("⚙️ Settings"))
    markup.add(KeyboardButton("⬅️ Back to Main"))
    return markup

# --- USER COMMANDS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    
    # 🔔 NOTIFY ADMINS WHEN SOMEONE STARTS THE BOT
    try:
        admin_notification = (
            f"🔔 **USER STARTED THE BOT**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** {message.from_user.first_name}\n"
            f"🆔 **ID:** `{message.from_user.id}`\n"
            f"🔗 **Username:** @{message.from_user.username or 'None'}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        for admin in admins_col.find():
            try: bot.send_message(admin["user_id"], admin_notification, parse_mode="Markdown")
            except: pass
    except: pass

    if not check_force_join(message.from_user.id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 Join Channel", url=validate_url(f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@', '')}")))
        markup.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_join"))
        bot.send_message(chat_id, "🛑 **Access Denied**\n\nYou must join our official channel to use this bot.", reply_markup=markup, parse_mode="Markdown")
        return

    user = users_col.find_one({"user_id": chat_id})
    if not user:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("📱 Share My Number", request_contact=True))
        bot.send_message(chat_id, "👋 **Welcome to PANEL STORE FREE FIRE!**\n\nTo continue, please share your phone number by tapping the button below.", reply_markup=markup, parse_mode="Markdown")
    else:
        main_menu(chat_id, user_first_name=message.from_user.first_name)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    if not users_col.find_one({"user_id": chat_id}):
        join_date = datetime.now().strftime("%d %b %Y")
        users_col.insert_one({
            "user_id": chat_id, 
            "first_name": message.from_user.first_name,
            "phone": message.contact.phone_number,
            "balance": 0.0,
            "type": "CUSTOMER",
            "orders": [], 
            "referrals": 0,
            "date": join_date
        })
    bot.send_message(chat_id, "✅ Number Verified Successfully!", reply_markup=telebot.types.ReplyKeyboardRemove())
    main_menu(chat_id, user_first_name=message.from_user.first_name)

def main_menu(chat_id, message_id=None, user_first_name="User"):
    config = settings_col.find_one({"_id": "config"}) or {}
    pay_proof_link = validate_url(config.get("pay_proof_link"))
    welcome_image = config.get("welcome_image", "")
    
    welcome_template = config.get("welcome_msg") or default_welcome
    text = welcome_template.replace("{name}", user_first_name)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Shop Now", callback_data="shop_menu"))
    markup.row(InlineKeyboardButton("📦 My Orders", callback_data="my_orders"), InlineKeyboardButton("👤 Profile", callback_data="my_profile"))
    markup.row(InlineKeyboardButton("↗️ Pay Proof", url=pay_proof_link), InlineKeyboardButton("❓ How to Use", callback_data="how_to_use"))
    markup.row(InlineKeyboardButton("💬 Support", callback_data="support_menu"), InlineKeyboardButton("🎁 Referral", callback_data="my_referral"))
    
    if message_id: 
        safe_edit_text(text, chat_id, message_id, markup, image=welcome_image)
    else: 
        if is_admin(chat_id):
            bot.send_message(chat_id, "👑 **Admin Access Granted**", reply_markup=user_main_keyboard(chat_id), parse_mode="Markdown")
        else:
            m = bot.send_message(chat_id, "Loading store...", reply_markup=user_main_keyboard(chat_id))
            try: bot.delete_message(chat_id, m.message_id)
            except: pass
            
        if welcome_image:
            try: bot.send_photo(chat_id, welcome_image, caption=text, reply_markup=markup, parse_mode="Markdown")
            except: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- ADMIN BOTTOM MENU ROUTER ---
@bot.message_handler(func=lambda message: message.text == "⚙️ Admin Panel")
def enter_admin_panel(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, "🔐 **Admin Panel Unlocked**\n\nSelect an option below:", reply_markup=admin_main_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "⬅️ Back to Main")
def back_to_main(message):
    send_welcome(message)

@bot.message_handler(func=lambda message: message.text in ["📦 Product Management", "📅 Plan Management", "⚙️ Settings", "📢 Broadcast", "👥 User Management", "💰 Deposit Requests", "🔑 Key Management", "✉️ Custom DM", "🎟 Promo Codes", "⭐ Reseller Management", "🎟 Coupon Management", "🔑 Reseller Keys"])
def admin_menu_handler(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    cmd = message.text

    if cmd == "📦 Product Management":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add Product", callback_data="prod_add"))
        markup.add(InlineKeyboardButton("❌ Delete Product", callback_data="prod_delete"))
        markup.add(InlineKeyboardButton("⬅️ Close", callback_data="close_menu"))
        bot.send_message(chat_id, "📦 **Product Management**", reply_markup=markup, parse_mode="Markdown")

    elif cmd == "📅 Plan Management":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add Plan", callback_data="plan_add"))
        markup.add(InlineKeyboardButton("❌ Delete Plan", callback_data="plan_delete"))
        markup.add(InlineKeyboardButton("⬅️ Close", callback_data="close_menu"))
        bot.send_message(chat_id, "📅 **Plan Management**", reply_markup=markup, parse_mode="Markdown")

    elif cmd == "🔑 Key Management":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add Keys", callback_data="keys_add"))
        markup.add(InlineKeyboardButton("📊 View Key Stats", callback_data="keys_view"))
        markup.add(InlineKeyboardButton("⬅️ Close", callback_data="close_menu"))
        bot.send_message(chat_id, "🔑 **Key Management**", reply_markup=markup, parse_mode="Markdown")

    elif cmd == "👥 User Management":
        msg = bot.send_message(chat_id, "👥 **User Management**\n\nSend the Telegram **User ID** you want to manage:")
        bot.register_next_step_handler(msg, step_manage_user)

    elif cmd == "✉️ Custom DM":
        msg = bot.send_message(chat_id, "✉️ **Custom Direct Message**\n\nSend the **User ID** you want to message:")
        bot.register_next_step_handler(msg, step_custom_dm_id)

    elif cmd == "💰 Deposit Requests":
        bot.send_message(chat_id, "💰 **Deposit Requests**\n\nPending wallet deposits will be forwarded here automatically for approval.")

    elif cmd == "🎟 Promo Codes" or cmd == "🎟 Coupon Management":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add Promo Code", callback_data="promo_add"))
        markup.add(InlineKeyboardButton("❌ Delete Promo Code", callback_data="promo_delete"))
        markup.add(InlineKeyboardButton("⬅️ Close", callback_data="close_menu"))
        bot.send_message(chat_id, "🎟 **Promo Code Management**", reply_markup=markup, parse_mode="Markdown")

    elif cmd == "⭐ Reseller Management" or cmd == "🔑 Reseller Keys":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add Reseller", callback_data="reseller_add"))
        markup.add(InlineKeyboardButton("❌ Remove Reseller", callback_data="reseller_remove"))
        markup.add(InlineKeyboardButton("⬅️ Close", callback_data="close_menu"))
        bot.send_message(chat_id, "⭐ **Reseller Management**", reply_markup=markup, parse_mode="Markdown")

    elif cmd == "📢 Broadcast":
        msg = bot.send_message(chat_id, "📢 **Broadcast**\n\nSend the message you want to broadcast to all users:")
        bot.register_next_step_handler(msg, process_broadcast)

    elif cmd == "⚙️ Settings":
        if chat_id != OWNER_ID: return bot.send_message(chat_id, "❌ Owner only access.")
        config = settings_col.find_one({"_id": "config"})
        text = (
            "⚙️ **SETTINGS**\n\n"
            f"**UPI ID:** `{config.get('upi_id')}`\n"
            f"**WhatsApp:** `{config.get('whatsapp_num', 'None')}`\n"
            f"**Welcome Msg:** `{str(config.get('welcome_msg', ''))[:20]}...`\n"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📝 Edit Welcome Msg", callback_data="set_welcome"), InlineKeyboardButton("🖼 Set Welcome Image", callback_data="set_welcome_img"))
        markup.row(InlineKeyboardButton("💳 Set UPI ID", callback_data="set_upi"), InlineKeyboardButton("📱 Set WhatsApp", callback_data="set_whatsapp"))
        markup.add(InlineKeyboardButton("🔗 Change Links", callback_data="admin_links"))
        markup.row(InlineKeyboardButton("👥 Add Admin", callback_data="admin_add"), InlineKeyboardButton("🚫 Remove Admin", callback_data="admin_remove"))
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

    # --- SUPPORT SUB-MENU ---
    elif call.data == "support_menu":
        sup_link = validate_url(config.get("support_link"))
        wa_num = config.get("whatsapp_num", "1234567890").replace("+", "").replace(" ", "")
        wa_link = f"https://wa.me/{wa_num}"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💬 Telegram Support", url=sup_link))
        markup.add(InlineKeyboardButton("🟢 WhatsApp Support", url=wa_link))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text("🆘 **Contact Support**\n\nChoose your preferred platform to contact our team:", chat_id, msg_id, markup)

    # --- INLINE UI SECTIONS ---
    elif call.data == "my_orders":
        user = users_col.find_one({"user_id": chat_id})
        orders = user.get("orders", []) if user else []
        text = "━━━━━━━━━━━━━━━━━━━━\n📦 **MY ORDERS (last 10)**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if not orders: text += "You have no previous orders.\n\n"
        else:
            for i, o in enumerate(reversed(orders[-10:]), 1):
                status = o.get("status", "Pending")
                icon = "⏳" if status == "Pending" else ("✅" if "Approved" in status else "🚫")
                text += f"{i}. {icon} **{o.get('plan_name', 'Product')}**\n   ⏱ {o.get('days','-')} Days • 💰 ₹{o.get('price', 0)} • {status}\n"
        text += "━━━━━━━━━━━━━━━━━━━━"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🛒 Shop Again", callback_data="shop_menu"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    elif call.data == "my_profile":
        user = users_col.find_one({"user_id": chat_id}) or {}
        phone = user.get("phone", "Not Provided")
        date = user.get("date", datetime.now().strftime("%d %b %Y"))
        balance = user.get("balance", 0.0)
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{chat_id}"
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n👤 **YOUR PROFILE**\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 **Name:** {call.from_user.first_name}\n"
            f"🆔 **User ID:** `{chat_id}`\n"
            f"📱 **Phone:** `+{phone.replace('+', '')}`\n"
            f"📅 **Member Since:** {date}\n"
            f"💰 **Balance:** ₹{balance}\n"
            f"🛒 **Total Orders:** {len(user.get('orders', []))}\n\n"
            f"🔗 **Your Referral Link:**\n`{ref_link}`\n"
            "Share → friend buys → you earn rewards!\n━━━━━━━━━━━━━━━━━━━━"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🛒 Shop Now", callback_data="shop_menu"), InlineKeyboardButton("📦 My Orders", callback_data="my_orders"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    elif call.data == "how_to_use":
        tutorial = validate_url(config.get("tutorial_link"))
        text = (
            "📖 **How to Buy — Panel Store Free Fire**\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Tap 🛒 **Shop Now**\n2️⃣ Choose **Android** or **iOS**\n"
            "3️⃣ Pick your product & plan\n4️⃣ Scan the UPI QR or copy UPI ID\n"
            "5️⃣ Pay the **exact** amount shown\n6️⃣ Tap ✅ **I Have Paid**\n"
            "7️⃣ Enter your UPI name and send screenshot\n"
            "8️⃣ Sit back — your panel key arrives shortly! 🚀"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("▶️ Watch Tutorial on YouTube", url=tutorial))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    elif call.data == "my_referral":
        bot_username = bot.get_me().username
        text = (
            "🎁 **REFERRAL PROGRAM**\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "📢 **How it works:**\n↳ Share your link with friends\n"
            "↳ When they complete their **1st order**, you earn balance!\n\n"
            f"🔗 **Your Referral Link:**\n`https://t.me/{bot_username}?start=ref_{chat_id}`\n\n_Tap the link to copy!_"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    # --- DYNAMIC SHOPPING ---
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
        for p in products: markup.add(InlineKeyboardButton(p["name"], callback_data=f"list_{p['_id']}"))
        markup.add(InlineKeyboardButton("⬅️ Back to Categories", callback_data="shop_menu"))
        icon = "📱" if category == "Android" else "🍎"
        safe_edit_text(f"🛒 **PANEL STORE — {icon} {category}**\n\nChoose a product 👇", chat_id, msg_id, markup)

    elif call.data.startswith("list_"):
        prod_id = call.data.replace("list_", "")
        p = products_col.find_one({"_id": prod_id})
        if not p: return bot.answer_callback_query(call.id, "Product removed.", show_alert=True)
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
            f"🔥 **ORDER CREATED**\n━━━━━━━━━━━━━━━━━━\n"
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
        upi_url = f"upi://pay?pa={upi_id}&pn=PanelStore&am={plan['price']}&cu=INR"
        qr_link = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(upi_url)}"
        try: bot.send_photo(chat_id, qr_link, caption=text, reply_markup=markup, parse_mode="Markdown")
        except: bot.send_message(chat_id, text + "\n\n*(QR Error. Please pay using UPI ID directly)*", reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("paid_"):
        plan_id = call.data.replace("paid_", "")
        bot.delete_message(chat_id, msg_id) 
        msg = bot.send_message(chat_id, "✅ **Payment Initiated**\n\nPlease type your **UPI registered name** exactly as it appears in your payment app:\n\n_Example: RAHUL SHARMA_", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_upi_name, plan_id, False)

    # --- ADMIN INLINE ADMIN ROUTERS ---
    elif call.data == "prod_add":
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "📝 **Add Product**\n\nEnter product name:")
        bot.register_next_step_handler(msg, step_prod_name)

    elif call.data == "prod_delete":
        products = list(products_col.find())
        if not products: return bot.answer_callback_query(call.id, "No products exist.", show_alert=True)
        markup = InlineKeyboardMarkup()
        for p in products: markup.add(InlineKeyboardButton(f"❌ {p['name']}", callback_data=f"delprod_{p['_id']}"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="close_menu"))
        safe_edit_text("Select product to delete:", chat_id, msg_id, markup)

    elif call.data.startswith("delprod_"):
        pid = call.data.split("_")[1]
        products_col.delete_one({"_id": pid})
        plans_col.delete_many({"product_id": pid})
        safe_edit_text("✅ Product deleted.", chat_id, msg_id, None)

    elif call.data == "plan_add":
        products = list(products_col.find())
        if not products: return bot.answer_callback_query(call.id, "Create a Product first!", show_alert=True)
        markup = InlineKeyboardMarkup()
        for p in products: markup.add(InlineKeyboardButton(p["name"], callback_data=f"addplan_{p['_id']}"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="close_menu"))
        safe_edit_text("Select Product to add plan to:", chat_id, msg_id, markup)

    elif call.data.startswith("addplan_"):
        pid = call.data.split("_")[1]
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "📝 **Add Plan**\n\nEnter plan duration in days (Numbers only, e.g. 7):")
        bot.register_next_step_handler(msg, step_plan_days, pid)

    elif call.data == "plan_delete":
        plans = list(plans_col.find())
        if not plans: return bot.answer_callback_query(call.id, "No plans exist.", show_alert=True)
        markup = InlineKeyboardMarkup()
        for p in plans: markup.add(InlineKeyboardButton(f"❌ {p['name']} (₹{p['price']})", callback_data=f"delplan_{p['_id']}"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="close_menu"))
        safe_edit_text("Select plan to delete:", chat_id, msg_id, markup)
        
    elif call.data.startswith("delplan_"):
        pid = call.data.split("_")[1]
        plans_col.delete_one({"_id": pid})
        safe_edit_text("✅ Plan deleted.", chat_id, msg_id, None)

    # --- ADMIN APPROVALS (ORDERS) ---
    elif call.data.startswith("approve_") or call.data.startswith("reject_"):
        if not is_admin(call.from_user.id): return bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        parts = call.data.split("_")
        action, user_id, order_id = parts[0], int(parts[1]), parts[2]
        
        user = users_col.find_one({"user_id": user_id})
        target_order = next((o for o in user.get("orders", []) if o.get("order_id") == order_id), None) if user else None
        if not target_order or target_order.get("status") != "Pending Verification":
            bot.answer_callback_query(call.id, "Already processed!", show_alert=True)
            bot.edit_message_caption(f"{call.message.caption}\n\n🔒 **PROCESSED**", chat_id=chat_id, message_id=msg_id, parse_mode="Markdown")
            return
            
        new_status = "Approved ✅" if action == "approve" else "Cancelled 🚫"
        users_col.update_one({"user_id": user_id, "orders.order_id": order_id}, {"$set": {"orders.$.status": new_status}})
        bot.edit_message_caption(f"{call.message.caption}\n\n**Status:** {new_status} (by {call.from_user.first_name})", chat_id=chat_id, message_id=msg_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, f"Order {new_status}")
        
        if action == "approve":
            plan_name = target_order.get('plan_name')
            plan = plans_col.find_one({"name": plan_name})
            
            key_val = None
            if plan:
                key_doc = keys_col.find_one_and_delete({"plan_id": plan["_id"]})
                if key_doc: key_val = key_doc["key"]
                
            if key_val:
                bot.send_message(user_id, f"✅ **Payment Approved!**\n\nYour order for `{plan_name}` was verified successfully.\n\n🔑 **Your Panel Key:**\n`{key_val}`\n\nEnjoy!", parse_mode="Markdown")
            else:
                bot.send_message(user_id, f"✅ **Payment Approved!**\n\nYour order for `{plan_name}` was verified. The admin will DM your key shortly.", parse_mode="Markdown")
        else: 
            bot.send_message(user_id, f"❌ **Payment Rejected!**\n\nYour order for `{target_order.get('plan_name')}` could not be verified.", parse_mode="Markdown")

    # --- ADMIN APPROVALS (DEPOSITS) ---
    elif call.data.startswith("dep_approve_") or call.data.startswith("dep_reject_"):
        if not is_admin(call.from_user.id): return
        parts = call.data.split("_")
        action, user_id, amount = parts[1], int(parts[2]), float(parts[3])
        
        bot.edit_message_caption(f"{call.message.caption}\n\n🔒 **PROCESSED** ({action.upper()})", chat_id=chat_id, message_id=msg_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, f"Deposit {action}")
        
        if action == "approve":
            users_col.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})
            bot.send_message(user_id, f"✅ **Deposit Approved!**\n\n₹{amount} has been added to your wallet balance.")
        else:
            bot.send_message(user_id, f"❌ **Deposit Rejected!**\n\nYour request to add ₹{amount} was declined.")

    # --- ADMIN USER MANAGEMENT CALLBACKS ---
    elif call.data.startswith("addbal_"):
        uid = int(call.data.split("_")[1])
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "Enter amount to ADD to this user's balance:")
        bot.register_next_step_handler(msg, lambda m: modify_balance(m, uid, True))
    elif call.data.startswith("deductbal_"):
        uid = int(call.data.split("_")[1])
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "Enter amount to DEDUCT from this user's balance:")
        bot.register_next_step_handler(msg, lambda m: modify_balance(m, uid, False))

    # --- ADMIN SETTINGS CALLBACKS ---
    elif call.data == "set_welcome":
        msg = bot.send_message(chat_id, "Send your new Welcome Message.\nUse `{name}` and `{prod_count}` for dynamic text.")
        bot.register_next_step_handler(msg, lambda m: settings_col.update_one({"_id": "config"}, {"$set": {"welcome_msg": m.text}}))
    elif call.data == "set_welcome_img":
        msg = bot.send_message(chat_id, "Send the image/photo you want to use for the Welcome Screen.\n\nType `NONE` to remove the current image.")
        bot.register_next_step_handler(msg, process_welcome_img)
    elif call.data == "set_upi":
        msg = bot.send_message(chat_id, "Send your exact UPI ID:")
        bot.register_next_step_handler(msg, lambda m: settings_col.update_one({"_id": "config"}, {"$set": {"upi_id": m.text.strip()}}))
    elif call.data == "set_whatsapp":
        msg = bot.send_message(chat_id, "Send your WhatsApp Number (with country code, e.g., +919876543210):")
        bot.register_next_step_handler(msg, process_whatsapp)
    elif call.data == "admin_links":
        msg = bot.send_message(chat_id, "Send new links separated by a space:\n`Support Proof Tutorial`\nExample:\n`https://t.me/sup https://t.me/prf https://youtu.be/x`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_links)
    elif call.data == "admin_add":
        msg = bot.send_message(chat_id, "Send the Telegram User ID of the new admin:")
        bot.register_next_step_handler(msg, process_add_admin)
    elif call.data == "admin_remove":
        msg = bot.send_message(chat_id, "Send the Telegram User ID of the admin to REMOVE:")
        bot.register_next_step_handler(msg, process_remove_admin)
        
    # --- ADVANCED ADMIN MANAGEMENT (KEYS, PROMOS, RESELLERS) ---
    elif call.data == "keys_add":
        plans = list(plans_col.find())
        if not plans: return bot.answer_callback_query(call.id, "Create a Plan first!", show_alert=True)
        markup = InlineKeyboardMarkup()
        for p in plans: markup.add(InlineKeyboardButton(f"{p['name']}", callback_data=f"addkey_{p['_id']}"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="close_menu"))
        safe_edit_text("🔑 Select Plan to add keys to:", chat_id, msg_id, markup)

    elif call.data.startswith("addkey_"):
        pid = call.data.replace("addkey_", "")
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "📝 Send the keys separated by commas (,)\nExample: `KEY1, KEY2, KEY3`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, step_add_keys, pid)

    elif call.data == "keys_view":
        plans = list(plans_col.find())
        text = "📊 **Key Statistics**\n\n"
        for p in plans:
            count = keys_col.count_documents({"plan_id": p["_id"]})
            text += f"🔹 **{p['name']}**: `{count}` keys\n"
        if not plans: text = "No plans found."
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Close", callback_data="close_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    elif call.data == "promo_add":
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "Enter new Promo Code (e.g. VIP20):")
        bot.register_next_step_handler(msg, step_promo_code)

    elif call.data == "promo_delete":
        promos = list(promos_col.find())
        if not promos: return bot.answer_callback_query(call.id, "No promos exist.", show_alert=True)
        markup = InlineKeyboardMarkup()
        for p in promos: markup.add(InlineKeyboardButton(f"❌ {p['code']} ({p['discount']}%)", callback_data=f"delpromo_{p['code']}"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="close_menu"))
        safe_edit_text("Select promo to delete:", chat_id, msg_id, markup)

    elif call.data.startswith("delpromo_"):
        code = call.data.split("_")[1]
        promos_col.delete_one({"code": code})
        safe_edit_text("✅ Promo deleted.", chat_id, msg_id, None)

    elif call.data == "reseller_add":
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "Enter Telegram User ID for new Reseller:")
        bot.register_next_step_handler(msg, step_reseller_add)

    elif call.data == "reseller_remove":
        resellers = list(admins_col.find({"role": "reseller"}))
        if not resellers: return bot.answer_callback_query(call.id, "No resellers exist.", show_alert=True)
        markup = InlineKeyboardMarkup()
        for r in resellers: markup.add(InlineKeyboardButton(f"❌ {r['user_id']}", callback_data=f"delreseller_{r['user_id']}"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="close_menu"))
        safe_edit_text("Select reseller to remove:", chat_id, msg_id, markup)

    elif call.data.startswith("delreseller_"):
        uid = int(call.data.split("_")[1])
        admins_col.delete_one({"user_id": uid, "role": "reseller"})
        safe_edit_text("✅ Reseller removed.", chat_id, msg_id, None)

# --- CREATION STEP HANDLERS ---
def step_prod_name(message):
    pending_inputs[message.chat.id] = {"name": message.text}
    msg = bot.send_message(message.chat.id, "Enter product category (Android or iOS):")
    bot.register_next_step_handler(msg, step_prod_cat)

def step_prod_cat(message):
    cat = message.text.strip()
    if cat not in ["Android", "iOS"]:
        return bot.send_message(message.chat.id, "❌ Cancelled. Category must be exactly `Android` or `iOS`.", parse_mode="Markdown")
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
        plans_col.insert_one({"_id": plan_id, "product_id": prod_id, "name": name, "days": data["days"], "price": price})
        bot.send_message(message.chat.id, f"✅ Plan **{name}** for ₹{price} added successfully!", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ Price must be a valid number. Cancelled.")

# --- ADMIN UTILITY HANDLERS ---
def process_welcome_img(message):
    if message.text and message.text.strip().upper() == "NONE":
        settings_col.update_one({"_id": "config"}, {"$set": {"welcome_image": ""}})
        bot.send_message(message.chat.id, "✅ Welcome image removed.")
    elif message.photo:
        file_id = message.photo[-1].file_id
        settings_col.update_one({"_id": "config"}, {"$set": {"welcome_image": file_id}})
        bot.send_message(message.chat.id, "✅ Welcome image updated successfully!")
    else:
        bot.send_message(message.chat.id, "❌ Error. Please send a valid photo.")

def process_whatsapp(message):
    settings_col.update_one({"_id": "config"}, {"$set": {"whatsapp_num": message.text.strip()}})
    bot.send_message(message.chat.id, "✅ WhatsApp number updated!")

def step_add_keys(message, plan_id):
    keys = [k.strip() for k in message.text.split(",") if k.strip()]
    if not keys: return bot.send_message(message.chat.id, "❌ No valid keys found.")
    for k in keys: keys_col.insert_one({"plan_id": plan_id, "key": k})
    bot.send_message(message.chat.id, f"✅ Successfully added {len(keys)} keys to the database.")

def step_promo_code(message):
    pending_inputs[message.chat.id] = {"code": message.text.strip().upper()}
    msg = bot.send_message(message.chat.id, "Enter discount percentage (e.g. 10 for 10%):")
    bot.register_next_step_handler(msg, step_promo_disc)

def step_promo_disc(message):
    try:
        disc = int(message.text)
        code = pending_inputs.pop(message.chat.id)["code"]
        promos_col.insert_one({"code": code, "discount": disc})
        bot.send_message(message.chat.id, f"✅ Promo `{code}` for {disc}% off created!", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ Invalid discount number.")

def step_reseller_add(message):
    try:
        uid = int(message.text)
        if not admins_col.find_one({"user_id": uid}): admins_col.insert_one({"user_id": uid, "role": "reseller"})
        bot.send_message(message.chat.id, f"✅ User {uid} is now a Reseller.")
    except: bot.send_message(message.chat.id, "❌ Invalid ID.")

def process_links(message):
    try:
        sup, prf, tut = message.text.split()
        settings_col.update_one({"_id": "config"}, {"$set": {"support_link": sup, "pay_proof_link": prf, "tutorial_link": tut}})
        bot.send_message(message.chat.id, "✅ Links updated successfully!")
    except:
        bot.send_message(message.chat.id, "❌ Error. Send exactly 3 valid links separated by spaces.")

def process_broadcast(message):
    bot.send_message(message.chat.id, "⏳ Broadcasting...")
    success = 0
    for user in users_col.find():
        try:
            bot.send_message(user["user_id"], f"📣 **Announcement**\n\n{message.text}", parse_mode="Markdown")
            success += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ Broadcast sent to {success} users.")

def process_add_admin(message):
    try:
        new_admin = int(message.text)
        if not admins_col.find_one({"user_id": new_admin}): admins_col.insert_one({"user_id": new_admin})
        bot.send_message(message.chat.id, f"✅ User {new_admin} is now an admin.")
    except: bot.send_message(message.chat.id, "❌ Invalid ID.")

def process_remove_admin(message):
    try:
        remove_id = int(message.text)
        admins_col.delete_one({"user_id": remove_id})
        bot.send_message(message.chat.id, f"✅ Admin {remove_id} removed.")
    except: bot.send_message(message.chat.id, "❌ Invalid ID.")

def step_manage_user(message):
    try:
        uid = int(message.text)
        user = users_col.find_one({"user_id": uid})
        if not user: return bot.send_message(message.chat.id, "❌ User not found in database.")
        
        text = f"👤 **User Management**\n\n**Name:** {user.get('first_name')}\n**ID:** `{uid}`\n**Balance:** ₹{user.get('balance', 0.0)}\n**Orders:** {len(user.get('orders', []))}"
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("➕ Add Balance", callback_data=f"addbal_{uid}"), InlineKeyboardButton("➖ Deduct Balance", callback_data=f"deductbal_{uid}"))
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ Invalid ID.")

def modify_balance(message, uid, is_add):
    try:
        amt = float(message.text)
        op = "$inc" if is_add else "$inc" 
        if not is_add: amt = -amt
        users_col.update_one({"user_id": uid}, {op: {"balance": amt}})
        bot.send_message(message.chat.id, f"✅ User balance updated by ₹{amt}.")
        bot.send_message(uid, f"🔔 **Wallet Update:** Your balance was modified by an admin. (Change: ₹{amt})")
    except:
        bot.send_message(message.chat.id, "❌ Invalid amount.")

def step_custom_dm_id(message):
    try:
        uid = int(message.text)
        msg = bot.send_message(message.chat.id, "Enter the message you want to send to this user:")
        bot.register_next_step_handler(msg, lambda m: step_custom_dm_send(m, uid))
    except:
        bot.send_message(message.chat.id, "❌ Invalid ID.")

def step_custom_dm_send(message, uid):
    try:
        bot.send_message(uid, f"✉️ **Message from Admin:**\n\n{message.text}", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ Message sent successfully.")
    except:
        bot.send_message(message.chat.id, "❌ Failed to send message. User may have blocked the bot.")

# --- CHECKOUT FLOW ---
def process_upi_name(message, ref_id, is_deposit):
    pending_inputs[message.chat.id] = {"upi_name": message.text, "ref_id": ref_id, "is_deposit": is_deposit}
    msg = bot.send_message(message.chat.id, "📸 **Almost done!**\nPlease send the **Screenshot** of your successful payment now.", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_payment_screenshot)

def process_payment_screenshot(message):
    chat_id = message.chat.id
    if not message.photo:
        msg = bot.send_message(chat_id, "❌ Please send a valid screenshot photo.")
        bot.register_next_step_handler(msg, process_payment_screenshot)
        return
        
    data = pending_inputs.pop(chat_id)
    is_deposit = data.get("is_deposit", False)
    
    bot.send_message(chat_id, "⏳ **Screenshot Received!**\n\nYour payment is being verified by admins.", parse_mode="Markdown")
    
    if is_deposit:
        amount = float(data["ref_id"])
        admin_caption = (
            f"🔔 **NEW DEPOSIT REQUEST**\n━━━━━━━━━━━━━━━━━━\n"
            f"👤 **User:** `{chat_id}` (@{message.from_user.username})\n"
            f"📛 **UPI Name:** `{data['upi_name']}`\n"
            f"💰 **Amount:** ₹{amount}\n━━━━━━━━━━━━━━━━━━"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("✅ Approve", callback_data=f"dep_approve_{chat_id}_{amount}"), InlineKeyboardButton("❌ Reject", callback_data=f"dep_reject_{chat_id}_{amount}"))
    else:
        plan = plans_col.find_one({"_id": data["ref_id"]})
        if not plan: return
        order_id = str(uuid.uuid4())[:8].upper()
        new_order = {
            "order_id": order_id, "plan_name": plan["name"], "days": plan["days"],
            "price": plan["price"], "status": "Pending Verification", "upi_name": data["upi_name"], "date": datetime.now().strftime("%d %b %Y")
        }
        users_col.update_one({"user_id": chat_id}, {"$push": {"orders": new_order}})
        
        admin_caption = (
            f"🔔 **NEW ORDER PAYMENT**\n━━━━━━━━━━━━━━━━━━\n"
            f"👤 **User:** `{chat_id}` (@{message.from_user.username})\n"
            f"📛 **UPI Name:** `{data['upi_name']}`\n"
            f"📦 **Item:** {plan['name']}\n"
            f"💰 **Amount:** ₹{plan['price']}\n"
            f"🔖 **Order ID:** `{order_id}`\n━━━━━━━━━━━━━━━━━━"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("✅ Approve", callback_data=f"approve_{chat_id}_{order_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}_{order_id}"))
    
    # Broadcast to all admins
    bot.send_photo(OWNER_ID, message.photo[-1].file_id, caption=admin_caption, reply_markup=markup, parse_mode="Markdown")
    for admin in admins_col.find():
        if admin["user_id"] != OWNER_ID:
            try: bot.send_photo(admin["user_id"], message.photo[-1].file_id, caption=admin_caption, reply_markup=markup, parse_mode="Markdown")
            except: pass

print("Bot is starting... Loading Environment Variables...")
bot.infinity_polling(skip_pending=True)
