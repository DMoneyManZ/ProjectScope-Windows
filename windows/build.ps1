# SPDX-License-Identifier: GPL-3.0-only
[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$SkipDependencyInstall,
    [switch]$SkipSetup
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($env:OS -ne "Windows_NT") { throw "Build this Windows package on Windows." }
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Version = "1.1.0-preview.1"
$Output = Join-Path $Root "windows-artifacts"
$Work = Join-Path $Root "build\windows"
$Dist = Join-Path $Root "dist\windows"
foreach ($Path in @($Output, $Work, $Dist)) {
    if (Test-Path $Path) { Remove-Item -LiteralPath $Path -Recurse -Force }
    New-Item -ItemType Directory -Path $Path | Out-Null
}
& $Python -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32, 'Python 3.12 x64 required'"
if ($LASTEXITCODE -ne 0) { throw "Python version or architecture check failed." }
if (-not $SkipDependencyInstall) {
    & $Python -m pip install -r windows/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
}
& $Python -m PyInstaller --noconfirm --clean --distpath $Dist --workpath (Join-Path $Work "pyinstaller") windows/ProjectScope.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
$Bundle = Join-Path $Dist "ProjectScope"
$Executable = Join-Path $Bundle "ProjectScope.exe"
foreach ($Relative in @("ProjectScope.exe", "_internal\LICENSE", "_internal\source\ProjectScope\windows\build.ps1", "_internal\licenses\components.json")) {
    if (-not (Test-Path (Join-Path $Bundle $Relative))) { throw "Missing package file: $Relative" }
}
# Human-readable entry points; the complete texts/sources remain in _internal.
Copy-Item (Join-Path $Root "LICENSE") (Join-Path $Bundle "LICENSE")
Copy-Item (Join-Path $Root "docs\WINDOWS-INSTALL.md") (Join-Path $Bundle "WINDOWS-INSTALL.md")
Copy-Item (Join-Path $Root "windows\THIRD-PARTY-NOTICES.md") (Join-Path $Bundle "THIRD-PARTY-NOTICES.md")

# This is a fresh native Windows process, never an offscreen Qt smoke test.
$PreviousPlatform = $env:QT_QPA_PLATFORM
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
$Validation = Join-Path $Output "validation"
New-Item -ItemType Directory -Path $Validation | Out-Null
$Screenshot = Join-Path $Validation "windows-frozen-smoke.png"
$SmokeData = Join-Path $Work "smoke-data"
try {
    $Arguments = '--smoke-test --output "' + $Screenshot + '" --data-dir "' + $SmokeData + '"'
    $Process = Start-Process -FilePath $Executable -ArgumentList $Arguments -PassThru
    if (-not $Process.WaitForExit(60000)) {
        $Process.Kill()
        throw "Frozen application smoke test timed out."
    }
    $Process.Refresh()
    if ($Process.ExitCode -ne 0) { throw "Frozen application smoke test failed: $($Process.ExitCode)" }
    if (-not (Test-Path $Screenshot)) { throw "Frozen application produced no smoke-test screenshot." }
    $Report = Get-Content ([IO.Path]::ChangeExtension($Screenshot, '.json')) -Raw | ConvertFrom-Json
    if (-not $Report.passed -or $Report.platform -ne 'win32' -or $Report.qt_platform -ne 'windows' -or $Report.presets -ne 30) {
        throw "Frozen report did not verify native Windows startup and all 30 presets."
    }
    if (-not ($Report.click_through -and $Report.no_activate -and $Report.layered)) {
        throw "Frozen report did not verify the required native overlay styles."
    }
    if ($Report.hotkeys_active.Count -ne 10) { throw "Not all 10 default global shortcuts registered." }
} finally {
    if ($null -ne $PreviousPlatform) { $env:QT_QPA_PLATFORM = $PreviousPlatform }
}

# Check included Qt modules against the corresponding-source set.
$AllowedQt = @("Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "Qt6Network.dll", "Qt6OpenGL.dll", "Qt6OpenGLWidgets.dll", "Qt6PrintSupport.dll", "Qt6DBus.dll", "Qt6Sql.dll", "Qt6Xml.dll", "Qt6Svg.dll", "Qt6SvgWidgets.dll", "Qt6Test.dll", "Qt6Concurrent.dll")
$QtDlls = Get-ChildItem -Path $Bundle -Filter "Qt6*.dll" -Recurse
foreach ($Dll in $QtDlls) {
    if ($AllowedQt -notcontains $Dll.Name) { throw "Review corresponding sources for unexpected Qt module: $($Dll.Name)" }
}
$Inventory = Get-ChildItem -Path $Bundle -File -Recurse | ForEach-Object {
    $_.FullName.Substring($Bundle.Length + 1).Replace('\', '/')
}
$Inventory | Set-Content (Join-Path $Validation "package-files.txt") -Encoding utf8
& $Python -m pip freeze | Set-Content (Join-Path $Validation "build-packages.txt") -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "Could not record build dependencies." }

$Zip = Join-Path $Output "ProjectScope-Windows-$Version-x64.zip"
Compress-Archive -Path $Bundle -DestinationPath $Zip -CompressionLevel Optimal

if (-not $SkipSetup) {
    $Compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    $ISCC = if ($Compiler) { $Compiler.Source } else { $null }
    if (-not $ISCC) {
        foreach ($Candidate in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe")) {
            if (Test-Path $Candidate) { $ISCC = $Candidate; break }
        }
    }
    if ($ISCC) {
        & $ISCC "/DSourceRoot=$Root" "/DOutputRoot=$Output" (Join-Path $PSScriptRoot "setup.iss")
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed." }
    } else {
        Write-Warning "Inno Setup is not installed. The portable ZIP is the completed Windows package."
    }
}
Get-ChildItem $Output -File | Where-Object { $_.Extension -in @('.zip', '.exe') } | Sort-Object Name | ForEach-Object {
    $Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$Hash  $($_.Name)"
} | Set-Content (Join-Path $Output "SHA256SUMS") -Encoding ascii
Write-Host "Private Windows build artifacts: $Output"
