[CmdletBinding()] param()
$ErrorActionPreference = 'Stop'
python -m leancapsule replay .
exit $LASTEXITCODE
