param(
  [string]$BaseUrl = "https://api.docpeg.cn",
  [Parameter(Mandatory = $true)][string]$ProjectId,
  [Parameter(Mandatory = $true)][string]$ChainId,
  [Parameter(Mandatory = $true)][string]$EntityUri,
  [Parameter(Mandatory = $true)][string]$ComponentUri,
  [string]$PileId = "",
  [string]$InspectionLocation = "",
  [string]$SourceMode = "component",
  [string]$FormCode = "",
  [string]$DocId = "",
  [string]$TripAction = "",
  [string]$BodyHash = "",
  [string]$ExecutorUri = "",
  [string]$SigData = "",
  [string]$Authorization = "",
  [string]$ApiKey = "",
  [string]$ActorRole = "designer",
  [string]$ActorName = "designer-user",
  [switch]$RunWriteOps,
  [switch]$Simulate,
  [switch]$StopOnError,
  [string]$PayloadDir = "tools/acceptance/docpeg_joint_debug_payloads",
  [string]$OutputFile = "tmp/docpeg_joint_debug_last_run.json"
)

$ErrorActionPreference = "Stop"

function Resolve-AuthValue([string]$explicitValue, [string]$envName) {
  if (-not [string]::IsNullOrWhiteSpace($explicitValue)) {
    return $explicitValue.Trim()
  }
  $item = Get-Item -Path ("Env:{0}" -f $envName) -ErrorAction SilentlyContinue
  if ($null -eq $item) { return "" }
  return [string]$item.Value
}

function ConvertTo-QueryString([hashtable]$query) {
  if ($null -eq $query -or $query.Count -eq 0) {
    return ""
  }

  $pairs = @()
  foreach ($key in $query.Keys) {
    $value = $query[$key]
    if ($null -eq $value) { continue }
    $text = [string]$value
    if ([string]::IsNullOrWhiteSpace($text)) { continue }
    $pairs += ("{0}={1}" -f [Uri]::EscapeDataString([string]$key), [Uri]::EscapeDataString($text))
  }

  if ($pairs.Count -eq 0) { return "" }
  return "?" + ($pairs -join "&")
}

function New-DocpegHeaders {
  $headers = @{}

  if (-not [string]::IsNullOrWhiteSpace($script:ResolvedAuthorization)) {
    $headers["Authorization"] = $script:ResolvedAuthorization
  }
  if (-not [string]::IsNullOrWhiteSpace($script:ResolvedApiKey)) {
    $headers["x-api-key"] = $script:ResolvedApiKey
  }
  if (-not [string]::IsNullOrWhiteSpace($ActorRole)) {
    $headers["x-actor-role"] = $ActorRole
  }
  if (-not [string]::IsNullOrWhiteSpace($ActorName)) {
    $headers["x-actor-name"] = $ActorName
  }

  $headers["x-client"] = "qcspec-smoke"
  $headers["x-trace-id"] = "qcspec-jd-{0}" -f ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
  return $headers
}

function Fill-TemplatePlaceholders([string]$rawText) {
  $result = $rawText
  foreach ($key in $script:TemplateVars.Keys) {
    $value = [string]$script:TemplateVars[$key]
    if ($null -eq $value) { $value = "" }
    $result = $result.Replace($key, $value)
  }
  return $result
}

function Load-Payload([string]$name) {
  $path = Join-Path $PayloadDir "$name.json"
  if (-not (Test-Path -LiteralPath $path)) {
    Write-Warning "Payload file not found: $path"
    return $null
  }

  $raw = Get-Content -LiteralPath $path -Raw
  $rendered = Fill-TemplatePlaceholders $raw
  if ($Simulate -and $rendered -match "__TODO_") {
    $rendered = [Regex]::Replace($rendered, "__TODO_[A-Z0-9_]+__", "SIM_VALUE")
  }
  if ($rendered -match "__TODO_") {
    Write-Warning "Payload still has TODO placeholders: $path"
    return $null
  }

  try {
    return $rendered | ConvertFrom-Json
  } catch {
    Write-Warning ("Invalid JSON payload: {0} - {1}" -f $path, $_.Exception.Message)
    return $null
  }
}

