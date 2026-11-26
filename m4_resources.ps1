# Example: .\m4_resources.ps1 -Seconds 600 -Out 'D:\evidence\run-01'
[CmdletBinding()]
param(
    [ValidateRange(1, 2147483647)]
    [int]$Seconds = 600,
    [string]$Out
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($Out)) {
    $Out = Join-Path $PSScriptRoot ("evidence\m4-{0}-{1}" -f (Get-Date -Format 'yyyyMMdd-HHmmss'), [guid]::NewGuid())
}
$python = Join-Path $env:LOCALAPPDATA 'nidh-venv\Scripts\python.exe'
$baseline = Join-Path $PSScriptRoot 'm4_baseline.py'
$reconcile = Join-Path $PSScriptRoot 'm4_reconcile.py'
foreach ($file in @($python, $baseline, $reconcile)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Required file is missing: $file"
    }
}
$docker = (Get-Command docker.exe -CommandType Application).Source
$runPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Out)
# New-Item without -Force rejects an existing directory, including a concurrent run.
$run = New-Item -ItemType Directory -Path $runPath
Write-Host "Collecting in $($run.FullName)"
$computer = Get-CimInstance Win32_ComputerSystem
$processors = Get-CimInstance Win32_Processor
$volume = Get-Volume -FilePath $run.FullName
$dockerInfo = & $docker info --format '{{json .}}'
if ($LASTEXITCODE -ne 0) { throw 'Could not read Docker engine limits.' }
$engine = $dockerInfo | ConvertFrom-Json
$revision = if (Get-Command git.exe -ErrorAction SilentlyContinue) {
    & git.exe -C $PSScriptRoot rev-parse HEAD
}
[ordered]@{
    collected_utc = [DateTime]::UtcNow.ToString('o')
    hostname = $computer.Name
    git_revision = $revision
    docker_engine = $engine.Name
    docker_memory_bytes = $engine.MemTotal
    docker_cpu_count = $engine.NCPU
    model = $computer.Model
    cpu = @($processors | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors)
    physical_memory_bytes = $computer.TotalPhysicalMemory
    output_volume = $volume.UniqueId
    free_disk_bytes = $volume.SizeRemaining
    requested_seconds = $Seconds
} | ConvertTo-Json -Depth 4 | Out-File (Join-Path $run.FullName 'hardware.json') -Encoding utf8 -NoClobber

$csv = Join-Path $run.FullName 'resources.csv'
'timestamp_utc,container_id,container_name,cpu_percent,memory_usage_limit,memory_percent' |
    Out-File $csv -Encoding utf8 -NoClobber
# Start-Process joins ArgumentList on Windows. Quote both paths to preserve spaces.
$arguments = '-u "{0}" --out "{1}" --seconds {2}' -f $baseline, (Join-Path $run.FullName 'workload'), $Seconds
$start = New-Object System.Diagnostics.ProcessStartInfo
$start.FileName = $python
$start.Arguments = $arguments
$start.WorkingDirectory = $PSScriptRoot
$start.UseShellExecute = $false
$workload = [System.Diagnostics.Process]::Start($start)
try {
    do {
        $stamp = [DateTime]::UtcNow.ToString('o')
        $stats = & $docker stats --no-stream --format '{{json .}}'
        if ($LASTEXITCODE -ne 0) { throw "docker stats failed with exit code $LASTEXITCODE." }
        if (-not $stats) { throw 'docker stats returned no running containers.' }
        $stats | ForEach-Object {
            $row = $_ | ConvertFrom-Json
            [pscustomobject]@{
                timestamp_utc = $stamp
                container_id = $row.ID
                container_name = $row.Name
                cpu_percent = $row.CPUPerc
                memory_usage_limit = $row.MemUsage
                memory_percent = $row.MemPerc
            }
        } | Export-Csv -LiteralPath $csv -Append -Encoding utf8 -NoTypeInformation
    } until ($workload.WaitForExit(5000))
    if ($workload.ExitCode -ne 0) { throw "Baseline failed with exit code $($workload.ExitCode)." }
} finally {
    if (-not $workload.HasExited) { $workload.Kill(); $workload.WaitForExit() }
    $workload.Dispose()
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & $python $reconcile (Join-Path $run.FullName 'workload')
    if ($LASTEXITCODE -ne 0) { throw "Reconciliation failed with exit code $LASTEXITCODE." }
} finally {
    Pop-Location
}
