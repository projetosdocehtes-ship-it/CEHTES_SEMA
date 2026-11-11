@echo off
REM Ativar o ambiente virtual
call .venv\Scripts\activate

REM Iniciar o servidor Django
echo Iniciando o servidor Django...
start cmd /k "python manage.py runserver 0.0.0.0:8000"

REM Iniciar o Celery Worker
echo Iniciando o Celery Worker...
start cmd /k "celery -A prime-RI worker -l info"

REM Iniciar o Celery Beat
echo Iniciando o Celery Beat...
start cmd /k "celery -A prime-RI beat -l info"

REM Esperar até que o usuário feche a janela
pause