function Resolve-StatusCodeFromError([object]$err) {
  try {
    $response = $err.Exception.Response
    if ($null -ne $response -and $null -ne $response.StatusCode) {
      return [int]$response.StatusCode
    }
  } catch {
  }
  return 0
}

function Resolve-DeepValue([object]$obj, [string[]]$keys) {
  if ($null -eq $obj) { return $null }

  foreach ($key in $keys) {
    if ($obj -is [System.Collections.IDictionary]) {
      if ($obj.Contains($key)) { return $obj[$key] }
    } elseif ($null -ne $obj.PSObject -and $obj.PSObject.Properties.Name -contains $key) {
      return $obj.$key
    }
  }

  foreach ($nested in @("data", "result", "payload")) {
    $child = $null
    if ($obj -is [System.Collections.IDictionary]) {
      if ($obj.Contains($nested)) { $child = $obj[$nested] }
    } elseif ($null -ne $obj.PSObject -and $obj.PSObject.Properties.Name -contains $nested) {
      $child = $obj.$nested
    }
    if ($null -ne $child) {
      $found = Resolve-DeepValue -obj $child -keys $keys
      if ($null -ne $found) { return $found }
    }
  }

  return $null
}

function Invoke-ApiStep {
  param(
    [Parameter(Mandatory = $true)][string]$StepName,
    [Parameter(Mandatory = $true)][string]$Method,
    [Parameter(Mandatory = $true)][string]$Path,
    [hashtable]$Query,
    [object]$Body
  )

  $uri = "{0}{1}{2}" -f $BaseUrl.TrimEnd("/"), $Path, (ConvertTo-QueryString $Query)
  $headers = New-DocpegHeaders
  $request = @{
    Method      = $Method
    Uri         = $uri
    Headers     = $headers
    TimeoutSec  = 60
  }

  if ($null -ne $Body) {
    $request["Body"] = ($Body | ConvertTo-Json -Depth 100)
    $request["ContentType"] = "application/json"
  }

  Write-Host ("[{0}] {1} {2}" -f $StepName, $Method, $uri)

  if ($Simulate) {
    $simData = [pscustomobject]@{
      ok = $true
      step = $StepName
      simulated = $true
    }
    if ($StepName -eq "normref-save-draft") {
      $simData = [pscustomobject]@{
        ok = $true
        instance_id = "sim-draft-001"
      }
    } elseif ($StepName -eq "signpeg-sign") {
      $simData = [pscustomobject]@{
        ok = $true
        doc_id = $(if ([string]::IsNullOrWhiteSpace($DocId)) { "sim-doc-001" } else { $DocId })
        sig_data = "signpeg:v1:simulated"
      }
    } elseif ($StepName -like "signpeg-status*") {
      $simData = [pscustomobject]@{
        ok = $true
        all_signed = $true
        proof_id = "proof-sim-001"
      }
    }

    $row = [pscustomobject]@{
      step       = $StepName
      method     = $Method
      path       = $Path
      http_code  = 200
      ok         = $true
      error      = ""
      timestamp  = [DateTimeOffset]::UtcNow.ToString("o")
    }
    $script:Summary.Add($row) | Out-Null
    return [pscustomobject]@{
      ok        = $true
      status    = 200
      data      = $simData
      uri       = $uri
      step_name = $StepName
    }
  }

  try {
    $response = Invoke-RestMethod @request
    $row = [pscustomobject]@{
      step       = $StepName
      method     = $Method
      path       = $Path
      http_code  = 200
      ok         = $true
      error      = ""
      timestamp  = [DateTimeOffset]::UtcNow.ToString("o")
    }
    $script:Summary.Add($row) | Out-Null
    return [pscustomobject]@{
      ok        = $true
      status    = 200
      data      = $response
      uri       = $uri
      step_name = $StepName
    }
  } catch {
    $statusCode = Resolve-StatusCodeFromError $_
    $message = $_.Exception.Message
    $row = [pscustomobject]@{
      step       = $StepName
      method     = $Method
      path       = $Path
      http_code  = $statusCode
      ok         = $false
      error      = $message
      timestamp  = [DateTimeOffset]::UtcNow.ToString("o")
    }
    $script:Summary.Add($row) | Out-Null
    Write-Warning ("{0} failed: HTTP {1} - {2}" -f $StepName, $statusCode, $message)
    if ($StopOnError) { throw }
    return [pscustomobject]@{
      ok        = $false
      status    = $statusCode
      data      = $null
      uri       = $uri
      error     = $message
      step_name = $StepName
    }
  }
}

