# Aplicar somente na copia temporaria, nunca nos arquivos originais.
param([Parameter(Mandatory=$true)][string]$Destino)
$ErrorActionPreference = 'Stop'
$Destino = (Resolve-Path -LiteralPath $Destino).Path
if ((Split-Path $Destino -Leaf) -notlike 'cehtes-publicacao-*' -or -not (Test-Path -LiteralPath (Join-Path $Destino '.git'))) {
    throw 'Sanitizacao permitida somente na copia de publicacao criada pelo script.'
}
$utf8 = [Text.UTF8Encoding]::new($false)
$patterns = @(
    '\b[ps]k\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
    '(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|sk-proj-[A-Za-z0-9_-]{30,}|sk-[A-Za-z0-9]{40,})',
    '(?m)(?<=-----BEGIN PRIVATE KEY-----)[\s\S]*?(?=-----END PRIVATE KEY-----)'
)
$assignment = '(?im)(\b(?:[a-z0-9_]{0,60}PASSWORD|SECRET_KEY|[a-z0-9_]{0,60}API_KEY|ACCESS_TOKEN)\s*[:=]\s*)(["''])([^"''\r\n]{8,})(\2)'
$envAssignment = '(?im)^(\s*(?:\w*PASSWORD|SECRET_KEY|\w*API_KEY|ACCESS_TOKEN)\s*=\s*)([^\r\n]+)$'
$changed = @()
foreach ($file in Get-ChildItem -LiteralPath $Destino -File -Recurse -Force) {
    if ($file.FullName.StartsWith((Join-Path $Destino '.git') + '\', [StringComparison]::OrdinalIgnoreCase)) { continue }
    if ($file.Name -in @('Sanitizar-Publicacao.ps1', 'Publicar-CEHTES.ps1')) { continue }
    if ($file.Extension -notin @('.py','.js','.jsx','.ts','.tsx','.json','.yaml','.yml','.ini','.cfg','.sample','.example','.txt','.md','.ipynb','.html','.xml','.sql','.toml')) { continue }
    $text = [IO.File]::ReadAllText($file.FullName)
    $new = $text
    if ($new.Contains('AKIA') -or $new.Contains('ghp_') -or $new.Contains('gho_') -or $new.Contains('ghu_') -or $new.Contains('ghs_') -or $new.Contains('ghr_') -or $new.Contains('sk-') -or $new.Contains('sk.') -or $new.Contains('pk.') -or $new.Contains('PRIVATE KEY')) {
        foreach ($pattern in $patterns) { $new = [regex]::Replace($new, $pattern, 'CONFIGURAR_LOCALMENTE') }
    }
    if ($file.Extension -in @('.py','.sample','.example','.ini','.cfg')) {
        $new = [regex]::Replace($new, $assignment, '${1}${2}CONFIGURAR_LOCALMENTE${4}')
    }
    if ($file.Extension -in @('.sample','.example','.ini','.cfg')) {
        $new = [regex]::Replace($new, $envAssignment, '${1}CONFIGURAR_LOCALMENTE')
    }
    if ($file.Extension -eq '.py') {
        $new = [regex]::Replace($new, '(?i)(make_password\(\s*)(["''])[^"''\r\n]+(\2)', '${1}${2}CONFIGURAR_LOCALMENTE${3}')
    }
    if ($new -cne $text) {
        [IO.File]::WriteAllText($file.FullName, $new, $utf8)
        $changed += $file.FullName.Substring($Destino.Length + 1)
    }
}
$report = Join-Path $Destino '.git\sanitizacao.txt'
[IO.File]::WriteAllLines($report, [string[]]$changed, $utf8)
Write-Host "Credenciais substituidas por CONFIGURAR_LOCALMENTE em $($changed.Count) arquivos da copia. Lista: $report"
