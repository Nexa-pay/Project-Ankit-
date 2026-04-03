import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import os
import pymongo

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "@Nexapayz") 
MONGO_URI = os.getenv("MONGO_URI")

# Now using OWNER_ID properly so it makes sense!
try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0")) 
except (ValueError, TypeError):
    OWNER_ID = 0

# --- SAFETY CHECK ---
if not BOT_TOKEN or not MONGO_URI or OWNER_ID == 0:
    print("❌ ERROR: Missing Environment Variables!")
    print(f"BOT_TOKEN: {'✅ Set' if BOT_TOKEN else '❌ MISSING'}")
    print(f"MONGO_URI: {'✅ Set' if MONGO_URI else '❌ MISSING'}")
    print(f"OWNER_ID: {'✅ Set' if OWNER_ID != 0 else '❌ MISSING'}")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- MONGODB DATABASE SETUP ---
client = pymongo.MongoClient(MONGO_URI)
db = client["panel_store_db"]

users_col = db["users"]
admins_col = db["admins"]
settings_col = db["settings"]
logs_col = db["logs"]

# Initialize default settings if database is empty
if not settings_col.find_one({"_id": "config"}):
    settings_col.insert_one({
        "_id": "config",
        "support_link": "https://t.me/Nexapayz",
        "pay_proof_link": "https://t.me/Nexapayz",
        "products": {
            "drip_1": {"name": "DRIP CLIENT MOBILE", "days": 1, "price": 98},
            "drip_3": {"name": "DRIP CLIENT MOBILE", "days": 3, "price": 190},
            "drip_7": {"name": "DRIP CLIENT MOBILE", "days": 7, "price": 349},
            "drip_30": {"name": "DRIP CLIENT MOBILE", "days": 30, "price": 960},
            "prime_1": {"name": "PRIME HOOK MOD", "days": 1, "price": 82},
            "prime_5": {"name": "PRIME HOOK MOD", "days": 5, "price": 230},
            "prime_10": {"name": "PRIME HOOK MOD", "days": 10, "price": 399},
            "alpha_7": {"name": "IOS - ALPHA PANEL", "days": 7, "price": 1260},
            "alpha_30": {"name": "IOS - ALPHA PANEL", "days": 30, "price": 2240},
        }
    })

# Ensure the Owner is always recognized in the DB
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

def force_join_prompt(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@', '')}"))
    markup.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_join"))
    bot.send_message(message.chat.id, "🛑 **Access Denied**\n\nYou must join our official channel to use this bot.", reply_markup=markup, parse_mode="Markdown")

# --- USER COMMANDS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not check_force_join(message.from_user.id):
        force_join_prompt(message)
        return

    # Check if user exists in MongoDB
    if not users_col.find_one({"user_id": message.from_user.id}):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("📱 Share My Number", request_contact=True))
        bot.send_message(message.chat.id, "👋 **Welcome to PANEL STORE FREE FIRE!**\n\nTo continue, please share your phone number by tapping the button below.", reply_markup=markup, parse_mode="Markdown")
    else:
        main_menu(message.chat.id, user_first_name=message.from_user.first_name)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if not users_col.find_one({"user_id": message.from_user.id}):
        users_col.insert_one({"user_id": message.from_user.id, "phone": message.contact.phone_number})
    bot.send_message(message.chat.id, "✅ Number Verified Successfully!", reply_markup=telebot.types.ReplyKeyboardRemove())
    main_menu(message.chat.id, user_first_name=message.from_user.first_name)

