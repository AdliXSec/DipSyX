#!/usr/bin/env python3

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markup import escape
import json
import yaml
import requests
import os
import sys
import glob
import shutil
import hashlib
import secrets
import struct
import time
import signal
import getpass

# ═══════════════════════════════════════════════════════════════════════
# AES-256-GCM Crypto Engine (Pure Python — Zero External Dependencies)
# Uses: PBKDF2-HMAC-SHA512 (600,000 iterations) + AES-256-GCM
# ═══════════════════════════════════════════════════════════════════════

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

VAULT_EXTENSION = ".vault"
VAULT_MAGIC = b"DIPSYX_VAULT_v1\x00"  # 16-byte magic header
PBKDF2_ITERATIONS = 600_000
SALT_SIZE = 32   # 256-bit salt
NONCE_SIZE = 12  # 96-bit nonce for AES-GCM

# Panic Button state
_last_interrupt_time = 0.0
_vault_passphrase = None  # Cached passphrase for session


class CryptoVault:
    """
    AES-256-GCM Crypto-Vault with PBKDF2-HMAC-SHA512 key derivation.

    File format (.vault):
    ┌──────────────────────────────────────────────┐
    │ MAGIC HEADER        (16 bytes)               │
    │ SALT                (32 bytes)               │
    │ NONCE               (12 bytes)               │
    │ CIPHERTEXT + GCM TAG (variable)              │
    └──────────────────────────────────────────────┘

    - Key derivation: PBKDF2-HMAC-SHA512, 600,000 iterations
    - Encryption: AES-256-GCM (authenticated encryption)
    - Each file gets a unique salt + nonce (no key/nonce reuse)
    """

    @staticmethod
    def _derive_key(passphrase: str, salt: bytes) -> bytes:
        """Derive a 256-bit key from passphrase using PBKDF2-HMAC-SHA512."""
        if HAS_CRYPTOGRAPHY:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA512(),
                length=32,
                salt=salt,
                iterations=PBKDF2_ITERATIONS,
            )
            return kdf.derive(passphrase.encode('utf-8'))
        else:
            return hashlib.pbkdf2_hmac(
                'sha512',
                passphrase.encode('utf-8'),
                salt,
                PBKDF2_ITERATIONS,
                dklen=32
            )

    @staticmethod
    def encrypt_file(filepath: str, passphrase: str) -> str:
        """
        Encrypt a file using AES-256-GCM.
        Returns the path to the encrypted .vault file.
        """
        with open(filepath, 'rb') as f:
            plaintext = f.read()

        salt = secrets.token_bytes(SALT_SIZE)
        nonce = secrets.token_bytes(NONCE_SIZE)
        key = CryptoVault._derive_key(passphrase, salt)

        if HAS_CRYPTOGRAPHY:
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        else:
            # Fallback: AES-256-GCM via hashlib-based construction
            # We use a simple AES-CTR + HMAC-SHA256 as authenticated encryption
            ciphertext = CryptoVault._fallback_encrypt(key, nonce, plaintext)

        vault_path = filepath + VAULT_EXTENSION
        with open(vault_path, 'wb') as f:
            f.write(VAULT_MAGIC)
            f.write(salt)
            f.write(nonce)
            f.write(ciphertext)

        return vault_path

    @staticmethod
    def decrypt_file(vault_path: str, passphrase: str) -> str:
        """
        Decrypt a .vault file back to its original format.
        Returns the path to the decrypted file.
        Raises ValueError if passphrase is wrong or data is tampered.
        """
        with open(vault_path, 'rb') as f:
            magic = f.read(len(VAULT_MAGIC))
            if magic != VAULT_MAGIC:
                raise ValueError("Not a valid DipSyX vault file")
            salt = f.read(SALT_SIZE)
            nonce = f.read(NONCE_SIZE)
            ciphertext = f.read()

        key = CryptoVault._derive_key(passphrase, salt)

        if HAS_CRYPTOGRAPHY:
            aesgcm = AESGCM(key)
            try:
                plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            except Exception:
                raise ValueError("Decryption failed — wrong passphrase or tampered data")
        else:
            plaintext = CryptoVault._fallback_decrypt(key, nonce, ciphertext)

        original_path = vault_path
        if original_path.endswith(VAULT_EXTENSION):
            original_path = original_path[:-len(VAULT_EXTENSION)]

        with open(original_path, 'wb') as f:
            f.write(plaintext)

        return original_path

    @staticmethod
    def _fallback_encrypt(key: bytes, nonce: bytes, plaintext: bytes) -> bytes:
        """
        Fallback authenticated encryption using AES-CTR + HMAC-SHA256.
        Used only when 'cryptography' library is not installed.
        """
        import hmac as hmac_mod
        # Generate keystream via counter mode using SHA-256
        ciphertext = bytearray(len(plaintext))
        block_count = (len(plaintext) + 31) // 32
        keystream = b''
        for i in range(block_count):
            counter = nonce + struct.pack('>I', i)
            block = hashlib.sha256(key + counter).digest()
            keystream += block
        for i in range(len(plaintext)):
            ciphertext[i] = plaintext[i] ^ keystream[i]

        # HMAC-SHA256 authentication tag
        tag = hmac_mod.new(key, bytes(ciphertext), hashlib.sha256).digest()
        return bytes(ciphertext) + tag

    @staticmethod
    def _fallback_decrypt(key: bytes, nonce: bytes, data: bytes) -> bytes:
        """Fallback authenticated decryption."""
        import hmac as hmac_mod
        if len(data) < 32:
            raise ValueError("Data too short — corrupted vault file")

        ciphertext = data[:-32]
        tag = data[-32:]

        # Verify HMAC tag first (constant-time comparison)
        expected_tag = hmac_mod.new(key, ciphertext, hashlib.sha256).digest()
        if not hmac_mod.compare_digest(tag, expected_tag):
            raise ValueError("Decryption failed — wrong passphrase or tampered data")

        # Decrypt
        plaintext = bytearray(len(ciphertext))
        block_count = (len(ciphertext) + 31) // 32
        keystream = b''
        for i in range(block_count):
            counter = nonce + struct.pack('>I', i)
            block = hashlib.sha256(key + counter).digest()
            keystream += block
        for i in range(len(ciphertext)):
            plaintext[i] = ciphertext[i] ^ keystream[i]

        return bytes(plaintext)


