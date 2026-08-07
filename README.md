# DipSyX - Dynamic Information & Pentest System eXploitation

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

DipSyX adalah terminal-based workspace manager dan tracker yang dirancang khusus untuk para penetration tester (pentester) dan bug hunter. Aplikasi ini membantu Anda melacak progres pengujian keamanan pada target tertentu melalui berbagai fase seperti *Information Gathering*, *Vulnerability Analysis*, dan *Exploitation*, lengkap dengan fitur pencatatan temuan (notes) dan pembuatan laporan.

## Fitur Utama

- **Manajemen Target**: Buat target manual atau import secara massal dari file teks.
- **Checklist Fase Pentest**: Lacak progres Anda per fase (berdasarkan standar PTES dan OWASP).
- **Import Custom Checklist**: Bawa checklist YAML sendiri dari URL manapun!
- **Sistem Pencatatan (Notes)**: Catat temuan, eksploitasi, atau catatan penting langsung di dalam sesi target.
- **Laporan Otomatis**: Render laporan progres dan temuan langsung di terminal Anda.
- **Dukungan Multi-Bahasa**: Tersedia dalam Bahasa Indonesia (`id`) dan Bahasa Inggris (`en`).
- **Antarmuka Interaktif**: Menggunakan `rich` dan `questionary` untuk UI terminal yang cantik dan interaktif.

## Prasyarat

Pastikan Anda telah menginstal:
- Python 3.x
- pip (Python Package Installer)

## Instalasi

### Linux / macOS
Jalankan script bash yang tersedia untuk menginstal dependensi dan mengatur DipSyX agar dapat dijalankan secara global:

```bash
chmod +x install.sh
./install.sh
```
Setelah instalasi selesai, Anda dapat menjalankan program dari mana saja dengan mengetik:
```bash
dipsyx
```

### Windows
Jalankan file batch untuk menginstal dependensi dan menyalin file konfigurasi awal:

1. Klik ganda pada file `install.bat` atau jalankan melalui Command Prompt:
```cmd
install.bat
```
2. Untuk menjalankan program, buka terminal di direktori proyek dan jalankan:
```cmd
python tracking.py
```

## Struktur File
- `tracking.py`: Script utama aplikasi.
- `data_en.yaml` / `data_id.yaml`: Basis data checklist berdasarkan fase pentest dalam format YAML yang mudah diedit.
- `requirements.txt`: Dependensi Python (`rich`, `questionary`, `pyyaml`, `requests`).
- `install.sh` / `install.bat`: Script instalasi.
- `~/.dipsyx/`: Direktori konfigurasi dan basis data tersembunyi yang dibuat otomatis.

## Kontribusi

Anda bebas untuk memodifikasi file `data_en.yaml` atau `data_id.yaml` jika ingin menambahkan checklist atau metodologi spesifik Anda sendiri. Format YAML yang didukung sangat mudah disesuaikan.
