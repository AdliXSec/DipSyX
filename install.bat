@echo off
echo [*] Menginstall dependensi Python (rich, questionary)...
pip install -r requirements.txt

echo [*] Membangun direktori workspace di %USERPROFILE%\.obsidian...
if not exist "%USERPROFILE%\.obsidian" mkdir "%USERPROFILE%\.obsidian"
copy /Y data_id.txt "%USERPROFILE%\.obsidian\data_id.txt"
copy /Y data_en.txt "%USERPROFILE%\.obsidian\data_en.txt"

echo [+] Instalasi Selesai! 
echo [+] Jalankan tools dengan perintah: python tracking.py
pause
