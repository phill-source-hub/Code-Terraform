# Task runner for Code: Terraform scripts. `make` is not installed on the dev
# machine, so this file is the single source of truth for local runs and CI.
#
#   pwsh -File tasks.ps1 check     # format check + lint + tests (what CI and the hook run)
#   pwsh -File tasks.ps1 test      # pytest only
#   pwsh -File tasks.ps1 format    # apply ruff formatting
#   pwsh -File tasks.ps1 sync      # dry run: what copying to the game folder would do
#   pwsh -File tasks.ps1 status    # read-only: warn/error log lines and script status
param(
    [Parameter(Position = 0)]
    [ValidateSet("lint", "format", "format-check", "test", "check", "sync", "status")]
    [string]$Task = "check"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

# Prefer the repo-local venv so tool versions match requirements-dev.txt.
$Py = if (Test-Path ".venv/Scripts/python.exe") { ".venv/Scripts/python.exe" }
      elseif (Test-Path ".venv/bin/python") { ".venv/bin/python" }
      else { "python" }

$Paths = @("scripts", "tests", "tools")

function Invoke-Step([string]$Name, [scriptblock]$Cmd) {
    Write-Host "== $Name" -ForegroundColor Cyan
    & $Cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Name (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Lint        { Invoke-Step "ruff lint" { & $Py -m ruff check @Paths } }
function FormatCheck { Invoke-Step "ruff format --check" { & $Py -m ruff format --check @Paths } }
function Format      { Invoke-Step "ruff format" { & $Py -m ruff format @Paths } }
function Test        { Invoke-Step "pytest" { & $Py -m pytest } }

switch ($Task) {
    "lint"         { Lint }
    "format"       { Format }
    "format-check" { FormatCheck }
    "test"         { Test }
    "check"        { FormatCheck; Lint; Test }
    "sync"         { & $Py tools/sync_to_game.py plan; exit $LASTEXITCODE }
    "status"       { & $Py tools/sync_to_game.py status; exit $LASTEXITCODE }
}

Write-Host "OK: $Task" -ForegroundColor Green

