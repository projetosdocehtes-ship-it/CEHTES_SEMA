@echo off
title Simulador Usina FV + BESS

echo ===============================
echo INICIANDO SISTEMA COMPLETO
echo ===============================

REM ===== BACKEND =====
echo.
echo Iniciando BACKEND (Django)...

IF NOT EXIST .venv (
echo Criando ambiente virtual...
python -m venv .venv
)

call .venv\Scripts\activate

echo Instalando dependencias...
pip install -r requirements.txt

echo Aplicando migrations...
python manage.py migrate

echo Rodando seed inicial...
python manage.py seed_data

start cmd /k "call .venv\Scripts\activate && python manage.py runserver"


cd ..

REM ===== FRONTEND =====
echo.
echo Iniciando FRONTEND (React)...


cd C:\Cethes\CEHTES_SEMA\CEHTES_SEMA\AgenteIA\prime-django\apps\grafos_bess\frontend



IF NOT EXIST node_modules (
echo Instalando dependencias do frontend...
npm install
)

start cmd /k "npm run dev"



cd ..

echo.
echo ===============================
echo SISTEMA INICIADO COM SUCESSO
echo ===============================
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5173
echo ===============================

pause
