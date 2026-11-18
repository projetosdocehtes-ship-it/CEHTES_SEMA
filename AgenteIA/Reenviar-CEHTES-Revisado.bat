@echo off
setlocal
cd /d "%~dp0"
echo Reenvia o commit revisado para a branch de importacao.
echo A conta autenticada deve ter permissao de escrita no repositorio.
powershell.exe -NoProfile -File "%~dp0Reenviar-CEHTES-Revisado.ps1" -Configuracao "%~dp0.env"
if errorlevel 1 (
  echo O GitHub recusou ou nao concluiu o envio. Confira o acesso da conta e a mensagem acima.
  pause
  exit /b 1
)
echo Publicacao concluida.
pause
endlocal
