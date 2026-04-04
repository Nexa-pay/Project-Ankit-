import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
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
    "🔥 ━━ **PANEL STORE** ━━ 🔥\n\n"
    "Welcome back, **{name}**!\n"
    "Welcome to PANEL STORE!\n\n"
    "Products: {prod_count}\n"
    "━━━━━━━━━━━━━━━━━━"
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
        "reseller_fee": 999
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

# --- KEYBOARDS (EXACTLY LIKE VIDEO) ---
def user_main_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🛍 Shop Now"))
    markup.row(KeyboardButton("📦 Orders"), KeyboardButton("👤 Profile"))
    markup.row(KeyboardButton("💰 Add Balance"), KeyboardButton("🎁 Referral"))
    markup.row(KeyboardButton("🎰 Lucky Spin"), KeyboardButton("❓ How to Use"))
    markup.add(KeyboardButton("🆘 Support"))
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
        markup.add(InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@', '')}"))
        markup.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_join"))
        bot.send_message(message.chat.id, "🛑 **Access Denied**\n\nYou must join our official channel to use this bot.", reply_markup=markup, parse_mode="Markdown")
        return

    user = users_col.find_one({"user_id": message.from_user.id})
    if not user:
        users_col.insert_one({
            "user_id": message.from_user.id, 
            "first_name": message.from_user.first_name,
            "balance": 0.0,
            "type": "CUSTOMER",
            "orders": [], 
            "referrals": 0,
            "join_date": datetime.now().strftime("%d %b %Y")
        })

    config = settings_col.find_one({"_id": "config"})
    prod_count = products_col.count_documents({})
    
    welcome_text = config.get("welcome_msg", default_welcome)
    welcome_text = welcome_text.replace("{name}", message.from_user.first_name).replace("{prod_count}", str(prod_count))
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=user_main_keyboard(message.from_user.id), parse_mode="Markdown")