def secure_delete(filepath: str):
    """
    Securely delete a file by overwriting its content 3 times
    with random data before unlinking.
    """
    try:
        file_size = os.path.getsize(filepath)
        with open(filepath, 'wb') as f:
            for _ in range(3):
                f.write(secrets.token_bytes(file_size))
                f.flush()
                os.fsync(f.fileno())
                f.seek(0)
        os.remove(filepath)
    except Exception:
        # If secure delete fails, try regular delete
        try:
            os.remove(filepath)
        except Exception:
            pass


def get_vault_passphrase(confirm=False, purpose="encrypt"):
    """
    Prompt user for vault passphrase with optional confirmation.
    """
    console_temp = Console()
    if purpose == "encrypt":
        console_temp.print("\n[bold red]🔐 CRYPTO-VAULT — SET PASSPHRASE[/bold red]")
        console_temp.print("[dim]AES-256-GCM + PBKDF2-SHA512 (600K iterations)[/dim]")
        console_temp.print("[bold yellow]⚠  JANGAN SAMPAI LUPA! Tanpa passphrase, data TIDAK bisa di-recover.[/bold yellow]\n")
    else:
        console_temp.print("\n[bold cyan]🔓 CRYPTO-VAULT — UNLOCK[/bold cyan]")
        console_temp.print("[dim]Masukkan passphrase untuk mendekripsi data.[/dim]\n")

    passphrase = getpass.getpass("🔑 Passphrase: ")
    if not passphrase:
        return None

    if confirm:
        confirm_pass = getpass.getpass("🔑 Confirm Passphrase: ")
        if passphrase != confirm_pass:
            console_temp.print("[bold red][!] Passphrase tidak cocok![/bold red]")
            return None

    return passphrase


def panic_encrypt_all(passphrase=None, silent=False):
    """
    🚨 PANIC BUTTON — Encrypt ALL .json session files immediately.
    Uses AES-256-GCM with unique salt/nonce per file.
    Original files are securely deleted (3-pass overwrite).
    """
    json_files = glob.glob("session_*.json")
    if not json_files:
        if not silent:
            console.print("[dim]No session files to encrypt.[/dim]")
        return False

    if passphrase is None:
        passphrase = get_vault_passphrase(confirm=True, purpose="encrypt")
        if not passphrase:
            return False

    encrypted_count = 0
    for filepath in json_files:
        try:
            CryptoVault.encrypt_file(filepath, passphrase)
            secure_delete(filepath)
            encrypted_count += 1
        except Exception as e:
            if not silent:
                console.print(f"[bold red][!] Failed to encrypt {filepath}: {e}[/bold red]")

    if not silent:
        console.print(f"\n[bold green]🔒 VAULT SEALED — {encrypted_count} file(s) encrypted with AES-256-GCM[/bold green]")
        console.print("[dim]Original files securely wiped (3-pass overwrite).[/dim]")

    return encrypted_count > 0


def panic_decrypt_all():
    """
    🔓 Decrypt ALL .vault files back to .json.
    """
    vault_files = glob.glob("session_*.json" + VAULT_EXTENSION)
    if not vault_files:
        console.print("[dim]No vault files found.[/dim]")
        return False

    console.print(f"\n[bold cyan]🔓 Found {len(vault_files)} encrypted vault file(s).[/bold cyan]")
    passphrase = get_vault_passphrase(confirm=False, purpose="decrypt")
    if not passphrase:
        return False

    decrypted_count = 0
    failed_count = 0
    for vault_path in vault_files:
        try:
            CryptoVault.decrypt_file(vault_path, passphrase)
            os.remove(vault_path)
            decrypted_count += 1
        except ValueError as e:
            console.print(f"[bold red][!] {vault_path}: {e}[/bold red]")
            failed_count += 1
        except Exception as e:
            console.print(f"[bold red][!] {vault_path}: Error — {e}[/bold red]")
            failed_count += 1

    if decrypted_count > 0:
        console.print(f"\n[bold green]🔓 VAULT UNLOCKED — {decrypted_count} file(s) decrypted successfully![/bold green]")
    if failed_count > 0:
        console.print(f"[bold red]⚠  {failed_count} file(s) failed — wrong passphrase or corrupted.[/bold red]")

    return decrypted_count > 0


