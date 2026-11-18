# Execute no PowerShell. Sem -Publicar, apenas prepara e mostra a revisao.
[CmdletBinding()]
param(
    [string]$Origem,
    [string]$Repositorio,
    [string]$Branch,
    [string]$Configuracao,
    [string]$Mensagem = 'Atualiza projeto CEHTES SEMA mantendo estrutura de pastas',
    [switch]$Publicar,
    [switch]$VerificarConfiguracao
)

$ErrorActionPreference = 'Stop'
if (-not $Configuracao) { $Configuracao = Join-Path $PSScriptRoot '.env' }
. (Join-Path $PSScriptRoot 'Configuracao-Publicacao.ps1')
$config = Get-ConfiguracaoPublicacao -Arquivo $Configuracao
if (-not $PSBoundParameters.ContainsKey('Origem')) { $Origem = $config.CEHTES_ORIGEM }
if (-not $PSBoundParameters.ContainsKey('Repositorio')) { $Repositorio = $config.CEHTES_REPOSITORIO }
if (-not $PSBoundParameters.ContainsKey('Branch')) { $Branch = $config.CEHTES_BRANCH }
function Invoke-Git {
    param([string[]]$GitArgs)
    & git --no-pager @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "Git falhou (codigo $LASTEXITCODE): $($GitArgs[0])" }
}

Get-Command git, robocopy -ErrorAction Stop | Out-Null
Invoke-Git -GitArgs @('check-ref-format', '--branch', $Branch)
if ($VerificarConfiguracao) {
    [pscustomobject]@{Repositorio=$Repositorio; Branch=$Branch; Origem=$Origem; Usuario=$config.GITHUB_USUARIO}
    return
}
$Origem = (Resolve-Path -LiteralPath $Origem).Path
if (-not (Test-Path -LiteralPath $Origem -PathType Container)) { throw 'Origem deve ser uma pasta.' }
Invoke-Git -GitArgs @('check-ref-format', '--branch', $Branch)

