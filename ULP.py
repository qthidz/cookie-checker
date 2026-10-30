#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import re
import sys
import time
import zipfile
import collections
import statistics
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.text import Text
from rich import box
from rich.align import Align

console = Console()
VERSION = "2.0"
AUTHOR = "@xghost123"
CHANNEL = "https://t.me/wstoren"

# ============================================================
#                      الإعدادات الأساسية
# ============================================================
DELIMITER_PATTERN = re.compile(r'[:;|]')
EMAIL_PATTERN = re.compile(r'^[\w\.-]+@([\w\.-]+\.\w+)$')
NUMERIC_PATTERN = re.compile(r'^\d+$')
ALPHA_PATTERN = re.compile(r'^[a-zA-Z]+$')
BAD_PHRASES = [
    'unknown version', 'notemmysbirthday', '██████', '██', '<br>', 'null',
    'undefined', 'password', 'user:pass', 'example', 'sample', 'test'
]
BAD_PHRASE_REGEX = re.compile('|'.join(map(re.escape, BAD_PHRASES)), re.IGNORECASE)

# ============================================================
#                      أنماط فرز الدول (من netflix_hunter)
# ============================================================
COUNTRY_NAME_MAP = {
    'EG': 'Egypt', 'US': 'United States', 'GB': 'United Kingdom', 'DE': 'Germany',
    'FR': 'France', 'IT': 'Italy', 'ES': 'Spain', 'SA': 'Saudi Arabia', 'AE': 'UAE',
    'QA': 'Qatar', 'KW': 'Kuwait', 'BH': 'Bahrain', 'OM': 'Oman', 'JO': 'Jordan',
    'TR': 'Turkey', 'IN': 'India', 'PK': 'Pakistan', 'BD': 'Bangladesh', 'MY': 'Malaysia',
    'SG': 'Singapore', 'ID': 'Indonesia', 'PH': 'Philippines', 'TH': 'Thailand',
    'VN': 'Vietnam', 'CN': 'China', 'JP': 'Japan', 'KR': 'South Korea', 'RU': 'Russia',
    'UA': 'Ukraine', 'PL': 'Poland', 'RO': 'Romania', 'NL': 'Netherlands', 'BE': 'Belgium',
    'CH': 'Switzerland', 'AT': 'Austria', 'SE': 'Sweden', 'NO': 'Norway', 'DK': 'Denmark',
    'FI': 'Finland', 'IE': 'Ireland', 'NZ': 'New Zealand', 'AU': 'Australia', 'ZA': 'South Africa',
    'BR': 'Brazil', 'MX': 'Mexico', 'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia',
    'PE': 'Peru', 'VE': 'Venezuela', 'CA': 'Canada'
}
ISO_COUNTRIES = {c.lower() for c in COUNTRY_NAME_MAP}
COUNTRY_PATTERNS = [
    re.compile(r"netflix\.com/([a-z]{2})(?:[-/]|$)"),
    re.compile(r"netflix\.com:([a-z]{2})")
]

def extract_country_from_line(line):
    l = line.lower()
    for pattern in COUNTRY_PATTERNS:
        m = pattern.search(l)
        if m and m.group(1) in ISO_COUNTRIES:
            return m.group(1)
    return None

# ============================================================
#                      دوال مساعدة
# ============================================================
def sizeof_fmt(num, suffix="B"):
    for unit in ['', 'K', 'M', 'G', 'T']:
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} P{suffix}"

def format_time(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"

def is_bad_combo(user, pw):
    if len(user) < 3 or len(pw) < 2 or len(user) > 100:
        return True
    if BAD_PHRASE_REGEX.search(user) or BAD_PHRASE_REGEX.search(pw):
        return True
    return False

def analyze_password(pw):
    if NUMERIC_PATTERN.match(pw):
        return 'numeric'
    if ALPHA_PATTERN.match(pw):
        return 'alpha'
    return 'mixed'

def parse_line_smart(line):
    parts = DELIMITER_PATTERN.split(line.strip())
    if len(parts) == 2:
        return parts[0], parts[1]
    elif len(parts) > 2:
        return parts[-2], parts[-1]
    return None, None

def get_all_txt_files(path):
    if os.path.isfile(path):
        return [path]
    file_list = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".txt") and not file.startswith('.'):
                file_list.append(os.path.join(root, file))
    return file_list

