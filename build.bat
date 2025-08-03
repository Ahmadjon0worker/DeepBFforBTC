@echo off
echo ========================================
echo    Bitcoin Wallet Generator Pro v2.0
echo    Building executable with PyInstaller
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python and try again.
    pause
    exit /b 1
)

:: Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not available!
    echo Please install pip and try again.
    pause
    exit /b 1
)

echo [1/6] Installing required dependencies...
pip install pyinstaller
pip install -r requirements_pro.txt

echo.
echo [2/6] Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"

echo.
echo [3/6] Creating build directory structure...
if not exist "build_assets" mkdir "build_assets"

echo.
echo [4/6] Building executable with PyInstaller...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "BitcoinWalletGeneratorPro" ^
    --icon="build_assets/bitcoin.ico" ^
    --add-data "config.json;." ^
    --add-data "requirements_pro.txt;." ^
    --hidden-import "flask" ^
    --hidden-import "flask_socketio" ^
    --hidden-import "socketio" ^
    --hidden-import "engineio" ^
    --hidden-import "ecdsa" ^
    --hidden-import "base58" ^
    --hidden-import "psutil" ^
    --hidden-import "sqlite3" ^
    --hidden-import "secrets" ^
    --hidden-import "hashlib" ^
    --hidden-import "threading" ^
    --hidden-import "queue" ^
    --hidden-import "concurrent.futures" ^
    --collect-all "flask_socketio" ^
    --collect-all "socketio" ^
    --collect-all "engineio" ^
    btc_wallet_generator_pro.py

echo.
echo [5/6] Copying additional files...
if exist "dist\BitcoinWalletGeneratorPro.exe" (
    copy "config.json" "dist\" >nul 2>&1
    copy "requirements_pro.txt" "dist\" >nul 2>&1
    copy "README_PRO.md" "dist\" >nul 2>&1
    echo Additional files copied to dist folder.
) else (
    echo ERROR: Build failed! Executable not found.
    pause
    exit /b 1
)

echo.
echo [6/6] Build completed successfully!
echo.
echo ========================================
echo    Build Summary
echo ========================================
echo Executable: dist\BitcoinWalletGeneratorPro.exe
echo Size: 
for %%A in ("dist\BitcoinWalletGeneratorPro.exe") do echo %%~zA bytes
echo.
echo Additional files in dist folder:
echo - config.json
echo - requirements_pro.txt  
echo - README_PRO.md
echo.
echo ========================================
echo To run the application:
echo 1. Go to 'dist' folder
echo 2. Run BitcoinWalletGeneratorPro.exe
echo 3. Open browser: http://localhost:5000
echo ========================================
echo.

pause