function Invoke-CompatPost {
  param(
    [Parameter(Mandatory = $true)][string]$StepName,
    [Parameter(Mandatory = $true)][string]$PrimaryPath,
    [Parameter(Mandatory = $true)][string]$CompatPath,
    [Parameter(Mandatory = $true)][object]$Body
  )

  $primary = Invoke-ApiStep -StepName $StepName -Method "POST" -Path $PrimaryPath -Body $Body
  if ($primary.ok) { return $primary }

  if ($primary.status -eq 404) {
    Write-Host ("[{0}] Retry with compat path: {1}" -f $StepName, $CompatPath)
    return Invoke-ApiStep -StepName ("{0}-compat" -f $StepName) -Method "POST" -Path $CompatPath -Body $Body
  }
  return $primary
}

function Invoke-CompatGet {
  param(
    [Parameter(Mandatory = $true)][string]$StepName,
    [Parameter(Mandatory = $true)][string]$PrimaryPath,
    [Parameter(Mandatory = $true)][string]$CompatPath,
    [hashtable]$Query
  )

  $primary = Invoke-ApiStep -StepName $StepName -Method "GET" -Path $PrimaryPath -Query $Query
  if ($primary.ok) { return $primary }
  if ($primary.status -eq 404) {
    Write-Host ("[{0}] Retry with compat path: {1}" -f $StepName, $CompatPath)
    return Invoke-ApiStep -StepName ("{0}-compat" -f $StepName) -Method "GET" -Path $CompatPath -Query $Query
  }
  return $primary
}

$script:ResolvedAuthorization = Resolve-AuthValue -explicitValue $Authorization -envName "DOCPEG_AUTHORIZATION"
$script:ResolvedApiKey = Resolve-AuthValue -explicitValue $ApiKey -envName "DOCPEG_X_API_KEY"
$script:Summary = New-Object System.Collections.Generic.List[object]

$script:TemplateVars = @{
  "__TODO_PROJECT_ID__" = $ProjectId
  "__TODO_CHAIN_ID__" = $ChainId
  "__TODO_COMPONENT_URI__" = $ComponentUri
  "__TODO_PILE_ID__" = $PileId
  "__TODO_INSPECTION_LOCATION__" = $InspectionLocation
  "__TODO_DOC_ID__" = $DocId
  "__TODO_ACTION__" = $TripAction
  "__TODO_BODY_HASH__" = $BodyHash
  "__TODO_EXECUTOR_URI__" = $ExecutorUri
  "__TODO_SIG_DATA__" = $SigData
}

if ([string]::IsNullOrWhiteSpace($script:ResolvedAuthorization) -and [string]::IsNullOrWhiteSpace($script:ResolvedApiKey)) {
  Write-Warning "No auth header configured. Set -Authorization/-ApiKey or DOCPEG_AUTHORIZATION/DOCPEG_X_API_KEY."
}

Write-Host "DocPeg joint-debug smoke run started."
Write-Host ("Base URL: {0}" -f $BaseUrl)
Write-Host ("ProjectId: {0}" -f $ProjectId)

$null = Invoke-ApiStep -StepName "health" -Method "GET" -Path "/health"
$null = Invoke-ApiStep -StepName "openapi" -Method "GET" -Path "/openapi.json"
$null = Invoke-ApiStep -StepName "docpeg-summary" -Method "GET" -Path "/api/v1/docpeg/summary"
$null = Invoke-ApiStep -StepName "projects-list" -Method "GET" -Path "/projects"
$null = Invoke-ApiStep -StepName "project-detail" -Method "GET" -Path "/projects/$ProjectId"

$null = Invoke-ApiStep -StepName "bindings-by-entity" -Method "GET" -Path "/projects/$ProjectId/process-chains/bindings/by-entity" -Query @{
  entity_uri = $EntityUri
}