# ============================================================
#                      دوال تلغرام
# ============================================================
def send_telegram_document(bot_token, chat_id, file_path, caption):
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}
            resp = requests.post(url, files=files, data=data, timeout=60)
            return resp.status_code == 200
    except Exception as e:
        console.print(f"[red]Telegram upload error: {e}[/red]")
        return False

def send_telegram_message(bot_token, chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
        resp = requests.post(url, data=data, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        console.print(f"[red]Telegram message error: {e}[/red]")
        return False

# ============================================================
#                      المعالجة الأساسية
# ============================================================
def process_files(file_list, keyword, domain_filter):
    email_pass_set = set()
    user_pass_set = set()
    all_valid_set = set()
    country_combos = collections.defaultdict(set)
    pass_stats = {'numeric': 0, 'alpha': 0, 'mixed': 0, 'lengths': []}
    domain_counter = collections.Counter()
    
    stats = {
        'total_lines': 0, 'valid': 0, 'duplicates': 0, 'bad': 0,
        'filtered': 0, 'email_type': 0, 'user_type': 0
    }
    
    for file_path in file_list:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    raw = line.strip()
                    stats['total_lines'] += 1
                    if not raw or not DELIMITER_PATTERN.search(raw):
                        stats['bad'] += 1
                        continue
                    
                    if keyword and keyword.lower() not in raw.lower():
                        stats['filtered'] += 1
                        continue
                    if domain_filter and domain_filter.lower() not in raw.lower():
                        stats['filtered'] += 1
                        continue
                    
                    user, pw = parse_line_smart(raw)
                    if not user or not pw or is_bad_combo(user, pw):
                        stats['bad'] += 1
                        continue
                    
                    combo = f"{user}:{pw}"
                    if combo in all_valid_set:
                        stats['duplicates'] += 1
                        continue
                    
                    all_valid_set.add(combo)
                    stats['valid'] += 1
                    
                    ptype = analyze_password(pw)
                    pass_stats[ptype] += 1
                    pass_stats['lengths'].append(len(pw))
                    
                    if '@' in user:
                        stats['email_type'] += 1
                        email_pass_set.add(combo)
                        match = EMAIL_PATTERN.match(user)
                        if match:
                            domain = match.group(1).lower()
                            domain_counter[domain] += 1
                    else:
                        stats['user_type'] += 1
                        user_pass_set.add(combo)
                    
                    cc = extract_country_from_line(raw)
                    if cc:
                        country_combos[cc].add(combo)
        except Exception as e:
            console.print(f"[red]Error reading {file_path}: {e}[/red]")
    
    return {
        'stats': stats,
        'email_pass': email_pass_set,
        'user_pass': user_pass_set,
        'all_valid': all_valid_set,
        'country_combos': country_combos,
        'domain_counter': domain_counter,
        'pass_stats': pass_stats
    }

def save_results(data, keyword, results_dir):
    os.makedirs(results_dir, exist_ok=True)
    
    all_file = os.path.join(results_dir, f"{keyword}_all.txt")
    email_file = os.path.join(results_dir, f"{keyword}_email_pass.txt")
    user_file = os.path.join(results_dir, f"{keyword}_user_pass.txt")
    
    with open(all_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sorted(data['all_valid'])))
    with open(email_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sorted(data['email_pass'])))
    with open(user_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sorted(data['user_pass'])))
    
    created_files = [all_file, email_file, user_file]
    
    if data['country_combos']:
        countries_dir = os.path.join(results_dir, "Countries")
        os.makedirs(countries_dir, exist_ok=True)
        for cc, combos in data['country_combos'].items():
            country_name = COUNTRY_NAME_MAP.get(cc.upper(), cc.upper())
            country_dir = os.path.join(countries_dir, country_name)
            os.makedirs(country_dir, exist_ok=True)
            out_file = os.path.join(country_dir, f"{country_name}_hits.txt")
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(sorted(combos)))
            created_files.append(out_file)
    
    return created_files

