
import os
import re
import random
from collections import defaultdict
from datetime import datetime
from colorama import Fore, Back, Style, init
import time

init(autoreset=True)

# POPÜLER ÜLKELER
POPULER_ULKELER = {
    'IN': 'India', 'UN': 'Unknown', 'EG': 'Egypt', 'FR': 'France', 'VN': 'Vietnam',
    'ES': 'Spain', 'MX': 'Mexico', 'US': 'United States', 'PK': 'Pakistan',
    'EN': 'England', 'LO': 'Laos', 'ID': 'Indonesia', 'BD': 'Bangladesh',
    'BR': 'Brazil', 'PH': 'Philippines', 'EC': 'Ecuador', 'PE': 'Peru',
    'CL': 'Chile', 'AR': 'Argentina', 'CO': 'Colombia', 'DE': 'Germany',
    'GB': 'United Kingdom', 'DZ': 'Algeria', 'VI': 'Vietnam', 'TH': 'Thailand',
    'TW': 'Taiwan', 'RS': 'Serbia', 'SA': 'Saudi Arabia', 'HU': 'Hungary',
    'MY': 'Malaysia', 'PL': 'Poland', 'IL': 'Israel', 'IT': 'Italy',
    'KR': 'South Korea', 'DO': 'Dominican Republic', 'TR': 'Turkey',
    'CA': 'Canada', 'BU': 'Bulgaria',
}

REKLAM = """
https://t.me/darklrx Free Cloud M1x Ma1ls H0tma1l Ulp Drops

Author @webbierx
"""

# DİL SİSTEMİ
LANG = 'tr'

