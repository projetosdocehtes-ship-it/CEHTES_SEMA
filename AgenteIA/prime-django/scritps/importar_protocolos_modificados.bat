@echo off

cd /d %~dp0

pwsh -NoExit -File ".\importar_protocolos_modificados.ps1"
