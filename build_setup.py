#!/usr/bin/env python3
"""
Bitcoin Wallet Generator Pro v2.0
PyInstaller Setup Script

This script provides advanced configuration for building the executable
with PyInstaller, including custom options and error handling.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Build configuration
BUILD_CONFIG = {
    'app_name': 'BitcoinWalletGeneratorPro',
    'main_script': 'btc_wallet_generator_pro.py',
    'icon_path': 'build_assets/bitcoin.ico',
    'version': '2.0.0',
    'description': 'Bitcoin Wallet Generator Pro - Advanced wallet generation tool',
    'company': 'Crypto Tools Inc.',
    'copyright': '© 2024 Bitcoin Wallet Generator Pro'
}

# Files to include in the build
ADDITIONAL_FILES = [
    'config.json',
    'requirements_pro.txt',
    'README_PRO.md'
]

# Hidden imports for PyInstaller
HIDDEN_IMPORTS = [
    'flask',
    'flask_socketio',
    'socketio',
    'engineio',
    'ecdsa',
    'base58',
    'psutil',
    'sqlite3',
    'secrets',
    'hashlib',
    'threading',
    'queue',
    'concurrent.futures',
    'json',
    'datetime',
    'time',
    'os',
    'requests'
]

# Collect-all modules
COLLECT_ALL = [
    'flask_socketio',
    'socketio',
    'engineio'
]

def check_requirements():
    """Check if all required tools and files are available"""
    print("🔍 Checking build requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required!")
        return False
    
    # Check if main script exists
    if not Path(BUILD_CONFIG['main_script']).exists():
        print(f"❌ Main script not found: {BUILD_CONFIG['main_script']}")
        return False
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not installed! Run: pip install pyinstaller")
        return False
    
    print("✅ All requirements satisfied!")
    return True

def clean_build():
    """Clean previous build artifacts"""
    print("🧹 Cleaning previous builds...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.spec']
    
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"   Removed: {dir_name}/")
    
    for pattern in files_to_clean:
        for file_path in Path('.').glob(pattern):
            file_path.unlink()
            print(f"   Removed: {file_path}")

def create_version_file():
    """Create version info file for Windows executable"""
    version_template = f'''
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({BUILD_CONFIG['version'].replace('.', ', ')}, 0),
    prodvers=({BUILD_CONFIG['version'].replace('.', ', ')}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'{BUILD_CONFIG['company']}'),
            StringStruct(u'FileDescription', u'{BUILD_CONFIG['description']}'),
            StringStruct(u'FileVersion', u'{BUILD_CONFIG['version']}'),
            StringStruct(u'InternalName', u'{BUILD_CONFIG['app_name']}'),
            StringStruct(u'LegalCopyright', u'{BUILD_CONFIG['copyright']}'),
            StringStruct(u'OriginalFilename', u'{BUILD_CONFIG['app_name']}.exe'),
            StringStruct(u'ProductName', u'{BUILD_CONFIG['app_name']}'),
            StringStruct(u'ProductVersion', u'{BUILD_CONFIG['version']}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    
    with open('version_info.txt', 'w') as f:
        f.write(version_template)
    
    print("✅ Version info file created")

def build_executable(build_type='onefile'):
    """Build the executable using PyInstaller"""
    print(f"🔨 Building {build_type} executable...")
    
    # Base PyInstaller command
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        f'--{build_type}',
        '--windowed',
        f'--name={BUILD_CONFIG["app_name"]}',
        f'--distpath=dist',
        f'--workpath=build'
    ]
    
    # Add icon if available
    if Path(BUILD_CONFIG['icon_path']).exists():
        cmd.extend([f'--icon={BUILD_CONFIG["icon_path"]}'])
    
    # Add version info if on Windows
    if sys.platform == 'win32' and Path('version_info.txt').exists():
        cmd.extend(['--version-file=version_info.txt'])
    
    # Add additional data files
    for file_path in ADDITIONAL_FILES:
        if Path(file_path).exists():
            cmd.extend([f'--add-data={file_path};.'])
    
    # Add hidden imports
    for module in HIDDEN_IMPORTS:
        cmd.extend([f'--hidden-import={module}'])
    
    # Add collect-all modules
    for module in COLLECT_ALL:
        cmd.extend([f'--collect-all={module}'])
    
    # Add main script
    cmd.append(BUILD_CONFIG['main_script'])
    
    print(f"🚀 Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed!")
        print(f"Error: {e.stderr}")
        return False

def create_launcher_scripts():
    """Create convenient launcher scripts"""
    print("📝 Creating launcher scripts...")
    
    if sys.platform == 'win32':
        # Windows batch launcher
        launcher_content = f'''@echo off
title {BUILD_CONFIG["app_name"]} v{BUILD_CONFIG["version"]}
echo.
echo ========================================
echo   {BUILD_CONFIG["app_name"]} v{BUILD_CONFIG["version"]}
echo ========================================
echo.
echo Starting application...
echo The web interface will open at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the application
echo.

timeout /t 3 /nobreak >nul
start http://localhost:5000
{BUILD_CONFIG["app_name"]}.exe
pause
'''
        
        launcher_path = Path('dist') / 'Start_Application.bat'
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        
        print(f"✅ Windows launcher created: {launcher_path}")
    
    # Create README for distribution
    readme_content = f'''# {BUILD_CONFIG["app_name"]} v{BUILD_CONFIG["version"]}

## Quick Start

### Windows:
1. Double-click "Start_Application.bat" (recommended)
2. Or run "{BUILD_CONFIG["app_name"]}.exe" directly

### Manual Start:
1. Run the executable
2. Open your web browser
3. Go to: http://localhost:5000

## Configuration

Edit `config.json` to customize settings:
- Worker threads count
- API timeouts
- Wallet types to generate
- Telegram notifications

## Support

For detailed documentation, see README_PRO.md

## Version: {BUILD_CONFIG["version"]}
Built with PyInstaller
'''
    
    readme_path = Path('dist') / 'README.txt'
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    print(f"✅ Distribution README created: {readme_path}")

def main():
    """Main build process"""
    print("🚀 Bitcoin Wallet Generator Pro - Build Script")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Clean previous builds
    clean_build()
    
    # Create version file
    if sys.platform == 'win32':
        create_version_file()
    
    # Ask user for build type
    print("\nChoose build type:")
    print("1. Single file executable (slower startup, portable)")
    print("2. Directory with executable (faster startup, larger)")
    
    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice == '1':
            build_type = 'onefile'
            break
        elif choice == '2':
            build_type = 'onedir'
            break
        else:
            print("Invalid choice! Please enter 1 or 2.")
    
    # Build executable
    if not build_executable(build_type):
        sys.exit(1)
    
    # Create launcher scripts
    create_launcher_scripts()
    
    # Final summary
    print("\n" + "=" * 50)
    print("🎉 Build completed successfully!")
    print("=" * 50)
    
    dist_path = Path('dist')
    if build_type == 'onefile':
        exe_path = dist_path / f'{BUILD_CONFIG["app_name"]}.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📁 Executable: {exe_path}")
            print(f"📏 Size: {size_mb:.1f} MB")
    else:
        folder_path = dist_path / BUILD_CONFIG["app_name"]
        if folder_path.exists():
            print(f"📁 Application folder: {folder_path}")
    
    print(f"📝 Launch with: Start_Application.bat")
    print(f"🌐 Web interface: http://localhost:5000")
    print("\n✅ Ready to distribute!")

if __name__ == '__main__':
    main()