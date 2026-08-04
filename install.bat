@echo off
echo [*] Menginstall dependensi Python (rich, questionary)...
pip install -r requirements.txt

echo [*] Membangun direktori workspace di %USERPROFILE%\.obsidian...
if not exist "%USERPROFILE%\.obsidian" mkdir "%USERPROFILE%\.obsidian"
copy /Y data_id.json "%USERPROFILE%\.obsidian\data_id.json"
copy /Y data_en.json "%USERPROFILE%\.obsidian\data_en.json"

echo [+] Instalasi Selesai! 
echo [+] Jalankan tools dengan perintah: python tracking.py
pause
