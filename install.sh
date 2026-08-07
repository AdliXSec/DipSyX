#!/bin/bash

# Banner instalasi
echo -e "\e[31m"
echo " ▓█████▄  ██▓ ██▓███    ██████ ▓██   ██▓ ▒██   ██▒"
echo " ▒██▀ ██▌▓██▒▓██░  ██▒▒██    ▒  ▒██  ██▒ ▒▒ █ █ ▒░"
echo " ░██   █▌▒██▒▓██░ ██▓▒░ ▓██▄     ▒██ ██░ ░░  █   ░"
echo " ░▓█▄   ▌░██░▒██▄█▓▒ ▒  ▒   ██▒  ░ ▐██▓░  ░ █ █ ▒ "
echo " ░▒████▓ ░██░▒██▒ ░  ░▒██████▒▒  ░ ██▒▓░ ▒██▒ ▒██▒"
echo "  ▒▒▓  ▒ ░▓  ▒▓▒░ ░  ░▒ ▒▓▒ ▒ ░   ██▒▒▒  ▒▒ ░ ░▓ ░"
echo -e "\e[0m"
echo -e "\e[1m[*] Memulai Instalasi DipSyX Framework...\e[0m\n"

# 1. Setup Direktori Data
echo -e "\e[34m[*]\e[0m Membangun direktori workspace di ~/.dipsyx..."
mkdir -p ~/.dipsyx
# Mengcopy file data bahasa ke folder rahasia user
if [ -f "data_id.yaml" ] && [ -f "data_en.yaml" ] && [ -f "tools.yaml" ]; then
    cp data_id.yaml ~/.dipsyx/data_id.yaml
    cp data_en.yaml ~/.dipsyx/data_en.yaml
    cp tools.yaml ~/.dipsyx/tools.yaml
else
    echo -e "\e[31m[!]\e[0m Peringatan: data_id.yaml, data_en.yaml atau tools.yaml tidak ditemukan di direktori saat ini!"
fi

# Copy script utama ke ~/.dipsyx
if [ -f "tracking.py" ]; then
    cp tracking.py ~/.dipsyx/dipsyx_core.py
else
    echo -e "\e[31m[!]\e[0m File script Python utama tidak ditemukan!"
    exit 1
fi

# 2. Install Dependencies via Venv
echo -e "\e[34m[*]\e[0m Menginstall dependensi Python (rich, questionary, pyyaml, requests) via virtual environment..."
python3 -m venv ~/.dipsyx/venv
~/.dipsyx/venv/bin/pip install -r requirements.txt

# 3. Setup Executable Wrapper
echo -e "\e[34m[*]\e[0m Memasang DipSyX ke /usr/local/bin/ (Membutuhkan akses root)..."
cat << 'EOF' > dipsyx_wrapper.sh
#!/bin/bash
~/.dipsyx/venv/bin/python ~/.dipsyx/dipsyx_core.py "$@"
EOF

sudo mv dipsyx_wrapper.sh /usr/local/bin/dipsyx
sudo chmod +x /usr/local/bin/dipsyx

echo -e "\n\e[32m[+]\e[0m Instalasi Selesai! Ketik \e[1mdipsyx\e[0m di terminal untuk memulai perburuan."
