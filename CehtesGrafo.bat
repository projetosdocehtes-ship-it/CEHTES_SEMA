@echo off
title INICIAR TODOS OS SISTEMAS

echo ====================================
echo INICIANDO GRAFOSBESS E PRIME-DJANGO
echo ====================================

REM ===== GRAFOSBESS =====
echo.
echo Iniciando GrafosBess...

cd C:\Cethes\CEHTES_SEMA\CEHTES_SEMA\AgenteIA\GrafosBess\

start "" "C:\Cethes\CEHTES_SEMA\CEHTES_SEMA\AgenteIA\GrafosBess\iniciar.bat"

timeout /t 3 >nul

REM ===== PRIME DJANGO =====
echo.
echo Iniciando Prime Django...

cd C:\Cethes\CEHTES_SEMA\CEHTES_SEMA\AgenteIA\prime-django\s

start "" "C:\Cethes\CEHTES_SEMA\CEHTES_SEMA\AgenteIA\prime-django\start_cehtes.bat"

echo.
echo ====================================
echo SISTEMAS INICIADOS
echo ====================================

pause
