@echo off
echo [*] Menginstall dependensi Python (rich, questionary, pyyaml, requests)...
pip install -r requirements.txt

echo [*] Membangun direktori workspace di %USERPROFILE%\.dipsyx...
if not exist "%USERPROFILE%\.dipsyx" mkdir "%USERPROFILE%\.dipsyx"
copy /Y data_id.yaml "%USERPROFILE%\.dipsyx\data_id.yaml"
copy /Y data_en.yaml "%USERPROFILE%\.dipsyx\data_en.yaml"
copy /Y tools.yaml "%USERPROFILE%\.dipsyx\tools.yaml"
copy /Y tracking.py "%USERPROFILE%\.dipsyx\dipsyx_core.py"

echo [*] Membuat command 'dipsyx' untuk Windows...
echo @echo off > "%USERPROFILE%\.dipsyx\dipsyx.bat"
echo python "%%~dp0dipsyx_core.py" %%* >> "%USERPROFILE%\.dipsyx\dipsyx.bat"

echo [*] Menambahkan ke Environment Variable PATH...
powershell -Command "$userPath = [Environment]::GetEnvironmentVariable('PATH', 'User'); if ($userPath -notlike '*%USERPROFILE%\.dipsyx*') { [Environment]::SetEnvironmentVariable('PATH', $userPath + ';%USERPROFILE%\.dipsyx', 'User') }"

echo [+] Instalasi Selesai! 
echo [+] Silakan BUKA ULANG terminal (tutup dan buka lagi) CMD/PowerShell Anda.
echo [+] Jalankan tools dengan perintah: dipsyx
pause
