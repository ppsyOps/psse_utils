<#
.SYNOPSIS
    Installs psse-utils (if needed) and runs log-min-to-con interactively,
    then opens the output folder.

.DESCRIPTION
    For non-technical end users: double-click (Run with PowerShell) or run
    from a shell. Prompts for the TARA mini log file path, ensures psse-utils
    is installed and current, runs log-min-to-con, then opens the output
    folder in Explorer.
#>

function Get-PythonCommand {
    foreach ($candidate in @(
        @{ Exe = 'python'; Args = @() },
        @{ Exe = 'py'; Args = @('-3') }
    )) {
        if (Get-Command $candidate.Exe -ErrorAction SilentlyContinue) {
            return $candidate
        }
    }
    return $null
}

function Read-PathPrompt {
    param(
        [string]$Prompt,
        [string]$Default
    )
    $suffix = if ($Default) { " [$Default]" } else { '' }
    $value = Read-Host "$Prompt$suffix"
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value.Trim('"')
}

try {
    $python = Get-PythonCommand
    if (-not $python) {
        Write-Host "Python was not found on PATH. Install Python 3.11+ and try again." -ForegroundColor Red
        exit 1
    }

    # --- Ensure psse-utils is installed and current ---
    & $python.Exe @($python.Args) -m pip show psse-utils *> $null
    $isInstalled = ($LASTEXITCODE -eq 0)
    if (-not $isInstalled) {
        Write-Host "Installing psse-utils..."
        & $python.Exe @($python.Args) -m pip install --pre --quiet psse-utils
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Install failed." -ForegroundColor Red
            exit 1
        }
    }
    else {
        $outdated = & $python.Exe @($python.Args) -m pip list --outdated --pre --format=json 2>$null |
            ConvertFrom-Json | Where-Object { $_.name -eq 'psse-utils' }
        if ($outdated) {
            Write-Host "Updating psse-utils..."
            & $python.Exe @($python.Args) -m pip install --pre --upgrade --quiet psse-utils
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Update failed." -ForegroundColor Red
                exit 1
            }
        }
    }

    # --- Prompt for inputs ---
    $logFilepath = Read-PathPrompt -Prompt "Path to the TARA mini log file (e.g. log_hourly-min.txt)"
    while (-not (Test-Path $logFilepath -PathType Leaf)) {
        Write-Host "File not found: $logFilepath" -ForegroundColor Yellow
        $logFilepath = Read-PathPrompt -Prompt "Path to the TARA mini log file"
    }
    $logFilepath = (Resolve-Path $logFilepath).Path

    $defaultOutDir = Join-Path (Split-Path $logFilepath -Parent) 'log_min_to_con_output'
    $outDir = Read-PathPrompt -Prompt "Output folder" -Default $defaultOutDir

    # --- Run ---
    Write-Host "Running log-min-to-con..."
    & $python.Exe @($python.Args) -m psse_utils.log_min_to_con `
        --log-filepath $logFilepath --out-dir $outDir --no-open-con-file
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        if (Test-Path $outDir) {
            Start-Process explorer.exe $outDir
        }
        Write-Host "Done."
    }
    else {
        Write-Host "log-min-to-con exited with code $exitCode." -ForegroundColor Red
    }
}
catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Read-Host "Press Enter to exit..." | Out-Null
}
