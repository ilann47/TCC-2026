param([ValidateRange(10, 600)][int]$TimeoutSeconds = 120)

$ErrorActionPreference = 'Stop'

function Test-TccLauncherIdentity {
    param($Record, $Process, [string]$LinuxApp)
    if (-not $Record -or -not $Process -or $Process.Name -ne 'wsl.exe') { return $false }
    try {
        $recordTime = ([datetime]$Record.started_utc).ToUniversalTime()
        return ($Record.process_id -eq $Process.ProcessId -and
            $recordTime -eq $Process.CreationDate.ToUniversalTime() -and
            $Process.CommandLine.Contains($LinuxApp) -and
            $Process.CommandLine.Contains('docker compose up -d') -and
            $Process.CommandLine.Contains('docker compose logs --follow'))
    } catch { return $false }
}

function Start-TccLocal {
    param([string]$AppRoot, [int]$WaitSeconds = 120)
    $resolvedApp = [IO.Path]::GetFullPath($AppRoot)
    if (-not (Test-Path -LiteralPath (Join-Path $resolvedApp 'docker-compose.override.yml'))) {
        throw 'Execute o iniciador dentro da copia completa de implementacao-java.'
    }
    $pathOutput = & wsl.exe --exec wslpath -a $resolvedApp
    if ($LASTEXITCODE -ne 0 -or -not $pathOutput) { throw 'Nao foi possivel resolver a pasta do projeto no WSL.' }
    $linuxApp = ([string]$pathOutput).Trim()
    if (-not $linuxApp.StartsWith('/') -or $linuxApp.Contains('"') -or $linuxApp.Contains("`n")) {
        throw 'Nao foi possivel resolver a pasta do projeto no WSL.'
    }
    $runtimeDir = Join-Path $resolvedApp '.runtime/demonstracao/painel'
    [IO.Directory]::CreateDirectory($runtimeDir) | Out-Null
    $recordPath = Join-Path $runtimeDir 'iniciador.json'
    $existing = $null
    if (Test-Path -LiteralPath $recordPath) {
        try {
            $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
            $candidate = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$record.process_id)" -ErrorAction Stop
            if (Test-TccLauncherIdentity $record $candidate $linuxApp) { $existing = $candidate }
        } catch { $existing = $null }
    }
    if (-not $existing) {
        # One Compose startup, then a read-only log follower keeps this WSL session alive.
        # No Python server outside Docker; no registry, firewall or global WSL changes.
        $arguments = @('--cd', ('"' + $linuxApp + '"'), '--exec', 'bash', '-c',
            '"docker compose up -d && exec docker compose logs --follow --no-color --tail 0 painel"')
        $launcher = Start-Process -FilePath 'wsl.exe' -ArgumentList $arguments -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $runtimeDir 'compose-wsl.out.log') `
            -RedirectStandardError (Join-Path $runtimeDir 'compose-wsl.err.log') -PassThru
        $owned = Get-CimInstance Win32_Process -Filter "ProcessId = $($launcher.Id)"
        if (-not $owned) { throw 'O iniciador encerrou antes de preparar o Compose. Consulte compose-wsl.err.log.' }
        @{ process_id = $launcher.Id; started_utc = $owned.CreationDate.ToUniversalTime().ToString('o') } |
            ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding UTF8
        Write-Host 'Iniciando o Compose em segundo plano. Nenhum teste sera executado.'
    } else {
        Write-Host 'O iniciador deste projeto ja esta ativo; nenhuma copia foi criada.'
    }
    $deadline = [datetime]::UtcNow.AddSeconds($WaitSeconds)
    while ([datetime]::UtcNow -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri 'http://localhost:5666/api/state' -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200 -and [string]$response.Headers['Server'] -like 'TCCDemo/*') {
                Write-Host 'Demonstracao: http://localhost:5666/'
                Write-Host 'Modo Banca:   http://localhost:5666/resultados'
                Write-Host 'Painel no Docker; servicos preparados pelo Compose. Use Verificar servicos antes de uma carga.'
                return
            }
        } catch { }
        Start-Sleep -Milliseconds 750
    }
    throw 'O painel ainda nao respondeu. Consulte .runtime/demonstracao/painel/compose-wsl.err.log e docker compose ps. Nenhuma carga foi iniciada.'
}

if ($MyInvocation.InvocationName -ne '.') {
    Start-TccLocal -AppRoot $PSScriptRoot -WaitSeconds $TimeoutSeconds
}
