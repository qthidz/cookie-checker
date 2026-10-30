import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    print('[-] requests is required. Run: pip install requests')
    raise SystemExit

try:
    from colorama import Fore, Style, init
    init(autoreset=False)
except ImportError:
    class _NoColor:
        def __getattr__(self, name):
            return ''
    Fore = _NoColor()
    Style = _NoColor()

from tkinter import filedialog

DEBUG = False
RESULT_TAG = 'plutobearz'
THREADS = 5
AUTO_JOIN = False
INVITE_CODE = ''

GREEN = Fore.GREEN
RED = Fore.RED
YELLOW = Fore.YELLOW
CYAN = Fore.CYAN
RESET = Style.RESET_ALL

TOKEN_RE = re.compile(r'[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{20,}')


def banner():
    print()
    print(GREEN + '+------------------------------------------+' + RESET)
    print(GREEN + '|       Plutos Discord Token Checker       |' + RESET)
    print(GREEN + '+------------------------------------------+' + RESET)


def validate_token(token):
    headers = {
        'Authorization': token,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0'
    }
    try:
        r = requests.get('https://discord.com/api/v10/users/@me', headers=headers, timeout=10)
        if r.status_code == 200:
            return True, r.json()
        elif r.status_code == 401:
            return False, 'invalid'
        elif r.status_code == 403:
            return False, 'forbidden'
        elif r.status_code == 429:
            return False, 'rate_limited'
        else:
            return False, 'status_%s' % r.status_code
    except requests.exceptions.Timeout:
        return False, 'timeout'
    except requests.exceptions.RequestException as e:
        if DEBUG:
            print(RED + '[DEBUG] %s' % e + RESET)
        return False, 'error'


def auto_join(token, invite_code):
    headers = {
        'Authorization': token,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0',
        'Content-Type': 'application/json'
    }
    try:
        r = requests.post('https://discord.com/api/v9/invites/%s' % invite_code, headers=headers, timeout=10, json={})
        if r.status_code in (200, 204):
            return True
        if DEBUG:
            print(RED + '[DEBUG] Join failed %s -> %s: %s' % (token[:32], r.status_code, r.text[:120]) + RESET)
        return False
    except requests.exceptions.RequestException as e:
        if DEBUG:
            print(RED + '[DEBUG] Join error %s -> %s' % (token[:32], e) + RESET)
        return False


def _write_results(valid_items, invalid_items):
    os.makedirs('./res', exist_ok=True)
    if valid_items:
        filename = 'res/x%s discord tokens @%s.txt' % (len(valid_items), RESULT_TAG)
        with open(filename, 'w', encoding='utf-8') as f:
            for token, data in valid_items:
                uid = data.get('id', 'unknown')
                user = data.get('username', 'unknown')
                f.write('%s|%s|%s\n' % (token, uid, user))
    if invalid_items:
        filename = 'res/x%s invalid discord tokens @%s.txt' % (len(invalid_items), RESULT_TAG)
        with open(filename, 'w', encoding='utf-8') as f:
            for token, status in invalid_items:
                f.write('%s|%s\n' % (token, status))


def _update_status(valid, invalid, remaining, checked):
    text = 'Valid: %s | Invalid: %s | Remaining: %s | Checked: %s' % (valid, invalid, remaining, checked)
    text = text.ljust(80)
    print(YELLOW + text + RESET, end='\r', flush=True)


def check_single():
    raw = input('Token: ').strip()
    matches = TOKEN_RE.findall(raw)
    token = matches[0] if matches else raw.split('|', 1)[0].strip()
    if not token:
        print(RED + 'No token entered' + RESET)
        return
    if DEBUG:
        print(YELLOW + '[DEBUG] Checking %s...' % token[:32] + RESET)
    valid, data = validate_token(token)
    if valid:
        if AUTO_JOIN and INVITE_CODE:
            joined = auto_join(token, INVITE_CODE)
            join_msg = ' [JOINED]' if joined else ' [JOIN FAILED]'
        else:
            join_msg = ''
        valid_items = [(token, data)]
        invalid_items = []
        print(GREEN + '[VALID] %s | %s (%s)%s' % (token[:32], data.get('username', 'unknown'), data.get('id', 'unknown'), join_msg) + RESET)
    else:
        valid_items = []
        invalid_items = [(token, data)]
        print(RED + '[INVALID] %s | %s' % (token[:32], data) + RESET)
    _write_results(valid_items, invalid_items)


