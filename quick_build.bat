@echo off
title Bitcoin Wallet Generator Pro - Quick Build
color 0A

echo.
echo  $$$$$$\  $$$$$$\ $$$$$$$$\  $$$$$$\   $$$$$$\  $$$$$$\ $$\   $$\ 
echo $$  __$$\ \_$$  _|\__$$  __|$$  __$$\ $$  __$$\ \_$$  _|$$$\  $$ |
echo $$ |  $$ |  $$ |     $$ |   $$ /  \__|$$ /  $$ |  $$ |  $$$$\ $$ |
echo $$$$$$$\ |  $$ |     $$ |   $$ |      $$ |  $$ |  $$ |  $$ $$\$$ |
echo $$  __$$\   $$ |     $$ |   $$ |      $$ |  $$ |  $$ |  $$ \$$$$ |
echo $$ |  $$ |  $$ |     $$ |   $$ |  $$\ $$ |  $$ |  $$ |  $$ |\$$$ |
echo $$$$$$$  |$$$$$$\    $$ |   \$$$$$$  | $$$$$$  |$$$$$$\ $$ | \$$ |
echo \_______/ \______|   \__|    \______/  \______/ \______|\__|  \__|
echo.
echo          WALLET GENERATOR PRO v2.0 - QUICK BUILD
echo ================================================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH!
    echo Please install Python 3.8+ and try again.
    echo.
    pause
    exit /b 1
)

echo [INFO] Python found! Starting quick build...
echo.

:: Install PyInstaller if not present
echo [STEP 1] Installing PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller!
    pause
    exit /b 1
)

:: Install dependencies
echo [STEP 2] Installing dependencies...
pip install -r requirements_pro.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)

:: Clean previous builds
echo [STEP 3] Cleaning previous builds...
if exist "dist" rmdir /s /q "dist" >nul 2>&1
if exist "build" rmdir /s /q "build" >nul 2>&1
del *.spec >nul 2>&1

:: Create build assets directory
if not exist "build_assets" mkdir "build_assets"

:: Quick build with PyInstaller
echo [STEP 4] Building executable (this may take a few minutes)...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "BitcoinWalletGeneratorPro" ^
    --add-data "config.json;." ^
    --add-data "requirements_pro.txt;." ^
    --hidden-import "flask" ^
    --hidden-import "flask_socketio" ^
    --hidden-import "socketio" ^
    --hidden-import "engineio" ^
    --hidden-import "ecdsa" ^
    --hidden-import "base58" ^
    --hidden-import "psutil" ^
    --collect-all "flask_socketio" ^
    --noconfirm ^
    btc_wallet_generator_pro.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo Check the error messages above.
    pause
    exit /b 1
)

:: Create launcher
echo [STEP 5] Creating launcher...
echo @echo off > "dist\START_HERE.bat"
echo title Bitcoin Wallet Generator Pro v2.0 >> "dist\START_HERE.bat"
echo echo. >> "dist\START_HERE.bat"
echo echo =========================================== >> "dist\START_HERE.bat"
echo echo   Bitcoin Wallet Generator Pro v2.0 >> "dist\START_HERE.bat"
echo echo =========================================== >> "dist\START_HERE.bat"
echo echo. >> "dist\START_HERE.bat"
echo echo [INFO] Starting application... >> "dist\START_HERE.bat"
echo echo [INFO] Web interface will open at: http://localhost:5000 >> "dist\START_HERE.bat"
echo echo [INFO] Press Ctrl+C to stop the application >> "dist\START_HERE.bat"
echo echo. >> "dist\START_HERE.bat"
echo timeout /t 3 /nobreak ^>nul >> "dist\START_HERE.bat"
echo start http://localhost:5000 >> "dist\START_HERE.bat"
echo BitcoinWalletGeneratorPro.exe >> "dist\START_HERE.bat"
echo pause >> "dist\START_HERE.bat"

:: Copy additional files
echo [STEP 6] Copying additional files...
copy "config.json" "dist\" >nul 2>&1
copy "README_PRO.md" "dist\" >nul 2>&1

:: Create quick setup guide
echo Bitcoin Wallet Generator Pro v2.0 > "dist\QUICK_START.txt"
echo ================================== >> "dist\QUICK_START.txt"
echo. >> "dist\QUICK_START.txt"
echo SUPER EASY START: >> "dist\QUICK_START.txt"
echo 1. Double-click "START_HERE.bat" >> "dist\QUICK_START.txt"
echo 2. Wait for browser to open >> "dist\QUICK_START.txt"
echo 3. Click "Start Generation" >> "dist\QUICK_START.txt"
echo. >> "dist\QUICK_START.txt"
echo MANUAL START: >> "dist\QUICK_START.txt"
echo 1. Run "BitcoinWalletGeneratorPro.exe" >> "dist\QUICK_START.txt"
echo 2. Open browser: http://localhost:5000 >> "dist\QUICK_START.txt"
echo. >> "dist\QUICK_START.txt"
echo FEATURES: >> "dist\QUICK_START.txt"
echo - 3 wallet types (Legacy, SegWit, Bech32) >> "dist\QUICK_START.txt"
echo - 4 parallel workers >> "dist\QUICK_START.txt"
echo - Real-time web interface >> "dist\QUICK_START.txt"
echo - Database storage >> "dist\QUICK_START.txt"
echo - Telegram notifications >> "dist\QUICK_START.txt"
echo - Multi-API support >> "dist\QUICK_START.txt"
echo. >> "dist\QUICK_START.txt"
echo Edit config.json to customize settings! >> "dist\QUICK_START.txt"

:: Success message
cls
echo.
echo  ███████╗██╗   ██╗ ██████╗ ██████╗███████╗███████╗███████╗██╗
echo  ██╔════╝██║   ██║██╔════╝██╔════╝██╔════╝██╔════╝██╔════╝██║
echo  ███████╗██║   ██║██║     ██║     █████╗  ███████╗███████╗██║
echo  ╚════██║██║   ██║██║     ██║     ██╔══╝  ╚════██║╚════██║╚═╝
echo  ███████║╚██████╔╝╚██████╗╚██████╗███████╗███████║███████║██╗
echo  ╚══════╝ ╚═════╝  ╚═════╝ ╚═════╝╚══════╝╚══════╝╚══════╝╚═╝
echo.
echo ================================================================
echo                    BUILD COMPLETED SUCCESSFULLY!
echo ================================================================
echo.

:: Get file size
for %%A in ("dist\BitcoinWalletGeneratorPro.exe") do (
    set size=%%~zA
    set /a sizeMB=!size!/1024/1024
)

echo [SUCCESS] Executable created: dist\BitcoinWalletGeneratorPro.exe
echo [SUCCESS] Size: %sizeMB% MB
echo.
echo [FILES CREATED]:
echo  📁 dist\BitcoinWalletGeneratorPro.exe  (main application)
echo  📁 dist\START_HERE.bat                 (easy launcher)
echo  📁 dist\config.json                    (configuration)
echo  📁 dist\QUICK_START.txt                (instructions)
echo  📁 dist\README_PRO.md                  (full documentation)
echo.
echo [NEXT STEPS]:
echo  1. Go to 'dist' folder
echo  2. Double-click 'START_HERE.bat'
echo  3. Enjoy your Bitcoin Wallet Generator Pro!
echo.
echo [TIP] You can copy the entire 'dist' folder to any Windows PC!
echo.
echo ================================================================

:: Ask to open dist folder
echo.
set /p open="Open dist folder now? (y/n): "
if /i "%open%"=="y" (
    explorer "dist"
)

echo.
echo Thanks for using Bitcoin Wallet Generator Pro!
pause