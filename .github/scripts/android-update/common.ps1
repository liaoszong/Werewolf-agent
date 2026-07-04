Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AndroidReleaseVersion {
  param(
    [Parameter(Mandatory = $true)][string]$ReleaseTag,
    [string]$ReleaseNotes,
    [string]$DefaultReleaseNotes = "Werewolf-agent Android release."
  )

  $tag = $ReleaseTag.Trim()
  if ([string]::IsNullOrWhiteSpace($tag)) {
    throw "Release tag is empty. Use tags like v0.2.0+2."
  }

  $version = if ($tag.StartsWith("v")) { $tag.Substring(1) } else { $tag }
  $match = [regex]::Match(
    $version,
    "^(?<name>[0-9]+(?:\.[0-9]+){2}(?:[-.][0-9A-Za-z]+)*)\+(?<code>[1-9][0-9]*)$"
  )
  if (-not $match.Success) {
    throw "Release tag '$tag' must be v<versionName>+<versionCode>, for example v0.2.0+2."
  }

  $notesPath = Join-Path $env:RUNNER_TEMP "release-notes.txt"
  $notes = if ([string]::IsNullOrWhiteSpace($ReleaseNotes)) {
    $DefaultReleaseNotes
  } else {
    $ReleaseNotes
  }
  Set-Content -Path $notesPath -Value $notes -Encoding utf8NoBOM

  [pscustomobject]@{
    Tag = $tag
    VersionName = $match.Groups["name"].Value
    VersionCode = [int]$match.Groups["code"].Value
    ReleaseNotesPath = $notesPath
  }
}

function Write-AndroidSigningFiles {
  param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("internal", "production")]
    [string]$Channel,
    [Parameter(Mandatory = $true)][string]$KeystoreBase64,
    [Parameter(Mandatory = $true)][string]$KeyProperties
  )

  if ([string]::IsNullOrWhiteSpace($KeystoreBase64)) {
    throw "Missing GitHub Secret: $($Channel.ToUpperInvariant())_ANDROID_KEYSTORE_BASE64."
  }
  if ([string]::IsNullOrWhiteSpace($KeyProperties)) {
    throw "Missing GitHub Secret: $($Channel.ToUpperInvariant())_ANDROID_KEY_PROPERTIES."
  }

  $androidDir = "clients/flutter_app/android"
  $appDir = Join-Path $androidDir "app"
  $keystoreFileName = "$Channel-upload-keystore.jks"
  $keystorePath = Join-Path $appDir $keystoreFileName
  $keyPropertiesPath = Join-Path $androidDir "$Channel-key.properties"
  New-Item -ItemType Directory -Force -Path $appDir | Out-Null

  try {
    $keystoreBytes = [Convert]::FromBase64String($KeystoreBase64.Trim())
  } catch {
    throw "$($Channel.ToUpperInvariant())_ANDROID_KEYSTORE_BASE64 must be valid base64."
  }
  if ($keystoreBytes.Length -eq 0) {
    throw "$($Channel.ToUpperInvariant())_ANDROID_KEYSTORE_BASE64 decoded to an empty keystore."
  }
  [IO.File]::WriteAllBytes($keystorePath, $keystoreBytes)

  $keyProperties = $KeyProperties.Trim()
  $parsedProperties = @{}
  foreach ($line in ($keyProperties -split "`r?`n")) {
    $trimmedLine = $line.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmedLine) -or $trimmedLine.StartsWith("#")) {
      continue
    }
    $separatorIndex = $trimmedLine.IndexOf("=")
    if ($separatorIndex -le 0) {
      continue
    }
    $name = $trimmedLine.Substring(0, $separatorIndex).Trim()
    $value = $trimmedLine.Substring($separatorIndex + 1).Trim()
    $parsedProperties[$name] = $value
  }

  foreach ($requiredKey in @("storeFile", "storePassword", "keyAlias", "keyPassword")) {
    if (
      -not $parsedProperties.ContainsKey($requiredKey) -or
      [string]::IsNullOrWhiteSpace([string]$parsedProperties[$requiredKey])
    ) {
      throw "$($Channel.ToUpperInvariant())_ANDROID_KEY_PROPERTIES must include non-empty '$requiredKey'."
    }
  }

  $repoRoot = if ([string]::IsNullOrWhiteSpace($env:GITHUB_WORKSPACE)) {
    (Get-Location).Path
  } else {
    $env:GITHUB_WORKSPACE
  }
  $androidFullPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $androidDir))
  $appFullPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $appDir))
  $keystoreFullPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $keystorePath))
  $storeFileValue = [string]$parsedProperties["storeFile"]
  $storeFileCandidates = if ([IO.Path]::IsPathRooted($storeFileValue)) {
    @([IO.Path]::GetFullPath($storeFileValue))
  } else {
    @(
      [IO.Path]::GetFullPath((Join-Path $androidFullPath $storeFileValue)),
      [IO.Path]::GetFullPath((Join-Path $appFullPath $storeFileValue))
    )
  }

  $resolvedStoreFile = $null
  foreach ($candidate in $storeFileCandidates) {
    if (Test-Path -LiteralPath $candidate) {
      $resolvedStoreFile = $candidate
      break
    }
  }
  if ($null -eq $resolvedStoreFile) {
    throw "$($Channel.ToUpperInvariant())_ANDROID_KEY_PROPERTIES storeFile '$storeFileValue' does not resolve to an existing keystore."
  }
  if (-not [string]::Equals($resolvedStoreFile, $keystoreFullPath, [StringComparison]::Ordinal)) {
    throw "$($Channel.ToUpperInvariant())_ANDROID_KEY_PROPERTIES storeFile '$storeFileValue' must resolve to '$keystorePath'."
  }

  Set-Content -Path $keyPropertiesPath -Value $keyProperties -Encoding utf8NoBOM
}

