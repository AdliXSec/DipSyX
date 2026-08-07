@echo off
echo [*] Menginstall dependensi Python (rich, questionary, pyyaml, requests)...
pip install -r requirements.txt

echo [*] Membangun direktori workspace di %USERPROFILE%\.dipsyx...
if not exist "%USERPROFILE%\.dipsyx" mkdir "%USERPROFILE%\.dipsyx"
copy /Y data_id.yaml "%USERPROFILE%\.dipsyx\data_id.yaml"
copy /Y data_en.yaml "%USERPROFILE%\.dipsyx\data_en.yaml"
copy /Y tools.yaml "%USERPROFILE%\.dipsyx\tools.yaml"

echo [+] Instalasi Selesai! 
echo [+] Jalankan tools dengan perintah: python tracking.py
pause
