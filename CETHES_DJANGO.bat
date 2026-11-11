@echo off
REM Vai para a pasta do projeto
cd /d C:\Cethes\CEHTES_SEMA\CEHTES_SEMA\AgenteIA\prime-django

REM (Opcional) Ativa o virtualenv
call venv\Scripts\activate.bat

python manage.py runserver 8001


