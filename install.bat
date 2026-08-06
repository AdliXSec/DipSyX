@echo off
echo [*] Menginstall dependensi Python (rich, questionary, pyyaml, requests)...
pip install -r requirements.txt

echo [*] Membangun direktori workspace di %USERPROFILE%\.onyx...
if not exist "%USERPROFILE%\.onyx" mkdir "%USERPROFILE%\.onyx"
copy /Y data_id.yaml "%USERPROFILE%\.onyx\data_id.yaml"
copy /Y data_en.yaml "%USERPROFILE%\.onyx\data_en.yaml"
copy /Y tools.yaml "%USERPROFILE%\.onyx\tools.yaml"

echo [+] Instalasi Selesai! 
echo [+] Jalankan tools dengan perintah: python tracking.py
pause
