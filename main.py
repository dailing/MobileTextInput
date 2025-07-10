#!/usr/bin/env python3
"""
Mobile Text Input Web Application
A web application that allows text input from mobile devices with automatic clipboard copying and keyboard simulation
"""

import socket
import pyperclip
from nicegui import ui, app
from datetime import datetime
import time
import logging
import sys
import platform
import tempfile
import os
import asyncio
from pathlib import Path
from fastapi import Request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mobile_text_input.log')
    ]
)
logger = logging.getLogger(__name__)

# Import keyboard simulation library
try:
    from pynput.keyboard import Key, Controller
    keyboard_controller = Controller()
    KEYBOARD_AVAILABLE = True
    PYNPUT_AVAILABLE = True
    logger.info("✅ pynput keyboard simulation library loaded successfully")
except ImportError:
    KEYBOARD_AVAILABLE = False
    PYNPUT_AVAILABLE = False
    keyboard_controller = None
    logger.warning("⚠️ pynput not available - keyboard simulation disabled")

# Import voice-to-text libraries
try:
    import whisper
    WHISPER_AVAILABLE = True
    logger.info("✅ OpenAI Whisper loaded successfully")
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("⚠️ OpenAI Whisper not available - voice-to-text disabled")

# OS detection and platform-specific setup
CURRENT_OS = platform.system()
logger.info(f"🖥️ Detected operating system: {CURRENT_OS}")

# Windows-specific fallback using ctypes
if CURRENT_OS == "Windows":
    try:
        import ctypes
        user32 = ctypes.windll.user32
        WINDOWS_FALLBACK = True
        logger.info("✅ Windows native keyboard simulation available")
    except ImportError:
        WINDOWS_FALLBACK = False
        user32 = None
        logger.warning("⚠️ Windows native keyboard simulation not available")
else:
    WINDOWS_FALLBACK = False
    user32 = None

# macOS detection
IS_MACOS = CURRENT_OS == "Darwin"
if IS_MACOS:
    logger.info("🍎 macOS detected - will use Cmd+V for paste operations")
else:
    logger.info("🪟 Non-macOS detected - will use Ctrl+V for paste operations")


