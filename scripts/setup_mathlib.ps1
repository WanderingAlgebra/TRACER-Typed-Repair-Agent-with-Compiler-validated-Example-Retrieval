[CmdletBinding()]
param(
  [string]$Project = "$PSScriptRoot\..\mathlib_project"
)

$ErrorActionPreference = "Stop"

function Invoke-NativeCommand {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Command,
    [Parameter(Mandatory = $true)]
    [string[]]$Arguments
  )

  & $Command @Arguments
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    throw "$Command failed with exit code $exitCode"
  }
}

if (-not (Get-Command lake -ErrorAction SilentlyContinue)) {
  throw "lake was not found on PATH"
}

$resolved = (Resolve-Path -LiteralPath $Project).Path
if ([string]::IsNullOrWhiteSpace($env:MATHLIB_CACHE_DIR)) {
  if ([string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
    throw "USERPROFILE is required when MATHLIB_CACHE_DIR is not set"
  }
  $env:MATHLIB_CACHE_DIR = Join-Path $env:USERPROFILE ".cache\mathlib"
}
New-Item -ItemType Directory -Force -Path $env:MATHLIB_CACHE_DIR | Out-Null

Push-Location $resolved
try {
  Write-Host "Syncing Mathlib dependencies..."
  Invoke-NativeCommand -Command "lake" -Arguments @("update")

  $cacheProbe = Join-Path $resolved ".lake\packages\mathlib\.lake\build\lib\lean\Mathlib.olean"
  if (-not (Test-Path -LiteralPath $cacheProbe)) {
    Write-Host "Fetching the Mathlib precompiled cache..."
    Invoke-NativeCommand -Command "lake" -Arguments @("exe", "cache", "get")
  }
  Write-Host "Mathlib environment is ready."
}
finally {
  Pop-Location
}