function Get-AndroidApkSigningCertificateSha256 {
  param([Parameter(Mandatory = $true)][string]$ApkPath)

  $apksigner = Get-AndroidApksignerPath
  if (-not [string]::IsNullOrWhiteSpace($apksigner)) {
    $output = & $apksigner verify --print-certs $ApkPath 2>&1
    if ($LASTEXITCODE -ne 0) {
      throw "apksigner failed to inspect APK signing certificate: $($output -join "`n")"
    }
    return Get-AndroidCertificateSha256FromToolOutput -Output ($output -join "`n")
  }

  $output = & keytool -printcert -jarfile $ApkPath 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "keytool failed to inspect APK signing certificate: $($output -join "`n")"
  }
  Get-AndroidCertificateSha256FromToolOutput -Output ($output -join "`n")
}

function Get-AndroidApksignerPath {
  $command = Get-Command apksigner -ErrorAction SilentlyContinue
  if ($null -ne $command) {
    return $command.Source
  }

  $sdkRoots = @($env:ANDROID_HOME, $env:ANDROID_SDK_ROOT) |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
    Select-Object -Unique
  foreach ($sdkRoot in $sdkRoots) {
    $buildToolsDir = Join-Path $sdkRoot "build-tools"
    if (-not (Test-Path -LiteralPath $buildToolsDir)) {
      continue
    }
    $buildTools = Get-ChildItem -Path $buildToolsDir -Directory |
      Sort-Object -Property Name -Descending
    foreach ($buildTool in $buildTools) {
      foreach ($fileName in @("apksigner", "apksigner.bat")) {
        $candidate = Join-Path $buildTool.FullName $fileName
        if (Test-Path -LiteralPath $candidate) {
          return $candidate
        }
      }
    }
  }

  return $null
}

function Get-AndroidCertificateSha256FromToolOutput {
  param([Parameter(Mandatory = $true)][string]$Output)

  $hashPattern = "(?<hash>(?:[0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2}|[0-9A-Fa-f]{64})"
  $patterns = @(
    "(?im)^\s*(?:.+?:\s*)?certificate SHA-256 digest:\s*$hashPattern\s*$",
    "(?im)^\s*SHA256:\s*$hashPattern\s*$",
    "(?im)^\s*SHA-256(?:\s+fingerprint)?:\s*$hashPattern\s*$"
  )

  foreach ($pattern in $patterns) {
    $match = [regex]::Match($Output, $pattern)
    if ($match.Success) {
      $normalized = $match.Groups["hash"].Value.Replace(":", "").ToLowerInvariant()
      if ($normalized.Length -ne 64) {
        break
      }
      return $normalized
    }
  }

  throw "Unable to extract APK signing certificate SHA256 from signing tool output."
}

function New-AndroidUpdateArtifacts {
  param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("internal", "production")]
    [string]$Channel,
    [Parameter(Mandatory = $true)][string]$ApplicationId,
    [Parameter(Mandatory = $true)][string]$VersionName,
    [Parameter(Mandatory = $true)][int]$VersionCode,
    [Parameter(Mandatory = $true)][string]$ReleaseTag,
    [Parameter(Mandatory = $true)][string]$GitCommit,
    [Parameter(Mandatory = $true)][string]$ApkPath,
    [Parameter(Mandatory = $true)][string]$ApkName,
    [Parameter(Mandatory = $true)][string]$ReleaseNotesPath,
    [Parameter(Mandatory = $true)][string]$OutputDirectory
  )

  if (-not (Test-Path -LiteralPath $ApkPath)) {
    throw "APK file does not exist: $ApkPath"
  }
  New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

  $apkTarget = Join-Path $OutputDirectory $ApkName
  $manifestTarget = Join-Path $OutputDirectory "latest.json"
  $metadataTarget = Join-Path $OutputDirectory "build-metadata.json"
  Copy-Item -Path $ApkPath -Destination $apkTarget -Force

  $apkSha256 = (Get-FileHash -Path $apkTarget -Algorithm SHA256).Hash.ToLowerInvariant()
  $apkSizeBytes = (Get-Item -Path $apkTarget).Length
  $signingCertificateSha256 = Get-AndroidApkSigningCertificateSha256 -ApkPath $apkTarget
  $releaseNotes = (Get-Content -Path $ReleaseNotesPath -Raw).Trim()
  $publishedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $apkUrl = "https://github.com/$env:GITHUB_REPOSITORY/releases/download/$ReleaseTag/$ApkName"

  $manifest = [ordered]@{
    schemaVersion = 1
    channel = $Channel
    applicationId = $ApplicationId
    versionName = $VersionName
    versionCode = $VersionCode
    releaseTag = $ReleaseTag
    gitCommit = $GitCommit
    signingCertificateSha256 = $signingCertificateSha256
    apkUrl = $apkUrl
    sha256 = $apkSha256
    sizeBytes = [int64]$apkSizeBytes
    releaseNotes = $releaseNotes
    publishedAt = $publishedAt
  }
  $metadata = [ordered]@{
    schemaVersion = 1
    channel = $Channel
    applicationId = $ApplicationId
    versionName = $VersionName
    versionCode = $VersionCode
    releaseTag = $ReleaseTag
    gitCommit = $GitCommit
    signingCertificateSha256 = $signingCertificateSha256
    apkSha256 = $apkSha256
    apkSizeBytes = [int64]$apkSizeBytes
    apkAssetName = $ApkName
    builtAt = $publishedAt
  }
  $manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestTarget -Encoding utf8NoBOM
  $metadata | ConvertTo-Json -Depth 6 | Set-Content -Path $metadataTarget -Encoding utf8NoBOM

  [pscustomobject]@{
    ApkPath = $apkTarget
    ManifestPath = $manifestTarget
    MetadataPath = $metadataTarget
    ApkSha256 = $apkSha256
    ApkSizeBytes = $apkSizeBytes
    SigningCertificateSha256 = $signingCertificateSha256
  }
}

function Assert-AndroidProductionPromotionCandidate {
  param(
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$MetadataPath
  )

  $manifest = Get-Content -Path $ManifestPath -Raw | ConvertFrom-Json
  $metadata = Get-Content -Path $MetadataPath -Raw | ConvertFrom-Json
  if ($manifest.schemaVersion -ne 1 -or $metadata.schemaVersion -ne 1) {
    throw "Only schemaVersion 1 can be promoted."
  }
  if ($manifest.channel -ne "production" -or $metadata.channel -ne "production") {
    throw "Only production channel candidates can be promoted to stable."
  }

  foreach ($field in @(
    "applicationId",
    "versionName",
    "versionCode",
    "releaseTag",
    "gitCommit",
    "signingCertificateSha256"
  )) {
    if ($manifest.$field -ne $metadata.$field) {
      throw "Promotion candidate mismatch: $field."
    }
  }
  if ($manifest.sha256 -ne $metadata.apkSha256) {
    throw "Promotion candidate mismatch: sha256."
  }
  if ([int64]$manifest.sizeBytes -ne [int64]$metadata.apkSizeBytes) {
    throw "Promotion candidate mismatch: sizeBytes."
  }
}
