@echo off
setlocal
title Instalacao CEHTES SEMA
if not exist "%~dp0Instalar-CEHTES.ps1" (
  echo Baixe Instalar-CEHTES.bat e Instalar-CEHTES.ps1 na mesma pasta.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Instalar-CEHTES.ps1" %*
set "resultado=%errorlevel%"
echo.
if not "%resultado%"=="0" echo Instalacao incompleta. Corrija o erro indicado e execute novamente.
pause
exit /b %resultado%
