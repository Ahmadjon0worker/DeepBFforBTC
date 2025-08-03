# 🔨 Build Instructions - Bitcoin Wallet Generator Pro

Sizning Python loyihangizni Windows `.exe` fayliga aylantirish uchun to'liq yo'riqnoma.

## 🚀 Quick Start (Eng Oson Yo'l)

### 1-Usul: Quick Build (Tavsiya etiladi)
```bash
# Faqat bu faylni ishga tushiring!
quick_build.bat
```
**Bu fayl hamma narsani avtomatik qiladi!**

## 📋 Manual Build Options

### 2-Usul: Advanced Python Script
```bash
# Interactive build with options
python build_setup.py
```

### 3-Usul: Professional BAT files
```bash
# Single EXE file
build.bat

# Portable folder version  
build_portable.bat
```

## 🛠️ Prerequisites (Talablar)

### Zarur Dasturlar:
- ✅ **Python 3.8+** (https://python.org)
- ✅ **pip** (Python bilan birga keladi)
- ✅ **Internet connection** (dependencies uchun)

### Auto-Install Dependencies:
Build scriptlar avtomatik o'rnatadi:
- PyInstaller
- Flask
- Flask-SocketIO
- va boshqa barcha kerakli kutubxonalar

## 📁 Build Options Comparison

| Build Type | File | Output | Size | Startup | Portability |
|------------|------|--------|------|---------|-------------|
| **Quick Build** | `quick_build.bat` | Single EXE | ~50MB | Medium | ⭐⭐⭐⭐⭐ |
| **Single File** | `build.bat` | Single EXE | ~45MB | Slow | ⭐⭐⭐⭐⭐ |
| **Portable** | `build_portable.bat` | Folder | ~35MB | Fast | ⭐⭐⭐⭐ |
| **Python Script** | `build_setup.py` | Custom | Variable | Variable | ⭐⭐⭐ |

## 🎯 Recommended Build Process

### Eng Yaxshi Variant:
1. **Quick Build** - oson va tez
2. Agar muammo bo'lsa **Portable Build**
3. Advanced users uchun **Python Script**

## 📦 Build Commands Detail

### Quick Build (Tavsiya):
```bash
quick_build.bat
```
**Xususiyatlari:**
- ✅ Hamma narsani avtomatik o'rnatadi
- ✅ Single EXE file yaratadi
- ✅ START_HERE.bat launcher qo'shadi
- ✅ QUICK_START.txt yo'riqnoma yaratadi
- ✅ Chiroyli ASCII art bilan
- ✅ Auto-open dist folder

### Professional Build:
```bash
build.bat
```
**Xususiyatlari:**
- ✅ To'liq error checking
- ✅ Version info qo'shadi
- ✅ Custom icon support
- ✅ Additional files auto-copy
- ✅ File size reporting

### Portable Build:
```bash
build_portable.bat
```
**Xususiyatlari:**
- ✅ Folder o'rniga EXE
- ✅ Tezroq ishga tushadi
- ✅ Launcher script yaratadi
- ✅ README.txt qo'shadi
- ✅ Har qanday PC ga ko'chirish mumkin

### Advanced Python Build:
```bash
python build_setup.py
```
**Xususiyatlari:**
- ✅ Interactive configuration
- ✅ Custom version info
- ✅ Error handling
- ✅ Build type selection
- ✅ Professional reporting

## 🔧 Manual PyInstaller Command

Agar barcha scriptlar ishlamasa, manual command:

```bash
# Dependencies install
pip install pyinstaller flask flask-socketio requests ecdsa base58 psutil

# Build command
pyinstaller --onefile --windowed --name "BitcoinWalletGeneratorPro" --add-data "config.json;." --hidden-import "flask" --hidden-import "flask_socketio" --collect-all "flask_socketio" btc_wallet_generator_pro.py
```

## 📋 Build Output Files

### Quick Build natijasi:
```
dist/
├── BitcoinWalletGeneratorPro.exe  (asosiy dastur)
├── START_HERE.bat                 (oson launcher)
├── config.json                    (sozlamalar)
├── QUICK_START.txt               (yo'riqnoma)
└── README_PRO.md                 (to'liq hujjat)
```

### Portable Build natijasi:
```
dist/BitcoinWalletGeneratorPro/
├── BitcoinWalletGeneratorPro.exe
├── Start_Bitcoin_Generator.bat
├── config.json
├── README.txt
├── README_PRO.md
└── _internal/ (kutubxonalar)
```

## ⚡ Performance Tips

### Tezroq Build uchun:
- ✅ SSD disk ishlatish
- ✅ Antivirus temporarily disable
- ✅ Close other programs
- ✅ Use fast internet connection

### Kichikroq EXE uchun:
- ✅ `--onefile` o'rniga `--onedir` ishlatish
- ✅ Unnecessary imports olib tashlash
- ✅ UPX compressor ishlatish (advanced)

## 🐛 Troubleshooting

### Common Issues:

#### 1. Python not found
```bash
# Solution:
# Python PATH ga qo'shilganligini tekshiring
python --version
```

#### 2. PyInstaller fails
```bash
# Solution:
pip install --upgrade pyinstaller
pip install --upgrade setuptools
```

#### 3. Missing modules
```bash
# Solution:
pip install -r requirements_pro.txt
# yoki
pip install flask flask-socketio requests ecdsa base58 psutil
```

#### 4. EXE doesn't work
```bash
# Solution:
# Console mode da test qiling:
pyinstaller --onefile --console btc_wallet_generator_pro.py
```

#### 5. Large EXE size
```bash
# Solution:
# Onedir version ishlatish:
pyinstaller --onedir btc_wallet_generator_pro.py
```

### Error Codes:
- **Exit Code 1**: Python not installed
- **Exit Code 2**: Dependencies missing  
- **Exit Code 3**: Build failed
- **Exit Code 4**: File permissions

## 🎨 Customization

### Icon qo'shish:
```bash
# build_assets/ folder yarating
# bitcoin.ico faylini qo'ying
# Build script avtomatik ishlatadi
```

### Version info:
```python
# build_setup.py da o'zgartiring:
BUILD_CONFIG = {
    'app_name': 'YourAppName',
    'version': '3.0.0',
    'description': 'Your Description'
}
```

## 📊 Build Time Estimates

| Build Type | Time | Size | 
|------------|------|------|
| Quick Build | 2-5 min | ~50MB |
| Single File | 3-7 min | ~45MB |
| Portable | 2-4 min | ~35MB |
| Advanced | 5-10 min | Variable |

## ✅ Final Checklist

Build oldidan tekshiring:
- [ ] Python 3.8+ o'rnatilgan
- [ ] pip ishlaydi
- [ ] Internet aloqasi mavjud
- [ ] Yetarli disk bo'sh joyi (1GB+)
- [ ] Antivirus to'sqinlik qilmaydi

Build keyin tekshiring:
- [ ] EXE fayli yaratildi
- [ ] Launcher bat file mavjud
- [ ] Config.json ko'chirildi
- [ ] README fayllar mavjud
- [ ] EXE ishga tushadi

## 🎉 Success!

Build muvaffaqiyatli tugagandan keyin:

1. **`dist/` papkasiga boring**
2. **`START_HERE.bat` ni bosing**
3. **Browser avtomatik ochiladi**
4. **Dasturingizdan foydalaning!**

### Distribution:
- To'liq `dist/` papkasini ZIP qiling
- Har qanday Windows PC ga ko'chiring
- Python o'rnatish shart emas!

---

## 💡 Pro Tips

### Tez build uchun:
```bash
# Faqat shu buyruqni ishlatish kifoya:
quick_build.bat
```

### Professional distribution:
```bash
# Advanced features bilan:
python build_setup.py
```

### Debugging uchun:
```bash
# Console version yaratish:
pyinstaller --onefile --console btc_wallet_generator_pro.py
```

---

**Happy Building! 🚀** Sizning Bitcoin Wallet Generator Pro dasturingiz tayyor!