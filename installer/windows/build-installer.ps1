# OpenDAW Windows Installer Build Script
# This script builds all components and creates the MSI installer

param(
    [string]$Version = "1.0.0",
    [string]$Configuration = "Release",
    [switch]$SkipRustBuild,
    [switch]$SkipCppBuild,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

# Paths
$ProjectRoot = Resolve-Path "$PSScriptRoot\..\.."
$BuildDir = "$ProjectRoot\installer\windows\build"
$StagingDir = "$BuildDir\staging"
$OutputDir = "$ProjectRoot\installer\windows\output"
$RustTargetDir = "$ProjectRoot\daw-engine\target\release"
$CppBuildDir = "$ProjectRoot\ui\build"

Write-Host "OpenDAW Windows Installer Build" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Version: $Version"
Write-Host "Configuration: $Configuration"
Write-Host "Project Root: $ProjectRoot"
Write-Host ""

# Clean if requested
if ($Clean) {
    Write-Host "Cleaning build directories..." -ForegroundColor Yellow
    if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
    if (Test-Path $OutputDir) { Remove-Item -Recurse -Force $OutputDir }
}

# Create directories
New-Item -ItemType Directory -Force -Path $StagingDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
New-Item -ItemType Directory -Force -Path "$StagingDir\ai_modules" | Out-Null

# Step 1: Build Rust Engine DLL
if (-not $SkipRustBuild) {
    Write-Host "`nStep 1: Building Rust Engine DLL..." -ForegroundColor Green
    Set-Location "$ProjectRoot\daw-engine"
    
    $rustBuildOutput = cargo build --release 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Rust build failed: $rustBuildOutput"
        exit 1
    }
    
    # Verify DLL was created
    $dllPath = "$RustTargetDir\daw_engine.dll"
    if (-not (Test-Path $dllPath)) {
        Write-Error "Rust DLL not found at $dllPath"
        exit 1
    }
    
    Write-Host "✓ Rust engine built successfully" -ForegroundColor Green
    Write-Host "  DLL: $dllPath"
    Write-Host "  Size: $((Get-Item $dllPath).Length / 1MB) MB"
} else {
    Write-Host "`nStep 1: Skipping Rust build (using existing DLL)" -ForegroundColor Yellow
}

# Step 2: Build C++ UI
if (-not $SkipCppBuild) {
    Write-Host "`nStep 2: Building C++ UI..." -ForegroundColor Green
    Set-Location "$ProjectRoot\ui"
    
    # Configure if not already done
    if (-not (Test-Path "$CppBuildDir\CMakeCache.txt")) {
        Write-Host "  Configuring CMake..."
        $cmakeOutput = cmake -B build -S . -DCMAKE_BUILD_TYPE=$Configuration 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "CMake configuration failed: $cmakeOutput"
            exit 1
        }
    }
    
    # Build
    Write-Host "  Building OpenDAW.exe..."
    $buildOutput = cmake --build build --config $Configuration 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "C++ build failed: $buildOutput"
        exit 1
    }
    
    # Verify EXE was created
    $exePath = "$CppBuildDir\$Configuration\OpenDAW.exe"
    if (-not (Test-Path $exePath)) {
        # Try alternative path
        $exePath = "$CppBuildDir\OpenDAW.exe"
    }
    
    if (-not (Test-Path $exePath)) {
        Write-Error "OpenDAW.exe not found. Searched:`n  - $CppBuildDir\$Configuration\OpenDAW.exe`n  - $CppBuildDir\OpenDAW.exe"
        exit 1
    }
    
    Write-Host "✓ C++ UI built successfully" -ForegroundColor Green
    Write-Host "  EXE: $exePath"
    Write-Host "  Size: $((Get-Item $exePath).Length / 1MB) MB"
} else {
    Write-Host "`nStep 2: Skipping C++ build (using existing EXE)" -ForegroundColor Yellow
}

# Step 3: Stage Files
Write-Host "`nStep 3: Staging installation files..." -ForegroundColor Green

# Copy Rust DLL
$sourceDll = "$RustTargetDir\daw_engine.dll"
if (Test-Path $sourceDll) {
    Copy-Item $sourceDll "$StagingDir\daw_engine.dll" -Force
    Write-Host "✓ Copied daw_engine.dll"
}

