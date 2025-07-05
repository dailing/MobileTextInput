# Mobile Text Input Web Application

A simple web application that allows you to use your mobile devices (phone, iPad, etc.) as a text input interface for your computer. Text entered on your mobile device is automatically copied to your computer's clipboard.

## Features

- **Mobile-friendly interface** - Optimized for touch input
- **Real-time clipboard copying** - Text is automatically copied to your computer's clipboard
- **Cross-platform** - Works on Windows, macOS, and Linux
- **Network accessible** - Connect from any device on your local network
- **Text history** - Keep track of recent text entries
- **Auto-copy toggle** - Enable/disable automatic clipboard copying

## Quick Start

1. **Run the application:**
   ```bash
   python setup_and_run.py
   ```

2. **Access from your mobile device:**
   - Connect your mobile device to the same Wi-Fi network as your computer
   - Open your mobile browser and visit: `http://YOUR_COMPUTER_IP:8080`
   - Start typing!

## What the setup script does

The `setup_and_run.py` script automatically:
- Checks Python version compatibility (3.8+)
- Creates a virtual environment if needed
- Installs required dependencies
- Starts the web server

## Manual Setup (if needed)

If you prefer to set up manually:

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment:**
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```

## Usage

1. **Start the server** on your computer using the setup script
2. **Find your computer's IP address** (displayed when the server starts)
3. **Connect your mobile device** to the same network
4. **Open your mobile browser** and visit `http://YOUR_COMPUTER_IP:8080`
5. **Type text** in the text area
6. **Text is automatically copied** to your computer's clipboard (if auto-copy is enabled)
7. **Paste anywhere** on your computer using Ctrl+V (or Cmd+V on Mac)

## Features

### Text Input
- Large, mobile-friendly text area
- Character count display
- Auto-copy as you type (can be toggled)
- Manual copy button

### Text History
- View recent text entries
- Copy previous entries with one tap
- Timestamp for each entry

### Mobile Optimization
- Responsive design for all screen sizes
- Touch-friendly interface
- Prevents zoom on input focus
- Full-screen friendly

## Network Access

The application runs on your local network only for security. To access from mobile devices:

1. Ensure your mobile device is connected to the same Wi-Fi network
2. Use the IP address displayed when starting the server
3. Default port is 8080

## Requirements

- Python 3.8 or higher
- Network connection (Wi-Fi)
- Modern web browser on mobile device

## Troubleshooting

### Can't connect from mobile device
- Ensure both devices are on the same network
- Check if firewall is blocking port 8080
- Try accessing `http://localhost:8080` from your computer first

### Clipboard not working
- On some systems, you may need to grant clipboard permissions
- The application uses `pyperclip` which supports most platforms

### Permission errors
- Make sure you have write permissions in the directory
- Try running as administrator (Windows) or with sudo (Linux/Mac) if needed

## Security Notes

- The application only accepts connections from your local network
- No data is stored permanently - everything is kept in memory
- Text is transmitted over your local network (not encrypted)
- For sensitive data, consider using on a trusted network only

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running to stop it. 