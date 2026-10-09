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
set PY=.venv\Scripts\python.exe
set NEEDVENV=0
if not exist "%PY%" set NEEDVENV=1
if exist "%PY%" ( "%PY%" -c "import sys" >nul 2>nul || set NEEDVENV=1 )
if "%NEEDVENV%"=="1" (
  echo Sanal ortam hazirlaniyor...
  python -m venv --clear .venv
  if errorlevel 1 ( echo Sanal ortam olusturulamadi. & pause & exit /b 1 )
)
"%PY%" -c "import msal, openpyxl, requests" >nul 2>nul
if errorlevel 1 (
  echo Gerekli paketler yukleniyor ^(yalnizca ilk seferde^)...
  "%PY%" -m pip install --quiet --upgrade pip
  "%PY%" -m pip install --quiet --only-binary=:all: -r requirements.txt
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
"%PY%" -m tank_haritasi gui
echo Program kapandi.
pause
