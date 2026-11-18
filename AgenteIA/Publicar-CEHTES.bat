@echo off
setlocal
cd /d "%~dp0"
echo Publicacao CEHTES SEMA no GitHub
echo Destino: main. Repositorio e origem serao lidos do .env nesta pasta.
echo Revise os arquivos antes de digitar PUBLICAR na confirmacao.
echo.
powershell.exe -NoProfile -File "%~dp0Publicar-CEHTES.ps1" -Configuracao "%~dp0.env" -Branch main -Publicar
if errorlevel 1 (
  echo.
  echo A publicacao nao foi concluida. Consulte a mensagem acima.
  pause
  exit /b 1
)
echo.
pause
endlocal
