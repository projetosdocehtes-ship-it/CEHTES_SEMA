# Navega para o diretório onde o script está localizado
Set-Location -Path $PSScriptRoot

# Exibe o diretório atual
Write-Output "Executando na pasta: $PSScriptRoot"

# Executa o servidor Django
..\venv\Scripts\Activate.ps1
Set-Location ..
python manage.py importar_protocolos_modificados