$null = Invoke-ApiStep -StepName "process-chain-status" -Method "GET" -Path "/projects/$ProjectId/process-chains/status" -Query @{
  chain_id = $ChainId
  component_uri = $ComponentUri
  pile_id = $PileId
  source_mode = $SourceMode
}

$null = Invoke-ApiStep -StepName "process-chain-summary" -Method "GET" -Path "/projects/$ProjectId/process-chains/$ChainId/summary" -Query @{
  component_uri = $ComponentUri
  pile_id = $PileId
}

$null = Invoke-ApiStep -StepName "process-chain-recommend" -Method "GET" -Path "/projects/$ProjectId/process-chains/recommend" -Query @{
  chain_id = $ChainId
  component_uri = $ComponentUri
  pile_id = $PileId
}

$null = Invoke-ApiStep -StepName "process-chain-dependencies" -Method "GET" -Path "/projects/$ProjectId/process-chains/dependencies" -Query @{
  chain_id = $ChainId
}

$null = Invoke-CompatGet -StepName "normref-forms" -PrimaryPath "/api/v1/normref/projects/$ProjectId/forms" -CompatPath "/projects/$ProjectId/normref/forms"

if (-not [string]::IsNullOrWhiteSpace($FormCode)) {
  $null = Invoke-CompatGet -StepName "normref-form-detail" -PrimaryPath "/api/v1/normref/projects/$ProjectId/forms/$FormCode" -CompatPath "/projects/$ProjectId/normref/forms/$FormCode"
  $null = Invoke-CompatGet -StepName "normref-latest-draft" -PrimaryPath "/api/v1/normref/projects/$ProjectId/forms/$FormCode/draft-instances/latest" -CompatPath "/projects/$ProjectId/normref/forms/$FormCode/draft-instances/latest"
  $null = Invoke-CompatGet -StepName "normref-latest-submitted" -PrimaryPath "/api/v1/normref/projects/$ProjectId/forms/$FormCode/latest-submitted" -CompatPath "/projects/$ProjectId/normref/forms/$FormCode/latest-submitted"
}

$null = Invoke-ApiStep -StepName "triprole-trips" -Method "GET" -Path "/api/v1/triprole/trips" -Query @{
  project_id = $ProjectId
}

$null = Invoke-ApiStep -StepName "dtorole-permission-check" -Method "GET" -Path "/api/v1/dtorole/permission-check" -Query @{
  permission = "document.create"
  project_id = $ProjectId
  actor_role = $ActorRole
  actor_name = $ActorName
}

$null = Invoke-ApiStep -StepName "boq-items" -Method "GET" -Path "/api/v1/boqitem/projects/$ProjectId/items"
$null = Invoke-ApiStep -StepName "boq-nodes" -Method "GET" -Path "/api/v1/boqitem/projects/$ProjectId/nodes"
$null = Invoke-ApiStep -StepName "boq-utxos" -Method "GET" -Path "/api/v1/boqitem/projects/$ProjectId/utxos"
$null = Invoke-ApiStep -StepName "layerpeg-chain-status" -Method "GET" -Path "/api/v1/layerpeg/chain-status" -Query @{
  project_id = $ProjectId
}

if (-not [string]::IsNullOrWhiteSpace($DocId)) {
  $null = Invoke-ApiStep -StepName "signpeg-status-initial" -Method "GET" -Path "/api/v1/signpeg/status/$DocId"
}

