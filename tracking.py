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

console = Console()
CHECKLIST_DATA = {}
DATA_EN = {}
DATA_ID = {}
CONFIG_PATH = os.path.expanduser("~/.onyx/config.json")
BASE_DIR = os.path.expanduser("~/.onyx")

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
        "notes_saved": "[+] Notes berhasil disimpen, bro!"
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
        "notes_saved": "[+] Notes saved successfully!"
    }
}

def print_banner():
    banner = """[bold red]
 ▄██████▄  ███▄▄▄▄   ▄██   ▄██ ▀████    ▐████▀ 
███    ███ ███▀▀▀██▄ ███   ███   ███▌   ████▀  
███    ███ ███   ███ ███▄▄▄███    ███  ▐███    
███    ███ ███   ███ ▀▀▀▀▀▀███    ▀███▄███▀    
▀██████▀   ▀█   █▀  ▄██   ███    ████▀██▄     
                    ▀█████▀    ▀███▀ ▀▀▀▀    
    [/bold red][bold white]ONYX TRACKER - Offensive Framework[/bold white]"""
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
        return yaml.safe_load(f)

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
    choices.append(questionary.Separator("───────────────────────────────\n"))
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
        console.print("[bold red]Exiting ONYX... Stay stealthy.[/bold red]")
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

            menu_choices = list(CHECKLIST_DATA.keys()) + [
                t["notes_btn"], 
                t["report_btn"], 
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
                
            elif action == t["report_btn"]:
                clear_screen()
                render_report(target, session_data, lang)
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