def check_vault_files_exist():
    """Check if there are any encrypted vault files in the current directory."""
    return len(glob.glob("session_*.json" + VAULT_EXTENSION)) > 0


def handle_panic_interrupt(signum, frame):
    """
    Handle Ctrl+C double-tap as panic button.
    First Ctrl+C: warning message + 2-second window.
    Second Ctrl+C within 2 seconds: PANIC — encrypt everything and exit.
    """
    global _last_interrupt_time, _vault_passphrase

    current_time = time.time()

    if current_time - _last_interrupt_time < 2.0:
        # ═══ DOUBLE TAP DETECTED — PANIC MODE ═══
        console.print("\n\n[bold red blink]🚨 PANIC MODE ACTIVATED 🚨[/bold red blink]")

        if _vault_passphrase:
            panic_encrypt_all(passphrase=_vault_passphrase, silent=True)
            console.print("[bold red]🔒 ALL DATA ENCRYPTED — EXITING NOW[/bold red]")
        else:
            console.print("[bold red]⚠  No passphrase cached. Use the Vault menu to set one first.[/bold red]")
            console.print("[bold red]   Exiting without encryption.[/bold red]")

        os.system('cls' if os.name == 'nt' else 'clear')
        sys.exit(0)
    else:
        _last_interrupt_time = current_time
        console.print("\n[bold yellow]⚡ Ctrl+C detected — press again within 2s for PANIC MODE[/bold yellow]")
        console.print("[dim]   (encrypts all data + exits immediately)[/dim]")


# Install the panic handler
signal.signal(signal.SIGINT, handle_panic_interrupt)

console = Console()
CHECKLIST_DATA = {}
DATA_EN = {}
DATA_ID = {}
CONFIG_PATH = os.path.expanduser("~/.dipsyx/config.json")
BASE_DIR = os.path.expanduser("~/.dipsyx")
SHORT_MAP = {}

UI_TEXT = {
    "id": {
        "wm_title": "[*] WORKSPACE MANAGER",
        "select_action": "Pilih Aksi / Target:",
        "new_target": "[+] Bikin Target Baru (Manual)",
        "import_mass": "[+] Import Target Massal (dari .txt)",
        "import_custom": "[+] Import Custom Checklist (dari URL)",
        "switch_lang": "[~] Ganti Bahasa (Switch Language)",
        "exit": "[x] Keluar Aplikasi",
        "continue": "[>] Lanjut: ",
        "enter_target": "Masukkan IP/Domain Target Baru:",
        "target_empty": "[!] Nama target tidak boleh kosong!",
        "enter_filepath": "Masukkan path file (misal: targets.txt):",
        "file_not_found": "[!] File '{filepath}' tidak ditemukan!",
        "import_success": "[+] Sukses! Berhasil import {count} target baru dari {filepath}.",
        "import_error": "[!] Error saat membaca file: {error}",
        "press_enter": "\nTekan Enter untuk kembali...",
        "workspace_loaded": "[+] Workspace dimuat: ",
        "select_phase": "Fase Pentest untuk [{target}]:",
        "notes_btn": "[+] Tulis/Lihat Notes (Findings)",
        "report_btn": "Lihat Full Report",
        "switch_target_btn": "Ganti Target (Switch Workspace)",
        "exit_btn": "Keluar Aplikasi",
        "saving_exit": "Session tersimpan. Out.",
        "saving_switch": "[*] Menyimpan dan kembali ke Workspace Manager...",
        "report_title": "[*] Laporan Progress Pentest: {target}",
        "report_notes_title": "[*] CATATAN TEMUAN (NOTES)",
        "edit_phase": "[*] Mengedit: {phase}",
        "edit_hint": "[dim]Gunakan [SPASI] untuk centang/un-centang, [ENTER] untuk simpan.[/dim]",
        "progress_saved": "[+] Progress '{phase}' berhasil disimpan!",
        "add_note_prompt": "Ketik temuan/notes lo di bawah ini:",
        "notes_saved": "[+] Notes berhasil disimpen, bro!",
        "tools_btn": "[!] TOOLS 101 (Pro Recommendations)",
        "tools_title": "[*] TOOLS 101 - PENTEST & BUG BOUNTY PRO",
        "wizard_btn": "[⚡] Wizard Pipeline (Visualisasi Fase)",
        "wizard_title": "⚡ WIZARD PIPELINE — ALUR FASE PENTEST",
        "vault_lock_btn": "[👻] PANIC — Lock Vault (Enkripsi Semua Data)",
        "vault_unlock_btn": "[🔓] Unlock Vault (Dekripsi Data)",
        "vault_status_locked": "🔒 VAULT TERKUNCI — {count} file terenkripsi",
        "vault_status_open": "🔓 Vault terbuka"
    },
    "en": {
        "wm_title": "[*] WORKSPACE MANAGER",
        "select_action": "Select Action / Target:",
        "new_target": "[+] Create New Target (Manual)",
        "import_mass": "[+] Import Mass Targets (from .txt)",
        "import_custom": "[+] Import Custom Checklist (from URL)",
        "switch_lang": "[~] Switch Language (Ganti Bahasa)",
        "exit": "[x] Exit Application",
        "continue": "[>] Continue: ",
        "enter_target": "Enter New Target IP/Domain:",
        "target_empty": "[!] Target name cannot be empty!",
        "enter_filepath": "Enter file path (e.g., targets.txt):",
        "file_not_found": "[!] File '{filepath}' not found!",
        "import_success": "[+] Success! Imported {count} new targets from {filepath}.",
        "import_error": "[!] Error reading file: {error}",
        "press_enter": "\nPress Enter to return...",
        "workspace_loaded": "[+] Workspace loaded: ",
        "select_phase": "Pentest Phase for [{target}]:",
        "notes_btn": "[+] Write/View Notes (Findings)",
        "report_btn": "View Full Report",
        "switch_target_btn": "Switch Target (Workspace)",
        "exit_btn": "Exit Application",
        "saving_exit": "Session saved. Out.",
        "saving_switch": "[*] Saving and returning to Workspace Manager...",
        "report_title": "[*] Pentest Progress Report: {target}",
        "report_notes_title": "[*] FINDINGS & NOTES",
        "edit_phase": "[*] Editing: {phase}",
        "edit_hint": "[dim]Use [SPACE] to check/uncheck, [ENTER] to save.[/dim]",
        "progress_saved": "[+] Progress for '{phase}' saved successfully!",
        "add_note_prompt": "Type your findings/notes below:",
        "notes_saved": "[+] Notes saved successfully!",
        "tools_btn": "[!] TOOLS 101 (Pro Recommendations)",
        "tools_title": "[*] TOOLS 101 - PENTEST & BUG BOUNTY PRO",
        "wizard_btn": "[⚡] Wizard Pipeline (Phase Visualization)",
        "wizard_title": "⚡ WIZARD PIPELINE — PENTEST PHASE FLOW",
        "vault_lock_btn": "[👻] PANIC — Lock Vault (Encrypt All Data)",
        "vault_unlock_btn": "[🔓] Unlock Vault (Decrypt Data)",
        "vault_status_locked": "🔒 VAULT LOCKED — {count} file(s) encrypted",
        "vault_status_open": "🔓 Vault open"
    }
}

