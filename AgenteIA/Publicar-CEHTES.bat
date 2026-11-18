@echo off
setlocal
cd /d "%~dp0"
echo Publicacao CEHTES SEMA no GitHub
echo Repositorio, branch e origem serao lidos do arquivo .env nesta pasta.
echo Revise os arquivos antes de digitar PUBLICAR na confirmacao.
echo.
powershell.exe -NoProfile -File "%~dp0Publicar-CEHTES.ps1" -Configuracao "%~dp0.env" -Publicar
if errorlevel 1 (
  echo.
  echo A publicacao nao foi concluida. Consulte a mensagem acima.
  pause
  exit /b 1
)
echo.
pause
endlocal
