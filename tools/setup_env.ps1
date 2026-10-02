<#
.SYNOPSIS
  Cria um ambiente isolado por subprojeto no Windows (equivalente a tools/setup_env.sh).

.DESCRIPTION
  Usa environments/<nome>.windows.lock.txt (mesmas versões do lock de Linux, resolvidas para win_amd64 por
  tools/lock_windows.sh). Ambientes sem lock de Windows dependem de pacotes só para Linux (GPU/triton, LAMMPS com
  MPI): use o WSL2 para eles. Requer o uv (recomendado: também instala a versão certa do Python) ou, na falta dele,
  o lançador "py" com a versão de Python do ambiente. Ambientes "conda" usam mamba/micromamba/conda.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup_env.ps1 -List
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup_env.ps1 core
  .\.venvs\core\Scripts\Activate.ps1
  python -m pytest code\tests -q
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup_env.ps1 core -Latest   # resolve core.in (versões novas)
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$Name,
    [switch]$List,
    [switch]$Latest
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$EnvDir = Join-Path $Root 'environments'
$Table = Join-Path $EnvDir 'envs.tsv'
if (-not $env:SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BOCODE) { $env:SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BOCODE = '0.0.0' }
$env:PYTHONUTF8 = '1'   # os scripts do projeto leem e escrevem UTF-8 (acentos nos CSV/Markdown)

function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "falhou ($LASTEXITCODE): $Exe $($Arguments -join ' ')" }
}

$rows = Get-Content $Table -Encoding UTF8 | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object {
    $f = $_ -split "`t"
    [pscustomobject]@{ Name = $f[0]; Type = $f[1]; Python = $f[2]; Spec = $f[3]; Desc = $f[4] }
}

if ($List -or -not $Name) {
    foreach ($r in $rows) {
        $win = if ($r.Type -eq 'conda') { 'conda' }
               elseif (Test-Path (Join-Path $EnvDir "$($r.Name).windows.lock.txt")) { 'Windows ok' }
               else { 'so WSL2' }
        '{0,-14} {1,-6} py{2,-5} {3,-11} {4}' -f $r.Name, $r.Type, $r.Python, $win, $r.Desc
    }
    if (-not $Name) { Write-Host "`nUso: tools\setup_env.ps1 <nome> [-Latest]" }
    exit 0
}

$row = $rows | Where-Object { $_.Name -eq $Name } | Select-Object -First 1
if (-not $row) { throw "Ambiente desconhecido: $Name (veja -List)" }

Push-Location $EnvDir   # caminhos relativos (-e ../projects/...) são resolvidos a partir daqui
try {
    if ($row.Type -eq 'conda') {
        $tool = @('mamba', 'micromamba', 'conda') | ForEach-Object { Get-Command $_ -ErrorAction SilentlyContinue } |
            Select-Object -First 1
        if (-not $tool) { throw "Precisa de conda/mamba para '$Name' ($($row.Spec))" }
        Invoke-Checked $tool.Source @('env', 'create', '-n', $Name, '-f', $row.Spec)
        Write-Host "Pronto: conda activate $Name"
        return
    }
    $winLock = "$Name.windows.lock.txt"
    if ($Latest) {
        $req = $row.Spec
    } elseif (Test-Path $winLock) {
        $req = $winLock
    } else {
        throw ("'$Name' nao tem lock para Windows: depende de pacotes so para Linux (GPU/triton ou LAMMPS com MPI). " +
               "Use o WSL2 (wsl --install) e, dentro dele: tools/setup_env.sh $Name")
    }
    $venv = Join-Path $Root ".venvs\$Name"
    $py = Join-Path $venv 'Scripts\python.exe'
    $ovr = @()
    if (Test-Path "$Name.override.txt") { $ovr = @('--override', "$Name.override.txt") }
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        Invoke-Checked $uv.Source @('venv', '-p', $row.Python, $venv)
        Invoke-Checked $uv.Source (@('pip', 'install', '--python', $py, '-r', $req) + $ovr)
    } else {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if (-not $launcher) {
            throw ('Instale o uv (recomendado): powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"' +
                   " ou o Python $($row.Python) com o lancador py")
        }
        Invoke-Checked $launcher.Source @("-$($row.Python)", '-m', 'venv', $venv)
        Invoke-Checked $py @('-m', 'pip', 'install', '-U', 'pip')
        $nodeps = @()
        if ($ovr.Count -gt 0 -and -not $Latest) { $nodeps = @('--no-deps') }   # o lock já está completo
        Invoke-Checked $py (@('-m', 'pip', 'install', '-r', $req) + $nodeps)
    }
    Write-Host "Pronto ($($row.Desc)): .\.venvs\$Name\Scripts\Activate.ps1"
} finally {
    Pop-Location
}
