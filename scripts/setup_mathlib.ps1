param(
  [string]$Project = "$PSScriptRoot\..\mathlib_project"
)

$ErrorActionPreference = "Stop"
$resolved = (Resolve-Path $Project).Path
$env:MATHLIB_CACHE_DIR = Join-Path $resolved ".lake\mathlib-cache"
New-Item -ItemType Directory -Force -Path $env:MATHLIB_CACHE_DIR | Out-Null
Push-Location $resolved
try {
  Write-Host "正在同步 Mathlib 依赖..."
  lake update
  if ($LASTEXITCODE -ne 0) { throw "lake update 失败，退出码：$LASTEXITCODE" }
  $cacheProbe = Join-Path $resolved ".lake\packages\mathlib\.lake\build\lib\lean\Mathlib.olean"
  if (-not (Test-Path -LiteralPath $cacheProbe)) {
    Write-Host "正在获取 Mathlib 预编译缓存..."
    lake exe cache get
    if ($LASTEXITCODE -ne 0) { throw "lake exe cache get 失败，退出码：$LASTEXITCODE" }
  }
  Write-Host "Mathlib 环境准备完成。"
}
finally {
  Pop-Location
}
