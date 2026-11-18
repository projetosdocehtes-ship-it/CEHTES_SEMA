# Obter o diretório atual do script
$scriptPath = [System.IO.Path]::GetFullPath($MyInvocation.MyCommand.Definition)
$scriptDir = [System.IO.Path]::GetDirectoryName($scriptPath)

# Definir o diretório de destino para o Memcached (um nível acima do diretório do script)
$parentDir = [System.IO.Path]::GetDirectoryName($scriptDir)
$memcachedDir = [System.IO.Path]::Combine($parentDir, "Memcached")

# Criar diretório para Memcached se não existir
if (-not (Test-Path -Path $memcachedDir)) {
    New-Item -ItemType Directory -Path $memcachedDir -Force
}

# Caminho para o arquivo zip do Memcached na pasta 'recursos'
$zipPath = [System.IO.Path]::Combine($scriptDir, "recursos", "memcached-win64-1.4.4-14.zip")

# Extrair arquivo zip do Memcached
Expand-Archive -LiteralPath $zipPath -DestinationPath $memcachedDir -Force

# Ajustar o caminho se o memcached.exe estiver em uma subpasta após a extração
# Remova "subpasta_se_houver" ou substitua pelo nome correto da subpasta
$memcachedExePath = [System.IO.Path]::Combine($memcachedDir, "memcached.exe")

# Verificar se o caminho do memcached.exe existe
if (Test-Path -Path $memcachedExePath) {
    # Instalar o Memcached como um serviço
    Start-Process -FilePath $memcachedExePath -ArgumentList "-d install" -NoNewWindow -Wait
}
else {
    Write-Error "O arquivo memcached.exe não foi encontrado no caminho especificado: $memcachedExePath"
}

# Iniciar o serviço Memcached (opcional, pois o comando de instalação geralmente já inicia o serviço)
Start-Service memcached
