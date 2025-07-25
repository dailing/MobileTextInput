# Mobile Text Input Web Application

A simple web application that allows you to use your mobile devices (phone, iPad, etc.) as a text input interface for your computer. Text entered on your mobile device is automatically copied to your computer's clipboard.

## Features

- **Mobile-friendly interface** - Optimized for touch input
- **Real-time clipboard copying** - Text is automatically copied to your computer's clipboard
- **Cross-platform** - Works on Windows, macOS, and Linux
- **Network accessible** - Connect from any device on your local network
- **Text history** - Keep track of recent text entries
- **Auto-copy toggle** - Enable/disable automatic clipboard copying
- **Voice-to-text** - Upload audio files for automatic transcription using OpenAI Whisper

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
- **For voice-to-text**: FFmpeg and additional Python packages (see Voice Setup below)

## Voice-to-Text Setup (Optional)

The application now supports voice-to-text transcription using OpenAI Whisper. This is optional but provides powerful speech recognition capabilities.

### Install Voice Dependencies

1. **Install FFmpeg** (required for audio processing):
   - **Windows**: `choco install ffmpeg` (requires Chocolatey)
   - **macOS**: `brew install ffmpeg` (requires Homebrew)
   - **Linux**: `sudo apt install ffmpeg`

2. **Install Python packages** (in your virtual environment):
   ```bash
   pip install openai-whisper librosa soundfile pydub
   ```

3. **Test the installation**:
   ```bash
   python test_voice.py
   ```

### Voice Features

- **Audio file upload** - Supports MP3, WAV, M4A, MP4, WebM, OGG formats
- **Automatic language detection** - Works with 99+ languages
- **Fast processing** - Uses Whisper base model for good speed/accuracy balance
- **Local processing** - All transcription happens on your computer (no cloud)
- **Mobile-friendly** - Upload audio files directly from your mobile device

### Usage

1. **Upload audio file**: Use the "📁 Upload Audio File" button
2. **Wait for processing**: Transcription typically takes 1-5 seconds
3. **Review result**: Transcribed text appears in the text area
4. **Auto-copy**: Use existing copy/paste features to transfer text

### Model Information

- **Model**: Whisper base (~140MB)
- **Accuracy**: Good for most languages and use cases
- **Speed**: Fast processing on modern hardware
- **Languages**: Supports 99+ languages with auto-detection

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

### Voice-to-text not working
- Check if voice dependencies are installed: `python test_voice.py`
- Ensure FFmpeg is installed and in your system PATH
- Verify audio file format is supported (MP3, WAV, M4A, MP4, WebM, OGG)
- Check file size is under 50MB limit

## Security Notes

- The application only accepts connections from your local network
- No data is stored permanently - everything is kept in memory
- Text is transmitted over your local network (not encrypted)
- For sensitive data, consider using on a trusted network only

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running to stop it.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 