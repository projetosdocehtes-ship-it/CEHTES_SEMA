@echo off
title Prime Django - Inicializacao

echo ================================
echo   INICIANDO PROJETO DJANGO
echo ================================

REM Ir para a pasta onde este .bat esta salvo
cd /d "%~dp0"

REM Verifica se o venv existe
if not exist venv\Scripts\activate (
    echo [ERRO] Virtualenv nao encontrado!
    pause
    exit /b
)

REM Ativar o ambiente virtual
call venv\Scripts\activate

REM Verifica se Django esta instalado
python -m django --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Django nao instalado no ambiente!
    echo Instalando dependencias...
    pip install -r requirements.txt
)

echo.
echo ================================
echo   PREPARANDO PROJETO...
echo ================================

python manage.py migrate
python manage.py collectstatic --noinput

echo.
echo ================================
echo   SUBINDO SERVIDOR NA PORTA 8001...
echo ================================

start http://127.0.0.1:8001/calendar/
python manage.py runserver 8001

pause