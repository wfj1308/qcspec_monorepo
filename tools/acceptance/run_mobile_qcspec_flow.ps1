param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "Running QCSpec mobile acceptance flow..."
& $Python "tools/acceptance/mobile_qcspec_flow_e2e.py"