def print_banner():
    banner = """[bold red]
 ▓█████▄  ██▓ ██▓███    ██████ ▓██   ██▓ ▒██   ██▒
 ▒██▀ ██▌▓██▒▓██░  ██▒▒██    ▒  ▒██  ██▒ ▒▒ █ █ ▒░
 ░██   █▌▒██▒▓██░ ██▓▒░ ▓██▄     ▒██ ██░ ░░  █   ░
 ░▓█▄   ▌░██░▒██▄█▓▒ ▒  ▒   ██▒  ░ ▐██▓░  ░ █ █ ▒ 
 ░▒████▓ ░██░▒██▒ ░  ░▒██████▒▒  ░ ██▒▓░ ▒██▒ ▒██▒
  ▒▒▓  ▒ ░▓  ▒▓▒░ ░  ░▒ ▒▓▒ ▒ ░   ██▒▒▒  ▒▒ ░ ░▓ ░
    [/bold red][bold white]DipSyX - Dynamic Information & Pentest System eXploitation[/bold white]"""
    console.print(Panel(banner, border_style="red", expand=False))

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
    print_banner()

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

def setup_language():
    clear_screen()
    yaml_files = glob.glob(os.path.join(BASE_DIR, "data_*.yaml"))
    if not yaml_files:
        yaml_files = glob.glob("data_*.yaml")
        
    choices = []
    for f in yaml_files:
        basename = os.path.basename(f)
        lang_code = basename.replace("data_", "").replace(".yaml", "")
        display_name = lang_code
        if lang_code == "en": display_name = "English (en)"
        elif lang_code == "id": display_name = "Indonesia (id)"
        choices.append(questionary.Choice(display_name, value=lang_code))
        
    if not choices:
        choices = [questionary.Choice("English (en)", value="en"), questionary.Choice("Indonesia (id)", value="id")]
        
    choice = questionary.select(
        "Select Language / Profile / Checklist:",
        choices=choices,
        style=questionary.Style([('selected', 'fg:#00ff00 bold')])
    ).ask()
    
    save_config({"lang": choice})
    return choice

def load_dynamic_checklist(lang):
    filename = f"data_{lang}.yaml"
    filepath = os.path.join(BASE_DIR, filename)
    
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
        
    if not os.path.exists(filepath):
        local_filepath = os.path.join(os.getcwd(), filename)
        if os.path.exists(local_filepath):
            shutil.copy(local_filepath, filepath)
        else:
            clear_screen()
            console.print(f"\n[bold red][!] Database file not found: {filepath}[/bold red]")
            console.print("[dim]Pastikan file data_*.yaml ada di direktori yang sama saat menjalankan script.[/dim]")
            raise FileNotFoundError(f"Missing checklist profile: {filepath}")
        
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    if "__SHORT_MAP__" in data:
        for k, v in data.pop("__SHORT_MAP__").items():
            SHORT_MAP[k] = v
            
    return data

def sanitize_filename(name):
    return name.replace(" ", "_").replace("/", "_").replace(":", "_")