class VoiceProcessor:
    """Handle voice-to-text processing using OpenAI Whisper"""
    
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.supported_formats = {'.mp3', '.wav', '.m4a', '.mp4', '.mpeg', '.mpga', '.webm', '.ogg'}
        
        if WHISPER_AVAILABLE:
            self.load_model()
        else:
            logger.error("❌ Whisper not available - voice processing disabled")
    
    def load_model(self):
        """Load the Whisper model (medium model for better accuracy)"""
        try:
            logger.info("🔄 Loading Whisper medium model...")
            self.model = whisper.load_model("medium")
            self.model_loaded = True
            logger.info("✅ Whisper medium model loaded successfully")
            logger.info("📝 Model supports: transcription and translation")
            logger.info("🌍 Languages: Supports 99 languages")
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            self.model_loaded = False
    
    def is_supported_format(self, filename):
        """Check if the audio file format is supported"""
        return Path(filename).suffix.lower() in self.supported_formats
    
    def transcribe_audio(self, audio_file_path, language=None):
        """
        Transcribe audio file to text
        
        Args:
            audio_file_path (str): Path to the audio file
            language (str, optional): Language code (e.g., 'en', 'es', 'fr')
        
        Returns:
            dict: Transcription result with text and metadata
        """
        if not self.model_loaded:
            return {"success": False, "error": "Whisper model not loaded"}
        
        if not os.path.exists(audio_file_path):
            return {"success": False, "error": "Audio file not found"}
        
        if not self.is_supported_format(audio_file_path):
            return {"success": False, "error": "Unsupported audio format"}
        
        try:
            logger.info(f"🎤 Starting transcription: {Path(audio_file_path).name}")
            start_time = time.time()
            
            # Transcribe the audio
            options = {}
            if language:
                options['language'] = language
            
            result = self.model.transcribe(audio_file_path, **options)
            
            processing_time = time.time() - start_time
            text = result["text"].strip()
            
            logger.info(f"✅ Transcription completed in {processing_time:.2f} seconds")
            logger.info(f"📝 Transcribed text: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            logger.info(f"🌍 Detected language: {result.get('language', 'unknown')}")
            
            return {
                "success": True,
                "text": text,
                "language": result.get("language"),
                "processing_time": processing_time,
                "duration": result.get("duration", 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_model_info(self):
        """Get information about the loaded model"""
        if not self.model_loaded:
            return "❌ No model loaded"
        
        return {
            "model": "medium",
            "size": "~769MB",
            "accuracy": "Better accuracy for most languages",
            "speed": "Moderate processing speed",
            "languages": "99 languages supported"
        }


class TextInputApp:
    def __init__(self):
        self.current_text = ""
        self.text_history = []
        self.max_history = 10
        self.storage_key = 'shared_text'
        self.history_key = 'shared_history'
        
        # Initialize voice processor
        self.voice_processor = VoiceProcessor() if WHISPER_AVAILABLE else None
        self.voice_enabled = WHISPER_AVAILABLE and self.voice_processor.model_loaded
        
        logger.info("📱 TextInputApp initialized")
        if self.voice_enabled:
            logger.info("🎤 Voice-to-text functionality enabled")
        else:
            logger.warning("⚠️ Voice-to-text functionality disabled")
    
    def get_local_ip(self):
        """Get the local IP address of the server"""
        try:
            # Create a socket to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            logger.info(f"🌐 Local IP address detected: {local_ip}")
            return local_ip
        except Exception as e:
            logger.error(f"❌ Failed to get local IP: {e}")
            return "localhost"
    
    def copy_to_clipboard(self, text):
        """Copy text to system clipboard"""
        try:
            pyperclip.copy(text)
            logger.info(f"📋 Text copied to clipboard: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to copy to clipboard: {e}")
            return False
    
    def simulate_paste(self):
        """Simulate paste key combination (Cmd+V on macOS, Ctrl+V on Windows/Linux)"""
        if not KEYBOARD_AVAILABLE:
            logger.error("❌ Keyboard simulation not available - cannot simulate paste")
            self.show_status("Keyboard simulation not available", "error")
            return False
        
        try:
            if IS_MACOS:
                # macOS: Use Cmd+V
                logger.info("🍎 Simulating Cmd+V paste on macOS")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.cmd):
                        keyboard_controller.press('v')
                        keyboard_controller.release('v')
                    logger.info("✅ Cmd+V paste operation completed successfully")
                    return True
                else:
                    logger.error("❌ pynput not available for macOS paste simulation")
                    return False
            
            elif CURRENT_OS == "Windows":
                # Windows: Try native method first (more reliable)
                logger.info("🪟 Simulating Ctrl+V paste on Windows")
                if WINDOWS_FALLBACK:
                    logger.info("🔧 Using Windows native keyboard simulation")
                    # Windows VK codes: Ctrl = 0x11, V = 0x56
                    user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
                    user32.keybd_event(0x56, 0, 0, 0)  # V down
                    user32.keybd_event(0x56, 0, 2, 0)  # V up
                    user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
                    logger.info("✅ Windows native Ctrl+V paste operation completed successfully")
                    return True
                
                # Fallback to pynput
                elif PYNPUT_AVAILABLE:
                    logger.info("🔧 Using pynput for Windows paste simulation")
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press('v')
                        keyboard_controller.release('v')
                    logger.info("✅ pynput Ctrl+V paste operation completed successfully")
                    return True
            
            else:
                # Linux and other systems: Use Ctrl+V
                logger.info(f"🐧 Simulating Ctrl+V paste on {CURRENT_OS}")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press('v')
                        keyboard_controller.release('v')
                    logger.info("✅ Ctrl+V paste operation completed successfully")
                    return True
                else:
                    logger.error("❌ pynput not available for paste simulation")
                    return False
            
        except Exception as e:
            logger.error(f"❌ Failed to simulate paste: {e}")
            return False
    
    def simulate_enter(self):
        """Simulate Enter key press"""
        if not KEYBOARD_AVAILABLE:
            logger.error("❌ Keyboard simulation not available - cannot simulate Enter")
            return False
        
        try:
            logger.info("⏎ Simulating Enter key press")
            
            if CURRENT_OS == "Windows":
                # Try Windows native method first
                if WINDOWS_FALLBACK:
                    logger.info("🔧 Using Windows native Enter key simulation")
                    # Windows VK code: Enter = 0x0D
                    user32.keybd_event(0x0D, 0, 0, 0)  # Enter down
                    user32.keybd_event(0x0D, 0, 2, 0)  # Enter up
                    logger.info("✅ Windows native Enter key operation completed successfully")
                    return True
            
            # Fallback to pynput for all systems
            if PYNPUT_AVAILABLE:
                logger.info("🔧 Using pynput for Enter key simulation")
                keyboard_controller.press(Key.enter)
                keyboard_controller.release(Key.enter)
                logger.info("✅ pynput Enter key operation completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to simulate Enter key: {e}")
            return False
    
    def auto_paste_text(self, text):
        """Auto-paste text by copying to clipboard then simulating paste"""
        if text.strip():
            logger.info(f"🚀 Starting auto-paste operation for text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # First copy to clipboard
            if self.copy_to_clipboard(text):
                # Small delay to ensure clipboard is updated
                time.sleep(0.1)
                
                # Then simulate paste
                if self.simulate_paste():
                    # Add to history
                    self.add_to_history(text)
                    self.update_history_display()
                    
                    # Press Enter if option is enabled
                    if hasattr(self, 'press_enter_toggle') and self.press_enter_toggle.value:
                        logger.info("⏎ Auto-Enter enabled - pressing Enter after paste")
                        time.sleep(0.1)  # Small delay between paste and enter
                        self.simulate_enter()
                    
                    logger.info("✅ Auto-paste operation completed successfully")
                    return True
                else:
                    logger.error("❌ Auto-paste failed at paste simulation step")
            else:
                logger.error("❌ Auto-paste failed at clipboard copy step")
        
        logger.warning("⚠️ Auto-paste operation failed or no text provided")
        return False
    
    def add_to_history(self, text):
        """Add text to history with timestamp"""
        if text.strip():
            # Check if this text is different from the most recent history entry
            if not self.text_history or text != self.text_history[0]['text']:
                timestamp = datetime.now().strftime("%H:%M:%S")
                logger.info(f"📝 Adding text to history: '{text[:30]}{'...' if len(text) > 30 else ''}' at {timestamp}")
                self.text_history.insert(0, {
                    'text': text,
                    'timestamp': timestamp
                })
                # Keep only recent entries
                if len(self.text_history) > self.max_history:
                    self.text_history = self.text_history[:self.max_history]
                
                # Sync to storage for cross-device synchronization
                self.sync_to_storage()
            else:
                logger.debug("📝 Text already exists in history, skipping duplicate")
    
    def sync_to_storage(self):
        """Sync current text and history to shared storage"""
        try:
            app.storage.general[self.storage_key] = self.current_text
            app.storage.general[self.history_key] = self.text_history
            logger.debug("💾 Successfully synced data to storage")
        except Exception as e:
            logger.error(f"❌ Failed to sync to storage: {e}")
    
    def sync_from_storage(self):
        """Sync text and history from shared storage"""
        try:
            # Load text from storage
            stored_text = app.storage.general.get(self.storage_key, "")
            if stored_text != self.current_text:
                logger.debug(f"🔄 Syncing text from storage: '{stored_text[:30]}{'...' if len(stored_text) > 30 else ''}'")
                self.current_text = stored_text
                if hasattr(self, 'text_area'):
                    self.text_area.set_value(stored_text)
                    self.char_count.set_text(f"{len(stored_text)} characters")
            
            # Load history from storage
            stored_history = app.storage.general.get(self.history_key, [])
            if stored_history != self.text_history:
                logger.debug(f"🔄 Syncing history from storage: {len(stored_history)} entries")
                self.text_history = stored_history
                if hasattr(self, 'history_container'):
                    self.update_history_display()
        except Exception as e:
            logger.error(f"❌ Failed to sync from storage: {e}")
    
    def start_storage_sync(self):
        """Start periodic sync with storage"""
        logger.info("🔄 Starting periodic storage synchronization")
        
        def sync_timer():
            try:
                self.sync_from_storage()
            except Exception as e:
                logger.error(f"❌ Storage sync error: {e}")
        
        # Use NiceGUI timer for periodic sync
        ui.timer(1.0, sync_timer)  # Check every second
    
    def create_ui(self):
        """Create the main UI"""
        # Set page title and meta tags for mobile
        ui.page_title("Mobile Text Input")
        
        # Add mobile-friendly viewport meta tag
        ui.add_head_html('''
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <meta name="apple-mobile-web-app-capable" content="yes">
            <meta name="apple-mobile-web-app-status-bar-style" content="default">
            <style>
                .text-input-container {
                    width: 100%;
                    max-width: 600px;
                    margin: 0 auto;
                }
                .mobile-textarea {
                    width: 100% !important;
                    min-height: 200px !important;
                    font-size: 16px !important;
                    padding: 15px !important;
                    border-radius: 8px !important;
                    border: 2px solid #ddd !important;
                    resize: vertical !important;
                }
                .mobile-textarea:focus {
                    border-color: #4CAF50 !important;
                    outline: none !important;
                }
                .action-button {
                    width: 100% !important;
                    padding: 15px !important;
                    font-size: 16px !important;
                    margin: 10px 0 !important;
                    border-radius: 8px !important;
                }
                .copy-button {
                    background-color: #4CAF50 !important;
                    color: white !important;
                }
                .clear-button {
                    background-color: #f44336 !important;
                    color: white !important;
                }
                .history-item {
                    background-color: #f5f5f5 !important;
                    padding: 10px !important;
                    margin: 5px 0 !important;
                    border-radius: 5px !important;
                    border-left: 4px solid #4CAF50 !important;
                }
                .header {
                    text-align: center !important;
                    padding: 20px 0 !important;
                    background-color: #f8f9fa !important;
                    margin-bottom: 20px !important;
                }
                .footer {
                    text-align: center !important;
                    padding: 20px 0 !important;
                    color: #666 !important;
                    font-size: 14px !important;
                }
                .voice-button {
                    background-color: #2196F3 !important;
                    color: white !important;
                }
                .upload-button {
                    background-color: #FF9800 !important;
                    color: white !important;
                    border: 2px dashed #FF9800 !important;
                }
                .voice-info {
                    background-color: #E8F5E8 !important;
                    padding: 10px !important;
                    border-radius: 5px !important;
                    margin: 10px 0 !important;
                }
            </style>
        ''')
        
        # Header
        ui.label(f"Server: {self.get_local_ip()}:8080")
        
        # Main content container
        with ui.column().classes('text-input-container'):
            # Text input area
            ui.label("Enter your text:").classes('text-h6')
            self.text_area = ui.textarea(
                placeholder="Type your text here...",
                value=""
            ).classes('mobile-textarea')
            
            # Character count
            self.char_count = ui.label("0 characters").classes('text-caption')
            
            # Action buttons
            with ui.row().classes('w-full'):
                self.copy_button = ui.button(
                    "Copy to Clipboard", 
                    on_click=self.copy_current_text
                ).classes('action-button copy-button')
                
                self.enter_button = ui.button(
                    "Press Enter", 
                    on_click=self.press_enter_key
                ).classes('action-button copy-button')
                
                self.clear_button = ui.button(
                    "Clear Text", 
                    on_click=self.clear_text
                ).classes('action-button clear-button')
            
            # Voice input section
            if self.voice_enabled:
                ui.separator()
                ui.label("Voice to Text:").classes('text-h6')
                
                with ui.row().classes('w-full'):
                    # Push-to-talk button
                    self.voice_button = ui.button(
                        "🎤 Hold to Record", 
                        on_click=None
                    ).classes('action-button voice-button')
                
                # Voice status and info
                voice_info = self.voice_processor.get_model_info()
                ui.label(f"✅ Whisper {voice_info['model']} model loaded ({voice_info['size']})").classes('text-caption text-green')
                ui.label("🎤 Press and hold button to record • Release to transcribe").classes('text-caption')
                ui.label("🌍 Auto-detects language • Works on mobile devices").classes('text-caption')
                
                # Add JavaScript for push-to-talk functionality
                ui.add_head_html('''
                    <script>
                    let mediaRecorder;
                    let audioChunks = [];
                    let isRecording = false;
                    let pollInterval;
                    
                    // Function to show status messages
                    function showStatus(message, type = 'info') {
                        // Create a temporary notification element
                        const notification = document.createElement('div');
                        notification.textContent = message;
                        notification.style.cssText = `
                            position: fixed;
                            top: 20px;
                            right: 20px;
                            background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
                            color: white;
                            padding: 12px 20px;
                            border-radius: 4px;
                            z-index: 9999;
                            font-size: 14px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                        `;
                        document.body.appendChild(notification);
                        
                        // Remove after 3 seconds
                        setTimeout(() => {
                            if (notification.parentNode) {
                                notification.parentNode.removeChild(notification);
                            }
                        }, 3000);
                    }
                    
                    // Function to update text area
                    function updateTextArea(newText) {
                        const textarea = document.querySelector('.mobile-textarea textarea');
                        if (textarea) {
                            const currentText = textarea.value || '';
                            const updatedText = currentText ? currentText + '\\n' + newText : newText;
                            textarea.value = updatedText;
                            
                            // Trigger input event to sync with backend
                            const event = new Event('input', { bubbles: true });
                            textarea.dispatchEvent(event);
                            
                            // Update character count
                            const charCount = document.querySelector('.text-caption');
                            if (charCount && charCount.textContent.includes('characters')) {
                                charCount.textContent = `${updatedText.length} characters`;
                            }
                        }
                    }
                    
                    // Function to poll for voice results
                    function pollForResults() {
                        fetch('/check-voice-result')
                            .then(response => response.json())
                            .then(data => {
                                if (data.success && data.result) {
                                    const result = data.result;
                                    updateTextArea(result.text);
                                    showStatus(
                                        `Transcribed in ${result.processing_time.toFixed(1)}s (Language: ${result.language})`,
                                        'success'
                                    );
                                    
                                    // Stop polling
                                    if (pollInterval) {
                                        clearInterval(pollInterval);
                                        pollInterval = null;
                                    }
                                }
                            })
                            .catch(error => {
                                console.error('Error polling for results:', error);
                            });
                    }
                    
                    async function startRecording() {
                        if (isRecording) return;
                        
                        try {
                            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                            mediaRecorder = new MediaRecorder(stream);
                            audioChunks = [];
                            
                            mediaRecorder.ondataavailable = event => {
                                audioChunks.push(event.data);
                            };
                            
                            mediaRecorder.onstop = async () => {
                                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                                const audioData = await audioBlob.arrayBuffer();
                                
                                // Show processing status
                                showStatus('Processing recorded audio...', 'info');
                                
                                // Send audio data to backend
                                fetch('/process-audio', {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/octet-stream',
                                    },
                                    body: audioData
                                })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.success) {
                                        // Start polling for results
                                        pollInterval = setInterval(pollForResults, 100);
                                        // Also check immediately
                                        pollForResults();
                                    } else {
                                        showStatus(`Transcription failed: ${data.error}`, 'error');
                                    }
                                })
                                .catch(error => {
                                    console.error('Error processing audio:', error);
                                    showStatus('Error processing audio', 'error');
                                });
                                
                                // Stop all tracks
                                stream.getTracks().forEach(track => track.stop());
                                isRecording = false;
                            };
                            
                            mediaRecorder.start();
                            isRecording = true;
                            
                            // Update button text
                            const button = document.querySelector('.voice-button');
                            if (button) {
                                button.textContent = '🔴 Recording... (Release to stop)';
                                button.style.backgroundColor = '#f44336';
                            }
                            
                        } catch (error) {
                            console.error('Error accessing microphone:', error);
                            showStatus('Error accessing microphone. Please check permissions.', 'error');
                        }
                    }
                    
                    function stopRecording() {
                        if (mediaRecorder && isRecording) {
                            mediaRecorder.stop();
                            
                            // Update button text
                            const button = document.querySelector('.voice-button');
                            if (button) {
                                button.textContent = '🎤 Hold to Record';
                                button.style.backgroundColor = '#2196F3';
                            }
                        }
                    }
                    
                    // Add event listeners when page loads
                    document.addEventListener('DOMContentLoaded', function() {
                        setTimeout(() => {
                            const button = document.querySelector('.voice-button');
                            if (button) {
                                // Desktop events
                                button.addEventListener('mousedown', startRecording);
                                button.addEventListener('mouseup', stopRecording);
                                button.addEventListener('mouseleave', stopRecording);
                                
                                // Mobile events
                                button.addEventListener('touchstart', (e) => {
                                    e.preventDefault();
                                    startRecording();
                                });
                                button.addEventListener('touchend', (e) => {
                                    e.preventDefault();
                                    stopRecording();
                                });
                                button.addEventListener('touchcancel', (e) => {
                                    e.preventDefault();
                                    stopRecording();
                                });
                            }
                        }, 100);
                    });
                    </script>
                ''')
            else:
                # Show voice unavailable message
                ui.separator()
                ui.label("Voice to Text:").classes('text-h6')
                ui.label("❌ Voice-to-text not available").classes('text-caption text-red')
                if not WHISPER_AVAILABLE:
                    ui.label("📦 Install: pip install openai-whisper").classes('text-caption text-red')
            
            # Auto-paste toggle
            with ui.row().classes('w-full justify-center'):
                paste_key = "Cmd+V" if IS_MACOS else "Ctrl+V"
                self.auto_paste_toggle = ui.checkbox(
                    f"Auto-paste when copying to clipboard ({paste_key})", 
                    value=False
                ).classes('text-center')
            
            # Press Enter toggle
            with ui.row().classes('w-full justify-center'):
                self.press_enter_toggle = ui.checkbox(
                    "Press Enter after pasting", 
                    value=False
                ).classes('text-center')
            
            # Keyboard simulation status
            keyboard_status = []
            if WINDOWS_FALLBACK:
                keyboard_status.append("✅ Windows native keyboard simulation")
            elif PYNPUT_AVAILABLE:
                keyboard_status.append("✅ pynput keyboard simulation") 
            else:
                keyboard_status.append("⚠️ Keyboard simulation not available")
            
            if not KEYBOARD_AVAILABLE:
                keyboard_status.append("📦 Install pynput: pip install pynput")
            
            for status in keyboard_status:
                ui.label(status).classes('text-caption')
            
            # Storage synchronization status
            ui.separator()
            ui.label("✅ Cross-device synchronization enabled").classes('text-caption text-blue')
            ui.label("Text syncs across all devices and browser tabs").classes('text-caption text-blue')
            
            # History section
            ui.separator()
            ui.label("Recent Text History:").classes('text-h6')
            self.history_container = ui.column().classes('w-full')
            
        # Footer
        with ui.column().classes('footer'):
            paste_key = "Cmd+V" if IS_MACOS else "Ctrl+V"
            ui.label("Tap text area to start typing • Text syncs across all devices and tabs")
            ui.label(f"Copy to clipboard • Auto-paste with {paste_key} on server")
        
        # Set up event handlers
        self.text_area.on('input', self.on_text_change)
        
        # Initialize from storage and start sync
        self.sync_from_storage()
        self.start_storage_sync()
        self.update_history_display()
    
    def on_text_change(self, event):
        """Handle text change events"""
        text = event.value if event.value else ""
        self.current_text = text  # Keep internal state synchronized
        
        # Update character count
        self.char_count.set_text(f"{len(text)} characters")
        
        # Sync to storage for cross-device synchronization
        self.sync_to_storage()
    
    def copy_current_text(self):
        """Copy current text to clipboard with user feedback"""
        # Get text directly from the text area widget to ensure we have the current value
        text = self.text_area.value.strip() if self.text_area.value else ""
        
        if not text:
            logger.warning("⚠️ Copy operation attempted with no text")
            self.show_status("No text to copy", "error")
            return
        
        logger.info(f"📋 Starting copy operation: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        if self.copy_to_clipboard(text):
            self.add_to_history(text)
            self.update_history_display()
            
            # Clear text area after successful copy
            logger.info("🗑️ Clearing text area after successful copy")
            self.text_area.set_value("")
            self.current_text = ""
            self.char_count.set_text("0 characters")
            self.sync_to_storage()
            
            # Auto-paste if enabled
            if self.auto_paste_toggle.value:
                logger.info("🔄 Auto-paste enabled, initiating paste sequence")
                # Small delay to ensure clipboard is updated
                time.sleep(0.1)
                
                # Simulate paste
                if self.simulate_paste():
                    # Press Enter if option is enabled
                    if hasattr(self, 'press_enter_toggle') and self.press_enter_toggle.value:
                        logger.info("⏎ Auto-Enter enabled, pressing Enter after paste")
                        time.sleep(0.1)  # Small delay between paste and enter
                        self.simulate_enter()
                    
                    logger.info("✅ Copy and auto-paste operation completed successfully")
                    self.show_status("Text copied and pasted!", "success")
                else:
                    logger.error("❌ Copy succeeded but auto-paste failed")
                    self.show_status("Text copied, but paste failed", "error")
            else:
                logger.info("✅ Copy operation completed successfully")
                self.show_status("Text copied to clipboard!", "success")
        else:
            logger.error("❌ Copy operation failed")
            self.show_status("Failed to copy text", "error")
    
    def press_enter_key(self):
        """Press Enter key on the server"""
        logger.info("⏎ Enter key button pressed")
        
        if self.simulate_enter():
            logger.info("✅ Enter key simulation completed successfully")
            self.show_status("Enter key pressed!", "success")
        else:
            logger.error("❌ Enter key simulation failed")
            self.show_status("Failed to press Enter key", "error")
    
    def copy_to_clipboard_silent(self, text):
        """Copy text to clipboard without showing status"""
        if text and self.copy_to_clipboard(text):
            self.add_to_history(text)
            self.update_history_display()
    
    def paste_from_history(self, text):
        """Paste text from history using Ctrl+V simulation"""
        if self.auto_paste_text(text):
            self.show_status("Text pasted from history!", "success")
        else:
            self.show_status("Failed to paste text", "error")
    
    def clear_text(self):
        """Clear the text area"""
        logger.info("🗑️ Clearing text area and syncing across devices")
        self.text_area.set_value("")
        self.current_text = ""
        self.char_count.set_text("0 characters")
        
        # Clear storage for cross-device synchronization
        self.sync_to_storage()
        
        logger.info("✅ Text cleared successfully on all devices")
        self.show_status("Text cleared on all devices", "success")
    
    def show_status(self, message, status_type="success"):
        """Show status notification to user"""
        if status_type == "success":
            ui.notify(message, type='positive', position='top')
            logger.info(f"✅ Status notification (success): {message}")
        elif status_type == "error":
            ui.notify(message, type='negative', position='top')
            logger.error(f"❌ Status notification (error): {message}")
        else:
            ui.notify(message, type='info', position='top')
            logger.info(f"ℹ️ Status notification (info): {message}")
    
    def copy_from_history(self, text):
        """Copy text from history"""
        if self.copy_to_clipboard(text):
            self.show_status("Text copied from history!", "success")
        else:
            self.show_status("Failed to copy text", "error")
    
    def update_history_display(self):
        """Update the history display"""
        self.history_container.clear()
        
        if not self.text_history:
            with self.history_container:
                ui.label("No recent text entries").classes('text-caption text-center')
            return
        
        with self.history_container:
            for i, entry in enumerate(self.text_history):
                with ui.card().classes('history-item w-full'):
                    with ui.row().classes('w-full justify-between items-center'):
                        with ui.column().classes('flex-grow'):
                            # Show preview of text (first 50 chars)
                            preview = entry['text'][:50]
                            if len(entry['text']) > 50:
                                preview += "..."
                            ui.label(preview).classes('text-body2')
                            ui.label(f"Added: {entry['timestamp']}").classes('text-caption')
                        
                        with ui.row():
                            ui.button(
                                "Copy",
                                on_click=lambda e, text=entry['text']: self.copy_from_history(text)
                            ).classes('copy-button')
                            
                            ui.button(
                                "Paste",
                                on_click=lambda e, text=entry['text']: self.paste_from_history(text)
                            ).classes('copy-button')

    async def handle_audio_upload(self, event):
        """Handle audio file upload and transcription"""
        if not self.voice_enabled:
            self.show_status("Voice-to-text is not available", "error")
            return
        
        if not event.content:
            self.show_status("No audio file selected", "error")
            return
        
        try:
            # Show processing status
            self.show_status("Processing audio file...", "info")
            logger.info(f"🎤 Processing uploaded audio file: {event.name}")
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(event.name).suffix) as temp_file:
                # Fix: Read content from SpooledTemporaryFile properly
                if hasattr(event.content, 'read'):
                    # If it's a file-like object, read its content
                    event.content.seek(0)  # Ensure we're at the beginning
                    audio_data = event.content.read()
                else:
                    # If it's already bytes
                    audio_data = event.content
                
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Transcribe the audio
            result = await asyncio.to_thread(
                self.voice_processor.transcribe_audio, 
                temp_file_path
            )
            
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
            
            if result["success"]:
                transcribed_text = result["text"]
                processing_time = result.get("processing_time", 0)
                language = result.get("language", "unknown")
                
                if transcribed_text:
                    # Add transcribed text to the text area
                    current_text = self.text_area.value or ""
                    if current_text:
                        new_text = current_text + "\n" + transcribed_text
                    else:
                        new_text = transcribed_text
                    
                    self.text_area.set_value(new_text)
                    self.current_text = new_text
                    self.char_count.set_text(f"{len(new_text)} characters")
                    self.sync_to_storage()
                    
                    # Add to history
                    self.add_to_history(transcribed_text)
                    self.update_history_display()
                    
                    # Show success status
                    self.show_status(
                        f"Transcribed in {processing_time:.1f}s (Language: {language})", 
                        "success"
                    )
                    logger.info(f"✅ Audio transcription successful: {len(transcribed_text)} characters")
                else:
                    self.show_status("No speech detected in audio", "error")
                    logger.warning("⚠️ No speech detected in uploaded audio")
            else:
                error_msg = result.get("error", "Unknown error")
                self.show_status(f"Transcription failed: {error_msg}", "error")
                logger.error(f"❌ Audio transcription failed: {error_msg}")
                
        except Exception as e:
            self.show_status(f"Error processing audio: {str(e)}", "error")
            logger.error(f"❌ Audio processing error: {e}")
    
    async def process_audio_data(self, audio_data):
        """Process raw audio data without UI updates (for API calls)"""
        if not self.voice_enabled:
            return {"success": False, "error": "Voice-to-text is not available"}
        
        try:
            logger.info("🎤 Processing push-to-talk audio recording")
            
            # Save audio data temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Transcribe the audio
            result = await asyncio.to_thread(
                self.voice_processor.transcribe_audio, 
                temp_file_path
            )
            
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
            
            if result["success"]:
                transcribed_text = result["text"]
                processing_time = result.get("processing_time", 0)
                language = result.get("language", "unknown")
                
                if transcribed_text:
                    # Store result in app storage for UI to pick up
                    app.storage.user['voice_result'] = {
                        'text': transcribed_text,
                        'processing_time': processing_time,
                        'language': language,
                        'timestamp': time.time()
                    }
                    
                    logger.info(f"✅ Push-to-talk transcription successful: {len(transcribed_text)} characters")
                    return {
                        "success": True, 
                        "text": transcribed_text,
                        "processing_time": processing_time,
                        "language": language
                    }
                else:
                    logger.warning("⚠️ No speech detected in push-to-talk recording")
                    return {"success": False, "error": "No speech detected in recording"}
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"❌ Push-to-talk transcription failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"❌ Push-to-talk audio processing error: {e}")
            return {"success": False, "error": str(e)}

    async def handle_audio_data(self, audio_data):
        """Handle raw audio data from push-to-talk recording (with UI updates)"""
        if not self.voice_enabled:
            self.show_status("Voice-to-text is not available", "error")
            return
        
        try:
            # Show processing status
            self.show_status("Processing recorded audio...", "info")
            
            # Process audio data
            result = await self.process_audio_data(audio_data)
            
            if result["success"]:
                transcribed_text = result["text"]
                processing_time = result.get("processing_time", 0)
                language = result.get("language", "unknown")
                
                # Add transcribed text to the text area
                current_text = self.text_area.value or ""
                if current_text:
                    new_text = current_text + "\n" + transcribed_text
                else:
                    new_text = transcribed_text
                
                self.text_area.set_value(new_text)
                self.current_text = new_text
                self.char_count.set_text(f"{len(new_text)} characters")
                self.sync_to_storage()
                
                # Add to history
                self.add_to_history(transcribed_text)
                self.update_history_display()
                
                # Show success status
                self.show_status(
                    f"Transcribed in {processing_time:.1f}s (Language: {language})", 
                    "success"
                )
            else:
                error_msg = result.get("error", "Unknown error")
                self.show_status(f"Transcription failed: {error_msg}", "error")
                
        except Exception as e:
            self.show_status(f"Error processing recorded audio: {str(e)}", "error")
            logger.error(f"❌ Push-to-talk audio processing error: {e}")
    
    def start_voice_recording(self):
        """Start voice recording (placeholder for future implementation)"""
        if not self.voice_enabled:
            self.show_status("Voice-to-text is not available", "error")
            return
        
        # This would be implemented with WebRTC MediaRecorder API in the future
        self.show_status("Voice recording not yet implemented. Please use file upload.", "info")
        logger.info("🎤 Voice recording requested (not yet implemented)")


def main():
    """Main function to run the application"""
    # Create the app instance
    text_app = TextInputApp()
    
    # Add API endpoint for processing recorded audio
    @app.post("/process-audio")
    async def process_audio(request: Request):
        """Handle recorded audio data from push-to-talk"""
        try:
            # Read the raw audio data
            audio_data = await request.body()
            
            if not audio_data:
                return {"success": False, "error": "No audio data received"}
            
            # Process the audio using the non-UI method
            result = await text_app.process_audio_data(audio_data)
            return result
            
        except Exception as e:
            logger.error(f"❌ API audio processing error: {e}")
            return {"success": False, "error": str(e)}
    
    @app.get("/check-voice-result")
    async def check_voice_result():
        """Check for new voice transcription results"""
        try:
            if 'voice_result' in app.storage.user:
                result = app.storage.user['voice_result']
                # Clear the result after reading
                del app.storage.user['voice_result']
                return {"success": True, "result": result}
            else:
                return {"success": False, "message": "No new results"}
        except Exception as e:
            logger.error(f"❌ Error checking voice result: {e}")
            return {"success": False, "error": str(e)}
    
    # Create the UI
    text_app.create_ui()
    
    # Get local IP for display
    local_ip = text_app.get_local_ip()
    
    print("Starting Mobile Text Input Server...")
    print("✅ Cross-device synchronization enabled")
    print("Local access: http://localhost:8080")
    print(f"Network access: http://{local_ip}:8080")
    print(f"Mobile access: Connect your mobile device to the same network and visit http://{local_ip}:8080")
    print("📱 Text syncs across all devices and browser tabs")
    print("Press Ctrl+C to stop the server")
    
    # Run the application
    ui.run(
        host="0.0.0.0",  # Accept connections from any IP
        port=8080,
        title="Mobile Text Input",
        reload=True,
        show=False,  # Don't auto-open browser
        storage_secret="mobile-text-input-secret-key-2024"  # Enable cross-device storage
    )


if __name__ == "__main__" or __name__ == "__mp_main__":
    main() 