#!/bin/bash

# Banner instalasi
echo -e "\e[35m"
echo " ██████╗ ██████╗ ███████╗██╗██████╗ ██╗ █████╗ ███╗   ██╗"
echo "██╔═══██╗██╔══██╗██╔════╝██║██╔══██╗██║██╔══██╗████╗  ██║"
echo "██║   ██║██████╔╝███████╗██║██║  ██║██║███████║██╔██╗ ██║"
echo "██║   ██║██╔══██╗╚════██║██║██║  ██║██║██╔══██║██║╚██╗██║"
echo "╚██████╔╝██████╔╝███████║██║██████╔╝██║██║  ██║██║ ╚████║"
echo " ╚═════╝ ╚═════╝ ╚══════╝╚═╝╚═════╝ ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝"
echo -e "\e[0m"
echo -e "\e[1m[*] Memulai Instalasi OBSIDIAN Framework...\e[0m\n"

# 1. Install Dependencies
echo -e "\e[34m[*]\e[0m Menginstall dependensi Python (rich, questionary)..."
pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt

# 2. Setup Direktori Data
echo -e "\e[34m[*]\e[0m Membangun direktori workspace di ~/.obsidian..."
mkdir -p ~/.obsidian
# Mengcopy file data bahasa ke folder rahasia user
if [ -f "data_id.txt" ] && [ -f "data_en.txt" ]; then
    cp data_id.txt ~/.obsidian/data_id.txt
    cp data_en.txt ~/.obsidian/data_en.txt
else
    echo -e "\e[31m[!]\e[0m Peringatan: data_id.txt atau data_en.txt tidak ditemukan di direktori saat ini!"
fi

# 3. Setup Executable
echo -e "\e[34m[*]\e[0m Memasang OBSIDIAN ke /usr/local/bin/ (Membutuhkan akses root)..."
# Pastikan nama file python utama lo bener (disini gue asumsikan namanya tracking.py atau obsidian.py, sesuaikan aja)
if [ -f "obsidian.py" ]; then
    sudo cp obsidian.py /usr/local/bin/obsidian
    sudo chmod +x /usr/local/bin/obsidian
elif [ -f "tracking.py" ]; then
    sudo cp tracking.py /usr/local/bin/obsidian
    sudo chmod +x /usr/local/bin/obsidian
else
    echo -e "\e[31m[!]\e[0m File script Python utama tidak ditemukan!"
    exit 1
fi

echo -e "\n\e[32m[+]\e[0m Instalasi Selesai! Ketik \e[1mobsidian\e[0m di terminal untuk memulai perburuan."
