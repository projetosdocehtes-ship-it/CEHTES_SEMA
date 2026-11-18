[CmdletBinding()]
param([string]$Configuracao, [switch]$VerificarConfiguracao)
$ErrorActionPreference = 'Stop'
if (-not $Configuracao) { $Configuracao = Join-Path $PSScriptRoot '.env' }
. (Join-Path $PSScriptRoot 'Configuracao-Publicacao.ps1')
$config = Get-ConfiguracaoPublicacao -Arquivo $Configuracao
$destino = $config.CEHTES_COPIA_REVISADA
if (-not $destino) { throw 'Preencha CEHTES_COPIA_REVISADA no .env.' }
if ($VerificarConfiguracao) { [pscustomobject]@{Repositorio=$config.CEHTES_REPOSITORIO; Branch=$config.CEHTES_BRANCH; Copia=$destino; Usuario=$config.GITHUB_USUARIO}; return }
if (-not (Test-Path -LiteralPath (Join-Path $destino '.git'))) { throw 'Copia revisada nao encontrada. Use Publicar-CEHTES.bat para preparar outra.' }
$remoto = & git -C $destino remote get-url origin
if ($LASTEXITCODE -ne 0 -or $remoto -cne $config.CEHTES_REPOSITORIO) { throw 'O repositorio da copia difere do .env. Nenhum envio realizado.' }
$branch = & git -C $destino branch --show-current
if ($LASTEXITCODE -ne 0 -or $branch -cne $config.CEHTES_BRANCH) { throw 'A branch da copia difere do .env. Nenhum envio realizado.' }
$argsGit = @('-C', $destino)
if ($config.GITHUB_USUARIO) { $argsGit += @('-c', "credential.username=$($config.GITHUB_USUARIO)") }
& git @argsGit push -u origin $config.CEHTES_BRANCH
if ($LASTEXITCODE -ne 0) { throw 'Envio nao concluido. Confira a autenticacao e a permissao de escrita no GitHub.' }
Write-Host 'Publicacao concluida.'