# Copy C++ EXE
$sourceExe = if (Test-Path "$CppBuildDir\$Configuration\OpenDAW.exe") { 
    "$CppBuildDir\$Configuration\OpenDAW.exe" 
} else { 
    "$CppBuildDir\OpenDAW.exe" 
}

if (Test-Path $sourceExe) {
    Copy-Item $sourceExe "$StagingDir\OpenDAW.exe" -Force
    Write-Host "✓ Copied OpenDAW.exe"
}

# Copy AI modules
$sourceAiModules = "$ProjectRoot\ai_modules"
if (Test-Path $sourceAiModules) {
    Copy-Item -Recurse -Force "$sourceAiModules\*" "$StagingDir\ai_modules\"
    Write-Host "✓ Copied AI modules"
}

# Copy documentation
$sourceReadme = "$ProjectRoot\README.md"
if (Test-Path $sourceReadme) {
    Copy-Item $sourceReadme "$StagingDir\README.md" -Force
    Write-Host "✓ Copied README.md"
}

# Copy license
$sourceLicense = "$ProjectRoot\LICENSE"
if (Test-Path $sourceLicense) {
    Copy-Item $sourceLicense "$StagingDir\LICENSE" -Force
    Write-Host "✓ Copied LICENSE"
}

# Step 4: Check for WiX tools
Write-Host "`nStep 4: Checking WiX Toolset..." -ForegroundColor Green

$wixDir = $env:WIX
if (-not $wixDir) {
    # Try to find WiX in common locations
    $possiblePaths = @(
        "C:\Program Files (x86)\WiX Toolset v3.11\bin",
        "C:\Program Files\WiX Toolset v3.11\bin",
        "${env:ProgramFiles(x86)}\WiX Toolset v3.11\bin",
        "${env:ProgramFiles}\WiX Toolset v3.11\bin"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path "$path\candle.exe") {
            $wixDir = $path
            break
        }
    }
}

if (-not $wixDir -or -not (Test-Path "$wixDir\candle.exe")) {
    Write-Error @"
WiX Toolset not found!

Please install WiX Toolset v3.11 or later from:
  https://wixtoolset.org/releases/

Or set the WIX environment variable to the WiX bin directory.
"@
    exit 1
}

Write-Host "✓ WiX Toolset found: $wixDir" -ForegroundColor Green

# Step 5: Generate WiX variables file
Write-Host "`nStep 5: Generating WiX variables..." -ForegroundColor Green

$wixVarsPath = "$BuildDir\variables.wxi"
$wixVars = @"
<?xml version="1.0" encoding="UTF-8"?>
<Include xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <?define ProductVersion = "$Version" ?>
  <?define SourceDir = "$StagingDir" ?>
  <?define UIBuildDir = "$StagingDir" ?>
  <?define EngineBuildDir = "$StagingDir" ?>
</Include>
"@

$wixVars | Out-File -FilePath $wixVarsPath -Encoding UTF8
Write-Host "✓ Generated variables.wxi"

# Step 6: Create installer assets if they don't exist
Write-Host "`nStep 6: Checking installer assets..." -ForegroundColor Green

$assetsDir = "$ProjectRoot\installer\windows"

# Check for LICENSE.rtf
if (-not (Test-Path "$assetsDir\LICENSE.rtf")) {
    if (Test-Path "$ProjectRoot\LICENSE") {
        Write-Host "  Converting LICENSE to RTF..."
        # Simple RTF wrapper around plain text
        $licenseText = Get-Content "$ProjectRoot\LICENSE" -Raw
        $rtfContent = "{\rtf1\ansi\deff0 {\fonttbl {\f0 Consolas;}}`n\f0\fs20 `n$licenseText`n}"
        $rtfContent | Out-File -FilePath "$assetsDir\LICENSE.rtf" -Encoding UTF8
        Write-Host "✓ Created LICENSE.rtf"
    }
}

# Check for banner bitmap (493x58)
if (-not (Test-Path "$assetsDir\banner.bmp")) {
    Write-Host "  WARNING: banner.bmp not found (493x58 pixels expected)" -ForegroundColor Yellow
    Write-Host "  Installer will use default WiX banner"
}

