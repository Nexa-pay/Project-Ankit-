import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import os

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
FORCE_JOIN_CHANNEL = os.environ.get("FORCE_JOIN_CHANNEL", "@your_channel_username") 
ADMIN_ID = os.environ.get("ADMIN_ID", "YOUR_ADMIN_ID") # For payment notifications

bot = telebot.TeleBot(BOT_TOKEN)

# In-memory dictionary to track users who have shared contacts (Use a database like SQLite/Postgres for production)
registered_users = set()

# --- UTILITY: FORCE JOIN CHECK ---
def check_force_join(user_id):
    try:
        status = bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False # Assume not joined if there's an error (e.g., bot not admin in channel)

def force_join_prompt(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@', '')}"))
    markup.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_join"))
    bot.send_message(message.chat.id, 
                     f"🛑 **Access Denied**\n\nYou must join our official channel to use this bot.", 
                     reply_markup=markup, parse_mode="Markdown")

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not check_force_join(message.from_user.id):
        force_join_prompt(message)
        return

    if message.from_user.id not in registered_users:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        contact_btn = KeyboardButton("📱 Share My Number", request_contact=True)
        markup.add(contact_btn)
        bot.send_message(message.chat.id, 
                         "👋 **Welcome to PANEL STORE FREE FIRE!**\n\nTo continue and secure your account, please share your phone number by tapping the button below.", 
                         reply_markup=markup, parse_mode="Markdown")
    else:
        main_menu(message.chat.id)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if not check_force_join(message.from_user.id):
        force_join_prompt(message)
        return
        
    registered_users.add(message.from_user.id)
    # Remove the reply keyboard
    remove_markup = telebot.types.ReplyKeyboardRemove()
    msg = bot.send_message(message.chat.id, "✅ Number verified successfully!", reply_markup=remove_markup)
    main_menu(message.chat.id)

def main_menu(chat_id, message_id=None):
    text = (
        "🔥 ━━ **PANEL STORE FREE FIRE** ━━ 🔥\n"
        "*Powered by Nexapayz*\n\n"
        "❓ **Why our store is trusted?**\n"
        "↳ Direct deals with every mod developer\n"
        "↳ Instant delivery after payment\n"
        "↳ **5% discount** on your 2nd purchase\n"
        "↳ Guaranteed discounted prices"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Shop Now", callback_data="shop_menu"))
    markup.row(InlineKeyboardButton("📦 My Orders", callback_data="dummy"), InlineKeyboardButton("👤 Profile", callback_data="dummy"))
    markup.row(InlineKeyboardButton("↗️ Pay Proof", url="https://t.me/your_proof_channel"), InlineKeyboardButton("❓ How to Use", callback_data="dummy"))
    markup.row(InlineKeyboardButton("💬 Support", callback_data="dummy"), InlineKeyboardButton("🎁 Referral", callback_data="dummy"))
    
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# --- CALLBACK QUERY HANDLER ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "check_join":
        if check_force_join(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ Thank you for joining!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ You haven't joined the channel yet!", show_alert=True)

    elif call.data == "shop_menu":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📱 Android", callback_data="shop_android"))
        markup.add(InlineKeyboardButton("🍎 iOS", callback_data="shop_ios"))
        markup.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu"))
        bot.edit_message_text("🔥 **Choose your device category:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "shop_android":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("DRIP CLIENT MOBILE", callback_data="prod_drip"), InlineKeyboardButton("PRIME HOOK MOD", callback_data="dummy"))
        markup.add(InlineKeyboardButton("⬅️ Back to Categories", callback_data="shop_menu"))
        bot.edit_message_text("🛒 **PANEL STORE — 📱 Android**\n\nChoose a product 👇", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "shop_ios":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("IOS - ALPHA PANEL", callback_data="prod_alpha"))
        markup.add(InlineKeyboardButton("⬅️ Back to Categories", callback_data="shop_menu"))
        bot.edit_message_text("🛒 **PANEL STORE — 🍎 iOS**\n\nChoose a product 👇", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "prod_drip":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("1 Day — ₹98", callback_data="checkout_drip_1"))
        markup.add(InlineKeyboardButton("3 Days — ₹190", callback_data="checkout_drip_3"))
        markup.add(InlineKeyboardButton("7 Days — ₹349", callback_data="checkout_drip_7"))
        markup.add(InlineKeyboardButton("30 Days — ₹960", callback_data="checkout_drip_30"))
        markup.add(InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop_android"))
        bot.edit_message_text("🏷 **DRIP CLIENT MOBILE**\n\nChoose a plan 👇", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("checkout_"):
        # Simulated Checkout Screen
        parts = call.data.split("_")
        product = parts[1].upper()
        duration = parts[2]
        price = "98.01" # In a real bot, map these dynamically
        
        text = (
            "🔥 **ORDER CREATED**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🏷 **Product:** {product} CLIENT\n"
            f"⏱ **Duration:** {duration} Days\n"
            f"💰 **Amount:** ₹{price}\n"
            "🔖 **Ref:** DX-0715EBBB\n\n"
            "📲 *Scan the QR to pay (or use UPI ID)*\n"
            f"⚠️ **Pay EXACTLY ₹{price}**\n"
            "⏰ Expires in 5 minutes"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ I Have Paid", callback_data="confirm_payment"))
        markup.add(InlineKeyboardButton("❌ Cancel", callback_data="shop_menu"))
        markup.add(InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop_menu"))
        
        # In a real scenario, you'd send an actual image of a QR code using bot.send_photo
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "confirm_payment":
        bot.answer_callback_query(call.id, "Payment verification sent to admins. Please wait.", show_alert=True)
        # Here you would trigger logic to notify ADMIN_ID

    elif call.data == "main_menu":
        main_menu(call.message.chat.id, call.message.message_id)

    elif call.data == "dummy":
        bot.answer_callback_query(call.id, "🚧 Feature under construction!")

print("Bot is running...")
bot.infinity_polling()
