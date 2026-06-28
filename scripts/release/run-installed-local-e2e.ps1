param(
    [Parameter(Mandatory=$true)]
    [string]$UpdateSource,

    [string]$ExpectedTargetVersion = "",
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"

function Fail($Message) {
    throw "[installed-e2e] $Message"
}

function Get-TargetVersionFromSource($Source) {
    $packages = Get-ChildItem -LiteralPath $Source -Filter "WerewolfAgent-*-full.nupkg" -File
    if (-not $packages) {
        Fail "no full package found in update source"
    }
    $versions = foreach ($package in $packages) {
        if ($package.Name -match '^WerewolfAgent-(.+)-full\.nupkg$') {
            try {
                [version]$Matches[1]
            } catch {
                $null
            }
        }
    }
    if (-not $versions) {
        Fail "could not infer target version from full package names"
    }
    return ($versions | Sort-Object -Descending | Select-Object -First 1).ToString()
}

function Invoke-UpdateJsonPost($Port, $Action, $SessionId, $SessionToken) {
    Add-Type -AssemblyName System.Net.Http
    $handler = [System.Net.Http.HttpClientHandler]::new()
    $handler.UseProxy = $false
    $client = [System.Net.Http.HttpClient]::new($handler)
    try {
        $client.Timeout = [TimeSpan]::FromSeconds(60)
        $body = @{
            schema_version = 1
            session_id = $SessionId
            session_token = $SessionToken
            action = $Action
        } | ConvertTo-Json -Compress
        $content = [System.Net.Http.StringContent]::new($body, [Text.Encoding]::UTF8, "application/json")
        $response = $client.PostAsync("http://127.0.0.1:$Port/update/$Action", $content).GetAwaiter().GetResult()
        $text = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            Fail "update action $Action failed with HTTP $([int]$response.StatusCode): $text"
        }
        return $text | ConvertFrom-Json
    } finally {
        $client.Dispose()
        $handler.Dispose()
    }
}

function Wait-ForQtUpdateSession($Deadline) {
    while ((Get-Date) -lt $Deadline) {
        $proc = Get-CimInstance Win32_Process |
            Where-Object { $_.Name -eq "appqt_observer.exe" -and $_.CommandLine -like "*--update-control-port*" } |
            Sort-Object CreationDate -Descending |
            Select-Object -First 1
        if ($proc) {
            $cmd = [string]$proc.CommandLine
            $port = [regex]::Match($cmd, '--update-control-port\s+(\d+)')
            $sessionId = [regex]::Match($cmd, '--update-session-id\s+([A-Za-z0-9]+)')
            $sessionToken = [regex]::Match($cmd, '--update-session-token\s+([A-Za-z0-9]+)')
            if ($port.Success -and $sessionId.Success -and $sessionToken.Success) {
                return @{
                    ProcessId = [int]$proc.ProcessId
                    Port = [int]$port.Groups[1].Value
                    SessionId = $sessionId.Groups[1].Value
                    SessionToken = $sessionToken.Groups[1].Value
                }
            }
        }
        Start-Sleep -Milliseconds 500
    }
    Fail "timed out waiting for Qt update session"
}