def check_file():
    file_path = filedialog.askopenfilename(
        title='Select token file',
        filetypes=[('Text files', '*.txt'), ('All files', '*.*')]
    )
    if not file_path:
        print('No file selected')
        return
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tokens = []
            for l in f:
                tokens.extend(TOKEN_RE.findall(l))
    except Exception as e:
        print(RED + 'Could not read file: %s' % e + RESET)
        return
    tokens = list(dict.fromkeys(tokens))
    total = len(tokens)
    if total == 0:
        print(YELLOW + 'No tokens in file' + RESET)
        return
    valid_items = []
    invalid_items = []
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(validate_token, token): token for token in tokens}
        for future in as_completed(futures):
            token = futures[future]
            v, data = future.result()
            if v:
                valid_items.append((token, data))
                if AUTO_JOIN and INVITE_CODE:
                    if auto_join(token, INVITE_CODE):
                        print(CYAN + '[JOINED] %s' % token[:32] + RESET)
            else:
                invalid_items.append((token, data))
            checked = len(valid_items) + len(invalid_items)
            if DEBUG:
                print(YELLOW + '[DEBUG] [%s/%s] %s' % (checked, total, token[:32]) + RESET)
            _update_status(len(valid_items), len(invalid_items), total - checked, checked)
    _write_results(valid_items, invalid_items)
    print()
    print(GREEN + 'Done. Valid: %s | Invalid: %s | Total: %s' % (len(valid_items), len(invalid_items), total) + RESET)


def settings_menu():
    global DEBUG, RESULT_TAG, THREADS, AUTO_JOIN, INVITE_CODE
    while True:
        banner()
        print(GREEN + '[1] Toggle debug (currently %s)' % ('ON' if DEBUG else 'OFF') + RESET)
        print(GREEN + '[2] Change result tag (currently @%s)' % RESULT_TAG + RESET)
        print(GREEN + '[3] Change threads (currently %s)' % THREADS + RESET)
        print(GREEN + '[4] Toggle auto-join (currently %s)' % ('ON' if AUTO_JOIN else 'OFF') + RESET)
        print(GREEN + '[5] Set invite code (currently %s)' % (INVITE_CODE if INVITE_CODE else 'None') + RESET)
        print(GREEN + '[6] Back' + RESET)
        choice = input('Choose: ').strip()
        if choice == '1':
            DEBUG = not DEBUG
            print(YELLOW + 'Debug set to %s' % ('ON' if DEBUG else 'OFF') + RESET)
        elif choice == '2':
            tag = input('Enter new result tag (without @): ').strip()
            if tag:
                RESULT_TAG = tag
            print(YELLOW + 'Result tag set to @%s' % RESULT_TAG + RESET)
        elif choice == '3':
            try:
                new_threads = int(input('Enter number of threads: ').strip())
                if new_threads > 0:
                    THREADS = new_threads
            except ValueError:
                pass
            print(YELLOW + 'Threads set to %s' % THREADS + RESET)
        elif choice == '4':
            AUTO_JOIN = not AUTO_JOIN
            print(YELLOW + 'Auto-join set to %s' % ('ON' if AUTO_JOIN else 'OFF') + RESET)
        elif choice == '5':
            code = input('Enter Discord invite code or link: ').strip()
            if code:
                code = code.split('?')[0].rstrip('/')
                if '/' in code:
                    code = code.rsplit('/', 1)[-1]
                INVITE_CODE = code
            print(YELLOW + 'Invite code set to %s' % (INVITE_CODE if INVITE_CODE else 'None') + RESET)
        elif choice == '6':
            break
        else:
            print(RED + 'Invalid option' + RESET)


def checker_menu():
    while True:
        banner()
        print(GREEN + '[1] Single Check' + RESET)
        print(GREEN + '[2] Check from text file' + RESET)
        print(GREEN + '[3] Go back' + RESET)
        choice = input('Choose: ').strip()
        if choice == '1':
            check_single()
        elif choice == '2':
            check_file()
        elif choice == '3':
            break
        else:
            print(RED + 'Invalid option' + RESET)


def main_menu():
    while True:
        banner()
        print(GREEN + '[1] Checker' + RESET)
        print(GREEN + '[2] Settings' + RESET)
        print(GREEN + '[3] Exit' + RESET)
        choice = input('Choose an option: ').strip()
        if choice == '1':
            checker_menu()
        elif choice == '2':
            settings_menu()
        elif choice == '3':
            print(GREEN + 'Exiting...' + RESET)
            break
        else:
            print(RED + 'Invalid option' + RESET)


def main():
    main_menu()


if __name__ == '__main__':
    main()
