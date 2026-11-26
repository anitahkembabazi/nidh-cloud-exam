$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$venv = Join-Path $env:LOCALAPPDATA "nidh-venv"
$python = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $python)) {
    py -3 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the Python environment." }
}
& $python -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
& $python -u .\start_pipeline.py
exit $LASTEXITCODE
