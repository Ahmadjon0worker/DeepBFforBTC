# 🔥 Bitcoin Wallet Generator

An advanced Bitcoin wallet generator with balance checking capabilities, featuring a modern web interface and Telegram notifications.

## ⚠️ Important Disclaimer

This tool is for **educational purposes only**. Bitcoin wallet generation and balance checking should comply with all local laws and regulations. The probability of finding a wallet with balance is extremely low (approximately 1 in 2^160).

## ✨ Features

### Core Functionality
- **Bitcoin Wallet Generation**: Generates valid Bitcoin addresses using ECDSA cryptography
- **Balance Checking**: Automatically checks wallet balances using blockchain.info API
- **Real-time Monitoring**: Live console output with colored status messages
- **Statistics Tracking**: Comprehensive statistics including generation rate and runtime

### User Interface
- **Modern Web Interface**: Beautiful, responsive design with gradient backgrounds
- **Real-time Updates**: Live console and statistics updates every second
- **Mobile Responsive**: Works perfectly on desktop and mobile devices
- **Status Indicators**: Visual indicators for running/stopped status

### Notifications & Logging
- **Telegram Integration**: Instant notifications when wallets with balance are found
- **File Logging**: Automatic saving of found wallets to text file
- **Error Handling**: Robust error handling with retry mechanisms
- **Rate Limiting**: Built-in rate limiting to respect API limits

## 🚀 Quick Start

### Installation

1. **Clone or download the files**
   ```bash
   # Make sure you have Python 3.7+ installed
   python --version
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Telegram (Optional)**
   - Edit `btc_wallet_generator.py`
   - Replace `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` with your values
   - Or set them to empty strings to disable notifications

4. **Run the application**
   ```bash
   python btc_wallet_generator.py
   ```

5. **Open your browser**
   - Navigate to `http://localhost:5000`
   - Click "Start Generation" to begin

### Configuration Options

You can modify these settings in the code:

```python
DEFAULT_PORT = 5000              # Web interface port
WALLET_FILE = "btc_wallets.txt"  # File to save found wallets
REQUEST_DELAY = 1.0              # Delay between balance checks (seconds)
MAX_CONSOLE_LINES = 1000         # Maximum console lines to keep in memory
```

## 📊 Statistics Dashboard

The application provides comprehensive statistics:

- **Wallets Generated**: Total number of wallets created
- **Wallets with Balance**: Number of wallets found with BTC balance
- **Total BTC Found**: Sum of all BTC found in wallets
- **Runtime**: How long the generator has been running
- **Generation Rate**: Wallets generated per minute

## 🔧 Technical Details

### Bitcoin Address Generation Process

1. **Private Key Generation**: Uses ECDSA with SECP256k1 curve
2. **Public Key Derivation**: Derives public key from private key
3. **Address Creation**: 
   - SHA256 hash of public key
   - RIPEMD160 hash of the result
   - Add version byte (0x00 for mainnet)
   - Calculate checksum with double SHA256
   - Encode with Base58

### Balance Checking

- Uses blockchain.info API for balance queries
- Implements retry logic for failed requests
- Handles rate limiting (HTTP 429) gracefully
- Includes proper User-Agent headers

### Error Handling

- Comprehensive exception handling throughout
- Automatic retry on API failures
- Graceful degradation when services are unavailable
- Detailed error logging with timestamps

## 📱 Telegram Setup (Optional)

To enable Telegram notifications:

1. **Create a Telegram Bot**:
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Follow the instructions to get your token

2. **Get your Chat ID**:
   - Message @userinfobot to get your chat ID
   - Or message your bot and check the logs

3. **Update the configuration**:
   ```python
   TELEGRAM_TOKEN = "your_bot_token_here"
   TELEGRAM_CHAT_ID = "your_chat_id_here"
   ```

## 🛡️ Security Considerations

- **Private Keys**: Generated private keys are cryptographically secure
- **API Keys**: Keep your Telegram bot token secure
- **Rate Limiting**: Respects API rate limits to avoid IP bans
- **Error Handling**: Doesn't expose sensitive information in error messages

## 📁 File Structure

```
├── btc_wallet_generator.py    # Main application file
├── requirements.txt           # Python dependencies
├── README.md                 # This documentation
└── btc_wallets.txt           # Output file (created when wallets are found)
```

## 🎯 Performance Optimization

The application includes several optimizations:

- **Memory Management**: Limits console output to prevent memory growth
- **Threading**: Uses separate thread for wallet generation
- **Efficient Logging**: Batched console updates
- **Rate Control**: Configurable delays between requests

## 🔍 Understanding the Odds

**Important**: The probability of finding a wallet with balance is astronomically low:

- Total possible Bitcoin addresses: ~2^160 (≈ 1.46 × 10^48)
- Active addresses with balance: ~40 million
- Probability: ~1 in 3.65 × 10^40

This tool is primarily for educational purposes to understand Bitcoin address generation.

## 🛠️ Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Install all dependencies with `pip install -r requirements.txt`
2. **Port already in use**: Change `DEFAULT_PORT` in the code
3. **API errors**: Check internet connection and API status
4. **Telegram not working**: Verify token and chat ID

### Performance Tips

- **Reduce REQUEST_DELAY**: For faster generation (but respect rate limits)
- **Increase console limit**: Modify `MAX_CONSOLE_LINES` for more history
- **Monitor memory usage**: On long runs, restart periodically

## 📄 License

This project is for educational purposes. Use responsibly and in compliance with all applicable laws.

## 🤝 Contributing

This is an educational project. Feel free to study the code and understand how Bitcoin address generation works.

---

**Remember**: This tool is for learning about Bitcoin cryptography. The chances of finding a wallet with balance are virtually zero!