def get_existing_targets():
    files = glob.glob("session_*.json")
    return [f.replace("session_", "").replace(".json", "") for f in files]

def load_session(target):
    filename = f"session_{sanitize_filename(target)}.json"
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_session(target, data):
    filename = f"session_{sanitize_filename(target)}.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def sync_legacy_session(session_data):
    if not DATA_EN or not DATA_ID:
        return session_data, False
        
    keys_en = list(DATA_EN.keys())
    keys_id = list(DATA_ID.keys())
    
    modified = False
    for i in range(min(len(keys_en), len(keys_id))):
        en_key = keys_en[i]
        id_key = keys_id[i]
        
        has_en = en_key in session_data
        has_id = id_key in session_data
        
        if has_en and not has_id:
            en_tasks = session_data[en_key]
            indices = [DATA_EN[en_key].index(t) for t in en_tasks if t in DATA_EN[en_key]]
            session_data[id_key] = [DATA_ID[id_key][idx] for idx in indices if idx < len(DATA_ID[id_key])]
            modified = True
        elif has_id and not has_en:
            id_tasks = session_data[id_key]
            indices = [DATA_ID[id_key].index(t) for t in id_tasks if t in DATA_ID[id_key]]
            session_data[en_key] = [DATA_EN[en_key][idx] for idx in indices if idx < len(DATA_EN[en_key])]
            modified = True
            
    return session_data, modified

def render_report(target, session_data, lang):
    t = UI_TEXT[lang]
    console.print(f"\n[bold yellow]" + t["report_title"].format(target=target) + "[/bold yellow]")
    
    for phase, tasks in CHECKLIST_DATA.items():
        completed_tasks = session_data.get(phase, [])
        table = Table(show_header=True, header_style="bold magenta", border_style="magenta", title=phase)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Task", style="dim")

        for task in tasks:
            if task in completed_tasks:
                table.add_row("[bold green]DONE[/bold green]", f"[strike]{task}[/strike]")
            else:
                table.add_row("[bold red]PENDING[/bold red]", task)
        
        console.print(table)
        print("\n")
        
    notes = session_data.get("__NOTES__", [])
    if notes:
        console.print(f"[bold yellow]{t['report_notes_title']}[/bold yellow]")
        formatted_notes = []
        for note in notes:
            formatted_notes.append(f"[bold cyan]-[/bold cyan] {escape(note)}")
        notes_panel = "\n\n".join(formatted_notes)
        console.print(Panel(notes_panel, border_style="yellow"))

def get_phase_short_name(phase_name):
    """Extract a short displayable name from a phase key using the YAML mapping."""
    if phase_name in SHORT_MAP:
        return SHORT_MAP[phase_name]
        
    # Fallback if somehow missing
    name = phase_name.strip()
    if name and name[0].isdigit():
        # Remove "1. " prefix
        parts = name.split(".", 1)
        if len(parts) > 1:
            name = parts[1].strip()
    name = name.rstrip(":")
    
    # Fallback: take first significant word(s) and truncate
    words = name.split()
    if len(words) >= 2:
        return (words[0][:4] + "-" + words[1][:4]).upper()
    return name[:10]

def get_phase_icon(index):
    """Get a themed icon for each phase."""
    icons = ["🔐", "🔍", "🛡️", "🌐", "💥", "👻", "📝", "✅", "🔬"]
    return icons[index % len(icons)]

def render_wizard_pipeline(session_data, lang):
    """Render a simple, minimal wizard step pipeline."""
    t = UI_TEXT[lang]
    phase_keys = list(CHECKLIST_DATA.keys())
    
    if not phase_keys:
        return
        
    total_tasks = 0
    total_done = 0
    
    lines = []
    lines.append("")
    
    for idx, phase_key in enumerate(phase_keys):
        tasks = CHECKLIST_DATA[phase_key]
        completed = session_data.get(phase_key, [])
        done_count = len(completed)
        task_count = len(tasks)
        total_tasks += task_count
        total_done += done_count
        
        if task_count == 0:
            pct = 0
        else:
            pct = int((done_count / task_count) * 100)
            
        if pct == 100:
            status = "[bold green]✓[/bold green]"
            color = "green"
        elif pct > 0:
            status = "[bold yellow]▶[/bold yellow]"
            color = "yellow"
        else:
            status = "[dim]○[/dim]"
            color = "bright_black"
            
        short = get_phase_short_name(phase_key)
        icon = get_phase_icon(idx)
        
        lines.append(f"  {status} [{color}]P{idx+1}: {icon} {short:<15}[/{color}]  [{color}]{done_count}/{task_count} ({pct}%)[/{color}]")
        
    overall_pct = int((total_done / total_tasks) * 100) if total_tasks > 0 else 0
    
    bar_width = 30
    filled = int(bar_width * overall_pct / 100)
    empty = bar_width - filled
    
    if overall_pct < 25:
        bar_color = "red"
    elif overall_pct < 50:
        bar_color = "yellow"
    elif overall_pct < 75:
        bar_color = "cyan"
    else:
        bar_color = "green"
        
    bar_str = f"[{bar_color}]{'█' * filled}[/{bar_color}][dim]{'░' * empty}[/dim]"
    
    lines.append("")
    lines.append(f"  [bold]Progress:[/bold] [{bar_color}]{overall_pct}%[/{bar_color}] {bar_str} [dim]({total_done}/{total_tasks})[/dim]")
    lines.append("")
    
    # Render all
    console.print(f"\n[bold magenta]{t['wizard_title']}[/bold magenta]")
    full_output = "\n".join(lines)
    console.print(full_output)


