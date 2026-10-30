import os
import sys
import threading
import re
import shutil
import zipfile
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QCheckBox, QTextEdit, QFileDialog, QFrame, QGridLayout, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QTextCursor, QFont, QColor

def get_desktop_path():
    home = os.path.expanduser("~")
    for p in [os.path.join(home, "OneDrive", "Masaüstü"), os.path.join(home, "OneDrive", "Desktop"), os.path.join(home, "Masaüstü"), os.path.join(home, "Desktop")]:
        if os.path.exists(p): return p
    return os.path.join(home, "Desktop")

class WorkerSignals(QObject):
    log = pyqtSignal(str, str)
    stats = pyqtSignal(dict)
    finished = pyqtSignal()

class NovaExtractorPremium(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NovaTools | Multi-Log Extractor Pro")
        self.resize(1250, 780)
        self.setStyleSheet(self.get_style())
        
        self.lock = threading.Lock()
        self.is_running = False
        self.files_to_scan = []
        
        self.extracted_data = {
            "ulp": set(),
            "admin": set(),
            "cc": set(),
            "tokens": set(),
            "cookies": set()
        }
        self.counts = {"checked": 0, "total": 0, "ulp": 0, "admin": 0, "cc": 0, "tdata": 0, "tokens": 0, "cookies": 0}
        
        self.signals = WorkerSignals()
        self.signals.log.connect(self.append_log)
        self.signals.stats.connect(self.update_stats)
        self.signals.finished.connect(self.on_finished)
        
        self.setup_ui()

    def add_shadow(self, widget, color="#000000", radius=15, offset=(0, 4)):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(radius)
        shadow.setColor(QColor(color))
        shadow.setOffset(offset[0], offset[1])
        widget.setGraphicsEffect(shadow)

    def get_style(self):
        return """
        QMainWindow { background-color: #050505; }
        QFrame#Sidebar { background-color: #0A0A0A; border-right: 1px solid #111111; }
        QLabel#Title { color: #E50914; font-size: 34px; font-weight: 900; font-family: 'Segoe UI Black'; letter-spacing: -1px; }
        QLabel#SubTitle { color: #FFFFFF; font-size: 13px; font-weight: 800; letter-spacing: 2px; }
        QPushButton#LoadBtn { background-color: #0F0F0F; color: #FFFFFF; border: 1px solid #222222; border-radius: 8px; padding: 16px; font-weight: 900; font-size: 13px; letter-spacing: 1px; }
        QPushButton#LoadBtn:hover { border: 1px solid #E50914; color: #E50914; background-color: #1A0505; }
        QPushButton#StartBtn { background-color: #E50914; color: #FFFFFF; border-radius: 8px; padding: 18px; font-weight: 900; font-size: 16px; border: none; letter-spacing: 2px; }
        QPushButton#StartBtn:hover { background-color: #FF1A26; }
        QPushButton#StartBtn:disabled { background-color: #1A1A1A; color: #444444; }
        QCheckBox { color: #B3B3B3; font-weight: 800; font-size: 13px; padding: 8px; }
        QCheckBox::indicator { width: 20px; height: 20px; background-color: #111111; border: 2px solid #222222; border-radius: 4px; }
        QCheckBox::indicator:checked { background-color: #E50914; border: 2px solid #E50914; }
        QFrame#StatCard { background-color: #0A0A0A; border: 1px solid #111111; border-radius: 12px; }
        QLabel#StatTitle { color: #737373; font-weight: 900; font-size: 12px; letter-spacing: 1px; }
        QLabel#StatVal { color: #E50914; font-weight: 900; font-size: 32px; }
        QTextEdit { background-color: transparent; color: #CCCCCC; border: none; font-size: 13px; padding: 10px; }
        QFrame#LogCard { background-color: #0A0A0A; border: 1px solid #111111; border-radius: 12px; }
        """

    def setup_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        ml = QHBoxLayout(cw)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        sb = QFrame(); sb.setObjectName("Sidebar"); sb.setFixedWidth(320)
        self.add_shadow(sb, "#000000", 20, (5, 0))
        sl = QVBoxLayout(sb); sl.setContentsMargins(30, 40, 30, 40)

        sl.addWidget(self.l("NOVATOOLS", "Title"))
        sl.addWidget(self.l("MULTI-EXTRACTOR", "SubTitle"))
        sl.addSpacing(40)

        self.btn_load = QPushButton("LOAD TARGET LOGS"); self.btn_load.setObjectName("LoadBtn")
        self.btn_load.clicked.connect(self.load_folder)
        self.add_shadow(self.btn_load, "#E50914", 10, (0, 0))
        sl.addWidget(self.btn_load)
        
        self.lbl_info = self.l("TARGETS LOADED: 0", "SubTitle"); self.lbl_info.setStyleSheet("color: #737373; font-size: 12px; margin-top: 5px;")
        sl.addWidget(self.lbl_info)
        sl.addSpacing(40)

        lbl_mod = QLabel("EXTRACTION MODULES"); lbl_mod.setStyleSheet("color: #666666; font-weight: 900; font-size: 11px; letter-spacing: 1px;")
        sl.addWidget(lbl_mod)

        self.chk_ulp = QCheckBox("Extract ULP & Admins"); self.chk_ulp.setChecked(True)
        self.chk_cc = QCheckBox("Extract Credit Cards (CC)")
        self.chk_tdata = QCheckBox("Clone Telegram Tdata")
        self.chk_tokens = QCheckBox("Extract Discord Tokens")
        self.chk_cookies = QCheckBox("Extract All Cookies")
        
        sl.addWidget(self.chk_ulp); sl.addWidget(self.chk_cc); sl.addWidget(self.chk_tdata)
        sl.addWidget(self.chk_tokens); sl.addWidget(self.chk_cookies)
        
        sl.addStretch()
        self.btn_start = QPushButton("INITIALIZE ENGINE"); self.btn_start.setObjectName("StartBtn")
        self.btn_start.clicked.connect(self.start_engine)
        self.add_shadow(self.btn_start, "#E50914", 25, (0, 5))
        sl.addWidget(self.btn_start)
        ml.addWidget(sb)

        rp = QWidget()
        rl = QVBoxLayout(rp); rl.setContentsMargins(30, 30, 30, 30); rl.setSpacing(20)
        
        gl = QGridLayout(); gl.setSpacing(20)
        self.s_chk = self.stat_card("FILES SCANNED", "0 / 0", gl, 0, 0)
        self.s_ulp = self.stat_card("ULP EXTRACTED", "0", gl, 0, 1)
        self.s_adm = self.stat_card("ADMIN LOGINS", "0", gl, 0, 2)
        self.s_cc = self.stat_card("CARDS (CC)", "0", gl, 1, 0)
        self.s_tok = self.stat_card("DISCORD TOKENS", "0", gl, 1, 1)
        self.s_tdt = self.stat_card("TDATA CLONED", "0", gl, 1, 2)
        rl.addLayout(gl)

        log_card = QFrame(); log_card.setObjectName("LogCard")
        self.add_shadow(log_card, "#000000", 20, (0, 5))
        log_layout = QVBoxLayout(log_card); log_layout.setContentsMargins(5, 5, 5, 5)
        
        self.console = QTextEdit(); self.console.setReadOnly(True); self.console.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.console)
        rl.addWidget(log_card)
        
        ml.addWidget(rp)

    def l(self, t, o):
        l = QLabel(t); l.setObjectName(o); return l

    def stat_card(self, title, val, layout, r, c):
        f = QFrame(); f.setObjectName("StatCard")
        self.add_shadow(f, "#000000", 15, (0, 5))
        l = QVBoxLayout(f); l.setAlignment(Qt.AlignCenter); l.setContentsMargins(15, 25, 15, 25)
        lt = QLabel(title); lt.setObjectName("StatTitle"); lt.setAlignment(Qt.AlignCenter)
        lv = QLabel(val); lv.setObjectName("StatVal"); lv.setAlignment(Qt.AlignCenter)
        l.addWidget(lt); l.addWidget(lv)
        layout.addWidget(f, r, c)
        return lv

    def append_log(self, msg, col="#B3B3B3"):
        self.console.moveCursor(QTextCursor.End)
        self.console.insertHtml(f'<span style="color: {col};">{msg}</span><br>')
        self.console.moveCursor(QTextCursor.End)

    def update_stats(self, c):
        self.s_chk.setText(f"{c['checked']} / {c['total']}")
        self.s_ulp.setText(str(c['ulp']))
        self.s_adm.setText(str(c['admin']))
        self.s_cc.setText(str(c['cc']))
        self.s_tok.setText(str(c['tokens']))
        self.s_tdt.setText(str(c['tdata']))

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Logs Directory")
        if folder:
            threading.Thread(target=self._scan_files, args=(folder,), daemon=True).start()

    def _scan_files(self, folder):
        files = []
        for r, d, f in os.walk(folder):
            if self.chk_tdata.isChecked() and 'tdata' in r.lower():
                if os.path.basename(r).lower() == 'tdata': files.append(("TDATA", r))
                continue
            for file in f:
                ext = file.lower()
                if ext.endswith(('.txt', '.log', '.ldb', '.sqlite', '.zip')):
                    files.append(("FILE", os.path.join(r, file)))
                    
        self.files_to_scan = files
        self.counts["total"] = len(files)
        self.signals.stats.emit(self.counts)
        self.lbl_info.setText(f"TARGETS LOADED: {len(files)}")
        self.signals.log.emit(f"[+] Successfully hooked {len(files)} target files into memory.", "#E50914")

    def start_engine(self):
        if not self.files_to_scan or self.is_running: return
        self.is_running = True
        self.btn_start.setEnabled(False)
        self.console.clear()
        
        for k in self.extracted_data: self.extracted_data[k].clear()
        for k in self.counts: 
            if k != "total": self.counts[k] = 0
            
        self.signals.stats.emit(self.counts)
        self.signals.log.emit(">> NOVA MULTI-CORE ENGINE ACTIVATED <<", "#FFFFFF")
        
        self.out_dir = os.path.join(get_desktop_path(), "Nova_Extracted_Logs")
        os.makedirs(self.out_dir, exist_ok=True)
        if self.chk_tdata.isChecked(): os.makedirs(os.path.join(self.out_dir, "Tdatas"), exist_ok=True)
        
        self.active_workers = 15
        for _ in range(15):
            threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        while self.is_running:
            item = None
            with self.lock:
                if self.files_to_scan: item = self.files_to_scan.pop()
                else: break

            if not item: break
            t, path = item

            if t == "TDATA":
                try:
                    with self.lock:
                        self.counts["tdata"] += 1
                        idx = self.counts["tdata"]
                    shutil.copytree(path, os.path.join(self.out_dir, "Tdatas", f"tdata_{idx}"))
                except: pass
                finally:
                    with self.lock: self.counts["checked"] += 1; self.signals.stats.emit(self.counts)
                continue

            try:
                if path.lower().endswith('.zip'):
                    with zipfile.ZipFile(path, 'r') as z:
                        for zn in z.namelist():
                            if zn.lower().endswith(('.txt', '.log')):
                                try:
                                    c = z.read(zn).decode('utf-8', errors='ignore')
                                    self.process_text(c, zn.lower())
                                except: pass
                else:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        c = f.read()
                    self.process_text(c, os.path.basename(path).lower())
            except: pass
            finally:
                with self.lock:
                    self.counts["checked"] += 1
                    if self.counts["checked"] % 50 == 0: self.signals.stats.emit(self.counts)

        with self.lock:
            self.active_workers -= 1
            if self.active_workers == 0:
                self.save_all()
                self.signals.finished.emit()

    def process_text(self, text, fname):
        if self.chk_ulp.isChecked() and ('pass' in fname or 'log' in fname):
            blocks = re.split(r'\n\s*\n', text)
            for b in blocks:
                h = re.search(r'(?:Host|URL|Website):\s*(.+)', b, re.IGNORECASE)
                l = re.search(r'(?:Login|Username|User):\s*(.+)', b, re.IGNORECASE)
                p = re.search(r'(?:Password|Pass):\s*(.+)', b, re.IGNORECASE)
                if h and l and p:
                    u, log, pw = h.group(1).strip(), l.group(1).strip(), p.group(1).strip()
                    if log and pw and u and 'http' in u:
                        line = f"{u}:{log}:{pw}"
                        with self.lock:
                            if line not in self.extracted_data["ulp"]:
                                self.extracted_data["ulp"].add(line)
                                self.counts["ulp"] += 1
                                if any(x in u.lower() for x in ['admin', 'panel', 'dashboard', 'login']):
                                    self.extracted_data["admin"].add(line)
                                    self.counts["admin"] += 1

        if self.chk_cc.isChecked() and ('card' in fname or 'cc' in fname or 'auto' in fname):
            for m in re.finditer(r'(\d{13,19})[^\d]{1,15}(\d{1,2})[^\d]{1,10}(\d{2,4})[^\d]{1,15}(\d{3,4})', text):
                cc, mm, yy, cvv = m.group(1), m.group(2).zfill(2), m.group(3), m.group(4)
                if 1 <= int(mm) <= 12 and 2 <= len(yy) <= 4:
                    if len(yy) == 2: yy = f"20{yy}"
                    line = f"{cc}|{mm}|{yy}|{cvv}"
                    with self.lock:
                        if line not in self.extracted_data["cc"]:
                            self.extracted_data["cc"].add(line)
                            self.counts["cc"] += 1

        if self.chk_tokens.isChecked() and ('token' in fname or 'local' in fname or fname.endswith(('.ldb', '.log'))):
            for tk in re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}|mfa\.[\w-]{84}', text):
                with self.lock:
                    if tk not in self.extracted_data["tokens"]:
                        self.extracted_data["tokens"].add(tk)
                        self.counts["tokens"] += 1

        if self.chk_cookies.isChecked() and 'cookie' in fname:
            for l in text.splitlines():
                if 'TRUE' in l or 'FALSE' in l:
                    with self.lock:
                        self.extracted_data["cookies"].add(l)

    def save_all(self):
        self.signals.log.emit("[!] Packaging unique extracted data...", "#737373")
        if self.extracted_data["ulp"]:
            with open(os.path.join(self.out_dir, "Nova_ULP_All.txt"), 'w', encoding='utf-8') as f:
                f.write("\n".join(self.extracted_data["ulp"]))
        if self.extracted_data["admin"]:
            with open(os.path.join(self.out_dir, "Nova_ULP_Admins.txt"), 'w', encoding='utf-8') as f:
                f.write("\n".join(self.extracted_data["admin"]))
        if self.extracted_data["cc"]:
            with open(os.path.join(self.out_dir, "Nova_Cards_CC.txt"), 'w', encoding='utf-8') as f:
                f.write("\n".join(self.extracted_data["cc"]))
        if self.extracted_data["tokens"]:
            with open(os.path.join(self.out_dir, "Nova_Discord_Tokens.txt"), 'w', encoding='utf-8') as f:
                f.write("\n".join(self.extracted_data["tokens"]))
        if self.extracted_data["cookies"]:
            with open(os.path.join(self.out_dir, "Nova_Cookies_Raw.txt"), 'w', encoding='utf-8') as f:
                f.write("\n".join(self.extracted_data["cookies"]))

    def on_finished(self):
        self.is_running = False
        self.btn_start.setEnabled(True)
        self.signals.stats.emit(self.counts)
        self.signals.log.emit("[+] EXTRACTION COMPLETE! Stored in Desktop/Nova_Extracted_Logs", "#E50914")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = NovaExtractorPremium()
    w.show()
    sys.exit(app.exec_())