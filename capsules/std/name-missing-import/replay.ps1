[CmdletBinding()] param()
$ErrorActionPreference = 'Stop'
$capsuleDir = (Get-Item -LiteralPath $PSScriptRoot).FullName
$cursor = Get-Item -LiteralPath $capsuleDir
while ($null -ne $cursor -and -not (Test-Path -LiteralPath (Join-Path $cursor.FullName 'leancapsule\__main__.py'))) {
  $cursor = $cursor.Parent
}
if ($null -ne $cursor) {
  Push-Location $cursor.FullName
}
try {
  & python -m leancapsule replay $capsuleDir
  $exitCode = $LASTEXITCODE
}
finally {
  if ($null -ne $cursor) {
    Pop-Location
  }
}
exit $exitCode