TRANSLATIONS = {
    'tr': {
        'select_lang': 'Dil Seçin / Select Language',
        'main_menu': 'ANA MENÜ',
        'tool1': 'Email Extractor (Domain Filtresi)',
        'tool2': 'Country Sorter (Ülke Ayırıcı)',
        'tool3': 'Base 34 BOT (Domain Searcher)',
        'exit': 'Çıkış',
        'select': 'Seçim',
        'folder_select': 'Klasör Seçimi',
        'current': 'Şu anki klasör',
        'use_current': 'Şu anki klasörü kullan',
        'enter_diff': 'Farklı klasör yolu gir',
        'mobile_ex': 'Mobil için örnekler',
        'pc_ex': 'PC için örnekler',
        'path': 'Klasör yolu',
        'found': 'Klasör bulundu!',
        'invalid': 'Geçersiz klasör! Varsayılan kullanılıyor.',
        'step': 'ADIM',
        'loading_kw': 'Keywords Yükleniyor',
        'error': 'HATA',
        'not_found': 'bulunamadı!',
        'success': 'Başarılı',
        'domains': 'domain yüklendi',
        'example': 'Örnek Domain\'ler',
        'more': 've daha fazla',
        'enter_files': 'Dosya Yollarını Girin',
        'mobile_example': 'Mobil için örnek',
        'pc_example': 'PC için örnek',
        'enter_each': 'Her dosya yolunu ENTER ile ayırın',
        'finish': 'Bitince boş ENTER basın',
        'file': 'Dosya',
        'not_txt': 'Dosya bulunamadı veya .txt değil!',
        'no_files': 'Hiç dosya girilmedi!',
        'extraction': 'Email Çıkarma',
        'processing': 'dosya işlenecek',
        'report': 'RAPOR',
        'total': 'TOPLAM',
        'emails': 'email bulundu',
        'save_ok': 'Kayıt Başarılı!',
        'location': 'Konum',
        'size': 'Boyut',
        'no_emails': 'Email bulunamadı!',
        'done': 'İşlem tamamlandı!',
        'press_enter': 'Çıkmak için ENTER',
        'cancelled': 'İşlem iptal!',
        'country_tool': 'Ülke Ayırıcı',
        'enter_ulp': 'ULP dosya yolunu girin',
        'file_size': 'Dosya boyutu',
        'proc_ulp': 'ULP DOSYASI İŞLENİYOR',
        'proc_line': 'İşlenen satır',
        'country_cnt': 'Ülke sayısı',
        'total_proc': 'Toplam işlenen satır',
        'skipped': 'Popüler olmayan ülkelerden atlanan',
        'creating': 'Dosyalar oluşturuluyor',
        'stats': 'ÜLKE İSTATİSTİKLERİ',
        'lines': 'satır',
        'countries': 'Toplam farklı ülke',
        'saved_to': 'Dosyalar kaydedildi',
        'telegram': 'Telegram mesajı oluşturuldu',
        'invalid_choice': 'Geçersiz seçim!',
        'base34_tool': 'Base 34 BOT',
        'enter_domain': 'Aranacak domain girin',
        'domain_example': 'Örnek: discord.com',
        'searching': 'Aranıyor',
        'files_proc': 'dosya işleniyor',
        'progress': 'İlerleme',
        'matches': 'Eşleşme',
        'unique': 'Benzersiz',
        'completed': 'Tamamlandı',
        'proc_time': 'İşlem süresi',
        'files_processed': 'İşlenen dosya',
        'query': 'Sorgu',
        'total_matches': 'Toplam eşleşme',
        'unique_accs': 'Benzersiz hesap',
        'dups_removed': 'Silinen duplicate',
        'dups_cleaned': 'duplicate temizlendi!',
        'files_saved': 'Kaydedilen dosyalar',
        'search_again': 'Tekrar ara? (evet/hayir)',
    },
    'en': {
        'select_lang': 'Dil Seçin / Select Language',
        'main_menu': 'MAIN MENU',
        'tool1': 'Email Extractor (Domain Filter)',
        'tool2': 'Country Sorter',
        'tool3': 'Base 34 BOT (Domain Searcher)',
        'exit': 'Exit',
        'select': 'Choice',
        'folder_select': 'Folder Selection',
        'current': 'Current folder',
        'use_current': 'Use current folder',
        'enter_diff': 'Enter different path',
        'mobile_ex': 'Mobile examples',
        'pc_ex': 'PC examples',
        'path': 'Folder path',
        'found': 'Folder found!',
        'invalid': 'Invalid folder! Using default.',
        'step': 'STEP',
        'loading_kw': 'Loading Keywords',
        'error': 'ERROR',
        'not_found': 'not found!',
        'success': 'Success',
        'domains': 'domains loaded',
        'example': 'Example Domains',
        'more': 'and more',
        'enter_files': 'Enter File Paths',
        'mobile_example': 'Mobile example',
        'pc_example': 'PC example',
        'enter_each': 'Press ENTER after each path',
        'finish': 'Empty ENTER to finish',
        'file': 'File',
        'not_txt': 'File not found or not .txt!',
        'no_files': 'No files entered!',
        'extraction': 'Email Extraction',
        'processing': 'files to process',
        'report': 'REPORT',
        'total': 'TOTAL',
        'emails': 'emails found',
        'save_ok': 'Save Successful!',
        'location': 'Location',
        'size': 'Size',
        'no_emails': 'No emails found!',
        'done': 'Operation completed!',
        'press_enter': 'Press ENTER to exit',
        'cancelled': 'Operation cancelled!',
        'country_tool': 'Country Sorter',
        'enter_ulp': 'Enter ULP file path',
        'file_size': 'File size',
        'proc_ulp': 'PROCESSING ULP FILE',
        'proc_line': 'Processed lines',
        'country_cnt': 'Country count',
        'total_proc': 'Total processed lines',
        'skipped': 'Skipped from unpopular countries',
        'creating': 'Creating files',
        'stats': 'COUNTRY STATISTICS',
        'lines': 'lines',
        'countries': 'Total countries',
        'saved_to': 'Files saved to',
        'telegram': 'Telegram message created',
        'invalid_choice': 'Invalid choice!',
        'base34_tool': 'Base 34 BOT',
        'enter_domain': 'Enter domain to search',
        'domain_example': 'Example: discord.com',
        'searching': 'Searching',
        'files_proc': 'files processing',
        'progress': 'Progress',
        'matches': 'Matches',
        'unique': 'Unique',
        'completed': 'Completed',
        'proc_time': 'Processing time',
        'files_processed': 'Files processed',
        'query': 'Query',
        'total_matches': 'Total matches',
        'unique_accs': 'Unique accounts',
        'dups_removed': 'Duplicates removed',
        'dups_cleaned': 'duplicates cleaned!',
        'files_saved': 'Files saved',
        'search_again': 'Search again? (yes/no)',
    }
}

