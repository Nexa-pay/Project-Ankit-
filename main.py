import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import os

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "@your_channel_username") 
OWNER_ID = int(os.getenv("ADMIN_ID", "123456789")) # Your numeric ID

bot = telebot.TeleBot(BOT_TOKEN)

# --- IN-MEMORY DATABASE ---
db = {
    "users": set(),
    "admins": {OWNER_ID},
    "logs": [],
    "support_link": "https://t.me/Nexapayz",
    "products": {
        "drip_1": {"name": "DRIP CLIENT", "days": 1, "price": 98},
        "drip_3": {"name": "DRIP CLIENT", "days": 3, "price": 190},
        "drip_7": {"name": "DRIP CLIENT", "days": 7, "price": 349},
        "drip_30": {"name": "DRIP CLIENT", "days": 30, "price": 960},
        "alpha_7": {"name": "IOS ALPHA", "days": 7, "price": 1260},
        "alpha_30": {"name": "IOS ALPHA", "days": 30, "price": 2240},
    }
}

# --- UTILITIES ---
def is_admin(user_id):
    return user_id in db["admins"]

def check_force_join(user_id):
    if is_admin(user_id): return True # Admins bypass force join
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

    if message.from_user.id not in db["users"]:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("📱 Share My Number", request_contact=True))
        bot.send_message(message.chat.id, "👋 **Welcome to PANEL STORE FREE FIRE!**\n\nPlease share your phone number below.", reply_markup=markup, parse_mode="Markdown")
    else:
        main_menu(message.chat.id)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    db["users"].add(message.from_user.id)
    bot.send_message(message.chat.id, "✅ Verified!", reply_markup=telebot.types.ReplyKeyboardRemove())
    main_menu(message.chat.id)

def main_menu(chat_id, message_id=None):
    text = "🔥 ━━ **PANEL STORE FREE FIRE** ━━ 🔥\n*Powered by Nexapayz*\n\n❓ **Why us?**\n↳ Direct deals\n↳ Instant delivery\n↳ Guaranteed discounts"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Shop Now", callback_data="shop_menu"))
    markup.row(InlineKeyboardButton("📦 My Orders", callback_data="dummy"), InlineKeyboardButton("👤 Profile", callback_data="dummy"))
    markup.row(InlineKeyboardButton("💬 Support", url=db["support_link"]))
    
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin', 'owner'])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ You do not have permission.")
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📊 Stats & Logs", callback_data="admin_stats"), InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast"))
    markup.row(InlineKeyboardButton("⚙️ Edit Prices", callback_data="admin_prices"), InlineKeyboardButton("👥 Add Admin", callback_data="admin_add"))
    markup.add(InlineKeyboardButton("🔗 Change Support Link", callback_data="admin_support"))
    bot.send_message(message.chat.id, "👑 **Owner & Admin Panel**", reply_markup=markup, parse_mode="Markdown")