if ($RunWriteOps) {
  Write-Host "RunWriteOps enabled: running write endpoints."

  if ([string]::IsNullOrWhiteSpace($FormCode)) {
    Write-Warning "FormCode is empty. Skip NormRef write endpoints."
  } else {
    $interpretPayload = Load-Payload "interpret-preview"
    if ($null -ne $interpretPayload) {
      $null = Invoke-CompatPost -StepName "normref-interpret-preview" -PrimaryPath "/api/v1/normref/projects/$ProjectId/forms/$FormCode/interpret-preview" -CompatPath "/projects/$ProjectId/normref/forms/$FormCode/interpret-preview" -Body $interpretPayload
    }

    $draftPayload = Load-Payload "draft-instance"
    $draftInstanceId = ""
    if ($null -ne $draftPayload) {
      $draftResp = Invoke-CompatPost -StepName "normref-save-draft" -PrimaryPath "/api/v1/normref/projects/$ProjectId/forms/$FormCode/draft-instances" -CompatPath "/projects/$ProjectId/normref/forms/$FormCode/draft-instances" -Body $draftPayload
      if ($draftResp.ok) {
        $draftInstanceId = [string](Resolve-DeepValue -obj $draftResp.data -keys @("instance_id", "instanceId", "draft_instance_id", "id"))
      }
    }

    if (-not [string]::IsNullOrWhiteSpace($draftInstanceId)) {
      $draftSubmitPayload = Load-Payload "draft-submit"
      if ($null -eq $draftSubmitPayload) { $draftSubmitPayload = @{} }
      $null = Invoke-CompatPost -StepName "normref-submit-draft" -PrimaryPath "/api/v1/normref/projects/$ProjectId/forms/$FormCode/draft-instances/$draftInstanceId/submit" -CompatPath "/projects/$ProjectId/normref/forms/$FormCode/draft-instances/$draftInstanceId/submit" -Body $draftSubmitPayload
    } else {
      Write-Warning "No draft instance id captured. Skip draft submit."
    }
  }

  $tripPreviewPayload = Load-Payload "trips-preview"
  if ($null -ne $tripPreviewPayload) {
    $null = Invoke-CompatPost -StepName "trips-preview" -PrimaryPath "/api/v1/trips/preview" -CompatPath "/trips/preview" -Body $tripPreviewPayload
  }

  $tripSubmitPayload = Load-Payload "trips-submit"
  if ($null -ne $tripSubmitPayload) {
    $null = Invoke-CompatPost -StepName "trips-submit" -PrimaryPath "/api/v1/trips/submit" -CompatPath "/trips/submit" -Body $tripSubmitPayload
  }

  $tripRolePreviewPayload = Load-Payload "triprole-preview"
  if ($null -ne $tripRolePreviewPayload) {
    $null = Invoke-ApiStep -StepName "triprole-preview" -Method "POST" -Path "/api/v1/triprole/preview" -Body $tripRolePreviewPayload
  }

  $tripRoleSubmitPayload = Load-Payload "triprole-submit"
  if ($null -ne $tripRoleSubmitPayload) {
    $null = Invoke-ApiStep -StepName "triprole-submit" -Method "POST" -Path "/api/v1/triprole/submit" -Body $tripRoleSubmitPayload
  }

  $layerpegAnchorPayload = Load-Payload "layerpeg-anchor"
  if ($null -ne $layerpegAnchorPayload) {
    $null = Invoke-ApiStep -StepName "layerpeg-anchor-write" -Method "POST" -Path "/api/v1/layerpeg/anchor" -Body $layerpegAnchorPayload
  }

  $signPayload = Load-Payload "sign"
  $signedDocId = ""
  if ($null -ne $signPayload) {
    $signResp = Invoke-ApiStep -StepName "signpeg-sign" -Method "POST" -Path "/api/v1/signpeg/sign" -Body $signPayload
    if ($signResp.ok) {
      $signedDocId = [string](Resolve-DeepValue -obj $signResp.data -keys @("doc_id", "docId"))
    }
  }

  $verifyPayload = Load-Payload "verify"
  if ($null -ne $verifyPayload) {
    $null = Invoke-ApiStep -StepName "signpeg-verify" -Method "POST" -Path "/api/v1/signpeg/verify" -Body $verifyPayload
  }

  if (-not [string]::IsNullOrWhiteSpace($signedDocId)) {
    $null = Invoke-ApiStep -StepName "signpeg-status-after-sign" -Method "GET" -Path "/api/v1/signpeg/status/$signedDocId"
  }
}

Write-Host ""
Write-Host "==== Summary ===="
$script:Summary | Format-Table -AutoSize

$outputDir = Split-Path -Parent $OutputFile
if (-not [string]::IsNullOrWhiteSpace($outputDir) -and -not (Test-Path -LiteralPath $outputDir)) {
  New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$script:Summary | ConvertTo-Json -Depth 20 | Set-Content -Path $OutputFile -Encoding UTF8
Write-Host ("Saved summary to: {0}" -f $OutputFile)