def create_zip(folder_path, zip_name):
    zip_path = os.path.join(os.path.dirname(folder_path), zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, os.path.dirname(folder_path))
                zipf.write(full_path, arcname)
    return zip_path

def build_report(data, keyword, elapsed, files_count):
    stats = data['stats']
    total_pass = stats['valid'] if stats['valid'] > 0 else 1
    pass_stats = data['pass_stats']
    avg_len = int(statistics.mean(pass_stats['lengths'])) if pass_stats['lengths'] else 0
    
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║               ✨ MURPHY ULP PROCESSOR REPORT ✨              ║
╚══════════════════════════════════════════════════════════════╝

🔍 <b>Keyword:</b> <code>{keyword}</code>

┌──────────────────────────────────────────────────────────────┐
│ 📊 <b>PERFORMANCE METRICS</b>                                  │
├──────────────────────────────────────────────────────────────┤
│ • Total lines processed: <b>{stats['total_lines']:,}</b>                       │
│ • Valid combos: <b>{stats['valid']:,}</b> ✅                                  │
│ • Duplicates skipped: <b>{stats['duplicates']:,}</b> 🔄                        │
│ • Bad combos: <b>{stats['bad']:,}</b> ❌                                     │
│ • Filtered out: <b>{stats['filtered']:,}</b> 🚫                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 📧 <b>EXTRACTION TYPES</b>                                     │
├──────────────────────────────────────────────────────────────┤
│ • Email:pass found: <b>{stats['email_type']:,}</b> 📧                         │
│ • User:pass found: <b>{stats['user_type']:,}</b> 👤                          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ ⏱️ <b>TIME INFORMATION</b>                                     │
├──────────────────────────────────────────────────────────────┤
│ • Processing time: <b>{format_time(elapsed)}</b> ⏰                          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 🔐 <b>PASSWORD ANALYSIS</b>                                    │
├──────────────────────────────────────────────────────────────┤
│ • Numeric only: <b>{pass_stats['numeric']:,}</b> ({pass_stats['numeric']/total_pass*100:.1f}%) 🔢 │
│ • Alpha only: <b>{pass_stats['alpha']:,}</b> ({pass_stats['alpha']/total_pass*100:.1f}%) 🔤    │
│ • Mixed (strong): <b>{pass_stats['mixed']:,}</b> ({pass_stats['mixed']/total_pass*100:.1f}%) 💪 │
│ • Average length: <b>{avg_len}</b> 📏                                        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 🌐 <b>COUNTRIES DETECTED</b> <b>({len(data['country_combos'])}):</b>                        │
"""
    for cc, combos in sorted(data['country_combos'].items(), key=lambda x: -len(x[1])):
        country_name = COUNTRY_NAME_MAP.get(cc.upper(), cc.upper())
        report += f"│ • <b>{country_name} ({cc.upper()}):</b> {len(combos):,} combos{' ' * (30 - len(str(len(combos))))}│\n"
    
    report += f"""
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 📁 <b>OUTPUT FILES</b> <b>({files_count} files):</b>                            │
├──────────────────────────────────────────────────────────────┤
│ • {keyword}_all.txt                                            │
│ • {keyword}_email_pass.txt                                     │
│ • {keyword}_user_pass.txt                                      │
│ • Countries/ folder                                            │
└──────────────────────────────────────────────────────────────┘

╔══════════════════════════════════════════════════════════════╗
║                    👨‍💻 DEVELOPER INFO                       ║
╠══════════════════════════════════════════════════════════════╣
║  Developer: <a href='https://t.me/xghost123'>@xghost123</a>                                      ║
║  Channel:   <a href='{CHANNEL}'>Join Channel</a>                                       ║
║  Chat:      <a href='{CHAT}'>Join Chat</a>                                          ║
╚══════════════════════════════════════════════════════════════╝

