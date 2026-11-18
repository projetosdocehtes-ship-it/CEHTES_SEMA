# Instalação do Chocolatey
if (-Not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Set-ExecutionPolicy Bypass -Scope Process -Force;
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072;
    iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'));
}

# Atualiza o Chocolatey
choco upgrade chocolatey -y

# Instala Python
choco install python -y

# Instala PostgreSQL
# Definir variáveis para o instalador
$installerPath = "$env:TEMP\postgresql_installer.exe"
$installerUrl = "https://get.enterprisedb.com/postgresql/postgresql-16.0-1-windows-x64.exe" # Atualize a URL conforme necessário
$installPath = "C:\Program Files\PostgreSQL\16" # Ou o caminho de sua preferência
$port = "5432"
$password = "gcMwsptdHVHVAL2YYZq9FENx7s7VYHdrV4Bjm9B3cmmRXuv9Q7ojLixJWh"
$dataPath = "C:\Program Files\PostgreSQL\16\data" # Ajuste conforme necessário

# Baixar o instalador do PostgreSQL
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

# Executar o instalador com os parâmetros especificados
Start-Process -FilePath $installerPath -ArgumentList "--mode unattended --unattendedmodeui minimal --data-dir `"$dataPath`" --install_runtimes 0 --serverport $port --superpassword `"$password`" --prefix `"$installPath`"" -Wait -NoNewWindow

Stop-Service -Name postgresql-x64-16 -Force

#Remove-Item -Path "C:/Program Files/PostgreSQL/16/data/*" -Recurse -Force

#& "C:\Program Files\PostgreSQL\16\bin\initdb.exe" -D "C:\Program Files\PostgreSQL\16\data" -E UTF8 --locale=pt_BR.UTF-8 -U postgres

Start-Service -Name postgresql-x64-16

Start-Sleep -s 10


choco install irfanview -y
choco install 7zip.install -y
choco install vscode -y
choco install powershell-core -y
choco install libreoffice-fresh -y
choco install git -y
choco install tortoisegit -y
choco install github -y
choco install memcached -y

# Comando para criar o banco de dados "cartorio"
$createDbCommand = "CREATE DATABASE cartorio;"

# Executar o comando psql para criar o banco de dados
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c $createDbCommand

# Instalar dependências do projeto
Get-Content requirements.txt | ForEach-Object {
    try {
        pip install $_
    }
    catch {
        Write-Error "Falha ao instalar o pacote $_"
    }
}

# Construir o caminho para o script
$scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "install_memcached.ps1"

# Executar o script install_memcached
Invoke-Expression -Command $scriptPath

# Executar migrações do Django
python manage.py migrate auth

python manage.py migrate

# Coletar arquivos estáticos
python manage.py collectstatic --noinput

code --install-extension 076923.python-image-preview
code --install-extension aaron-bond.better-comments
code --install-extension anteprimorac.html-end-tag-labels
code --install-extension atishay-jain.all-autocomplete
code --install-extension batisteo.vscode-django
code --install-extension bibhasdn.django-html
code --install-extension charliermarsh.ruff
code --install-extension christian-kohler.path-intellisense
code --install-extension dbalage.vscode-stylesheet-formatter
code --install-extension donjayamanne.python-environment-manager
code --install-extension donjayamanne.python-extension-pack
code --install-extension drcika.apc-extension
code --install-extension eamodio.gitlens
code --install-extension ecmel.vscode-html-css
code --install-extension fabiospampinato.vscode-git-history
code --install-extension formulahendry.auto-close-tag
code --install-extension formulahendry.auto-complete-tag
code --install-extension formulahendry.auto-rename-tag
code --install-extension github.copilot
code --install-extension github.copilot-chat
code --install-extension gruntfuggly.todo-tree
code --install-extension ibm.output-colorizer
code --install-extension jerryhong.autofilename
code --install-extension joy-yu.css-snippets
code --install-extension mechatroner.rainbow-csv
code --install-extension mhutchie.git-graph
code --install-extension miguelsolorio.min-theme
code --install-extension miguelsolorio.symbols
code --install-extension mikestead.dotenv
code --install-extension monosans.djlint
code --install-extension ms-ceintl.vscode-language-pack-pt-br
code --install-extension ms-dotnettools.csharp
code --install-extension ms-dotnettools.vscode-dotnet-runtime
code --install-extension ms-python.debugpy
code --install-extension ms-python.mypy-type-checker
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension ms-vscode-remote.remote-ssh
code --install-extension ms-vscode-remote.remote-ssh-edit
code --install-extension ms-vscode-remote.vscode-remote-extensionpack
code --install-extension ms-vscode.powershell
code --install-extension ms-vscode.remote-explorer
code --install-extension ms-vscode.remote-repositories
code --install-extension ms-vscode.remote-server
code --install-extension mtxr.sqltools
code --install-extension nilssoderman.batch-runner
code --install-extension oderwat.indent-rainbow
code --install-extension sid200026.django-snippets
code --install-extension stuart.unique-window-colors
code --install-extension stylelint.vscode-stylelint
code --install-extension visualstudioexptteam.intellicode-api-usage-examples
code --install-extension visualstudioexptteam.vscodeintellicode
code --install-extension wolfieshorizon.python-auto-venv


Write-Host "Configuração concluída."
