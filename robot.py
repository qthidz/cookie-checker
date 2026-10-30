import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# ---------------- CONFIGURATION ----------------
BOT_TOKEN = "8994246539:AAGiZ_Z8tGiAIOB19nw49W80oehq_RO_syk"  
BOT_PASSWORD = "robot"
CHANNEL_USERNAME = "@SellingTgAccountsChannel"
# -----------------------------------------------

authenticated_users = set()
active_groups = {}
user_selected_gc = {}

POWERED_BY = "\n\n⚡ *Powered by @AlphaNoirr*"

async def is_user_subscribed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['left', 'kicked']:
            return False
        return True
    except BadRequest:
        return False

# Group tracking function: Jab bot kisi GC mein add hoga, toh ye chupchaap data save karega, bina koi message bheje
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    # Agar bot ko group me add kiya gaya hai ya group me koi naya message aaya hai
    if chat.type in ["group", "supergroup"]:
        active_groups[chat.id] = chat.title

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Strict Private Chat check: Agar command group me chalayi jaye toh bot ignore karega
    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id
    
    # Check Subscription
    if not await is_user_subscribed(context, user_id):
        keyboard = [[InlineKeyboardButton("📢 Join Channel Now", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")]]
        await update.message.reply_text(
            f"❌ *ACCESS DENIED*\n\nPehle hamare channel {CHANNEL_USERNAME} ko join karein, tabhi ye bot kaam karega!"
            f"{POWERED_BY}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if user_id in authenticated_users:
        await show_main_menu(update, context)
    else:
        await update.message.reply_text(
            "🔒 *🚨 ACCESS SYSTEM LOCKED 🚨*\n\n"
            "This is a strictly restricted Alpha-Level Control Bot.\n"
            "⚠️ Enter the Master Password to unlock system capabilities:"
            f"{POWERED_BY}",
            parse_mode="Markdown"
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_to_gc_url = f"https://t.me/{context.bot.username}?startgroup=true"
    keyboard = [
        [InlineKeyboardButton("➕ 🌀 Add Bot to GC 🌀 ➕", url=add_to_gc_url)],
        [InlineKeyboardButton("👥 🔮 Show All GCs 🔮 👥", callback_data="show_gcs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "👑 *⚡ ALPHA CONTROL INTERFACE UNLOCKED ⚡* 👑\n\n"
        "Welcome back, Boss! All systems are operational.\n"
        "Select an action from the control panel below 👇"
        f"{POWERED_BY}"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not await is_user_subscribed(context, user_id):
        await query.message.reply_text(f"❌ Join {CHANNEL_USERNAME} first! {POWERED_BY}")
        return

    if user_id not in authenticated_users:
        return

    if query.data == "show_gcs":
        if not active_groups:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]
            await query.message.edit_text(f"❌ No active chats found! {POWERED_BY}", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        keyboard = [[InlineKeyboardButton(f"🌐 ➡️ {gc_name}", callback_data=f"select_gc_{gc_id}")] for gc_id, gc_name in active_groups.items()]
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_main")])
        await query.message.edit_text(f"👥 *SELECT TARGET GROUP* 👥{POWERED_BY}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif query.data == "back_main":
        await show_main_menu(update, context)
    elif query.data.startswith("select_gc_"):
        selected_id = int(query.data.replace("select_gc_", ""))
        user_selected_gc[user_id] = selected_id
        await query.message.edit_text(f"🎯 *TARGET LOCKED* 🧬\nAb aap messages bhejein.{POWERED_BY}", parse_mode="Markdown")

async def handle_private_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await is_user_subscribed(context, user_id):
        await update.message.reply_text(f"❌ Pehle {CHANNEL_USERNAME} join karo!{POWERED_BY}", parse_mode="Markdown")
        return

    if user_id not in authenticated_users:
        if update.message.text == BOT_PASSWORD:
            authenticated_users.add(user_id)
            await update.message.reply_text(f"🔓 *UNLOCKED!* {POWERED_BY}", parse_mode="Markdown")
            await show_main_menu(update, context)
        else:
            await update.message.reply_text(f"❌ *INVALID PASSWORD* {POWERED_BY}", parse_mode="Markdown")
        return

    target_id = user_selected_gc.get(user_id)
    if not target_id:
        await update.message.reply_text(f"⚠️ *No GC selected!* {POWERED_BY}", parse_mode="Markdown")
        return
    
    try:
        if update.message.text: 
            await context.bot.send_message(chat_id=target_id, text=update.message.text)
        await update.message.reply_text(f"✅ *SUCCESS!* {POWERED_BY}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}{POWERED_BY}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 1. Group Tracking Handler: Yeh background mein chupchaap groups ko save karega jab bot add hoga
    application.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))
    
    # 2. Main handlers (Sirf Private Chats ke liye filters lagaye hain)
    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(handle_callbacks))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, handle_private_messages))
    
    application.run_polling()

if __name__ == '__main__':
    main()
    