# Trabalha em uma copia isolada; nao altera nem inicializa Git na pasta original.
$Destino = Join-Path ([IO.Path]::GetTempPath()) ('cehtes-publicacao-' + [guid]::NewGuid().ToString('N'))
$sourcePrefix = $Origem.TrimEnd('\') + '\'
if ([IO.Path]::GetFullPath($Destino).StartsWith($sourcePrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'A pasta temporaria nao pode ficar dentro da origem.'
}
$cloneArgs = @('clone', '-c', 'core.longpaths=true', $Repositorio, $Destino)
if ($config.GITHUB_USUARIO) { $cloneArgs = @('-c', "credential.username=$($config.GITHUB_USUARIO)") + $cloneArgs }
Invoke-Git -GitArgs $cloneArgs
Invoke-Git -GitArgs @('-C', $Destino, 'config', 'core.longpaths', 'true')
if ($config.GITHUB_USUARIO) { Invoke-Git -GitArgs @('-C', $Destino, 'config', 'credential.username', $config.GITHUB_USUARIO) }
& git -C $Destino show-ref --verify --quiet "refs/remotes/origin/$Branch"
if ($LASTEXITCODE -eq 0) {
    Invoke-Git -GitArgs @('-C', $Destino, 'switch', '-C', $Branch, "origin/$Branch")
} elseif ($LASTEXITCODE -eq 1) {
    Invoke-Git -GitArgs @('-C', $Destino, 'switch', '-c', $Branch)
} else { throw 'Nao foi possivel verificar a branch remota.' }

# /E preserva subpastas. Nao usa /MIR: arquivos remotos ausentes localmente ficam preservados.
# /XJ evita seguir junctions. Copias de repositorios internos viram pastas comuns sem seu .git.
$pastasExcluidas = @('.git', '.venv', 'venv', 'env', 'node_modules', '__pycache__',
    '.pytest_cache', '.mypy_cache', '.ruff_cache', 'dist', 'build', '.next',
    '.aws', '.ssh', '.codex', '.idea', '.vs')
$arquivosExcluidos = @('.env', '.env.*', '*.pem', '*.key', '*.pfx', '*.p12',
    'credentials.json', 'credentials.ini', 'service-account*.json',
    '*.sqlite', '*.sqlite3', '*.db', '*.pyc', '*.pyo', '*.log', '~$*', '.git')
$log = Join-Path $Destino '.git\copia-local.log'
$copiaArgs = @($Origem, $Destino, '/E', '/XJ', '/R:1', '/W:1', '/COPY:DAT', '/DCOPY:DAT',
    '/NFL', '/NDL', '/NP', "/LOG:$log", '/XD') + $pastasExcluidas + @('/XF') + $arquivosExcluidos
& robocopy @copiaArgs | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Falha na copia. Consulte: $log" }

$ignorePath = Join-Path $Destino '.gitignore'
$ignore = if (Test-Path -LiteralPath $ignorePath) { [IO.File]::ReadAllText($ignorePath) } else { '' }
$regras = @('', '# Arquivos locais excluidos da publicacao CEHTES') +
    ($pastasExcluidas | Where-Object { $_ -ne '.git' } | ForEach-Object { "$_/" }) +
    ($arquivosExcluidos | Where-Object { $_ -ne '.git' })
$existentes = @($ignore -split '\r?\n')
$novasRegras = @($regras | Where-Object { $_ -and $_ -notin $existentes })
if ($novasRegras.Count) {
    [IO.File]::WriteAllText($ignorePath, $ignore.TrimEnd("`r", "`n") + "`n" + ($novasRegras -join "`n") + "`n", [Text.UTF8Encoding]::new($false))
}

& (Join-Path $PSScriptRoot 'Sanitizar-Publicacao.ps1') -Destino $Destino
# .gitignore nao remove arquivos que o remoto ja rastreava.
$ignoradosRastreados = @(Invoke-Git -GitArgs @('-C', $Destino, '-c', 'core.quotepath=false', 'ls-files', '-ci', '--exclude-standard'))
foreach ($arquivo in $ignoradosRastreados) {
    Invoke-Git -GitArgs @('-C', $Destino, 'rm', '--cached', '--', $arquivo)
}
Invoke-Git -GitArgs @('-C', $Destino, 'add', '--all')
# /E conserva os READMEs remotos quando nao existem na origem local.
# Garante que regras de ignore locais nao retirem a documentacao do indice.
foreach ($readme in @('README.md', 'AgenteIA/README.md')) {
    $readmePath = Join-Path $Destino $readme
    if (-not (Test-Path -LiteralPath $readmePath -PathType Leaf) -or (Get-Item -LiteralPath $readmePath).Length -eq 0) {
        throw "README ausente ou vazio: $readme. Publicacao interrompida para preservar a documentacao."
    }
    Invoke-Git -GitArgs @('-C', $Destino, 'add', '--force', '--', $readme)
}
# Verifica o indice inteiro, inclusive arquivos que ja eram rastreados no remoto.
$indice = @(Invoke-Git -GitArgs @('-C', $Destino, 'ls-files', '--stage'))
if ($indice | Where-Object { $_ -match '^160000 ' }) {
    throw "Existem submodulos no repositorio. Revise-os manualmente em $Destino antes de publicar."
}
$objetos = @($indice | ForEach-Object { if ($_ -match '^\d+ ([0-9a-f]+) ') { $Matches[1] } } | Sort-Object -Unique)
if ($objetos.Count -gt 0) {
    $tamanhos = @($objetos | & git -C $Destino cat-file '--batch-check=%(objectname) %(objectsize)')
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel verificar tamanhos.' }
    $grandes = @($tamanhos | Where-Object { [long](($_ -split ' ')[1]) -ge 100MB })
    if ($grandes.Count) { throw "Ha arquivos de 100 MiB ou mais. Configure Git LFS ou exclua-os em $Destino antes de publicar." }
}

Write-Host "`nCopia preparada em: $Destino" -ForegroundColor Cyan
Write-Host "Branch: $Branch"
$resumoPath = Join-Path $Destino '.git\arquivos-para-revisao.txt'
$resumo = @(Invoke-Git -GitArgs @('-C', $Destino, 'diff', '--cached', '--stat', '--no-color'))
[IO.File]::WriteAllLines($resumoPath, [string[]]$resumo, [Text.UTF8Encoding]::new($false))
Invoke-Git -GitArgs @('-C', $Destino, 'diff', '--cached', '--shortstat', '--no-color')
Write-Host "Lista completa dos arquivos: $resumoPath"
Write-Host "`nPara revisar todo o conteudo: git -C `"$Destino`" diff --cached"
Write-Host 'Revise dados pessoais, relatorios, imagens, backups e senhas no codigo; as exclusoes nao substituem essa revisao.'
if (-not $Publicar) {
    Write-Host "`nNada foi enviado. Apos revisar, publique esta MESMA copia com:"
    Write-Host "git -C `"$Destino`" commit -m `"Importa estrutura CEHTES SEMA`""
    Write-Host "git -C `"$Destino`" push -u origin `"$Branch`""
    exit 0
}

$confirmacao = Read-Host 'Revisou os arquivos e autoriza enviar esta branch ao GitHub? Digite PUBLICAR'
if ($confirmacao -cne 'PUBLICAR') { Write-Host 'Envio cancelado; copia local preservada.'; exit 0 }
& git -C $Destino diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Write-Host 'Nenhuma alteracao para enviar.'; exit 0 }
if ($LASTEXITCODE -ne 1) { throw 'Falha ao consultar alteracoes.' }
Invoke-Git -GitArgs @('-C', $Destino, 'commit', '-m', $Mensagem)
Invoke-Git -GitArgs @('-C', $Destino, 'push', '-u', 'origin', $Branch)
Write-Host "Concluido. Branch publicada: $Branch. Estrutura das subpastas e READMEs preservados."
