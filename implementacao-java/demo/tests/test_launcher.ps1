$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../../Iniciar-TCC.ps1')

$appPath = '/mnt/c/project/TCC-2026/implementacao-java'
$created = [datetime]'2026-11-23T18:00:00Z'
$record = [pscustomobject]@{ process_id = 12345; started_utc = $created.ToUniversalTime().ToString('o') }
$process = [pscustomobject]@{ ProcessId = 12345; Name = 'wsl.exe'; CreationDate = $created;
    CommandLine = "wsl --cd $appPath -- bash -c docker compose up -d && exec docker compose logs --follow" }
if (-not (Test-TccLauncherIdentity $record $process $appPath)) { throw 'Valid launcher was not recognized' }
$serialized = $record | ConvertTo-Json | ConvertFrom-Json
if (-not (Test-TccLauncherIdentity $serialized $process $appPath)) { throw 'Serialized record was not recognized' }
if (Test-TccLauncherIdentity $record $process '/another/project') { throw 'Foreign project accepted' }
$record.process_id = 44444
if (Test-TccLauncherIdentity $record $process $appPath) { throw 'Foreign PID accepted' }
$record.process_id = 12345
$process.CreationDate = $created.AddDays(1)
if (Test-TccLauncherIdentity $record $process $appPath) { throw 'Reused PID accepted' }
$process.CreationDate = $created
$process.CommandLine = 'wsl --cd /another/project -- python3 server.py'
if (Test-TccLauncherIdentity $record $process $appPath) { throw 'Unknown command accepted' }
Write-Host '6 launcher identity checks passed; no process was started or stopped.'