function Wait-ForVersion($Exe, $Expected, $Deadline) {
    while ((Get-Date) -lt $Deadline) {
        try {
            $output = & $Exe --version 2>$null
            if (($output -join "`n") -match [regex]::Escape($Expected)) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Close-InstalledQtClients($AppRoot) {
    $children = Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq "appqt_observer.exe" -and
            $_.ExecutablePath -and
            $_.ExecutablePath.StartsWith($AppRoot, [StringComparison]::OrdinalIgnoreCase)
        }
    foreach ($child in $children) {
        $proc = Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
        if ($proc) {
            $proc.CloseMainWindow() | Out-Null
        }
    }
}

function Wait-ForInstalledQtClient($AppRoot, $Deadline) {
    while ((Get-Date) -lt $Deadline) {
        $child = Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -eq "appqt_observer.exe" -and
                $_.ExecutablePath -and
                $_.ExecutablePath.StartsWith($AppRoot, [StringComparison]::OrdinalIgnoreCase)
            } |
            Select-Object -First 1
        if ($child) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

$sourcePath = (Resolve-Path -LiteralPath $UpdateSource).Path
if ([string]::IsNullOrWhiteSpace($ExpectedTargetVersion)) {
    $ExpectedTargetVersion = Get-TargetVersionFromSource $sourcePath
}

$appRoot = Join-Path $env:LOCALAPPDATA "WerewolfAgent\current"
$appExe = Join-Path $appRoot "Werewolf-agent.exe"
$dataRoot = Join-Path $env:LOCALAPPDATA "Werewolf-agent"

if (-not (Test-Path -LiteralPath $appExe -PathType Leaf)) {
    Fail "installed app executable not found at $appExe"
}
if (-not (Test-Path -LiteralPath $dataRoot -PathType Container)) {
    Fail "user data root not found at $dataRoot"
}
foreach ($name in @("runs", "profiles", "configs", "logs", "runtime-state")) {
    if (Test-Path -LiteralPath (Join-Path $appRoot $name)) {
        Fail "user data directory is inside replaceable app root: $name"
    }
}

$sentinels = @(
    (Join-Path $dataRoot "runs\velopack-e2e-run-marker.txt"),
    (Join-Path $dataRoot "profiles\velopack-e2e-profile-marker.json"),
    (Join-Path $dataRoot "configs\velopack-e2e-config-marker.json"),
    (Join-Path $dataRoot "runtime-state\velopack-e2e-state-marker.json")
)
foreach ($path in $sentinels) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $path) | Out-Null
    Set-Content -LiteralPath $path -Value "preserve:$ExpectedTargetVersion" -Encoding UTF8
}

$settingsPath = "HKCU:\Software\WerewolfAgent\CredentialStore"
New-Item -Path $settingsPath -Force | Out-Null
New-ItemProperty -Path $settingsPath -Name "velopack_e2e_preserve" -Value $ExpectedTargetVersion -PropertyType String -Force | Out-Null

$credentialTarget = "WerewolfAgent/byokey/velopack_e2e_preserve"
cmdkey.exe /generic:$credentialTarget /user:WerewolfAgent /pass:nonsecret-e2e-marker | Out-Null

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$hostProc = $null
try {
    $previous = $env:WEREWOLF_ALLOW_VELOPACK_TEST_SOURCE
    $env:WEREWOLF_ALLOW_VELOPACK_TEST_SOURCE = "1"
    $hostProc = Start-Process -FilePath $appExe `
        -ArgumentList @("--velopack-test-update-source", $sourcePath) `
        -PassThru `
        -WindowStyle Hidden
    $env:WEREWOLF_ALLOW_VELOPACK_TEST_SOURCE = $previous

    $session = Wait-ForQtUpdateSession $deadline
    $check = Invoke-UpdateJsonPost $session.Port "check_for_update" $session.SessionId $session.SessionToken
    if ($check.status.phase -ne "available") {
        Fail "check did not report available update: $($check.status.phase)"
    }
    if ([string]$check.status.target_version -ne $ExpectedTargetVersion) {
        Fail "target version mismatch: expected $ExpectedTargetVersion got $($check.status.target_version)"
    }
    if ([string]::IsNullOrWhiteSpace([string]$check.status.release_notes)) {
        Fail "release notes missing from update status"
    }

    $download = Invoke-UpdateJsonPost $session.Port "download_update" $session.SessionId $session.SessionToken
    if ($download.status.phase -ne "downloaded" -or [int]$download.status.progress -ne 100) {
        Fail "download did not complete: phase=$($download.status.phase) progress=$($download.status.progress)"
    }

    $apply = Invoke-UpdateJsonPost $session.Port "apply_downloaded_update" $session.SessionId $session.SessionToken
    if ($apply.status.phase -ne "applying") {
        Fail "apply did not enter applying phase: $($apply.status.phase)"
    }

    $qtProcess = Get-Process -Id $session.ProcessId -ErrorAction SilentlyContinue
    if ($qtProcess) {
        $closed = $qtProcess.CloseMainWindow()
        if (-not $closed) {
            Fail "Qt client did not accept a normal close request"
        }
        Wait-Process -Id $qtProcess.Id -Timeout 30
    }
    if ($hostProc) {
        Wait-Process -Id $hostProc.Id -Timeout 60
    }

    if (-not (Wait-ForInstalledQtClient $appRoot $deadline)) {
        Fail "updated app did not automatically restart the Qt client"
    }

    if (-not (Wait-ForVersion $appExe $ExpectedTargetVersion $deadline)) {
        Fail "installed app did not report version $ExpectedTargetVersion after update"
    }

    foreach ($path in $sentinels) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            Fail "data sentinel missing after update: $path"
        }
    }
    $settingsValue = (Get-ItemProperty -Path $settingsPath -Name "velopack_e2e_preserve").velopack_e2e_preserve
    if ($settingsValue -ne $ExpectedTargetVersion) {
        Fail "QSettings registry marker changed after update"
    }
    $credentialList = cmdkey.exe /list:$credentialTarget
    if (($credentialList -join "`n") -notmatch [regex]::Escape($credentialTarget)) {
        Fail "Credential Manager marker missing after update"
    }

    Write-Host "[installed-e2e] PASS updated to $ExpectedTargetVersion and preserved data markers"
} finally {
    cmdkey.exe /delete:$credentialTarget 2>$null | Out-Null
    if ($appRoot) {
        Close-InstalledQtClients $appRoot
    }
    if ($previous -ne $null) {
        $env:WEREWOLF_ALLOW_VELOPACK_TEST_SOURCE = $previous
    } else {
        Remove-Item Env:\WEREWOLF_ALLOW_VELOPACK_TEST_SOURCE -ErrorAction SilentlyContinue
    }
}
