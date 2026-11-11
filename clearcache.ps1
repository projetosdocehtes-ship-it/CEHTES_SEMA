# Define o diretório atual como ponto de partida
$StartDirectory = Get-Location

# Procura por todas as pastas '__pycache__' a partir do diretório atual, recursivamente
$PycacheDirectories = Get-ChildItem -Path $StartDirectory -Recurse -Directory -Filter "__pycache__"

# Remove cada pasta '__pycache__' encontrada
foreach ($Dir in $PycacheDirectories) {
    Remove-Item -Path $Dir.FullName -Recurse -Force
    Write-Host "Removed: $($Dir.FullName)"
}

# Procura por todos os arquivos '.pyc' a partir do diretório atual, recursivamente
$PycFiles = Get-ChildItem -Path $StartDirectory -Recurse -Filter "*.pyc"

# Remove cada arquivo '.pyc' encontrado
foreach ($File in $PycFiles) {
    Remove-Item -Path $File.FullName -Force
    Write-Host "Removed: $($File.FullName)"
}

Write-Host "Cache do Python limpo ."