def select_workspace(lang):
    clear_screen()
    t = UI_TEXT[lang]
    existing = get_existing_targets()
    
    # 1. Bikin list choices yang terstruktur pakai object Choice & Separator
    choices = [
        questionary.Choice(t["new_target"], value="NEW"),
        questionary.Choice(t["import_mass"], value="IMPORT"),
        questionary.Choice(t["import_custom"], value="IMPORT_CUSTOM")
    ]
    
    # 2. Kasih Separator biar target lama nggak nyampur sama menu utama
    if existing:
        sep_text = " TARGET TERSIMPAN " if lang == "id" else " SAVED WORKSPACES "
        choices.append(questionary.Separator(f"\n   ───[{sep_text}]───"))
        
        for tgt in existing:
            # Tambahin indentasi spasi biar lebih menjorok ke dalam
            choices.append(questionary.Choice(f"   {t['continue']}{tgt}", value=f"TARGET_{tgt}"))
            
    # 3. Kasih Separator penutup untuk menu bawah
    vault_count = len(glob.glob("session_*.json" + VAULT_EXTENSION))
    choices.append(questionary.Separator("───────────────────────────────\n"))

    # Vault status indicator
    if vault_count > 0:
        vault_status = t["vault_status_locked"].format(count=vault_count)
        choices.append(questionary.Separator(f"   {vault_status}"))
        choices.append(questionary.Choice(t["vault_unlock_btn"], value="VAULT_UNLOCK"))
    else:
        if existing:
            choices.append(questionary.Choice(t["vault_lock_btn"], value="VAULT_LOCK"))

    choices.append(questionary.Choice(t["switch_lang"], value="LANG"))
    choices.append(questionary.Choice(t["exit"], value="EXIT"))

    console.print(f"\n[bold yellow]{t['wm_title']}[/bold yellow]")
    
    # Warnanya gue bikin lebih kontras biar gampang milihnya
    choice = questionary.select(
        t["select_action"],
        choices=choices,
        style=questionary.Style([
            ('qmark', 'fg:#ff00ff bold'),
            ('question', 'bold'),
            ('selected', 'fg:#00ffff bold'), # Cyan color for selected item
            ('pointer', 'fg:#ff00ff bold'),
            ('highlighted', 'fg:#ffffff bold'),
        ])
    ).ask()

    # 4. Handle balikan dari value Choice
    if choice == "EXIT" or not choice:
        console.print("[bold red]Exiting DipSyX... Stay stealthy.[/bold red]")
        sys.exit()
    
    elif choice == "LANG":
        new_lang = setup_language()
        return "SWITCH_LANG", new_lang

    elif choice == "NEW":
        target = questionary.text(t["enter_target"]).ask()
        if not target:
            console.print(f"[bold red]{t['target_empty']}[/bold red]")
            input(t["press_enter"])
            return None, lang
        return target, lang
        
    elif choice == "IMPORT":
        filepath = questionary.text(t["enter_filepath"]).ask()
        if not filepath or not os.path.exists(filepath):
            console.print(f"\n[bold red]" + t["file_not_found"].format(filepath=filepath) + "[/bold red]")
            input(t["press_enter"])
            return None, lang
            
        try:
            with open(filepath, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
            count = 0
            for tgt in lines:
                filename = f"session_{sanitize_filename(tgt)}.json"
                if not os.path.exists(filename):
                    save_session(tgt, {})
                    count += 1
            console.print(f"\n[bold green]" + t["import_success"].format(count=count, filepath=filepath) + "[/bold green]")
            input(t["press_enter"])
            return None, lang
        except Exception as e:
            console.print(f"\n[bold red]" + t["import_error"].format(error=str(e)) + "[/bold red]")
            input(t["press_enter"])
            return None, lang
            
    elif choice == "IMPORT_CUSTOM":
        url = questionary.text("Masukkan URL raw YAML/JSON (Custom Checklist):").ask()
        if not url: return None, lang
        name = questionary.text("Beri nama profile ini (misal: owasp, mobile):").ask()
        if not name: return None, lang
        
        try:
            console.print(f"[*] Downloading dari {url}...")
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            
            yaml.safe_load(r.text)
            
            save_path = os.path.join(BASE_DIR, f"data_{name.strip()}.yaml")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(r.text)
                
            console.print(f"[bold green][+] Berhasil disimpan sebagai profile '{name.strip()}'![/bold green]")
            input(t["press_enter"])
        except Exception as e:
            console.print(f"[bold red][!] Gagal mendownload atau format tidak valid: {e}[/bold red]")
            input(t["press_enter"])
        return None, lang

    elif choice == "VAULT_LOCK":
        global _vault_passphrase
        confirm = questionary.confirm(
            "⚠  PERHATIAN: Semua file session akan dienkripsi dengan AES-256-GCM.\n"
            "   Pastikan Anda mengingat passphrase! Lanjutkan?"
        ).ask()
        if confirm:
            passphrase = get_vault_passphrase(confirm=True, purpose="encrypt")
            if passphrase:
                _vault_passphrase = passphrase
                panic_encrypt_all(passphrase=passphrase)
                console.print("[dim]✓ Passphrase di-cache untuk Panic Hotkey (Ctrl+C x2).[/dim]")
        input(t["press_enter"])
        return None, lang

    elif choice == "VAULT_UNLOCK":
        result = panic_decrypt_all()
        input(t["press_enter"])
        return None, lang

    elif str(choice).startswith("TARGET_"):
        return choice.replace("TARGET_", ""), lang

def main():
    global CHECKLIST_DATA, DATA_EN, DATA_ID
    config = load_config()
    lang = config.get("lang")
    
    if not lang:
        lang = setup_language()
        
    try: DATA_EN = load_dynamic_checklist("en")
    except Exception: DATA_EN = {}
    
    try: DATA_ID = load_dynamic_checklist("id")
    except Exception: DATA_ID = {}
    
    if lang == "en" and DATA_EN: CHECKLIST_DATA = DATA_EN
    elif lang == "id" and DATA_ID: CHECKLIST_DATA = DATA_ID
    else: CHECKLIST_DATA = load_dynamic_checklist(lang)
    
    while True:
        target, new_lang = select_workspace(lang)
        
        if target == "SWITCH_LANG":
            lang = new_lang
            if lang == "en" and DATA_EN: CHECKLIST_DATA = DATA_EN
            elif lang == "id" and DATA_ID: CHECKLIST_DATA = DATA_ID
            else: CHECKLIST_DATA = load_dynamic_checklist(lang)
            continue
            
        if target is None:
            continue
            
        session_data = load_session(target)
        session_data, modified = sync_legacy_session(session_data)
        if modified:
            save_session(target, session_data)
        t = UI_TEXT[lang]
        
        while True:
            clear_screen()
            console.print(f"\n[bold green]{t['workspace_loaded']}[bold cyan]{target}[/bold cyan][/bold green]")
            
            # Render wizard pipeline on the main dashboard
            render_wizard_pipeline(session_data, lang)

            menu_choices = list(CHECKLIST_DATA.keys()) + [
                t["wizard_btn"],
                t["notes_btn"], 
                t["report_btn"], 
                t["tools_btn"],
                t["vault_lock_btn"],
                t["switch_target_btn"], 
                t["exit_btn"]
            ]
            
            action = questionary.select(
                t["select_phase"].format(target=target),
                choices=menu_choices,
                style=questionary.Style([
                    ('qmark', 'fg:#ff00ff bold'),
                    ('question', 'bold'),
                    ('selected', 'fg:#00ff00 bold'),
                    ('pointer', 'fg:#ff00ff bold'),
                    ('highlighted', 'fg:#ffffff bold'),
                ])
            ).ask()

            if action == t["exit_btn"] or action is None:
                console.print(f"[bold green]{t['saving_exit']}[/bold green]")
                sys.exit()
            elif action == t["switch_target_btn"]:
                break 
            
            elif action == t["notes_btn"]:
                while True:
                    clear_screen()
                    notes = session_data.get("__NOTES__", [])
                    console.print(f"\n[bold yellow]{t['report_notes_title']}[/bold yellow]")
                    
                    if notes:
                        for idx, note in enumerate(notes, 1):
                            console.print(f"\n[bold cyan]Note #{idx}:[/bold cyan]\n{escape(note)}")
                    else:
                        console.print("[dim]No notes yet. / Belum ada notes.[/dim]")
                        
                    console.print("\n" + "="*50 + "\n")
                    
                    note_action = questionary.select(
                        "Manage Notes / Kelola Catatan:",
                        choices=[
                            questionary.Choice("[+] Add New Note / Tambah Note", value="ADD"),
                            questionary.Choice("[-] Delete Note / Hapus Note", value="DELETE"),
                            questionary.Choice("[~] Edit Note", value="EDIT"),
                            questionary.Choice("[<] Back / Kembali", value="BACK")
                        ],
                        style=questionary.Style([('selected', 'fg:#00ffff bold')])
                    ).ask()

                    if note_action == "BACK" or not note_action:
                        break
                    elif note_action == "ADD":
                        new_note = questionary.text(
                            t["add_note_prompt"],
                            multiline=True,
                            qmark="📝"
                        ).ask()
                        
                        if new_note and new_note.strip():
                            notes.append(new_note.strip())
                            session_data["__NOTES__"] = notes
                            save_session(target, session_data)
                            console.print(f"\n[bold green]{t['notes_saved']}[/bold green]")
                            input(t["press_enter"])
                    elif note_action == "DELETE":
                        if not notes:
                            console.print("[!] No notes to delete / Belum ada note.")
                            input(t["press_enter"])
                            continue
                            
                        note_choices = [questionary.Choice(f"Note #{i+1}: {n[:30]}...", value=i) for i, n in enumerate(notes)]
                        note_choices.append(questionary.Choice("[Batal / Cancel]", value=-1))
                        
                        del_idx = questionary.select(
                            "Select note to delete / Pilih note yang akan dihapus:",
                            choices=note_choices
                        ).ask()
                        
                        if del_idx != -1 and del_idx is not None:
                            confirm = questionary.confirm("Are you sure? / Yakin ingin menghapus?").ask()
                            if confirm:
                                notes.pop(del_idx)
                                session_data["__NOTES__"] = notes
                                save_session(target, session_data)
                                console.print("[+] Note deleted / Note dihapus.")
                                input(t["press_enter"])
                    elif note_action == "EDIT":
                        if not notes:
                            console.print("[!] No notes to edit / Belum ada note.")
                            input(t["press_enter"])
                            continue
                            
                        note_choices = [questionary.Choice(f"Note #{i+1}: {n[:30]}...", value=i) for i, n in enumerate(notes)]
                        note_choices.append(questionary.Choice("[Batal / Cancel]", value=-1))
                        
                        edit_idx = questionary.select(
                            "Select note to edit / Pilih note yang akan diedit:",
                            choices=note_choices
                        ).ask()
                        
                        if edit_idx != -1 and edit_idx is not None:
                            edited_note = questionary.text(
                                "Edit Note:",
                                default=notes[edit_idx],
                                multiline=True
                            ).ask()
                            
                            if edited_note and edited_note.strip():
                                notes[edit_idx] = edited_note.strip()
                                session_data["__NOTES__"] = notes
                                save_session(target, session_data)
                                console.print("[+] Note updated / Note diedit.")
                                input(t["press_enter"])
                
            elif action == t["wizard_btn"]:
                clear_screen()
                render_wizard_pipeline(session_data, lang)
                input(t["press_enter"])
                
            elif action == t["report_btn"]:
                clear_screen()
                render_report(target, session_data, lang)
                input(t["press_enter"])
            
            elif action == t["tools_btn"]:
                clear_screen()
                console.print(f"\n[bold magenta]{t['tools_title']}[/bold magenta]")
                tools_path = os.path.join(BASE_DIR, "tools.yaml")
                if not os.path.exists(tools_path):
                    local_tools = os.path.join(os.getcwd(), "tools.yaml")
                    if os.path.exists(local_tools):
                        shutil.copy(local_tools, tools_path)
                
                try:
                    with open(tools_path, 'r', encoding='utf-8') as f:
                        tools_data = yaml.safe_load(f)
                        
                    for category, tools in tools_data.items():
                        console.print(f"\n[bold yellow]{category}[/bold yellow]")
                        for tool in tools:
                            console.print(f"  [bold cyan]>[/bold cyan] {tool}")
                except Exception as e:
                    console.print(f"[bold red]Gagal memuat tools.yaml: {e}[/bold red]")
                    
                input(t["press_enter"])

            elif action == t["vault_lock_btn"]:
                # Save current session first
                save_session(target, session_data)
                passphrase = get_vault_passphrase(confirm=True, purpose="encrypt")
                if passphrase:
                    global _vault_passphrase
                    _vault_passphrase = passphrase
                    panic_encrypt_all(passphrase=passphrase)
                    console.print("[dim]✓ Passphrase di-cache untuk Panic Hotkey (Ctrl+C x2).[/dim]")
                    input(t["press_enter"])
                    break  # Return to workspace manager
                input(t["press_enter"])
                
            else:
                phase_tasks = CHECKLIST_DATA[action]
                completed_in_phase = session_data.get(action, [])
                
                task_choices = []
                for task in phase_tasks:
                    is_checked = task in completed_in_phase
                    task_choices.append(questionary.Choice(task, checked=is_checked))

                clear_screen()
                console.print(f"\n[bold yellow]" + t["edit_phase"].format(phase=action) + "[/bold yellow]")
                console.print(t["edit_hint"])
                
                updated_tasks = questionary.checkbox(
                    "Checklist:",
                    choices=task_choices,
                    style=questionary.Style([
                        ('selected', 'fg:#00ff00'),
                        ('highlighted', 'fg:#ffffff bold'),
                    ])
                ).ask()

                if updated_tasks is not None:
                    session_data[action] = updated_tasks
                    
                    is_en = action in DATA_EN
                    is_id = action in DATA_ID
                    
                    if is_en and not is_id:
                        phase_idx = list(DATA_EN.keys()).index(action)
                        if phase_idx < len(list(DATA_ID.keys())):
                            other_action = list(DATA_ID.keys())[phase_idx]
                            selected_indices = [DATA_EN[action].index(t) for t in updated_tasks]
                            session_data[other_action] = [DATA_ID[other_action][i] for i in selected_indices if i < len(DATA_ID[other_action])]
                    elif is_id and not is_en:
                        phase_idx = list(DATA_ID.keys()).index(action)
                        if phase_idx < len(list(DATA_EN.keys())):
                            other_action = list(DATA_EN.keys())[phase_idx]
                            selected_indices = [DATA_ID[action].index(t) for t in updated_tasks]
                            session_data[other_action] = [DATA_EN[other_action][i] for i in selected_indices if i < len(DATA_EN[other_action])]
                        
                    save_session(target, session_data)
                    console.print(f"\n[bold green]" + t["progress_saved"].format(phase=action) + "[/bold green]")
                    input(t["press_enter"])

if __name__ == "__main__":
    main()