# --- CALLBACK ROUTER ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

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
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="main_menu"))
        bot.edit_message_text("🔥 **Choose device:**", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "shop_android":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("DRIP CLIENT MOBILE", callback_data="prod_drip"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="shop_menu"))
        bot.edit_message_text("🛒 **Android Products:**", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "shop_ios":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("IOS - ALPHA PANEL", callback_data="prod_alpha"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="shop_menu"))
        bot.edit_message_text("🛒 **iOS Products:**", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "prod_drip":
        markup = InlineKeyboardMarkup()
        for k in ["drip_1", "drip_3", "drip_7", "drip_30"]:
            p = db["products"][k]
            markup.add(InlineKeyboardButton(f"{p['days']} Days — ₹{p['price']}", callback_data=f"buy_{k}"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="shop_android"))
        bot.edit_message_text("🏷 **DRIP CLIENT** - Choose plan:", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "prod_alpha":
        markup = InlineKeyboardMarkup()
        for k in ["alpha_7", "alpha_30"]:
            p = db["products"][k]
            markup.add(InlineKeyboardButton(f"{p['days']} Days — ₹{p['price']}", callback_data=f"buy_{k}"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="shop_ios"))
        bot.edit_message_text("🏷 **IOS ALPHA** - Choose plan:", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("buy_"):
        prod_key = call.data.replace("buy_", "")
        p = db["products"][prod_key]
        text = f"🔥 **ORDER CREATED**\n\n🏷 Product: {p['name']}\n⏱ Duration: {p['days']} Days\n💰 Amount: ₹{p['price']}\n\n⚠️ Pay EXACTLY ₹{p['price']}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ I Have Paid", callback_data=f"paid_{prod_key}"))
        markup.add(InlineKeyboardButton("⬅️ Cancel", callback_data="main_menu"))
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("paid_"):
        prod_key = call.data.replace("paid_", "")
        bot.answer_callback_query(call.id, "Verification sent to Admins!", show_alert=True)
        # Log it
        p = db["products"][prod_key]
        db["logs"].append(f"User {call.from_user.id} bought {p['name']} ({p['days']}d) for ₹{p['price']}")
        bot.send_message(OWNER_ID, f"🔔 **NEW PAYMENT**\nUser: `{call.from_user.id}`\nItem: {p['name']} ({p['days']}d)\nAmount: ₹{p['price']}", parse_mode="Markdown")

    elif call.data == "main_menu":
        main_menu(chat_id, msg_id)

    # --- Admin Callbacks ---
    elif call.data == "admin_stats":
        if not is_admin(call.from_user.id): return
        logs = "\n".join(db["logs"][-5:]) if db["logs"] else "No purchases yet."
        text = f"📊 **Bot Statistics**\n\n👥 Total Users: {len(db['users'])}\n👮 Admins: {len(db['admins'])}\n\n🛒 **Recent Logs:**\n{logs}"
        bot.send_message(chat_id, text, parse_mode="Markdown")

    elif call.data == "admin_broadcast":
        if not is_admin(call.from_user.id): return
        msg = bot.send_message(chat_id, "Send the message you want to broadcast to all users:")
        bot.register_next_step_handler(msg, process_broadcast)

    elif call.data == "admin_support":
        if not is_admin(call.from_user.id): return
        msg = bot.send_message(chat_id, "Send the new Support link (e.g., https://t.me/myusername):")
        bot.register_next_step_handler(msg, process_support)

    elif call.data == "admin_add":
        if call.from_user.id != OWNER_ID:
            bot.answer_callback_query(call.id, "Only the Owner can add admins.", show_alert=True)
            return
        msg = bot.send_message(chat_id, "Send the Telegram User ID of the new admin:")
        bot.register_next_step_handler(msg, process_add_admin)

    elif call.data == "admin_prices":
        if not is_admin(call.from_user.id): return
        text = "⚙️ **Send a command to update a price.**\nFormat: `key new_price`\n\n**Keys available:**\n"
        for k, v in db["products"].items():
            text += f"`{k}` : {v['name']} ({v['days']}d) = ₹{v['price']}\n"
        msg = bot.send_message(chat_id, text, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_price_change)

    elif call.data == "dummy":
        bot.answer_callback_query(call.id, "🚧 Under construction!", show_alert=True)

# --- ADMIN STEP HANDLERS ---
def process_broadcast(message):
    success = 0
    bot.send_message(message.chat.id, "⏳ Broadcasting...")
    for user_id in db["users"]:
        try:
            bot.send_message(user_id, f"📣 **Announcement**\n\n{message.text}", parse_mode="Markdown")
            success += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ Broadcast sent to {success} users.")

def process_support(message):
    db["support_link"] = message.text
    bot.send_message(message.chat.id, f"✅ Support link updated to: {message.text}")

def process_add_admin(message):
    try:
        new_admin = int(message.text)
        db["admins"].add(new_admin)
        bot.send_message(message.chat.id, f"✅ User {new_admin} is now an admin.")
    except:
        bot.send_message(message.chat.id, "❌ Invalid ID. Must be numbers.")

def process_price_change(message):
    try:
        key, new_price = message.text.split()
        if key in db["products"]:
            db["products"][key]["price"] = int(new_price)
            bot.send_message(message.chat.id, f"✅ Price for {key} updated to ₹{new_price}")
        else:
            bot.send_message(message.chat.id, "❌ Invalid Key.")
    except:
        bot.send_message(message.chat.id, "❌ Error. Format must be: `drip_1 150`", parse_mode="Markdown")

print("Bot is running...")
bot.infinity_polling()
