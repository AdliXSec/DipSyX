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

# 1. Setup Direktori Data
echo -e "\e[34m[*]\e[0m Membangun direktori workspace di ~/.obsidian..."
mkdir -p ~/.obsidian
# Mengcopy file data bahasa ke folder rahasia user
if [ -f "data_id.json" ] && [ -f "data_en.json" ]; then
    cp data_id.json ~/.obsidian/data_id.json
    cp data_en.json ~/.obsidian/data_en.json
else
    echo -e "\e[31m[!]\e[0m Peringatan: data_id.json atau data_en.json tidak ditemukan di direktori saat ini!"
fi

# Copy script utama ke ~/.obsidian
if [ -f "obsidian.py" ]; then
    cp obsidian.py ~/.obsidian/obsidian_core.py
elif [ -f "tracking.py" ]; then
    cp tracking.py ~/.obsidian/obsidian_core.py
else
    echo -e "\e[31m[!]\e[0m File script Python utama tidak ditemukan!"
    exit 1
fi

# 2. Install Dependencies via Venv
echo -e "\e[34m[*]\e[0m Menginstall dependensi Python (rich, questionary) via virtual environment..."
python3 -m venv ~/.obsidian/venv
~/.obsidian/venv/bin/pip install -r requirements.txt

# 3. Setup Executable Wrapper
echo -e "\e[34m[*]\e[0m Memasang OBSIDIAN ke /usr/local/bin/ (Membutuhkan akses root)..."
cat << 'EOF' > obsidian_wrapper.sh
#!/bin/bash
~/.obsidian/venv/bin/python ~/.obsidian/obsidian_core.py "$@"
EOF

sudo mv obsidian_wrapper.sh /usr/local/bin/obsidian
sudo chmod +x /usr/local/bin/obsidian

echo -e "\n\e[32m[+]\e[0m Instalasi Selesai! Ketik \e[1mobsidian\e[0m di terminal untuk memulai perburuan."