<i>✨ Report generated by Murphy ULP Processor v{VERSION} ✨</i>
"""
    return report

# ============================================================
#                      الواجهة الرئيسية
# ============================================================
def print_logo():
    ascii_art = r"""
  ███╗   ██╗███████╗████████╗███████╗██╗     ██╗██╗  ██╗██╗  ██╗██╗   ██╗███╗   ██╗████████╗███████╗██████╗ 
  ████╗  ██║██╔════╝╚══██╔══╝██╔════╝██║     ██║╚██╗██╔╝██║  ██║██║   ██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗
  ██╔██╗ ██║█████╗     ██║   █████╗  ██║     ██║ ╚███╔╝ ███████║██║   ██║██╔██╗ ██║   ██║   █████╗  ██████╔╝
  ██║╚██╗██║██╔══╝     ██║   ██╔══╝  ██║     ██║ ██╔██╗ ██╔══██║██║   ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗
  ██║ ╚████║███████╗   ██║   ██║     ███████╗██║██╔╝ ██╗██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗██║  ██║
  ╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝     ╚══════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
    """
    # Creating a cleaner panel with better spacing
    logo_text = Text(ascii_art, justify="center", style="bold cyan")
    panel = Panel(logo_text, border_style="bright_blue", padding=(1, 2))
    console.print(panel)
    
    # Title with better formatting
    title = Text("⚡ MURPHY ULP PROCESSOR v2.0 ⚡", style="bold magenta")
    console.print(Align.center(title))
    
    # Subtitle with developer info
    dev_text = Text(f"Developer: {AUTHOR} | Channel: {CHANNEL} | Chat: {CHAT}", style="dim cyan")
    console.print(Align.center(dev_text))
    console.print()

def select_input_source():
    console.print(Panel.fit("[bold cyan]📂 SELECT INPUT SOURCE[/bold cyan]", border_style="cyan", padding=(0, 2)))
    current_dir = os.getcwd()
    txt_files = [f for f in os.listdir(current_dir) if f.endswith('.txt') and os.path.isfile(f)]
    
    if txt_files:
        table = Table(box=box.ROUNDED, border_style="blue", title="[bold]Available Text Files[/bold]")
        table.add_column("#", style="cyan", width=4)
        table.add_column("File Name", style="white")
        table.add_column("Size", style="dim")
        for i, name in enumerate(txt_files, 1):
            size = sizeof_fmt(os.path.getsize(name))
            table.add_row(f"[cyan]{i:02d}[/cyan]", name, f"[dim]{size}[/dim]")
        console.print(table)
    else:
        console.print("[dim]⚠️ No text files found in current directory.[/dim]")
    
    console.print("\n[bold yellow]💡 Enter number for file or path for Batch Mode[/bold yellow]")
    while True:
        choice = console.input("[bold green]➜[/bold green] [cyan]INPUT >[/cyan] ").strip().strip('"\'')
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(txt_files):
                return [txt_files[idx-1]], False
        if os.path.exists(choice):
            if os.path.isfile(choice):
                return [choice], False
            elif os.path.isdir(choice):
                files = get_all_txt_files(choice)
                if files:
                    console.print(f"[green]✓ Found {len(files)} text files in directory[/green]")
                    return files, True
                else:
                    console.print("[red]❌ No text files found in folder.[/red]")
                    continue
        console.print("[red]❌ Invalid input. Please try again.[/red]")

def main():
    console.clear()
    print_logo()
    
    file_list, is_batch = select_input_source()
    if not file_list:
        return
    
    keyword = console.input("\n[bold cyan]🔑 Enter keyword (for filtering & naming): [/bold cyan]").strip()
    if not keyword:
        console.print("[red]❌ Keyword required![/red]")
        return
    
    domain_filter = console.input("[bold cyan]🌐 Optional domain filter (press Enter to skip): [/bold cyan]").strip()
    
    console.print("\n[bold yellow]⚙️ Telegram Configuration (optional)[/bold yellow]")
    console.print("[dim]💡 Get your bot token from @BotFather and chat ID from @userinfobot[/dim]")
    bot_token = console.input("[bold cyan]🤖 Bot Token: [/bold cyan]").strip()
    chat_id = console.input("[bold cyan]💬 Chat ID: [/bold cyan]").strip()
    
    results_dir = os.path.join(os.getcwd(), f"{keyword}_results")
    
    start_time = time.time()
    with console.status("[bold green]⚙️ Processing files...[/bold green]"):
        data = process_files(file_list, keyword, domain_filter)
    elapsed = time.time() - start_time
    
    created_files = save_results(data, keyword, results_dir)
    console.print(f"[green]✅ Results saved in: {results_dir}[/green]")
    
    zip_path = create_zip(results_dir, f"{keyword}_results.zip")
    console.print(f"[green]✅ Results zipped: {zip_path}[/green]")
    
    stats = data['stats']
    total_valid = stats['valid']
    pass_stats = data['pass_stats']
    total_pass = total_valid if total_valid > 0 else 1
    avg_len = int(statistics.mean(pass_stats['lengths'])) if pass_stats['lengths'] else 0
    
    # Summary Table
    summary_table = Table(title=f"[bold magenta]📈 Summary for: {keyword}[/bold magenta]", 
                         box=box.ROUNDED, 
                         border_style="cyan",
                         show_header=True,
                         header_style="bold cyan")
    summary_table.add_column("Metric", style="bold white")
    summary_table.add_column("Value", style="white", justify="right")
    summary_table.add_row("📄 Total lines", f"{stats['total_lines']:,}")
    summary_table.add_row("✅ Valid combos", f"[green]{total_valid:,}[/green]")
    summary_table.add_row("🔄 Duplicates", f"[yellow]{stats['duplicates']:,}[/yellow]")
    summary_table.add_row("❌ Bad combos", f"[red]{stats['bad']:,}[/red]")
    summary_table.add_row("📧 Email:pass", f"[cyan]{stats['email_type']:,}[/cyan]")
    summary_table.add_row("👤 User:pass", f"[cyan]{stats['user_type']:,}[/cyan]")
    summary_table.add_row("🌍 Countries detected", f"{len(data['country_combos'])}")
    summary_table.add_row("📏 Avg password length", f"{avg_len}")
    summary_table.add_row("⏱️ Processing time", format_time(elapsed))
    console.print(summary_table)
    
    if data['country_combos']:
        country_table = Table(title="[bold magenta]🌍 Countries Breakdown[/bold magenta]", 
                             box=box.ROUNDED, 
                             border_style="green",
                             show_header=True,
                             header_style="bold green")
        country_table.add_column("Country", style="bold cyan")
        country_table.add_column("Combos", style="white", justify="right")
        country_table.add_column("Percentage", style="dim", justify="right")
        
        total_combos = sum(len(combos) for combos in data['country_combos'].values())
        for cc, combos in sorted(data['country_combos'].items(), key=lambda x: -len(x[1])):
            country_name = COUNTRY_NAME_MAP.get(cc.upper(), cc.upper())
            percentage = (len(combos) / total_combos * 100) if total_combos > 0 else 0
            country_table.add_row(
                f"{country_name} ({cc.upper()})", 
                f"{len(combos):,}",
                f"{percentage:.1f}%"
            )
        console.print(country_table)
    
    if bot_token and chat_id:
        console.print("\n[bold cyan]📤 Sending report to Telegram...[/bold cyan]")
        report = build_report(data, keyword, elapsed, len(created_files))
        if send_telegram_message(bot_token, chat_id, report):
            console.print("[green]✅ Report sent successfully[/green]")
        else:
            console.print("[red]❌ Failed to send report[/red]")
        
        zip_size = os.path.getsize(zip_path)
        if zip_size <= 50 * 1024 * 1024:
            caption = f"📦 Results for: {keyword}\n📄 {len(created_files)} files, {sizeof_fmt(zip_size)}"
            if send_telegram_document(bot_token, chat_id, zip_path, caption):
                console.print("[green]✅ ZIP file sent successfully[/green]")
            else:
                console.print("[red]❌ Failed to send ZIP file[/red]")
        else:
            console.print(f"[yellow]⚠️ ZIP file too large ({sizeof_fmt(zip_size)} > 50MB). Skipping Telegram upload.[/yellow]")
    
    console.print(f"\n[bold green]✨ Done! Results saved in: {results_dir}[/bold green]")
    console.print(f"[dim]📦 ZIP archive: {zip_path}[/dim]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Process interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