def t(key):
    """Çeviri"""
    return TRANSLATIONS[LANG].get(key, key)

def is_mobile():
    return 'ANDROID_ROOT' in os.environ or 'ANDROID_DATA' in os.environ

def clear():
    if is_mobile():
        print('\n' * 50)
    else:
        os.system('cls' if os.name == 'nt' else 'clear')

def select_language():
    global LANG
    clear()
    print(f"\n{Fore.CYAN}╔{'═'*48}╗")
    print(f"║  {Fore.YELLOW}{t('select_lang'):<46}{Fore.CYAN}║")
    print(f"╚{'═'*48}╝{Style.RESET_ALL}\n")
    print(f"{Fore.GREEN}1.{Fore.WHITE} 🇹🇷 Türkçe{Style.RESET_ALL}")
    print(f"{Fore.GREEN}2.{Fore.WHITE} 🇬🇧 English{Style.RESET_ALL}")
    c = input(f"\n{Fore.YELLOW}➤ {Fore.WHITE}").strip()
    LANG = 'en' if c == '2' else 'tr'

def banner():
    clear()
    mobile = is_mobile()
    if mobile:
        b = f"""
{Fore.CYAN}╔{'═'*48}╗
║  {Fore.YELLOW}ULP MULTI-TOOL v3.0{Fore.CYAN}                      ║
║  {Fore.GREEN}Email • Country • Domain Search{Fore.CYAN}          ║
╚{'═'*48}╝{Style.RESET_ALL}
"""
    else:
        b = f"""
{Fore.CYAN}    ╔{'═'*63}╗
    ║  {Fore.YELLOW}███{Fore.RED}╗{Fore.YELLOW}   ██{Fore.RED}╗{Fore.YELLOW}██{Fore.RED}╗{Fore.YELLOW}     ██████{Fore.RED}╗{Fore.YELLOW}                                      {Fore.CYAN}║
    ║  {Fore.YELLOW}██{Fore.RED}║{Fore.YELLOW}   ██{Fore.RED}║{Fore.YELLOW}██{Fore.RED}║{Fore.YELLOW}     ██{Fore.RED}╔══{Fore.YELLOW}██{Fore.RED}╗{Fore.YELLOW}                                     {Fore.CYAN}║
    ║  {Fore.YELLOW}██{Fore.RED}║{Fore.YELLOW}   ██{Fore.RED}║{Fore.YELLOW}██{Fore.RED}║{Fore.YELLOW}     ██████{Fore.RED}╔╝{Fore.YELLOW}                                     {Fore.CYAN}║
    ║  {Fore.YELLOW}██{Fore.RED}║{Fore.YELLOW}   ██{Fore.RED}║{Fore.YELLOW}██{Fore.RED}║{Fore.YELLOW}     ██{Fore.RED}╔═══╝{Fore.YELLOW}                                      {Fore.CYAN}║
    ║  {Fore.YELLOW}╚██████{Fore.RED}╔╝{Fore.YELLOW}███████{Fore.RED}╗{Fore.YELLOW}██{Fore.RED}║{Fore.YELLOW}                                          {Fore.CYAN}║
    ║   {Fore.RED}╚═════╝{Fore.YELLOW} ╚══════╝╚═╝                                          {Fore.CYAN}║
    ║        {Fore.GREEN}🔥 ULP MULTI-TOOL BY @webbierx🔥{Fore.CYAN}                         ║
    ║        {Fore.MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Fore.CYAN}                         ║
    ║        {Fore.WHITE}Email • Country • Domain Search{Fore.CYAN}                    ║
    ╚{'═'*63}╝{Style.RESET_ALL}
"""
    print(b)
    dev = "📱 Mobil (Pydroid 3)" if mobile else "💻 PC"
    print(f"{Fore.CYAN}[{Fore.GREEN}+{Fore.CYAN}] {Fore.WHITE}Platform: {Fore.YELLOW}{dev}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}[{Fore.GREEN}+{Fore.CYAN}] {Fore.WHITE}{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}{Style.RESET_ALL}")