# --- USER BOTTOM MENU ROUTER ---
@bot.message_handler(func=lambda message: message.text in ["🛍 Shop Now", "📦 Orders", "👤 Profile", "💰 Add Balance", "🎁 Referral", "🎰 Lucky Spin", "❓ How to Use", "🆘 Support"])
def user_menu_handler(message):
    chat_id = message.chat.id
    
    if message.text == "🛍 Shop Now":
        products = list(products_col.find())
        if not products:
            return bot.send_message(chat_id, "🚫 The store is currently empty.")
            
        markup = InlineKeyboardMarkup()
        for p in products:
            markup.add(InlineKeyboardButton(p["name"], callback_data=f"view_prod_{p['_id']}"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="close_menu"))
        
        bot.send_message(chat_id, "✅ **CHOOSE YOUR PRODUCT** 🎮\n\n🛡 Premium Keys\n⚡ Instant Delivery\n🔒 Secure Payment\n\nSelect a product below: 👇", reply_markup=markup, parse_mode="Markdown")

    elif message.text == "👤 Profile":
        user = users_col.find_one({"user_id": chat_id})
        text = (
            "👤 **YOUR PROFILE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 **Name:** {user.get('first_name', 'User')}\n"
            f"🆔 **User ID:** `{chat_id}`\n"
            f"💰 **Balance:** ₹{user.get('balance', 0.0)}\n"
            f"⭐ **Type:** {user.get('type', 'CUSTOMER')}\n"
            f"🛒 **Total Orders:** {len(user.get('orders', []))}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")
        
    elif message.text == "📦 Orders":
        user = users_col.find_one({"user_id": chat_id})
        orders = user.get("orders", []) if user else []
        text = "📦 **MY ORDERS**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if not orders: text += "You have no previous orders."
        else:
            for i, o in enumerate(reversed(orders[-5:]), 1):
                text += f"{i}. **{o['plan_name']}** - ₹{o['price']} ({o['status']})\n"
        bot.send_message(chat_id, text, parse_mode="Markdown")
        
    else:
        bot.send_message(chat_id, "🚧 Feature under construction!")

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
        markup.add(InlineKeyboardButton("✏️ Edit Product", callback_data="prod_edit"))
        markup.add(InlineKeyboardButton("❌ Delete Product", callback_data="prod_delete"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="close_menu"))
        bot.send_message(chat_id, "📦 **PRODUCTS**\n\nActions:", reply_markup=markup, parse_mode="Markdown")

    elif message.text == "📅 Plan Management":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add Plan", callback_data="plan_add"))
        markup.add(InlineKeyboardButton("❌ Delete Plan", callback_data="plan_delete"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="close_menu"))
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
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- INLINE CALLBACK ROUTER ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    
    if call.data == "close_menu":
        bot.delete_message(chat_id, msg_id)

    # --- PRODUCT MANAGEMENT (STEP BY STEP) ---
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

    # --- PLAN MANAGEMENT (STEP BY STEP) ---
    elif call.data == "plan_add":
        products = list(products_col.find())
        if not products: return bot.answer_callback_query(call.id, "Create a Product first!", show_alert=True)
        markup = InlineKeyboardMarkup()
        for p in products: markup.add(InlineKeyboardButton(p["name"], callback_data=f"addplan_{p['_id']}"))
        safe_edit_text("Select Product to add plan to:", chat_id, msg_id, markup)

    elif call.data.startswith("addplan_"):
        pid = call.data.split("_")[1]
        bot.delete_message(chat_id, msg_id)
        msg = bot.send_message(chat_id, "📝 **Add Plan**\n\nEnter plan name (e.g., 1 Day / 7 Days):")
        bot.register_next_step_handler(msg, step_plan_name, pid)

    # --- SHOPPING DYNAMICS ---
    elif call.data.startswith("view_prod_"):
        pid = call.data.replace("view_prod_", "")
        p = products_col.find_one({"_id": pid})
        plans = list(plans_col.find({"product_id": pid}))
        
        markup = InlineKeyboardMarkup()
        if not plans:
            markup.add(InlineKeyboardButton("⬅️ Back", callback_data="close_menu"))
            safe_edit_text(f"🏷 **{p['name']}**\n\n{p['desc']}\n\n*No plans available yet.*", chat_id, msg_id, markup)
            return

        for plan in plans:
            markup.add(InlineKeyboardButton(f"{plan['name']} — ₹{plan['price']}", callback_data=f"buy_plan_{plan['_id']}"))
        markup.add(InlineKeyboardButton("⬅️ Close", callback_data="close_menu"))
        
        safe_edit_text(f"🏷 **{p['name']}**\n\n_{p['desc']}_\n\nChoose a plan 👇", chat_id, msg_id, markup)

    # --- DYNAMIC CHECKOUT ---
    elif call.data.startswith("buy_plan_"):
        plan_id = call.data.replace("buy_plan_", "")
        plan = plans_col.find_one({"_id": plan_id})
        if not plan: return bot.answer_callback_query(call.id, "Plan not found!", show_alert=True)
        
        config = settings_col.find_one({"_id": "config"})
        upi_id = config.get("upi_id", "error@upi")
        
        text = (
            f"🔥 **ORDER CREATED**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏷 **Plan:** {plan['name']}\n"
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
        
        try:
            bot.send_photo(chat_id, qr_link, caption=text, reply_markup=markup, parse_mode="Markdown")
        except:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("paid_"):
        plan_id = call.data.replace("paid_", "")
        bot.delete_message(chat_id, msg_id) 
        msg = bot.send_message(chat_id, "✅ **Payment Initiated**\n\nPlease type your **UPI registered name** exactly as it appears in your payment app:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_upi_name, plan_id)

    # --- SETTINGS CALLBACKS ---
    elif call.data == "set_welcome":
        msg = bot.send_message(chat_id, "Send your new Welcome Message.\nUse `{name}` and `{prod_count}` for dynamic text.")
        bot.register_next_step_handler(msg, lambda m: settings_col.update_one({"_id": "config"}, {"$set": {"welcome_msg": m.text}}))
    elif call.data == "set_upi":
        msg = bot.send_message(chat_id, "Send your exact UPI ID:")
        bot.register_next_step_handler(msg, lambda m: settings_col.update_one({"_id": "config"}, {"$set": {"upi_id": m.text.strip()}}))

# --- STEP HANDLERS (PRODUCT/PLAN) ---
def step_prod_name(message):
    pending_inputs[message.chat.id] = {"name": message.text}
    msg = bot.send_message(message.chat.id, "Enter product description:")
    bot.register_next_step_handler(msg, step_prod_desc)

def step_prod_desc(message):
    pending_inputs[message.chat.id]["desc"] = message.text
    msg = bot.send_message(message.chat.id, "Enter download link (or send - for none):")
    bot.register_next_step_handler(msg, step_prod_link)

def step_prod_link(message):
    data = pending_inputs.pop(message.chat.id)
    prod_id = str(uuid.uuid4())[:6]
    products_col.insert_one({
        "_id": prod_id,
        "name": data["name"],
        "desc": data["desc"],
        "link": message.text if message.text != "-" else ""
    })
    bot.send_message(message.chat.id, f"✅ Product **{data['name']}** added successfully!", parse_mode="Markdown")

def step_plan_name(message, prod_id):
    pending_inputs[message.chat.id] = {"name": message.text}
    msg = bot.send_message(message.chat.id, "Enter price in ₹ (Numbers only):")
    bot.register_next_step_handler(msg, step_plan_price, prod_id)

def step_plan_price(message, prod_id):
    try:
        price = int(message.text)
        data = pending_inputs.pop(message.chat.id)
        plan_id = str(uuid.uuid4())[:8]
        plans_col.insert_one({
            "_id": plan_id,
            "product_id": prod_id,
            "name": data["name"],
            "price": price
        })
        bot.send_message(message.chat.id, f"✅ Plan **{data['name']}** added successfully!", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ Price must be a valid number. Try again.")

# --- CHECKOUT HANDLERS ---
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
    if not plan: return
    
    order_id = str(uuid.uuid4())[:8].upper()
    new_order = {
        "order_id": order_id,
        "plan_name": plan["name"],
        "price": plan["price"],
        "status": "Pending Verification",
        "upi_name": data["upi_name"],
        "date": datetime.now().strftime("%d %b %Y")
    }
    
    users_col.update_one({"user_id": chat_id}, {"$push": {"orders": new_order}})
    bot.send_message(chat_id, "⏳ **Screenshot Received!**\n\nYour payment is being verified by admins.", parse_mode="Markdown")
    
    # Notify Admin Flow (Mocking approval mechanism for UI consistency)
    bot.send_message(OWNER_ID, f"🔔 **NEW PAYMENT**\n\nUser: {chat_id}\nUPI Name: {data['upi_name']}\nAmount: ₹{plan['price']}\nOrder ID: {order_id}")
    bot.send_photo(OWNER_ID, message.photo[-1].file_id)

print("Bot is starting... Loading Environment Variables...")
bot.infinity_polling(skip_pending=True)
