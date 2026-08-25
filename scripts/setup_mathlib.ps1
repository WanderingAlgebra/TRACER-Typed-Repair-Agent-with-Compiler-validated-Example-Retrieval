param(
  [string]$Project = "$PSScriptRoot\..\mathlib_project"
)

$ErrorActionPreference = "Stop"
$resolved = (Resolve-Path $Project).Path
Push-Location $resolved
try {
  Write-Host "正在同步 Mathlib 依赖..."
  lake update
  $cacheProbe = Join-Path $resolved ".lake\packages\mathlib\.lake\build\lib\lean\Mathlib.olean"
  if (-not (Test-Path -LiteralPath $cacheProbe)) {
    Write-Host "正在获取 Mathlib 预编译缓存..."
    lake exe cache get
  }
  Write-Host "Mathlib 环境准备完成。"
}
finally {
  Pop-Location
}
