@echo off
echo ========================================
echo  Bitcoin Wallet Generator Pro v2.0
echo  Building Portable Version (Folder)
echo ========================================
echo.

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo [1/5] Installing dependencies...
pip install pyinstaller
pip install -r requirements_pro.txt

echo.
echo [2/5] Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"

echo.
echo [3/5] Building portable application...
pyinstaller ^
    --onedir ^
    --windowed ^
    --name "BitcoinWalletGeneratorPro" ^
    --icon="build_assets/bitcoin.ico" ^
    --add-data "config.json;." ^
    --add-data "requirements_pro.txt;." ^
    --add-data "README_PRO.md;." ^
    --hidden-import "flask" ^
    --hidden-import "flask_socketio" ^
    --hidden-import "socketio" ^
    --hidden-import "engineio" ^
    --hidden-import "ecdsa" ^
    --hidden-import "base58" ^
    --hidden-import "psutil" ^
    --hidden-import "sqlite3" ^
    --collect-all "flask_socketio" ^
    btc_wallet_generator_pro.py

echo.
echo [4/5] Creating launcher script...
echo @echo off > "dist\BitcoinWalletGeneratorPro\Start_Bitcoin_Generator.bat"
echo echo Starting Bitcoin Wallet Generator Pro... >> "dist\BitcoinWalletGeneratorPro\Start_Bitcoin_Generator.bat"
echo echo. >> "dist\BitcoinWalletGeneratorPro\Start_Bitcoin_Generator.bat"
echo echo The application will start in a few seconds... >> "dist\BitcoinWalletGeneratorPro\Start_Bitcoin_Generator.bat"
echo echo After startup, open your browser and go to: >> "dist\BitcoinWalletGeneratorPro\Start_Bitcoin_Generator.bat"
echo echo http://localhost:5000 >> "dist\BitcoinWalletGeneratorPro\Start_Bitcoin_Generator.bat"
echo echo. >> "dist\BitcoinWalletGeneratorPro\Start_Bitcoin_Generator.bat"
echo timeout /t 3 /nobreak ^>nul >> "dist\BitcoinWalletGeneratorPro\Start_Bitcoin_Generator.bat"
echo start http://localhost:5000 >> "dist\BitcoinWalletGeneratorPro\Start_Bitcoin_Generator.bat"
echo BitcoinWalletGeneratorPro.exe >> "dist\BitcoinWalletGeneratorPro\Start_Bitcoin_Generator.bat"

echo.
echo [5/5] Creating README for portable version...
echo Bitcoin Wallet Generator Pro v2.0 - Portable Version > "dist\BitcoinWalletGeneratorPro\README.txt"
echo. >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo QUICK START: >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo 1. Double-click "Start_Bitcoin_Generator.bat" >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo 2. Wait for browser to open automatically >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo 3. If browser doesn't open, go to: http://localhost:5000 >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo. >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo MANUAL START: >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo 1. Run "BitcoinWalletGeneratorPro.exe" >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo 2. Open browser and go to http://localhost:5000 >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo. >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo CONFIGURATION: >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo - Edit config.json to customize settings >> "dist\BitcoinWalletGeneratorPro\README.txt"
echo - See README_PRO.md for detailed documentation >> "dist\BitcoinWalletGeneratorPro\README.txt"

echo.
echo ========================================
echo       Build Completed Successfully!
echo ========================================
echo.
echo Portable application created in:
echo dist\BitcoinWalletGeneratorPro\
echo.
echo To use:
echo 1. Go to dist\BitcoinWalletGeneratorPro\ folder
echo 2. Double-click "Start_Bitcoin_Generator.bat"
echo 3. Browser will open automatically
echo.
echo Files included:
echo - BitcoinWalletGeneratorPro.exe (main application)
echo - Start_Bitcoin_Generator.bat (easy launcher)
echo - config.json (configuration file)
echo - README.txt (quick start guide)
echo - README_PRO.md (full documentation)
echo - _internal\ folder (required libraries)
echo.
echo You can copy this entire folder to any Windows PC!
echo ========================================

pause