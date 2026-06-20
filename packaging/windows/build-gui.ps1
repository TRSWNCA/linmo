param(
    [string]$DistRoot = "dist\windows",
    [string]$BuildRoot = "build\windows",
    [switch]$NoArchive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$FrontendDir = Join-Path $RepoRoot "frontend"
$FrontendDist = Join-Path $FrontendDir "dist"
$SrcDir = Join-Path $RepoRoot "src"
$IconPath = Join-Path $FrontendDir "icon.png"
$DistPath = Join-Path $RepoRoot $DistRoot
$BuildPath = Join-Path $RepoRoot $BuildRoot
$EntryDir = Join-Path $BuildPath "entry"
$EntryPath = Join-Path $EntryDir "linmo_gui.py"
$AppDir = Join-Path $DistPath "Linmo"
$BundledFrontend = Join-Path $AppDir "frontend\dist"
$ArchivePath = Join-Path $DistPath "Linmo-windows-gui.zip"

Require-Command "uv"
Require-Command "npm"

Push-Location $RepoRoot
try {
    Write-Host "Installing Python dependencies..."
    uv sync --frozen

    Write-Host "Building frontend..."
    Push-Location $FrontendDir
    try {
        npm ci
        npm run build
    }
    finally {
        Pop-Location
    }

    if (-not (Test-Path (Join-Path $FrontendDist "index.html"))) {
        throw "Frontend build did not produce frontend\dist\index.html"
    }

    New-Item -ItemType Directory -Force -Path $EntryDir | Out-Null
    @"
from linmo_app.launcher import main

if __name__ == "__main__":
    main()
"@ | Set-Content -Path $EntryPath -Encoding UTF8

    if (Test-Path $AppDir) {
        Remove-Item -Recurse -Force $AppDir
    }
    if (Test-Path $ArchivePath) {
        Remove-Item -Force $ArchivePath
    }

    $PyInstallerArgs = @(
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name", "Linmo",
        "--distpath", $DistPath,
        "--workpath", $BuildPath,
        "--specpath", $BuildPath,
        "--paths", $SrcDir,
        "--icon", $IconPath,
        "--hidden-import", "webview.platforms.edgechromium",
        "--exclude-module", "PySide6",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PyQt6",
        "--exclude-module", "qtpy",
        "--exclude-module", "gi",
        "--exclude-module", "webview.platforms.cocoa",
        "--exclude-module", "webview.platforms.gtk",
        "--exclude-module", "webview.platforms.qt",
        $EntryPath
    )

    Write-Host "Freezing Linmo GUI with PyInstaller..."
    uv run --with pyinstaller pyinstaller @PyInstallerArgs

    Write-Host "Copying frontend assets..."
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $BundledFrontend) | Out-Null
    if (Test-Path $BundledFrontend) {
        Remove-Item -Recurse -Force $BundledFrontend
    }
    Copy-Item -Recurse -Force $FrontendDist $BundledFrontend

    if (-not $NoArchive) {
        Write-Host "Creating portable archive..."
        Compress-Archive -Path (Join-Path $AppDir "*") -DestinationPath $ArchivePath -Force
    }

    Write-Host "Done."
    Write-Host "App: $AppDir"
    if (-not $NoArchive) {
        Write-Host "Archive: $ArchivePath"
    }
}
finally {
    Pop-Location
}
