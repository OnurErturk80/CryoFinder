@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Tank Haritasi baslatiliyor...
where python >nul 2>nul
if errorlevel 1 (
  echo Python bulunamadi. https://www.python.org/downloads/ adresinden kurun ^(Add Python to PATH isaretli^), sonra tekrar acin.
  pause
  exit /b 1
)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -c "import msal, openpyxl, requests" >nul 2>nul
if errorlevel 1 (
  echo Gerekli paketler yukleniyor ^(yalnizca ilk seferde^)...
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet --only-binary=:all: -r requirements.txt
  if errorlevel 1 ( echo Paket kurulumu basarisiz. & pause & exit /b 1 )
)
if not exist .env copy .env.example .env >nul
findstr /c:"AZURE_CLIENT_ID=0000" .env >nul
if not errorlevel 1 (
  echo AYAR GEREKLI: .env dosyasinda AZURE_CLIENT_ID satirina Client ID yazip kaydedin, sonra tekrar acin.
  notepad .env
  pause
  exit /b 0
)
python -m tank_haritasi gui
echo Program kapandi.
pause
