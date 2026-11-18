# Criar o ambiente virtual em um diretório chamado .venv
python -m venv .venv

# Ativar o ambiente virtual
.venv\Scripts\Activate.ps1

# Instalar dependências do projeto
Get-Content requirements.txt | ForEach-Object {
    try {
        pip install $_
    }
    catch {
        Write-Error "Falha ao instalar o pacote $_"
    }
}
