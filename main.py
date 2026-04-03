import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import os
import pymongo
from datetime import datetime

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "@Nexapayz") 
MONGO_URI = os.getenv("MONGO_URI")

try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0")) 
except (ValueError, TypeError):
    OWNER_ID = 0

# --- SAFETY CHECK ---
if not BOT_TOKEN or not MONGO_URI or OWNER_ID == 0:
    print("❌ ERROR: Missing Environment Variables!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# --- MONGODB DATABASE SETUP ---
client = pymongo.MongoClient(MONGO_URI)
db = client["panel_store_db"]

users_col = db["users"]
admins_col = db["admins"]
settings_col = db["settings"]
logs_col = db["logs"]

# Initialize default settings
if not settings_col.find_one({"_id": "config"}):
    settings_col.insert_one({
        "_id": "config",
        "support_link": "https://t.me/Nexapayz",
        "pay_proof_link": "https://t.me/Nexapayz",
        "tutorial_link": "https://youtube.com",
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

# 🛠️ THE CRASH FIX: Safe Edit Function
def safe_edit_text(text, chat_id, message_id, markup):
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        # If it's a photo or identical message, delete and send fresh
        try: bot.delete_message(chat_id, message_id)
        except: pass
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- USER COMMANDS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not check_force_join(message.from_user.id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@', '')}"))
        markup.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_join"))
        bot.send_message(message.chat.id, "🛑 **Access Denied**\n\nYou must join our official channel to use this bot.", reply_markup=markup, parse_mode="Markdown")
        return

    # User Registration
    user = users_col.find_one({"user_id": message.from_user.id})
    if not user:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("📱 Share My Number", request_contact=True))
        bot.send_message(message.chat.id, "👋 **Welcome to PANEL STORE FREE FIRE!**\n\nTo continue, please share your phone number by tapping the button below.", reply_markup=markup, parse_mode="Markdown")
    else:
        # Load Owner Bottom Menu if Owner
        if message.from_user.id == OWNER_ID:
            owner_markup = ReplyKeyboardMarkup(resize_keyboard=True)
            owner_markup.row(KeyboardButton("👑 Owner Panel"), KeyboardButton("🔗 Links & Prices"))
            bot.send_message(message.chat.id, "Welcome back, Boss! Loading admin tools...", reply_markup=owner_markup)
            
        main_menu(message.chat.id, user_first_name=message.from_user.first_name)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if not users_col.find_one({"user_id": message.from_user.id}):
        join_date = datetime.now().strftime("%d %b %Y")
        users_col.insert_one({"user_id": message.from_user.id, "phone": message.contact.phone_number, "date": join_date, "orders": []})
    
    # Remove the contact keyboard
    bot.send_message(message.chat.id, "✅ Number Verified Successfully!", reply_markup=telebot.types.ReplyKeyboardRemove())
    
    if message.from_user.id == OWNER_ID:
        owner_markup = ReplyKeyboardMarkup(resize_keyboard=True)
        owner_markup.row(KeyboardButton("👑 Owner Panel"), KeyboardButton("🔗 Links & Prices"))
        bot.send_message(message.chat.id, "Admin tools loaded.", reply_markup=owner_markup)

    main_menu(message.chat.id, user_first_name=message.from_user.first_name)

def main_menu(chat_id, message_id=None, user_first_name="User"):
    config = settings_col.find_one({"_id": "config"}) or {}
    support_link = config.get("support_link", "https://t.me/Nexapayz")
    pay_proof_link = config.get("pay_proof_link", "https://t.me/Nexapayz")
    
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
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Shop Now", callback_data="shop_menu"))
    markup.row(InlineKeyboardButton("📦 My Orders", callback_data="my_orders"), InlineKeyboardButton("👤 Profile", callback_data="my_profile"))
    markup.row(InlineKeyboardButton("↗️ Pay Proof", url=pay_proof_link), InlineKeyboardButton("❓ How to Use", callback_data="how_to_use"))
    markup.row(InlineKeyboardButton("💬 Support", url=support_link), InlineKeyboardButton("🎁 Referral", callback_data="my_referral"))
    
    if message_id: safe_edit_text(text, chat_id, message_id, markup)
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- OWNER BOTTOM MENU HANDLERS ---
@bot.message_handler(func=lambda message: message.text == "👑 Owner Panel" and message.from_user.id == OWNER_ID)
def bottom_owner_panel(message):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📊 Stats & Logs", callback_data="admin_stats"), InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast"))
    markup.row(InlineKeyboardButton("👥 Add Admin", callback_data="admin_add"), InlineKeyboardButton("🚫 Remove Admin", callback_data="admin_remove"))
    bot.send_message(message.chat.id, "👑 **Owner Panel** (Full Access)", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🔗 Links & Prices" and message.from_user.id == OWNER_ID)
def bottom_links_prices(message):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("⚙️ Edit Prices", callback_data="admin_prices"), InlineKeyboardButton("🔗 Change Links", callback_data="admin_links"))
    bot.send_message(message.chat.id, "⚙️ **Management Dashboard**", reply_markup=markup, parse_mode="Markdown")

# --- CALLBACK ROUTER ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    config = settings_col.find_one({"_id": "config"}) or {}

    # MAIN NAVIGATION
    if call.data == "check_join":
        if check_force_join(call.from_user.id):
            bot.delete_message(chat_id, msg_id)
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)
            
    elif call.data == "main_menu":
        main_menu(chat_id, msg_id, call.from_user.first_name)

    # --- UI SECTIONS ---
    elif call.data == "my_orders":
        user = users_col.find_one({"user_id": chat_id})
        orders = user.get("orders", []) if user else []
        
        text = "━━━━━━━━━━━━━━━━━━━━\n📦 **MY ORDERS (last 10)**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if not orders:
            text += "You have no previous orders.\n\n"
        else:
            for i, o in enumerate(reversed(orders[-10:]), 1):
                icon = "⏳" if o["status"] == "Pending" else "✅"
                text += f"{i}. {icon} **{o['name']}**\n   ⏱ {o['days']} Days • 💰 ₹{o['price']} • {o['status']}\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🛒 Shop Again", callback_data="shop_menu"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    elif call.data == "my_profile":
        user = users_col.find_one({"user_id": chat_id}) or {}
        phone = user.get("phone", "Not Provided")
        date = user.get("date", "Unknown")
        orders_count = len(user.get("orders", []))
        ref_link = f"https://t.me/{bot.get_me().username}?start=ref_{chat_id}"
        
        text = (
            "👤 **YOUR PROFILE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 **Name:** {call.from_user.first_name}\n"
            f"🆔 **User ID:** `{chat_id}`\n"
            f"📱 **Phone:** `{phone}`\n"
            f"📅 **Member Since:** {date}\n"
            f"🛒 **Total Orders:** {orders_count}\n\n"
            f"🔗 **Your Referral Link:**\n`{ref_link}`\n"
            "_Share → friend buys → you earn rewards!_"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🛒 Shop Now", callback_data="shop_menu"), InlineKeyboardButton("📦 My Orders", callback_data="my_orders"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    elif call.data == "my_referral":
        ref_link = f"https://t.me/{bot.get_me().username}?start=ref_{chat_id}"
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
        tutorial = config.get("tutorial_link", "https://youtube.com")
        text = (
            "📖 **How to Buy — Panel Store Free Fire**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Tap 🛒 **Shop Now**\n"
            "2️⃣ Choose **Android** or **iOS**\n"
            "3️⃣ Pick your product & plan\n"
            "4️⃣ Scan the UPI QR or copy UPI ID\n"
            "5️⃣ Pay the **exact** amount shown\n"
            "6️⃣ Tap ✅ **I Have Paid**\n"
            "7️⃣ Sit back — your panel key arrives shortly! 🚀\n\n"
            "⚠️ _Always pay the exact amount. Partial payments will NOT be detected._\n\n"
            "🎬 **Watch the full tutorial video below 👇**"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("▶️ Watch Tutorial on YouTube", url=tutorial))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="main_menu"))
        safe_edit_text(text, chat_id, msg_id, markup)

    # --- SHOPPING SYSTEM ---
    elif call.data == "shop_menu":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📱 Android", callback_data="shop_android"))
        markup.add(InlineKeyboardButton("🍎 iOS", callback_data="shop_ios"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        safe_edit_text("🔥 **Choose your device category:**", chat_id, msg_id, markup)

    elif call.data == "shop_android":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("DRIP CLIENT MOBILE", callback_data="prod_drip"), InlineKeyboardButton("PRIME HOOK MOD", callback_data="prod_prime"))
        markup.add(InlineKeyboardButton("⬅️ Back to Categories", callback_data="shop_menu"))
        safe_edit_text("🛒 **PANEL STORE — 📱 Android**\n\nChoose a product 👇", chat_id, msg_id, markup)

    elif call.data == "shop_ios":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("IOS - ALPHA PANEL", callback_data="prod_alpha"))
        markup.add(InlineKeyboardButton("⬅️ Back to Categories", callback_data="shop_menu"))
        safe_edit_text("🛒 **PANEL STORE — 🍎 iOS**\n\nChoose a product 👇", chat_id, msg_id, markup)

    elif call.data == "prod_drip":
        markup = InlineKeyboardMarkup()
        for k in ["drip_1", "drip_3", "drip_7", "drip_30"]:
            p = config.get("products", {}).get(k)
            if p: markup.add(InlineKeyboardButton(f"{p['days']} Day{'s' if p['days']>1 else ''} — ₹{p['price']}", callback_data=f"buy_{k}"))
        markup.add(InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop_android"))
        safe_edit_text("🏷 **DRIP CLIENT MOBILE**\n\nChoose a plan 👇", chat_id, msg_id, markup)

    elif call.data == "prod_prime":
        markup = InlineKeyboardMarkup()
        for k in ["prime_1", "prime_5", "prime_10"]:
            p = config.get("products", {}).get(k)
            if p: markup.add(InlineKeyboardButton(f"{p['days']} Day{'s' if p['days']>1 else ''} — ₹{p['price']}", callback_data=f"buy_{k}"))
        markup.add(InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop_android"))
        safe_edit_text("🏷 **PRIME HOOK MOD**\n\nChoose a plan 👇", chat_id, msg_id, markup)

    elif call.data == "prod_alpha":
        markup = InlineKeyboardMarkup()
        for k in ["alpha_7", "alpha_30"]:
            p = config.get("products", {}).get(k)
            if p: markup.add(InlineKeyboardButton(f"{p['days']} Days — ₹{p['price']}", callback_data=f"buy_{k}"))
        markup.add(InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop_ios"))
        safe_edit_text("🏷 **IOS - ALPHA PANEL**\n\nChoose a plan 👇", chat_id, msg_id, markup)

    # --- CHECKOUT SYSTEM ---
    elif call.data.startswith("buy_"):
        prod_key = call.data.replace("buy_", "")
        p = config.get("products", {}).get(prod_key)
        
        if not p: return bot.answer_callback_query(call.id, "Product not found!", show_alert=True)
            
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
            bot.send_message(chat_id, text + "\n\n*(Error: QR Image Missing! Upload qr.jpg to GitHub)*", reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("paid_"):
        prod_key = call.data.replace("paid_", "")
        bot.answer_callback_query(call.id, "Verification sent to Admins!", show_alert=True)
        
        p = config.get("products", {}).get(prod_key)
        if not p: return
        
        # Log to DB and append to user's "My Orders"
        log_entry = f"User {call.from_user.id} claimed payment for {p['name']} (₹{p['price']})"
        logs_col.insert_one({"log": log_entry}) 
        
        new_order = {"name": p["name"], "days": p["days"], "price": p["price"], "status": "Pending"}
        users_col.update_one({"user_id": chat_id}, {"$push": {"orders": new_order}})
        
        payment_msg = f"🔔 **NEW PAYMENT ALERT**\nUser ID: `{call.from_user.id}`\nItem: {p['name']} ({p['days']}d)\nAmount: ₹{p['price']}"
        try: bot.send_message(OWNER_ID, payment_msg, parse_mode="Markdown")
        except: pass
        
        # Send user back to menu so they don't get stuck on the QR code
        main_menu(chat_id, msg_id, call.from_user.first_name)

    # --- ADMIN INLINE CALLBACKS ---
    elif call.data == "admin_stats":
        if not (call.from_user.id == OWNER_ID or is_admin(call.from_user.id)): return
        total_users = users_col.count_documents({})
        recent_logs = list(logs_col.find().sort("_id", -1).limit(5))
        logs_text = "\n".join([log["log"] for log in recent_logs]) if recent_logs else "No purchases yet."
        safe_edit_text(f"📊 **Bot Statistics**\n\n👥 Total Users: {total_users}\n\n🛒 **Recent Logs:**\n{logs_text}", chat_id, msg_id, None)

    elif call.data == "admin_broadcast":
        if not (call.from_user.id == OWNER_ID or is_admin(call.from_user.id)): return
        msg = bot.send_message(chat_id, "Send the message you want to broadcast to all users:")
        bot.register_next_step_handler(msg, process_broadcast)

    elif call.data == "admin_links":
        if call.from_user.id != OWNER_ID: return
        msg = bot.send_message(chat_id, "Send the new links separated by a space:\n`Support_Link Proof_Link Tutorial_Link`\n\nExample:\n`https://t.me/sup https://t.me/prf https://youtu.be/x`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_links)

    elif call.data == "admin_add":
        if call.from_user.id != OWNER_ID: return
        msg = bot.send_message(chat_id, "Send the Telegram User ID of the new admin:")
        bot.register_next_step_handler(msg, process_add_admin)
        
    elif call.data == "admin_remove":
        if call.from_user.id != OWNER_ID: return
        msg = bot.send_message(chat_id, "Send the Telegram User ID of the admin to REMOVE:")
        bot.register_next_step_handler(msg, process_remove_admin)

    elif call.data == "admin_prices":
        if call.from_user.id != OWNER_ID: return
        text = "⚙️ **Send a command to update a price.**\nFormat: `key new_price`\n\n**Keys available:**\n"
        for k, v in config.get("products", {}).items():
            text += f"`{k}` : {v['name']} ({v['days']}d) = ₹{v['price']}\n"
        msg = bot.send_message(chat_id, text, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_price_change)

# --- STEP HANDLERS ---
def process_broadcast(message):
    bot.send_message(message.chat.id, "⏳ Broadcasting...")
    success = 0
    for user in users_col.find():
        try:
            bot.send_message(user["user_id"], f"📣 **Announcement**\n\n{message.text}", parse_mode="Markdown")
            success += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ Broadcast sent to {success} users.")

def process_links(message):
    try:
        sup, prf, tut = message.text.split()
        settings_col.update_one({"_id": "config"}, {"$set": {"support_link": sup, "pay_proof_link": prf, "tutorial_link": tut}})
        bot.send_message(message.chat.id, "✅ Links updated successfully!")
    except:
        bot.send_message(message.chat.id, "❌ Error. Make sure you send exactly 3 links separated by spaces.")

def process_add_admin(message):
    try:
        new_admin = int(message.text)
        if not admins_col.find_one({"user_id": new_admin}): admins_col.insert_one({"user_id": new_admin})
        bot.send_message(message.chat.id, f"✅ User {new_admin} is now an admin.")
    except: bot.send_message(message.chat.id, "❌ Invalid ID. Must be numbers.")

def process_remove_admin(message):
    try:
        remove_id = int(message.text)
        admins_col.delete_one({"user_id": remove_id})
        bot.send_message(message.chat.id, f"✅ Admin {remove_id} removed.")
    except: bot.send_message(message.chat.id, "❌ Invalid ID.")

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
