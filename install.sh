#!/bin/bash

# Banner instalasi
echo -e "\e[31m"
echo " ▄██████▄  ███▄▄▄▄   ▄██   ▄██ ▀████    ▐████▀ "
echo "███    ███ ███▀▀▀██▄ ███   ███   ███▌   ████▀  "
echo "███    ███ ███   ███ ███▄▄▄███    ███  ▐███    "
echo "███    ███ ███   ███ ▀▀▀▀▀▀███    ▀███▄███▀    "
echo "▀██████▀   ▀█   █▀  ▄██   ███    ████▀██▄     "
echo "                    ▀█████▀    ▀███▀ ▀▀▀▀    "
echo -e "\e[0m"
echo -e "\e[1m[*] Memulai Instalasi ONYX TRACKER Framework...\e[0m\n"

# 1. Setup Direktori Data
echo -e "\e[34m[*]\e[0m Membangun direktori workspace di ~/.onyx..."
mkdir -p ~/.onyx
# Mengcopy file data bahasa ke folder rahasia user
if [ -f "data_id.yaml" ] && [ -f "data_en.yaml" ]; then
    cp data_id.yaml ~/.onyx/data_id.yaml
    cp data_en.yaml ~/.onyx/data_en.yaml
else
    echo -e "\e[31m[!]\e[0m Peringatan: data_id.yaml atau data_en.yaml tidak ditemukan di direktori saat ini!"
fi

# Copy script utama ke ~/.onyx
if [ -f "tracking.py" ]; then
    cp tracking.py ~/.onyx/onyx_core.py
else
    echo -e "\e[31m[!]\e[0m File script Python utama tidak ditemukan!"
    exit 1
fi

# 2. Install Dependencies via Venv
echo -e "\e[34m[*]\e[0m Menginstall dependensi Python (rich, questionary, pyyaml, requests) via virtual environment..."
python3 -m venv ~/.onyx/venv
~/.onyx/venv/bin/pip install -r requirements.txt

# 3. Setup Executable Wrapper
echo -e "\e[34m[*]\e[0m Memasang ONYX ke /usr/local/bin/ (Membutuhkan akses root)..."
cat << 'EOF' > onyx_wrapper.sh
#!/bin/bash
~/.onyx/venv/bin/python ~/.onyx/onyx_core.py "$@"
EOF

sudo mv onyx_wrapper.sh /usr/local/bin/onyxtracker
sudo chmod +x /usr/local/bin/onyxtracker

echo -e "\n\e[32m[+]\e[0m Instalasi Selesai! Ketik \e[1monyxtracker\e[0m di terminal untuk memulai perburuan."
