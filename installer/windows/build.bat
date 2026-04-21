@echo off
REM Build script for OpenDAW Windows Installer
REM Requires WiX Toolset v3.11 or later

echo Building OpenDAW Windows Installer...

REM Set paths
set WIX_DIR=C:\Program Files (x86)\WiX Toolset v3.11\bin
set SOURCE_DIR=..\..
set UI_BUILD_DIR=%SOURCE_DIR%\ui\build
set ENGINE_BUILD_DIR=%SOURCE_DIR%\daw-engine\target\release
set BUILD_DIR=..\build
set OUTPUT_DIR=..\output

REM Create directories
if not exist %BUILD_DIR% mkdir %BUILD_DIR%
if not exist %OUTPUT_DIR% mkdir %OUTPUT_DIR%

REM Preprocess the source file to resolve variables
echo Preprocessing WiX source...
"%WIX_DIR%\candle.exe" -nologo ^
  -dSourceDir=%SOURCE_DIR% ^
  -dUIBuildDir=%UI_BUILD_DIR% ^
  -dEngineBuildDir=%ENGINE_BUILD_DIR% ^
  -dVCRedistDir=%SOURCE_DIR%\third_party ^
  -out %BUILD_DIR%\OpenDAW.wixobj ^
  OpenDAW.wxs

if %ERRORLEVEL% neq 0 (
  echo ERROR: Candle preprocessing failed
  exit /b 1
)

REM Link the installer
echo Linking installer...
"%WIX_DIR%\light.exe" -nologo ^
  -out %OUTPUT_DIR%\OpenDAW-Setup-1.0.0.msi ^
  -ext WixUIExtension ^
  -ext WixUtilExtension ^
  -cultures:en-us ^
  %BUILD_DIR%\OpenDAW.wixobj

if %ERRORLEVEL% neq 0 (
  echo ERROR: Light linking failed
  exit /b 1
)

echo.
echo Installer built successfully: %OUTPUT_DIR%\OpenDAW-Setup-1.0.0.msi
echo.

REM Optional: Build bundle with VCRedist
echo Building bootstrapper bundle...
"%WIX_DIR%\candle.exe" -nologo -out %BUILD_DIR%\Bundle.wixobj Bundle.wxs
"%WIX_DIR%\light.exe" -nologo -out %OUTPUT_DIR%\OpenDAW-Setup-1.0.0.exe -ext WixBalExtension %BUILD_DIR%\Bundle.wixobj

echo Bootstrapper built: %OUTPUT_DIR%\OpenDAW-Setup-1.0.0.exe
echo.
echo Build complete!

pause