def menu():
    print(f"\n{Fore.CYAN}╔{'═'*48}╗")
    print(f"║  {Fore.YELLOW}{t('main_menu'):<46}{Fore.CYAN}║")
    print(f"╚{'═'*48}╝{Style.RESET_ALL}\n")
    print(f"{Fore.GREEN}1.{Fore.WHITE} 📧 {t('tool1')}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}2.{Fore.WHITE} 🌍 {t('tool2')}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}3.{Fore.WHITE} 🔍 {t('tool3')}{Style.RESET_ALL}")
    print(f"{Fore.RED}4.{Fore.WHITE} ❌ {t('exit')}{Style.RESET_ALL}")
    return input(f"\n{Fore.YELLOW}➤ {Fore.WHITE}").strip()

def get_folder():
    print(f"\n{Fore.CYAN}[{Fore.YELLOW}📁{Fore.CYAN}] {Fore.WHITE}{t('folder_select')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─'*50}{Style.RESET_ALL}")
    curr = os.getcwd()
    print(f"{Fore.CYAN}{t('current')}:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{curr}{Style.RESET_ALL}\n")
    print(f"{Fore.GREEN}1.{Style.RESET_ALL} {t('use_current')}")
    print(f"{Fore.GREEN}2.{Style.RESET_ALL} {t('enter_diff')}")
    c = input(f"\n{Fore.YELLOW}➤ {Fore.WHITE}").strip()
    
    if c == '2':
        if is_mobile():
            print(f"\n{Fore.CYAN}{t('mobile_ex')}:{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}/storage/emulated/0/Download{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}/sdcard/Documents{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.CYAN}{t('pc_ex')}:{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}C:\\Users\\User\\Desktop{Style.RESET_ALL}")
        
        p = input(f"\n{Fore.YELLOW}➤ {t('path')}: {Fore.WHITE}").strip()
        if os.path.exists(p) and os.path.isdir(p):
            print(f"{Fore.GREEN}✓ {t('found')}{Style.RESET_ALL}")
            return p
        print(f"{Fore.RED}✗ {t('invalid')}{Style.RESET_ALL}")
        time.sleep(1)
    return curr

