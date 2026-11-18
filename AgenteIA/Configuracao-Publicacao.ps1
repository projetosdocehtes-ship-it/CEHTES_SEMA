function Get-ConfiguracaoPublicacao {
    param([Parameter(Mandatory=$true)][string]$Arquivo)
    if (-not (Test-Path -LiteralPath $Arquivo -PathType Leaf)) { throw "Configuracao nao encontrada: $Arquivo" }
    $config = @{}
    $permitidas = @('CEHTES_REPOSITORIO','CEHTES_BRANCH','CEHTES_ORIGEM','CEHTES_COPIA_REVISADA','GITHUB_USUARIO')
    foreach ($linha in [IO.File]::ReadAllLines($Arquivo)) {
        $linha = $linha.Trim()
        if (-not $linha -or $linha.StartsWith('#')) { continue }
        if ($linha -notmatch '^([A-Z_]+)\s*=(.*)$') { throw 'Linha invalida no .env. Use CHAVE=valor.' }
        $chave, $valor = $Matches[1], $Matches[2].Trim()
        if ($chave -notin $permitidas) { throw "Chave nao suportada no .env: $chave" }
        if ($config.ContainsKey($chave)) { throw "Chave repetida no .env: $chave" }
        if ($valor.Length -ge 2 -and (($valor.StartsWith('"') -and $valor.EndsWith('"')) -or ($valor.StartsWith("'") -and $valor.EndsWith("'")))) {
            $valor = $valor.Substring(1, $valor.Length - 2)
        }
        $config[$chave] = $valor
    }
    foreach ($chave in @('CEHTES_REPOSITORIO','CEHTES_BRANCH','CEHTES_ORIGEM')) {
        if (-not $config[$chave]) { throw "Preencha $chave no .env." }
    }
    if ($config.CEHTES_REPOSITORIO -notmatch '^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$') {
        throw 'Use uma URL HTTPS do GitHub sem senha, token ou virgula final.'
    }
    if ($config.GITHUB_USUARIO -and $config.GITHUB_USUARIO -notmatch '^[A-Za-z0-9][A-Za-z0-9-]*$') { throw 'Login GitHub invalido.' }
    # Valores sao dados literais. Nao executar nem expandir comandos do .env.
    return $config
}
