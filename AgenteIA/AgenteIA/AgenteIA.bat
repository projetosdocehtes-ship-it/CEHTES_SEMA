@echo off
setlocal enabledelayedexpansion

REM Vai para a pasta principal
cd /d C:\Cethes\CEHTES_SEMA\CEHTES_SEMA\AgenteIA\agente_ia_web_pdf

REM Ativa o ambiente virtual
call venv\Scripts\activate


REM Executa o Streamlit
streamlit run app.py

REM Mantém o prompt aberto após o término
pause