def load_kw(kw_file):
    print(f"\n{Fore.CYAN}[{Fore.YELLOW}{t('step')} 1{Fore.CYAN}] {Fore.WHITE}{t('loading_kw')}...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─'*50}{Style.RESET_ALL}")
    
    if not os.path.exists(kw_file):
        print(f"{Fore.RED}✗ {t('error')}: {kw_file} {t('not_found')}{Style.RESET_ALL}")
        return set()
    
    kws = set()
    with open(kw_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            d = line.strip().lower()
            if d and not d.startswith('http'):
                kws.add(d)
    
    print(f"{Fore.GREEN}✓ {t('success')}: {len(kws)} {t('domains')}{Style.RESET_ALL}")
    
    if kws:
        mx = 3 if is_mobile() else 5
        print(f"\n{Fore.CYAN}   {t('example')}:{Style.RESET_ALL}")
        for i, d in enumerate(list(kws)[:mx], 1):
            print(f"{Fore.CYAN}   {i}. {Fore.YELLOW}{d}{Style.RESET_ALL}")
        if len(kws) > mx:
            print(f"{Fore.CYAN}   ... {t('more')} {len(kws)-mx}{Style.RESET_ALL}")
    return kws

def extract_emails(txt, kws):
    if not os.path.exists(txt):
        return []
    emails = []
    try:
        with open(txt, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(':')
                if len(parts) >= 3:
                    email_part = None
                    pass_part = None
                    for i, part in enumerate(parts):
                        if '@' in part:
                            email_part = part
                            if i + 1 < len(parts):
                                pass_part = ':'.join(parts[i+1:])
                            break
                    if email_part and pass_part:
                        domain = email_part.split('@')[1].lower()
                        if domain in kws:
                            emails.append(f"{email_part}:{pass_part}")
    except:
        pass
    return emails

def get_files():
    print(f"\n{Fore.CYAN}[{Fore.YELLOW}{t('step')} 2{Fore.CYAN}] {Fore.WHITE}{t('enter_files')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═'*50}{Style.RESET_ALL}")
    
    if is_mobile():
        print(f"{Fore.YELLOW}📱 {t('mobile_example')}:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}/storage/emulated/0/Download/combo.txt{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}💻 {t('pc_example')}:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}C:\\combo\\list.txt{Style.RESET_ALL}")
    
    print(f"\n{Fore.WHITE}{t('enter_each')}")
    print(f"{t('finish')}{Style.RESET_ALL}\n")
    
    files = []
    i = 1
    while True:
        fp = input(f"{Fore.YELLOW}{t('file')} {i}: {Fore.WHITE}").strip().strip('"').strip("'")
        if not fp:
            break
        if os.path.exists(fp) and fp.endswith('.txt'):
            files.append(fp)
            sz = os.path.getsize(fp) / 1024
            print(f"{Fore.GREEN}   ✓ {os.path.basename(fp)} ({sz:.2f} KB){Style.RESET_ALL}")
            i += 1
        else:
            print(f"{Fore.RED}   ✗ {t('not_txt')}{Style.RESET_ALL}")
    return files

def email_tool(work_dir):
    kw_file = os.path.join(work_dir, "keywords.txt")
    kws = load_kw(kw_file)
    
    if not kws:
        input(f"\n{Fore.YELLOW}{t('press_enter')}...{Style.RESET_ALL}")
        return
    
    txts = get_files()
    
    if not txts:
        print(f"\n{Fore.RED}✗ {t('no_files')}{Style.RESET_ALL}")
        input(f"\n{Fore.YELLOW}{t('press_enter')}...{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}[{Fore.YELLOW}{t('step')} 3{Fore.CYAN}] {Fore.WHITE}{t('extraction')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═'*50}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🔍 {len(txts)} {t('processing')}...{Style.RESET_ALL}\n")
    
    all_em = []
    results = []
    
    for i, txt in enumerate(txts, 1):
        fn = os.path.basename(txt)
        fs = fn[:35] + '...' if len(fn) > 35 else fn
        print(f"{Fore.MAGENTA}[{i}/{len(txts)}]{Fore.WHITE} {fs}{Style.RESET_ALL}")
        
        ems = extract_emails(txt, kws)
        all_em.extend(ems)
        results.append((fn, len(ems)))
        print(f"  {Fore.GREEN}✓ {len(ems)} email{Style.RESET_ALL}\n")
    
    print(f"\n{Fore.CYAN}{'═'*50}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📊 {t('report')}:{Style.RESET_ALL}\n")
    
    for fn, cnt in results:
        fs = fn[:30] + '...' if len(fn) > 30 else fn
        print(f"  {Fore.CYAN}{fs:<33}{Fore.WHITE}{cnt:>4}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'─'*50}{Style.RESET_ALL}")
    print(f"  {Fore.YELLOW}{t('total')}: {Fore.WHITE}{len(all_em)} {t('emails')}{Style.RESET_ALL}")
    
    if all_em:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = os.path.join(work_dir, f"extracted_emails_{ts}.txt")
        
        with open(out, 'w', encoding='utf-8') as f:
            for em in all_em:
                f.write(em + '\n')
        
        print(f"\n{Fore.GREEN}💾 {t('save_ok')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}   {t('location')}: {Fore.YELLOW}{work_dir}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}   {t('size')}: {Fore.YELLOW}{os.path.getsize(out)/1024:.2f} KB{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}⚠ {t('no_emails')}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}✨ {t('done')}{Style.RESET_ALL}")
    input(f"\n{Fore.YELLOW}{t('press_enter')}...{Style.RESET_ALL}")

def country_tool(work_dir):
    print(f"\n{Fore.CYAN}[{Fore.YELLOW}🌍{Fore.CYAN}] {Fore.WHITE}{t('country_tool')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═'*50}{Style.RESET_ALL}")
    
    if is_mobile():
        print(f"{Fore.YELLOW}📱 {t('mobile_example')}:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}/storage/emulated/0/Download/ulp.txt{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}💻 {t('pc_example')}:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}C:\\combo\\ulp.txt{Style.RESET_ALL}")
    
    fp = input(f"\n{Fore.YELLOW}➤ {t('enter_ulp')}: {Fore.WHITE}").strip().strip('"').strip("'")
    
    if not os.path.exists(fp):
        print(f"{Fore.RED}✗ {t('not_found')}{Style.RESET_ALL}")
        input(f"\n{Fore.YELLOW}{t('press_enter')}...{Style.RESET_ALL}")
        return
    
    sz = os.path.getsize(fp)
    if sz >= 1024**3:
        print(f"{Fore.CYAN}📦 {t('file_size')}: {sz/(1024**3):.2f} GB{Style.RESET_ALL}")
    else:
        print(f"{Fore.CYAN}📦 {t('file_size')}: {sz/(1024**2):.2f} MB{Style.RESET_ALL}")
    
    out_dir = os.path.join(work_dir, "ulkelere_gore")
    os.makedirs(out_dir, exist_ok=True)
    
    data = defaultdict(list)
    skip = 0
    
    print(f"\n{Fore.CYAN}{'═'*50}")
    print(f"🌍 {t('proc_ulp')}")
    print(f"{'═'*50}{Style.RESET_ALL}\n")
    
    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
        cnt = 0
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if len(line) >= 2 and line[:2].isalpha():
                cc = line[:2].upper()
                
                if cc in POPULER_ULKELER:
                    clean = line[2:].strip()
                    if clean:
                        data[cc].append(clean)
                        cnt += 1
                else:
                    skip += 1
                
                if cnt % 100000 == 0:
                    print(f"{Fore.CYAN}⏳ {t('proc_line')}: {cnt:,} | {t('country_cnt')}: {len(data)}{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}✓ {t('total_proc')}: {cnt:,}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⚠ {t('skipped')}: {skip:,}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}⚙️  {t('creating')}...{Style.RESET_ALL}\n")
    
    for cc, lines in data.items():
        ln_cnt = len(lines)
        cname = POPULER_ULKELER[cc]
        fname = f"[{cc}] {cname} {ln_cnt} lines.txt"
        fpath = os.path.join(out_dir, fname)
        
        with open(fpath, 'w', encoding='utf-8') as f:
            ad_pos = random.randint(35, 45)
            for idx, line in enumerate(lines, 1):
                f.write(line + '\n')
                if idx == ad_pos and idx < ln_cnt:
                    f.write(REKLAM.strip() + '\n\n')
                    ad_pos += random.randint(35, 45)
    
    # Telegram mesajı
    tg_file = os.path.join(out_dir, "TELEGRAM_MESSAGE.txt")
    with open(tg_file, 'w', encoding='utf-8') as f:
        python
        f.write("╔══════════════════════════════════╗\n")
        f.write("║     🔥 NEW ULP DROP 🔥          ║\n")
        f.write("╚══════════════════════════════════╝\n\n")
        f.write(f"📅 Date: {datetime.now().strftime('%d.%m.%Y')}\n")
        f.write(f"📊 Total Countries: {len(data)}\n\n")
        f.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        f.write("        🌍 COUNTRY LIST 🌍\n")
        f.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
        
        for cc, lines in sorted(data.items(), key=lambda x: len(x[1]), reverse=True):
            ln_cnt = len(lines)
            cname = POPULER_ULKELER[cc]
            f.write(f"🌐 [{cc}] {cname}\n")
            f.write(f"   └─ 📝 {ln_cnt:,} lines\n\n")
        
        f.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        f.write("⚡️ Fresh & HQ | Private ULP\n")
        f.write("📢 Channel: https://t.me/darklrx\n")
        f.write("👤 By: @webbierx\n")
        f.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    print(f"{Fore.CYAN}{'═'*50}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📊 {t('stats')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═'*50}{Style.RESET_ALL}\n")
    
    for cc, lines in sorted(data.items(), key=lambda x: len(x[1]), reverse=True):
        ln_cnt = len(lines)
        cname = POPULER_ULKELER[cc]
        print(f"{Fore.GREEN}✅ {cc} ({cname}): {Fore.WHITE}{ln_cnt:,} {t('lines')}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}📁 {t('countries')}: {Fore.WHITE}{len(data)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📂 {t('saved_to')}: {Fore.YELLOW}{out_dir}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✓ {t('telegram')}: {Fore.WHITE}TELEGRAM_MESSAGE.txt{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}✨ {t('done')}{Style.RESET_ALL}")
    input(f"\n{Fore.YELLOW}{t('press_enter')}...{Style.RESET_ALL}")

def extract_credentials(line):
    """Base34: Extract login:password from combo line"""
    if '/' in line:
        parts = line.split('/')
        credentials = parts[-1]
    else:
        credentials = line
    
    credentials = credentials.replace('https://', '').replace('http://', '')
    
    first_colon = credentials.find(':')
    if first_colon != -1:
        return credentials[first_colon + 1:]
    
    return credentials

def process_chunk(lines, query, seen, out_url, out_pass):
    """Base34: Process chunk of lines"""
    total = 0
    unique = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if query not in line.lower():
            continue
        
        total += 1
        key = line.lower()
        
        if key in seen:
            continue
        
        seen.add(key)
        unique += 1
        
        out_url.write(line + '\n')
        credentials = extract_credentials(line)
        out_pass.write(credentials + '\n')
    
    return total, unique

def base34_tool(work_dir):
    """Base 34 BOT - Domain Searcher"""
    print(f"\n{Fore.CYAN}[{Fore.YELLOW}🔍{Fore.CYAN}] {Fore.WHITE}{t('base34_tool')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═'*50}{Style.RESET_ALL}")
    
    # Dosya seçimi
    txts = get_files()
    
    if not txts:
        print(f"\n{Fore.RED}✗ {t('no_files')}{Style.RESET_ALL}")
        input(f"\n{Fore.YELLOW}{t('press_enter')}...{Style.RESET_ALL}")
        return
    
    # Domain sorgusu
    print(f"\n{Fore.CYAN}{t('domain_example')}:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}discord.com, instagram.com, netflix.com{Style.RESET_ALL}")
    
    query = input(f"\n{Fore.YELLOW}➤ {t('enter_domain')}: {Fore.WHITE}").strip()
    
    if not query:
        print(f"\n{Fore.RED}✗ {t('cancelled')}{Style.RESET_ALL}")
        input(f"\n{Fore.YELLOW}{t('press_enter')}...{Style.RESET_ALL}")
        return
    
    # Domain temizle
    query = query.lower().replace('https://', '').replace('http://', '')
    query = query.split('/')[0].replace('www.', '')
    
    print(f"\n{Fore.CYAN}[{Fore.YELLOW}{t('step')} 3{Fore.CYAN}] {Fore.WHITE}{t('searching')}: {Fore.YELLOW}{query}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═'*50}{Style.RESET_ALL}\n")
    
    start_time = time.time()
    
    # Temp dosyalar
    temp_url = os.path.join(work_dir, f"temp_{query}_with_url.txt")
    temp_pass = os.path.join(work_dir, f"temp_{query}_log_pass.txt")
    
    # Temizle
    for f in [temp_url, temp_pass]:
        if os.path.exists(f):
            os.remove(f)
    
    seen = set()
    total_matches = 0
    unique_count = 0
    
    try:
        with open(temp_url, 'w', encoding='utf-8', errors='ignore') as out_url, \
             open(temp_pass, 'w', encoding='utf-8', errors='ignore') as out_pass:
            
            for file_idx, filepath in enumerate(txts, 1):
                file_size = os.path.getsize(filepath)
                processed = 0
                filename = os.path.basename(filepath)
                
                print(f"{Fore.MAGENTA}[{file_idx}/{len(txts)}]{Fore.WHITE} {filename}{Style.RESET_ALL}")
                
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    chunk_size = 50000
                    lines_buffer = []
                    last_print = 0
                    
                    for line in f:
                        lines_buffer.append(line)
                        processed += len(line.encode('utf-8'))
                        
                        if len(lines_buffer) >= chunk_size:
                            total, unique = process_chunk(lines_buffer, query, seen, out_url, out_pass)
                            total_matches += total
                            unique_count += unique
                            lines_buffer = []
                            
                            out_url.flush()
                            out_pass.flush()
                            
                            progress_pct = min(100, int((processed / file_size) * 100))
                            
                            if progress_pct - last_print >= 10:
                                print(f"   {t('progress')}: {progress_pct}% | {t('matches')}: {total_matches:,} | {t('unique')}: {unique_count:,}")
                                last_print = progress_pct
                    
                    # Kalan satırlar
                    if lines_buffer:
                        total, unique = process_chunk(lines_buffer, query, seen, out_url, out_pass)
                        total_matches += total
                        unique_count += unique
                
                print(f"   {Fore.GREEN}✓ {t('completed')}: 100% | {t('matches')}: {total_matches:,} | {t('unique')}: {unique_count:,}{Style.RESET_ALL}\n")
        
        # İstatistikler
        end_time = time.time()
        proc_time = end_time - start_time
        dups_removed = total_matches - unique_count
        
        # Son dosya isimleri
        final_url = os.path.join(work_dir, f"{unique_count}x {query}.txt")
        final_pass = os.path.join(work_dir, f"{unique_count}x {query}_LogPass.txt")
        
        if os.path.exists(temp_url):
            if os.path.exists(final_url):
                os.remove(final_url)
            os.rename(temp_url, final_url)
        
        if os.path.exists(temp_pass):
            if os.path.exists(final_pass):
                os.remove(final_pass)
            os.rename(temp_pass, final_pass)
        
        # Sonuçlar
        print(f"{Fore.CYAN}{'═'*50}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ {t('completed').upper()}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═'*50}{Style.RESET_ALL}\n")
        
        print(f"{Fore.CYAN}⏱️  {t('proc_time')}: {Fore.WHITE}{proc_time:.2f}s{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📂 {t('files_processed')}: {Fore.WHITE}{len(txts)}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🔍 {t('query')}: {Fore.YELLOW}'{query}'{Style.RESET_ALL}\n")
        
        print(f"{Fore.CYAN}📊 {t('total_matches')}: {Fore.WHITE}{total_matches:,}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ {t('unique_accs')}: {Fore.WHITE}{unique_count:,}{Style.RESET_ALL}")
        print(f"{Fore.RED}🗑️  {t('dups_removed')}: {Fore.WHITE}{dups_removed:,}{Style.RESET_ALL}")
        
        if dups_removed > 0:
            dup_pct = (dups_removed / total_matches * 100)
            print(f"{Fore.MAGENTA}💪 {dup_pct:.1f}% {t('dups_cleaned')}{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}📝 {t('files_saved')}:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}   💾 {os.path.basename(final_url)}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}   🔐 {os.path.basename(final_pass)}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═'*50}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"\n{Fore.RED}✗ {t('error')}: {str(e)}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}✨ {t('done')}{Style.RESET_ALL}")
    input(f"\n{Fore.YELLOW}{t('press_enter')}...{Style.RESET_ALL}")

def main():
    select_language()
    
    while True:
        banner()
        choice = menu()
        
        if choice == '1':
            # Email Extractor
            work_dir = get_folder()
            email_tool(work_dir)
        
        elif choice == '2':
            # Country Sorter
            work_dir = get_folder()
            country_tool(work_dir)
        
        elif choice == '3':
            # Base 34 BOT
            work_dir = get_folder()
            base34_tool(work_dir)
        
        elif choice == '4':
            # Çıkış
            print(f"\n{Fore.YELLOW}👋 {t('done')}{Style.RESET_ALL}")
            break
        
        else:
            print(f"\n{Fore.RED}✗ {t('invalid_choice')}{Style.RESET_ALL}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠ {t('cancelled')}{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}✗ {t('error')}: {e}{Style.RESET_ALL}")
        input(f"\n{Fore.YELLOW}{t('press_enter')}...{Style.RESET_ALL}")
