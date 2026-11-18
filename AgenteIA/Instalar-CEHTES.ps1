# Instalador Windows. Nao altera configuracoes globais nem instala programas como administrador.
[CmdletBinding()]
param(
    [string]$Destino,
    [switch]$IncluirMicrorredes,
    [switch]$PrepararBancoPrime,
    [switch]$VerificarRequisitos
)
$ErrorActionPreference = 'Stop'
$repo = 'https://github.com/projetosdocehtes-ship-it/CEHTES_SEMA.git'
function Executar {
    param([string]$Programa, [string[]]$Argumentos)
    & $Programa @Argumentos | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Falha em $Programa (codigo $LASTEXITCODE). Corrija o erro acima e execute novamente." }
}
function Preparar-Ambiente {
    param([string]$Pasta, [string]$Nome)
    $ambiente = Join-Path $Pasta $Nome
    $python = Join-Path $ambiente 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $ambiente)) {
        Executar 'py' @('-3.12', '-m', 'venv', $ambiente)
    }
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Ambiente incompleto: $ambiente. Renomeie essa pasta e tente novamente; o instalador nao apaga ambientes existentes."
    }
    Executar $python @('-c', 'import sys; assert sys.version_info[:2] == (3,12), "Este instalador exige ambiente Python 3.12"')
    Executar $python @('-m', 'pip', 'install', '--upgrade', 'pip')
    Executar $python @('-m', 'pip', 'install', '-r', (Join-Path $Pasta 'requirements.txt'))
    return $python
}

try {
    foreach ($programa in @('git', 'py', 'node', 'npm.cmd')) {
        if (-not (Get-Command $programa -ErrorAction SilentlyContinue)) {
            throw "Falta $programa. Instale Git, Python 3.12 (com py) e Node.js com npm. Reabra o terminal depois."
        }
    }
    Executar 'git' @('--version')
    & py -3.12 --version | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 nao encontrado pelo inicializador py. Instale Python 3.12 com o launcher e reabra o terminal.' }
    Executar 'node' @('--version')
    Executar 'node' @('-e', 'if(Number(process.versions.node.split(".")[0])<20)process.exit(1)')
    Executar 'npm.cmd' @('--version')
    if ($VerificarRequisitos) {
        Write-Host 'Requisitos basicos encontrados. PostgreSQL e dependencias do projeto ainda precisam ser configurados.'
        exit 0
    }
    if (-not $Destino) {
        $padrao = Join-Path $env:USERPROFILE 'CEHTES_SEMA'
        $Destino = Read-Host "Pasta de instalacao (Enter para $padrao)"
        if (-not $Destino) { $Destino = $padrao }
    }
    $Destino = [IO.Path]::GetFullPath($Destino)
    if (Test-Path -LiteralPath $Destino) {
        if (-not (Test-Path -LiteralPath (Join-Path $Destino '.git'))) {
            throw 'A pasta ja existe e nao e um clone do projeto. Escolha uma pasta nova.'
        }
        $origemGit = & git -C $Destino remote get-url origin
        if ($LASTEXITCODE -ne 0 -or $origemGit -ne $repo) { throw 'O repositorio existente nao corresponde ao CEHTES SEMA.' }
        $branch = & git -C $Destino branch --show-current
        if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') { throw 'A copia existente precisa estar na branch main.' }
        $mudancas = & git -C $Destino status --porcelain
        if ($LASTEXITCODE -ne 0 -or $mudancas) { throw 'Existem alteracoes locais. Preserve ou publique essas alteracoes antes de reinstalar.' }
        Executar 'git' @('-C', $Destino, 'config', 'core.longpaths', 'true')
        Executar 'git' @('-C', $Destino, 'pull', '--ff-only', 'origin', 'main')
    } else {
        Executar 'git' @('clone', '-c', 'core.longpaths=true', '--branch', 'main', $repo, $Destino)
    }
    $agente = Join-Path $Destino 'AgenteIA'
    $prime = Join-Path $agente 'prime-django'
    $backend = Join-Path $agente 'GrafosBess\backend'
    $frontend = Join-Path $agente 'GrafosBess\frontend'
    foreach ($arquivo in @('README.md', 'AgenteIA\README.md', 'AgenteIA\prime-django\requirements.txt', 'AgenteIA\GrafosBess\backend\requirements.txt', 'AgenteIA\GrafosBess\frontend\package.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $Destino $arquivo))) { throw "Clone incompleto: $arquivo" }
    }

    Write-Host 'Preparando GrafosBess...' -ForegroundColor Cyan
    # Saida dos instaladores vai para a tela; a funcao retorna apenas o caminho Python.
    $pythonBackend = Preparar-Ambiente $backend '.venv'
    Executar $pythonBackend @((Join-Path $backend 'manage.py'), 'migrate', '--noinput')
    Executar $pythonBackend @((Join-Path $backend 'manage.py'), 'seed_data')
    Push-Location $frontend
    try {
        if (Test-Path -LiteralPath 'package-lock.json') { Executar 'npm.cmd' @('ci') }
        else { Executar 'npm.cmd' @('install') }
        Executar 'npm.cmd' @('run', 'build')
    } finally { Pop-Location }

    Write-Host 'Preparando Prime Django e Equipamentos...' -ForegroundColor Cyan
    $pythonPrime = Preparar-Ambiente $prime 'venv'
    $envPrime = Join-Path $prime '.env'
    $criado = $false
    if (-not (Test-Path -LiteralPath $envPrime)) {
        $bytes = New-Object byte[] 48
        $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        $chave = [Convert]::ToBase64String($bytes)
        $conteudo = "DEBUG=True`r`nSECRET_KEY=$chave`r`nDB_HOST=127.0.0.1`r`nDB_PORT=5432`r`nDB_NAME=cehtes_sema`r`nDB_USERNAME=CONFIGURAR_LOCALMENTE`r`nDB_PASS=CONFIGURAR_LOCALMENTE`r`n"
        [IO.File]::WriteAllText($envPrime, $conteudo, [Text.UTF8Encoding]::new($false))
        $criado = $true
    }
    if ($IncluirMicrorredes) {
        $micro = Join-Path $agente 'microrredes'
        $pythonMicro = Preparar-Ambiente $micro '.venv'
        Executar $pythonMicro @('-m', 'pip', 'install', '-e', $micro)
    }
    if ($PrepararBancoPrime) {
        if ($criado -or [IO.File]::ReadAllText($envPrime).Contains('CONFIGURAR_LOCALMENTE')) {
            throw "Configure o PostgreSQL em $envPrime e execute novamente com -PrepararBancoPrime."
        }
        Executar $pythonPrime @((Join-Path $prime 'manage.py'), 'check')
        Executar $pythonPrime @((Join-Path $prime 'manage.py'), 'migrate', '--noinput')
        Executar $pythonPrime @((Join-Path $prime 'manage.py'), 'collectstatic', '--noinput')
    }
    Write-Host "`nAmbientes preparados em $Destino" -ForegroundColor Green
    Write-Host "GrafosBess: execute iniciar.bat a partir de $(Join-Path $agente 'GrafosBess'). Abra http://127.0.0.1:5173"
    if (-not $PrepararBancoPrime) {
        Write-Host "PENDENTE: crie o banco PostgreSQL e configure $envPrime. As migracoes do Prime Django ainda nao foram executadas." -ForegroundColor Yellow
    }
    Write-Host "Prime Django: apos configurar o banco, execute $prime\start_cehtes.bat. Abra http://127.0.0.1:8001/calendar/"
    Write-Host 'Dados privados e bancos do computador original nao sao baixados do GitHub.'
} catch {
    Write-Host "`nERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
