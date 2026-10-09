#!/bin/bash
# Çift tıklayarak başlatın. İlk çalıştırmada gerekli kurulumu kendisi yapar.
cd "$(dirname "$0")" || exit 1
clear
echo "Tank Haritası başlatılıyor..."
pause_exit() { echo; read -n 1 -s -r -p "Çıkmak için bir tuşa basın..."; echo; exit "${1:-0}"; }

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 bulunamadı. https://www.python.org/downloads/ adresinden kurun, sonra bu dosyayı tekrar açın."
  pause_exit 1
fi
# Sanal ortam: 'activate' kullanılmaz (klasör taşınınca bozulur); doğrudan .venv içindeki python kullanılır.
PY=".venv/bin/python"
if [ ! -x "$PY" ] || ! "$PY" -c "import sys" >/dev/null 2>&1; then
  echo "Sanal ortam hazırlanıyor (yalnızca ilk seferde veya bozuksa)..."
  python3 -m venv --clear .venv || { echo "Sanal ortam oluşturulamadı."; pause_exit 1; }
fi
if ! "$PY" -c "import msal, openpyxl, requests" >/dev/null 2>&1; then
  echo "Gerekli paketler yükleniyor (yalnızca ilk seferde, birkaç dakika sürebilir)..."
  "$PY" -m pip install --quiet --upgrade pip
  "$PY" -m pip install --quiet --only-binary=:all: -r requirements.txt || { echo "Paket kurulumu başarısız."; pause_exit 1; }
fi
if [ ! -f .env ] || grep -q "AZURE_CLIENT_ID=0000" .env; then
  [ -f .env ] || cp .env.example .env
  echo
  echo "AYAR GEREKLİ: açılan .env dosyasında AZURE_CLIENT_ID satırına Azure'daki Client ID'nizi yazıp kaydedin."
  echo "Sonra bu dosyayı tekrar çift tıklayın."
  open -e .env 2>/dev/null || ${EDITOR:-nano} .env
  pause_exit 0
fi
echo "Microsoft girişi gerekirse tarayıcı açılır. Program hazır olunca arayüz de açılır."
"$PY" -m tank_haritasi gui
echo
echo "Program kapandı."
pause_exit 0