def main_menu(chat_id, message_id=None, user_first_name="User"):
    config = settings_col.find_one({"_id": "config"}) or {}
    
    # Safely fetch links, providing defaults if they are missing in the database
    support_link = config.get("support_link", "https://t.me/Nexapayz")
    pay_proof_link = config.get("pay_proof_link", "https://t.me/Nexapayz")
    
    # Exact Old UI Text
    text = (
        "🔥 ━━ **PANEL STORE FREE FIRE** ━━ 🔥\n"
        "*Powered by Nexapayz*\n\n"
        f"💥 Yo **{user_first_name}**, Welcome!!\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "❓ **Why our store is trusted?**\n"
        "↳ Direct deals with every mod developer\n"
        "↳ Instant delivery after payment\n"
        "↳ **5% discount** on your 2nd & every extra purchase\n"
        "↳ Guaranteed discounted prices"
    )
    
    # Exact Old UI Buttons
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Shop Now", callback_data="shop_menu"))
    markup.row(InlineKeyboardButton("📦 My Orders", callback_data="dummy"), InlineKeyboardButton("👤 Profile", callback_data="dummy"))
    markup.row(InlineKeyboardButton("↗️ Pay Proof", url=pay_proof_link), InlineKeyboardButton("❓ How to Use", callback_data="dummy"))
    markup.row(InlineKeyboardButton("💬 Support", url=support_link), InlineKeyboardButton("🎁 Referral", callback_data="dummy"))
    
    try:
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.delete_message(chat_id, message_id)
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- ROLES & ADMIN PANEL ---
@bot.message_handler(commands=['admin', 'owner'])
def admin_panel(message):
    user_id = message.from_user.id
    is_owner = (user_id == OWNER_ID)
    is_admin_user = is_admin(user_id)
    
    if not (is_owner or is_admin_user):
        return bot.reply_to(message, "❌ You do not have permission.")
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📊 Stats & Logs", callback_data="admin_stats"), InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast"))
    
    if is_owner:
        markup.row(InlineKeyboardButton("⚙️ Edit Prices", callback_data="admin_prices"), InlineKeyboardButton("🔗 Links", callback_data="admin_links"))
        markup.row(InlineKeyboardButton("👥 Add Admin", callback_data="admin_add"), InlineKeyboardButton("🚫 Remove Admin", callback_data="admin_remove"))
        text = "👑 **Owner Panel** (Full Access)"
    else:
        text = "👮 **Admin Panel** (Support Access)\n\n*You can view stats and broadcast messages to users.*"
        
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# --- CALLBACK ROUTER ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    config = settings_col.find_one({"_id": "config"}) or {}

    # User Callbacks
    if call.data == "check_join":
        if check_force_join(call.from_user.id):
            bot.delete_message(chat_id, msg_id)
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)

    elif call.data == "shop_menu":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📱 Android", callback_data="shop_android"))
        markup.add(InlineKeyboardButton("🍎 iOS", callback_data="shop_ios"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        bot.edit_message_text("🔥 **Choose your device category:**", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "shop_android":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("DRIP CLIENT MOBILE", callback_data="prod_drip"), InlineKeyboardButton("PRIME HOOK MOD", callback_data="prod_prime"))
        markup.add(InlineKeyboardButton("⬅️ Back to Categories", callback_data="shop_menu"))
        bot.edit_message_text("🛒 **PANEL STORE — 📱 Android**\n\nChoose a product 👇", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "shop_ios":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("IOS - ALPHA PANEL", callback_data="prod_alpha"))
        markup.add(InlineKeyboardButton("⬅️ Back to Categories", callback_data="shop_menu"))
        bot.edit_message_text("🛒 **PANEL STORE — 🍎 iOS**\n\nChoose a product 👇", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "prod_drip":
        markup = InlineKeyboardMarkup()
        products = config.get("products", {})
        for k in ["drip_1", "drip_3", "drip_7", "drip_30"]:
            p = products.get(k)
            if p: markup.add(InlineKeyboardButton(f"{p['days']} Day{'s' if p['days']>1 else ''} — ₹{p['price']}", callback_data=f"buy_{k}"))
        markup.add(InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop_android"))
        bot.edit_message_text("🏷 **DRIP CLIENT MOBILE**\n\nChoose a plan 👇", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "prod_prime":
        markup = InlineKeyboardMarkup()
        products = config.get("products", {})
        for k in ["prime_1", "prime_5", "prime_10"]:
            p = products.get(k)
            if p: markup.add(InlineKeyboardButton(f"{p['days']} Day{'s' if p['days']>1 else ''} — ₹{p['price']}", callback_data=f"buy_{k}"))
        markup.add(InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop_android"))
        bot.edit_message_text("🏷 **PRIME HOOK MOD**\n\nChoose a plan 👇", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "prod_alpha":
        markup = InlineKeyboardMarkup()
        products = config.get("products", {})
        for k in ["alpha_7", "alpha_30"]:
            p = products.get(k)
            if p: markup.add(InlineKeyboardButton(f"{p['days']} Days — ₹{p['price']}", callback_data=f"buy_{k}"))
        markup.add(InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop_ios"))
        bot.edit_message_text("🏷 **IOS - ALPHA PANEL**\n\nChoose a plan 👇", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("buy_"):
        prod_key = call.data.replace("buy_", "")
        p = config.get("products", {}).get(prod_key)
        
        if not p:
            return bot.answer_callback_query(call.id, "Product not found!", show_alert=True)
            
        text = (
            f"🔥 **ORDER CREATED**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏷 **Product:** {p['name']}\n"
            f"⏱ **Duration:** {p['days']} Day{'s' if p['days'] > 1 else ''}\n"
            f"💰 **Amount:** ₹{p['price']}\n"
            f"🔖 **Ref:** DX-0715EBBB\n\n"
            f"📲 *Scan the QR above to pay*\n"
            f"⚠️ **Pay EXACTLY ₹{p['price']}**\n"
            f"⏰ Expires in 5 minutes"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ I Have Paid", callback_data=f"paid_{prod_key}"))
        markup.add(InlineKeyboardButton("❌ Cancel", callback_data="main_menu"))
        markup.add(InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop_menu"))
        
        bot.delete_message(chat_id, msg_id)
        try:
            with open("qr.jpg", "rb") as qr_img:
                bot.send_photo(chat_id, qr_img, caption=text, reply_markup=markup, parse_mode="Markdown")
        except FileNotFoundError:
            bot.send_message(chat_id, text + "\n\n*(Error: QR Image Missing! Upload qr.jpg)*", reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("paid_"):
        prod_key = call.data.replace("paid_", "")
        bot.answer_callback_query(call.id, "Verification sent to Admins!", show_alert=True)
        
        p = config.get("products", {}).get(prod_key)
        if not p: return
        
        log_entry = f"User {call.from_user.id} claimed payment for {p['name']} (₹{p['price']})"
        logs_col.insert_one({"log": log_entry}) 
        
        # Notify Owner and Admins
        payment_msg = f"🔔 **NEW PAYMENT ALERT**\nUser ID: `{call.from_user.id}`\nItem: {p['name']} ({p['days']}d)\nAmount: ₹{p['price']}"
        try: bot.send_message(OWNER_ID, payment_msg, parse_mode="Markdown")
        except: pass
        
        for admin in admins_col.find():
            if admin["user_id"] != OWNER_ID: # Prevent duplicate message to owner
                try: bot.send_message(admin["user_id"], payment_msg, parse_mode="Markdown")
                except: pass

    elif call.data == "main_menu":
        main_menu(chat_id, msg_id, call.from_user.first_name)

    # --- Admin Callbacks ---
    elif call.data == "admin_stats":
        if not (call.from_user.id == OWNER_ID or is_admin(call.from_user.id)): return
        
        total_users = users_col.count_documents({})
        total_admins = admins_col.count_documents({})
        recent_logs = list(logs_col.find().sort("_id", -1).limit(5))
        
        logs_text = "\n".join([log["log"] for log in recent_logs]) if recent_logs else "No purchases yet."
        text = f"📊 **Bot Statistics**\n\n👥 Total Users: {total_users}\n👮 Admins: {total_admins}\n\n🛒 **Recent Logs:**\n{logs_text}"
        bot.send_message(chat_id, text, parse_mode="Markdown")

    elif call.data == "admin_broadcast":
        if not (call.from_user.id == OWNER_ID or is_admin(call.from_user.id)): return
        msg = bot.send_message(chat_id, "Send the message you want to broadcast to all users:")
        bot.register_next_step_handler(msg, process_broadcast)

    # --- Owner ONLY Callbacks ---
    elif call.data == "admin_links":
        if call.from_user.id != OWNER_ID: return bot.answer_callback_query(call.id, "Owner only.", show_alert=True)
        msg = bot.send_message(chat_id, "Send the new Support Link AND Proof Channel Link separated by a space.\nExample: `https://t.me/support https://t.me/proofs`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_links)

    elif call.data == "admin_add":
        if call.from_user.id != OWNER_ID: return bot.answer_callback_query(call.id, "Owner only.", show_alert=True)
        msg = bot.send_message(chat_id, "Send the Telegram User ID of the new admin:")
        bot.register_next_step_handler(msg, process_add_admin)
        
    elif call.data == "admin_remove":
        if call.from_user.id != OWNER_ID: return bot.answer_callback_query(call.id, "Owner only.", show_alert=True)
        msg = bot.send_message(chat_id, "Send the Telegram User ID of the admin to REMOVE:")
        bot.register_next_step_handler(msg, process_remove_admin)

    elif call.data == "admin_prices":
        if call.from_user.id != OWNER_ID: return bot.answer_callback_query(call.id, "Owner only.", show_alert=True)
        text = "⚙️ **Send a command to update a price.**\nFormat: `key new_price`\n\n**Keys available:**\n"
        for k, v in config.get("products", {}).items():
            text += f"`{k}` : {v['name']} ({v['days']}d) = ₹{v['price']}\n"
        msg = bot.send_message(chat_id, text, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_price_change)

    elif call.data == "dummy":
        bot.answer_callback_query(call.id, "🚧 Feature under construction!", show_alert=True)

# --- STEP HANDLERS ---
def process_broadcast(message):
    success = 0
    bot.send_message(message.chat.id, "⏳ Broadcasting...")
    users = users_col.find()
    for user in users:
        try:
            bot.send_message(user["user_id"], f"📣 **Announcement**\n\n{message.text}", parse_mode="Markdown")
            success += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ Broadcast sent to {success} users.")

def process_links(message):
    try:
        support, proof = message.text.split()
        settings_col.update_one({"_id": "config"}, {"$set": {"support_link": support, "pay_proof_link": proof}})
        bot.send_message(message.chat.id, "✅ Links updated successfully!")
    except:
        bot.send_message(message.chat.id, "❌ Error. Make sure you send exactly two links separated by a space.")

def process_add_admin(message):
    try:
        new_admin = int(message.text)
        if not admins_col.find_one({"user_id": new_admin}):
            admins_col.insert_one({"user_id": new_admin})
        bot.send_message(message.chat.id, f"✅ User {new_admin} is now an admin.")
    except:
        bot.send_message(message.chat.id, "❌ Invalid ID. Must be numbers.")

def process_remove_admin(message):
    try:
        remove_id = int(message.text)
        admins_col.delete_one({"user_id": remove_id})
        bot.send_message(message.chat.id, f"✅ Admin {remove_id} removed.")
    except:
        bot.send_message(message.chat.id, "❌ Invalid ID.")

def process_price_change(message):
    try:
        key, new_price = message.text.split()
        config = settings_col.find_one({"_id": "config"}) or {}
        if key in config.get("products", {}):
            settings_col.update_one({"_id": "config"}, {"$set": {f"products.{key}.price": int(new_price)}})
            bot.send_message(message.chat.id, f"✅ Price for {key} updated to ₹{new_price}")
        else:
            bot.send_message(message.chat.id, "❌ Invalid Key.")
    except:
        bot.send_message(message.chat.id, "❌ Error. Format must be: `drip_1 150`", parse_mode="Markdown")

print("Bot is starting... Loading Environment Variables...")
bot.infinity_polling(skip_pending=True)