# Check for dialog bitmap (493x312)
if (-not (Test-Path "$assetsDir\dialog.bmp")) {
    Write-Host "  WARNING: dialog.bmp not found (493x312 pixels expected)" -ForegroundColor Yellow
    Write-Host "  Installer will use default WiX dialog"
}

# Check for icon
if (-not (Test-Path "$assetsDir\OpenDAW.ico")) {
    Write-Host "  WARNING: OpenDAW.ico not found" -ForegroundColor Yellow
    Write-Host "  Installer will extract icon from OpenDAW.exe"
}

# Step 7: Compile WiX source
Write-Host "`nStep 7: Compiling WiX source..." -ForegroundColor Green

Set-Location $ProjectRoot

$sourceWxs = "$ProjectRoot\installer\windows\OpenDAW.wxs"
if (-not (Test-Path $sourceWxs)) {
    Write-Error "WiX source file not found: $sourceWxs"
    exit 1
}

# Compile with candle
Write-Host "  Running candle.exe..."
$candleOutput = & "$wixDir\candle.exe" `
    -nologo `
    -out "$BuildDir\OpenDAW.wixobj" `
    -I "$BuildDir" `
    -dSourceDir="$StagingDir" `
    -dUIBuildDir="$StagingDir" `
    -dEngineBuildDir="$StagingDir" `
    -dVCRedistDir="$env:SystemRoot\System32" `
    "$sourceWxs" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Error "WiX compilation failed:`n$candleOutput"
    exit 1
}

Write-Host "✓ Compiled OpenDAW.wxs → OpenDAW.wixobj"

# Step 8: Link MSI
Write-Host "`nStep 8: Linking MSI installer..." -ForegroundColor Green

$msiName = "OpenDAW-$Version.msi"
$msiPath = "$OutputDir\$msiName"

Write-Host "  Running light.exe..."
$lightOutput = & "$wixDir\light.exe" `
    -nologo `
    -out "$msiPath" `
    -ext "$wixDir\..\WixUIExtension.dll" `
    -ext "$wixDir\..\WixUtilExtension.dll" `
    "$BuildDir\OpenDAW.wixobj" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Error "WiX linking failed:`n$lightOutput"
    exit 1
}

Write-Host "✓ Linked OpenDAW.wixobj → $msiName"

# Step 9: Verify output
Write-Host "`nStep 9: Verifying installer..." -ForegroundColor Green

if (Test-Path $msiPath) {
    $msiSize = (Get-Item $msiPath).Length / 1MB
    Write-Host "✓ MSI created successfully" -ForegroundColor Green
    Write-Host "  Path: $msiPath"
    Write-Host "  Size: $([math]::Round($msiSize, 2)) MB"
    
    # Get MSI info
    try {
        $windowsInstaller = New-Object -com WindowsInstaller.Installer
        $database = $windowsInstaller.GetType().InvokeMember(
            "OpenDatabase", "InvokeMethod", $null, $windowsInstaller,
            @($msiPath, 0)
        )
        
        $query = "SELECT Value FROM Property WHERE Property = 'ProductVersion'"
        $view = $database.GetType().InvokeMember(
            "OpenView", "InvokeMethod", $null, $database, @($query)
        )
        $view.GetType().InvokeMember("Execute", "InvokeMethod", $null, $view, $null)
        $record = $view.GetType().InvokeMember("Fetch", "InvokeMethod", $null, $view, $null)
        $version = $record.GetType().InvokeMember(
            "StringData", "GetProperty", $null, $record, 1
        )
        $view.GetType().InvokeMember("Close", "InvokeMethod", $null, $view, $null)
        
        Write-Host "  Version: $version"
    } catch {
        Write-Host "  (Could not read MSI version info)"
    }
} else {
    Write-Error "MSI not found at expected path: $msiPath"
    exit 1
}

# Summary
Write-Host "`n=================================" -ForegroundColor Cyan
Write-Host "Build Complete!" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "`nOutput: $msiPath"
Write-Host "`nTo install:"
Write-Host "  msiexec /i `"$msiPath`" /qn"
Write-Host "`nTo test installation:"
Write-Host "  1. Run the MSI on a clean Windows machine"
Write-Host "  2. Verify OpenDAW appears in Start Menu"
Write-Host "  3. Launch OpenDAW.exe"
Write-Host "  4. Verify all components load (UI, engine, AI modules)"
Write-Host ""
