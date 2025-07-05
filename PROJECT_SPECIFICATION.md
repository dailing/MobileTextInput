# Mobile Text Input Web Application

## Project Overview
A web application that allows users to input text on mobile devices (phone, iPad) and automatically copy that text to the server's clipboard for easy pasting on the host computer.

## Core Functionality
- **Mobile Text Input**: Users can access a web interface from their mobile devices
- **Real-time Synchronization**: Text entered on mobile devices is immediately synchronized with the server
- **Clipboard Integration**: Text is automatically copied to the server's clipboard
- **Cross-device Compatibility**: Works on phones, tablets, and other devices with web browsers

## Technical Stack

### Backend
- **Framework**: NiceGUI (Python-based web framework)
- **Language**: Python 3.8+
- **Clipboard Library**: pyperclip (for cross-platform clipboard access)
- **Network**: Built-in NiceGUI server with network binding

### Frontend
- **UI Framework**: NiceGUI's built-in components
- **Responsive Design**: Mobile-first approach
- **Real-time Updates**: WebSocket-based synchronization (built into NiceGUI)

### Dependencies
- `nicegui` - Main web framework
- `pyperclip` - Clipboard functionality
- `uvicorn` - ASGI server (included with NiceGUI)

## Features

### Core Features
1. **Text Input Interface**
   - Large, mobile-friendly text area
   - Real-time text synchronization
   - Clear/reset functionality

2. **Clipboard Integration**
   - Automatic clipboard copying when text is entered
   - Manual copy button for explicit copying
   - Visual feedback when text is copied

3. **Network Accessibility**
   - Server accessible from local network
   - Mobile-optimized interface
   - Responsive design for various screen sizes

### Nice-to-Have Features
1. **Text History**
   - Recent text entries list
   - Ability to re-copy previous entries

2. **Security**
   - Basic authentication (optional)
   - Local network restriction

3. **UI Enhancements**
   - Dark/light theme toggle
   - Font size adjustment
   - Character count display

## Implementation Plan

### Phase 1: Basic Application
1. Set up project structure
2. Create basic NiceGUI application
3. Implement text input interface
4. Add clipboard functionality
5. Configure network access

### Phase 2: Mobile Optimization
1. Optimize UI for mobile devices
2. Add responsive design
3. Implement real-time synchronization
4. Test on various devices

### Phase 3: Enhancement
1. Add text history feature
2. Implement visual feedback
3. Add basic styling and themes
4. Performance optimization

## Network Configuration
- **Host**: 0.0.0.0 (accessible from network)
- **Port**: 8080 (configurable)
- **Access**: Local network only for security

## Security Considerations
- Application will be accessible only on local network
- No external internet access required
- Optional: Basic password protection
- Text data is not stored permanently (only in memory)

## File Structure
```
webinput/
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── README.md              # User instructions
└── static/                # Static assets (if needed)
    └── styles.css         # Custom styles
```

## Usage Workflow
1. Start the application on the server computer
2. Connect mobile device to the same network
3. Open the application URL in mobile browser
4. Type text in the input field
5. Text is automatically copied to server clipboard
6. Paste text anywhere on the server computer

## Testing Requirements
- Test on iOS Safari
- Test on Android Chrome
- Test on iPad
- Verify clipboard functionality on different operating systems
- Test network connectivity from various devices 