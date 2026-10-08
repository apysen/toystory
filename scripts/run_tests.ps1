<#
.SYNOPSIS
    Runs every test in the project: the static checks, then each probe.

.DESCRIPTION
    A test is anything under `tests/` that `extends SceneTree`, which is what makes a
    script runnable with `--script`. Fixtures extend RefCounted and are skipped by that
    rule without being listed. Probes that read the rendered frame (`get_texture`,
    `save_png`, `warp_mouse`) get a real window; the rest run headless.

.PARAMETER GodotExecutable
    Godot 4.7. Found on PATH or at the Steam install when not given.

.PARAMETER Filter
    Wildcard against the test's file name, e.g. -Filter "battle_*". Runs everything when
    not given.

.PARAMETER SkipPerformance
    Skips tests/performance, which are the slow ones and measure rather than assert.

.PARAMETER ListOnly
    Prints what would run, headless and windowed, and exits.

.PARAMETER TimeoutSeconds
    Per-test limit. A hung probe is reported as a timeout instead of stopping the run.

.EXAMPLE
    pwsh scripts/run_tests.ps1
    pwsh scripts/run_tests.ps1 -Filter "battle_*"
#>
param(
    [string]$GodotExecutable = "",
    [string]$Filter = "*",
    [switch]$SkipPerformance,
    [switch]$ListOnly,
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Resolve-Godot {
    param([string]$Explicit)
    if (-not [string]::IsNullOrWhiteSpace($Explicit)) { return $Explicit }
    $found = Get-Command godot, godot4 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $found) { return $found.Source }
    $steamGodot = "E:\Steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe"
    if (Test-Path -LiteralPath $steamGodot) { return $steamGodot }
    return ""
}

$GodotExecutable = Resolve-Godot -Explicit $GodotExecutable
if ([string]::IsNullOrWhiteSpace($GodotExecutable) -or -not (Test-Path -LiteralPath $GodotExecutable)) {
    throw "Godot executable not found. Pass -GodotExecutable with a Godot 4.7 path."
}

# Anything that calls one of these needs a real window. Kept as one pattern so the
# classification is a property of the probe rather than of a list in this file.
$windowedCallPattern = 'get_texture\(|save_png|warp_mouse'

function Get-Tests {
    $roots = @("tests")
    $discovered = @()
    foreach ($root in $roots) {
        $rootPath = Join-Path $projectRoot $root
        if (-not (Test-Path -LiteralPath $rootPath)) { continue }
        foreach ($file in Get-ChildItem -LiteralPath $rootPath -Recurse -Filter *.gd) {
            $text = Get-Content -Raw -LiteralPath $file.FullName
            # A test is a script the engine can be pointed at. A topic module or a
            # fixture extends RefCounted and is loaded by one, so it is not a test.
            if ($text -notmatch '(?m)^extends SceneTree\b') { continue }
            $relative = $file.FullName.Substring($projectRoot.Length + 1).Replace('\', '/')
            if ($SkipPerformance -and $relative -like "tests/performance/*") { continue }
            if ($file.BaseName -notlike $Filter) { continue }
            $discovered += [pscustomobject]@{
                Name     = $file.BaseName
                Path     = "res://$relative"
                Windowed = ($text -match $windowedCallPattern)
            }
        }
    }
    return $discovered | Sort-Object Windowed, Name
}

# The static checks run first and are not under tests/: they parse and scan the source
# rather than play the game, and a failure in one explains failures in everything else.
$staticChecks = @(
    [pscustomobject]@{ Name = "check_structure"; Path = "res://tools/check_structure.gd"; Windowed = $false }
)
$staticChecks = $staticChecks | Where-Object { $_.Name -like $Filter }

$tests = @($staticChecks) + @(Get-Tests)
if ($tests.Count -eq 0) {
    Write-Host "No tests matched -Filter '$Filter'."
    exit 0
}

if ($ListOnly) {
    foreach ($test in $tests) {
        $kind = if ($test.Windowed) { "windowed" } else { "headless" }
        Write-Host ("{0,-10} {1}" -f $kind, $test.Path)
    }
    Write-Host ""
    Write-Host ("{0} test(s): {1} headless, {2} windowed." -f `
        $tests.Count,
        (@($tests | Where-Object { -not $_.Windowed })).Count,
        (@($tests | Where-Object { $_.Windowed })).Count)
    exit 0
}

$logDirectory = Join-Path $projectRoot ".godot/test_logs"
if (-not (Test-Path -LiteralPath $logDirectory)) {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

# Once, before anything runs. A new class_name that has not been imported fails every
# test after it with "Could not resolve external class member" and a cascade of type
# errors that hide whatever the real state was.
Write-Host "Importing..."
$import = Start-Process -FilePath $GodotExecutable `
    -ArgumentList @("--headless", "--path", $projectRoot, "--import") `
    -WindowStyle Hidden -Wait -PassThru
if ($import.ExitCode -ne 0) {
    Write-Host "Import failed ($($import.ExitCode)). Nothing was run."
    exit $import.ExitCode
}

$results = @()
foreach ($test in $tests) {
    $kind = if ($test.Windowed) { "windowed" } else { "headless" }
    Write-Host ("Running {0} [{1}]" -f $test.Path, $kind)
    $logPath = Join-Path $logDirectory "$($test.Name).log"
    $arguments = @("--path", $projectRoot, "--audio-driver", "Dummy", "--log-file", $logPath, "--script", $test.Path)
    if (-not $test.Windowed) { $arguments = @("--headless") + $arguments }

    $started = Get-Date
    $process = Start-Process -FilePath $GodotExecutable -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        # Killed rather than waited on: a hung probe would otherwise hold the whole run,
        # and a timeout is a result worth reporting in its own right.
        try { $process.Kill() } catch { }
        $results += [pscustomobject]@{ Name = $test.Name; Status = "TIMEOUT"; Seconds = $TimeoutSeconds; Passes = 0 }
        Write-Host "  TIMEOUT after ${TimeoutSeconds}s"
        continue
    }
    $seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)

    $passes = 0
    if (Test-Path -LiteralPath $logPath) {
        $log = Get-Content -Encoding utf8 -LiteralPath $logPath
        $passes = (@($log | Select-String -SimpleMatch "PASS: ")).Count
        if ($process.ExitCode -ne 0) {
            # Only the failures, not the whole log: a passing probe prints hundreds of
            # lines and a failing one is being read for the handful that say why.
            $log | Select-String -Pattern "FAIL|ERROR" | ForEach-Object { Write-Host "  $_" }
        }
    }
    $status = if ($process.ExitCode -eq 0) { "PASS" } else { "FAIL($($process.ExitCode))" }
    $results += [pscustomobject]@{ Name = $test.Name; Status = $status; Seconds = $seconds; Passes = $passes }
    Write-Host ("  {0} in {1}s ({2} checks)" -f $status, $seconds, $passes)
}

Write-Host ""
$failed = @($results | Where-Object { $_.Status -ne "PASS" })
$totalPasses = ($results | Measure-Object -Property Passes -Sum).Sum
Write-Host ("{0} test(s), {1} check(s), {2} failed." -f $results.Count, $totalPasses, $failed.Count)
foreach ($failure in $failed) {
    Write-Host ("  {0}: {1}  (.godot/test_logs/{0}.log)" -f $failure.Name, $failure.Status)
}
if ($failed.Count -gt 0) { exit 1 }
Write-Host "All tests passed."
