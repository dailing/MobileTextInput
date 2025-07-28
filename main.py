#!/usr/bin/env python3
"""
Mobile Text Input Web Application
A web application that allows text input from mobile devices with automatic
clipboard copying and keyboard simulation
"""

from functools import partial
from nicegui import ui, app
import logging
import sys
import tempfile
import os
import asyncio
import json
from datetime import datetime
from pathlib import Path
from fastapi import Request
from typing import List
from instance_manager import create_application_instance_manager
from voice_processor import VoiceProcessor
from key_simulator import create_key_simulator
from mouse_controller import create_mouse_controller
from button_definitions import AVAILABLE_BUTTONS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Text backup configuration
BACKUP_DIR = Path.home() / ".webinput_backups"
BACKUP_FILE = BACKUP_DIR / "voice_text_backup.json"
AUTO_SAVE_FILE = BACKUP_DIR / "auto_save.txt"


def ensure_backup_directory():
    """Ensure backup directory exists"""
    BACKUP_DIR.mkdir(exist_ok=True)
    logger.info(f"📁 Backup directory: {BACKUP_DIR}")


def save_text_backup(text: str, source: str = "manual"):
    """Save text to backup file with timestamp"""
    try:
        ensure_backup_directory()
        
        # Save to auto-save file (latest text)
        with open(AUTO_SAVE_FILE, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Save to backup history with timestamp
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "text": text,
            "text_length": len(text)
        }
        
        # Load existing backups
        backups = []
        if BACKUP_FILE.exists():
            try:
                with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
                    backups = json.load(f)
            except (json.JSONDecodeError, Exception):
                backups = []
        
        # Add new backup
        backups.append(backup_data)
        
        # Keep only last 10 backups to prevent file from growing too large
        backups = backups[-10:]
        
        # Save updated backups
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(backups, f, indent=2, ensure_ascii=False)
            
        logger.info(f"💾 Text backup saved ({len(text)} chars)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save text backup: {e}")
        return False


def load_latest_backup():
    """Load the latest auto-saved text"""
    try:
        if AUTO_SAVE_FILE.exists():
            with open(AUTO_SAVE_FILE, 'r', encoding='utf-8') as f:
                text = f.read()
                logger.info(f"📂 Loaded backup text ({len(text)} chars)")
                return text
    except Exception as e:
        logger.error(f"❌ Failed to load backup: {e}")
    return ""


def get_backup_history():
    """Get list of previous backups"""
    try:
        if BACKUP_FILE.exists():
            with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
                backups = json.load(f)
                return backups[-5:]  # Return last 5 backups
    except Exception as e:
        logger.error(f"❌ Failed to load backup history: {e}")
    return []


# Import voice-to-text libraries
try:
    import torch

    WHISPER_AVAILABLE = True
    TORCH_AVAILABLE = True
    logger.info("✅ OpenAI Whisper loaded successfully")

    # Check for CUDA availability
    if torch.cuda.is_available():
        logger.info("✅ CUDA available - GPU acceleration enabled")
        logger.info(f"🚀 CUDA device count: {torch.cuda.device_count()}")
        logger.info(f"🎯 CUDA device name: {torch.cuda.get_device_name(0)}")
        CUDA_AVAILABLE = True
    else:
        logger.info("💻 CUDA not available - using CPU for voice processing")
        CUDA_AVAILABLE = False

except ImportError as e:
    WHISPER_AVAILABLE = False
    TORCH_AVAILABLE = False
    CUDA_AVAILABLE = False
    logger.warning(f"⚠️ Voice-to-text libraries not available: {e}")

# OS detection is now handled by os_detector module


# Initialize components
voice_processor = VoiceProcessor() if WHISPER_AVAILABLE else None
voice_enabled = WHISPER_AVAILABLE
instance_manager = create_application_instance_manager("Cursor")
storage_key = "shared_text"

# Voice processing lock to prevent race conditions
voice_processing_lock = asyncio.Lock()
voice_request_counter = 0


# Initialize key simulator and mouse controller
# OS detection is now handled centrally by os_detector module
key_simulator = create_key_simulator()
mouse_controller = create_mouse_controller()


def create_all_buttons(show_status) -> List:
    """Create all UI buttons from button definitions

    Args:
        show_status: Function to display status messages to user

    Returns:
        List of created UI buttons
    """

    def handle_button_click(button_config):
        """Handle button click based on configuration"""
        # Execute pre-action if defined
        if button_config.pre_action:
            if not button_config.pre_action():
                logger.info("Pre-action prevented key simulation")
                return

        # Simulate key sequence
        if button_config.key_sequence:
            success = key_simulator.simulate_key_sequence(button_config.key_sequence)
            if success:
                show_status(f"{button_config.name} executed!", "success")
            else:
                show_status(f"Failed to execute {button_config.name}", "error")

    buttons = []
    for button_func in AVAILABLE_BUTTONS:
        config = button_func()
        # Create button with click handler and styling
        button = ui.button(
            config.name,
            on_click=partial(handle_button_click, config),
            color=None,
        ).classes(f"w-24 h-24 bg-blue-500 {config.classes}")
        buttons.append(button)
        logger.info(f"✅ Created button: {config.name} classes: {config.classes}")

    return buttons


@ui.page("/")
def text_input_page():
    """Main page function for text input application"""
    # Initialize state variables
    is_recording = False

    def toggle_voice_recording(voice_button):
        """Toggle voice recording state and trigger JavaScript recording"""
        nonlocal is_recording

        if not voice_enabled:
            show_status("Voice-to-text is not available", "error")
            return

        if not is_recording:
            # Start recording
            is_recording = True
            voice_button.set_text("Recording... (Click to Stop)")
            voice_button.classes(replace="flex-1 p-2 m-1 bg-red-500")
            ui.run_javascript("startRecording();")
        else:
            # Stop recording
            is_recording = False
            voice_button.set_text("🎤 Start Recording")
            voice_button.classes(replace="flex-1 p-2 m-1 bg-primary")
            ui.run_javascript("stopRecording();")

    def show_status(message, status_type="success"):
        """Show status notification to user"""
        if status_type == "success":
            ui.notify(message, type="positive")
        elif status_type == "error":
            ui.notify(message, type="negative")
        else:
            ui.notify(message, type="info")

    def auto_save_text():
        """Auto-save current text to backup"""
        current_text = app.storage.general.get(storage_key, "") or ""
        if current_text.strip():
            if save_text_backup(current_text, "auto_save"):
                return True
        return False

    def recover_latest_text():
        """Recover latest backup text"""
        backup_text = load_latest_backup()
        if backup_text:
            app.storage.general[storage_key] = backup_text
            show_status(f"Recovered text ({len(backup_text)} characters)", "success")
            return True
        else:
            show_status("No backup text found", "info")
            return False

    def restore_backup(backup_data):
        """Restore a specific backup"""
        app.storage.general[storage_key] = backup_data['text']
        show_status(f"Restored backup from {backup_data['timestamp']}", "success")

    def refresh_backup_table():
        """Refresh the backup history table"""
        backup_container.clear()
        backups = get_backup_history()
        
        if backups:
            with backup_container:
                ui.label('Backup History').classes('text-lg font-bold mb-2')
                
                # Create table headers
                with ui.row().classes('w-full border-b pb-2 mb-2'):
                    ui.label('Time').classes('flex-1 font-bold')
                    ui.label('Source').classes('flex-1 font-bold')  
                    ui.label('Text Preview').classes('flex-2 font-bold')
                    ui.label('Action').classes('w-20 font-bold')
                
                # Create table rows
                for backup in reversed(backups):  # Show newest first
                    timestamp = datetime.fromisoformat(backup['timestamp']).strftime('%m-%d %H:%M')
                    source = backup['source'].replace('_', ' ').title()
                    
                    # Truncate text preview to first 50 characters
                    text_preview = backup['text'].replace('\n', ' ').strip()
                    if len(text_preview) > 50:
                        text_preview = text_preview[:50] + '...'
                    
                    with ui.row().classes('w-full border-b py-1 items-center'):
                        ui.label(timestamp).classes('flex-1 text-sm')
                        ui.label(source).classes('flex-1 text-sm')
                        ui.label(text_preview).classes('flex-2 text-sm')
                        ui.button('Restore', 
                                  on_click=lambda b=backup: restore_backup(b)
                                  ).classes('w-16 h-8 bg-blue-500 text-white text-xs')

    def refresh_instances():
        """Refresh and recreate the instance tabs"""
        instance_container.clear()

        if not instance_manager.is_available():
            with instance_container:
                ui.label("Instance manager not available").classes("text-gray-500")
            return

        app_instances = instance_manager.list_instances()

        if app_instances:
            with instance_container:
                with ui.tabs().classes("w-full") as tabs:
                    instance_tabs = {}
                    for instance in app_instances:
                        workspace = instance.get("workspace", "Unknown")
                        tab = ui.tab(workspace)
                        instance_tabs[workspace] = {
                            "tab": tab,
                            "instance": instance,
                        }

                    def on_tab_change(e):
                        selected_workspace = e.args
                        if selected_workspace and selected_workspace in instance_tabs:
                            instance = instance_tabs[selected_workspace]["instance"]
                            instance_id = instance.get("id")
                            instance_manager.focus_instance(instance_id)

                    tabs.on("update:model-value", on_tab_change)
        else:
            with instance_container:
                ui.label("No Cursor instances found").classes("text-gray-500")
                ui.label("Open Cursor and refresh page to detect instances").classes(
                    "text-sm text-gray-400"
                )

    # Create UI elements
    ui.page_title("Mobile Text Input")

    # Instance Management Section
    if instance_manager.is_available():
        instance_container = ui.column().classes("w-full")
        refresh_instances()

    # Main content container
    with ui.column().classes("w-full max-w-2xl mx-auto"):
        # Text input area with direct storage binding
        ui.textarea(placeholder="Type your text here...").props("clearable").bind_value(
            app.storage.general, storage_key
        ).classes("w-full")

        # Voice input section
        with ui.row().classes("w-full"):
            if voice_enabled:
                voice_button = ui.button(
                    "🎤 Start Recording",
                    on_click=lambda: toggle_voice_recording(voice_button),
                ).classes("flex-1 p-2 m-1 bg-primary")

        # Create buttons from configuration
        with ui.row().classes("w-full border justify-center"):
            create_all_buttons(show_status)

        # Define joystick handlers after coordinates is available
        def handle_joystick_start(event):
            """Handle joystick start event"""
            # Call mouse controller on_start method
            mouse_controller.on_start()
            coordinates.set_text("0, 0")

        def handle_joystick_move(event):
            """Handle joystick movement events"""
            # Update joystick coordinates display
            coordinates.set_text(f"{event.x:.3f}, {event.y:.3f}")

            # Call mouse controller on_move method
            mouse_controller.on_move(event.x, event.y)

        def handle_joystick_end(event):
            """Handle joystick release event"""
            coordinates.set_text("0, 0")
            # Call mouse controller on_end method
            mouse_controller.on_end()

        def handle_left_click():
            """Handle left mouse button click"""
            mouse_controller.click_left_button()

        def handle_right_click():
            """Handle right mouse button click"""
            mouse_controller.click_right_button()

        ui.joystick(
            color="blue",
            size=350,
            on_start=handle_joystick_start,
            on_move=handle_joystick_move,
            on_end=handle_joystick_end,
        ).classes("bg-slate-300 w-full")

        # Mouse button controls - split into two halves
        with ui.row().classes("w-full mt-2"):
            ui.button(
                "Left Click",
                on_click=handle_left_click,
            ).classes("flex-1 p-4 m-1 bg-green-500 text-white font-bold")
            
            ui.button(
                "Right Click",
                on_click=handle_right_click,
            ).classes("flex-1 p-4 m-1 bg-red-500 text-white font-bold")

        # Text backup/recovery controls
        with ui.row().classes("w-full mt-2"):
            ui.button("💾 Save Backup", 
                      on_click=lambda: auto_save_text() and show_status("Text backup saved!", "success")
                      ).classes("flex-1 p-2 m-1 bg-green-600 text-white")
            ui.button("📂 Recover Latest", 
                      on_click=recover_latest_text
                      ).classes("flex-1 p-2 m-1 bg-blue-600 text-white")

        # Joystick coordinates
        coordinates = ui.label("0, 0")

        # Backup history table at the bottom
        backup_container = ui.column().classes("w-full mt-4")
        
    # Initialize backup table
    refresh_backup_table()

    # Add voice recording JavaScript if enabled
    if voice_enabled:
        ui.add_head_html(
            """
            <script>
            let mediaRecorder;
            let audioChunks = [];
            let isRecording = false;
            let microphonePermissionGranted = false;
            let audioStream = null;
            
            async function startRecording() {
                if (isRecording) return;
                
                try {
                    // Request microphone permission and start recording
                    audioStream = await navigator.mediaDevices.getUserMedia(
                        { audio: true }
                    );
                    microphonePermissionGranted = true;
                    
                    mediaRecorder = new MediaRecorder(audioStream);
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                    };
                    
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(
                            audioChunks, { type: 'audio/wav' }
                        );
                        const audioData = await audioBlob.arrayBuffer();
                        
                        console.log('🎤 Audio recording completed, sending to backend...');
                        console.log(`📁 Audio data size: ${audioData.byteLength} bytes`);
                        
                        // Send audio data to backend
                        fetch('/process-audio', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/octet-stream',
                            },
                            body: audioData
                        })
                        .then(response => response.json())
                        .then(result => {
                            if (result.success) {
                                console.log(`✅ Voice request #${result.request_id || 'unknown'} completed successfully`);
                                console.log(`📝 Transcribed: "${result.text}"`);
                                console.log(`⏱️ Processing time: ${result.processing_time || 0}s`);
                                console.log(`🌍 Language: ${result.language || 'unknown'}`);
                            } else {
                                console.error(`❌ Voice request #${result.request_id || 'unknown'} failed:`, result.error);
                            }
                        })
                        .catch(error => {
                            console.error('❌ Error processing audio:', error);
                        });
                        
                        // Stop all tracks
                        if (audioStream) {
                            audioStream.getTracks().forEach(
                                track => track.stop()
                            );
                            audioStream = null;
                        }
                        isRecording = false;
                    };
                    
                    mediaRecorder.start();
                    isRecording = true;
                    
                } catch (error) {
                    console.error('Error accessing microphone:', error);
                    microphonePermissionGranted = false;
                }
            }
            
            function stopRecording() {
                if (mediaRecorder && isRecording) {
                    mediaRecorder.stop();
                }
            };
            
            </script>
        """
        )

    # Add API endpoint for processing recorded audio


@app.post("/process-audio")
async def process_audio(request: Request):
    """Handle recorded audio data from push-to-talk with race condition protection"""
    global voice_request_counter
    
    # Assign unique request ID for tracking
    voice_request_counter += 1
    request_id = voice_request_counter
    
    logger.info(f"🎤 Voice request #{request_id} received - checking for audio data")
    
    try:
        audio_data = await request.body()
        if not audio_data:
            logger.warning(f"❌ Voice request #{request_id} failed - no audio data received")
            return {"success": False, "error": "No audio data received"}

        logger.info(f"📁 Voice request #{request_id} - audio data received ({len(audio_data)} bytes)")

        # Process the audio file creation
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name

        logger.info(f"💾 Voice request #{request_id} - temp file created: {temp_file_path}")

        # Use type-safe function call
        transcribe_func = (
            voice_processor.transcribe_audio
            if voice_processor
            else lambda x: {
                "success": False,
                "error": "Voice processing not available",
            }
        )

        # CRITICAL SECTION: Acquire lock to prevent race conditions
        logger.info(f"⏳ Voice request #{request_id} - waiting for processing lock...")
        
        async with voice_processing_lock:
            logger.info(f"🔒 Voice request #{request_id} - LOCK ACQUIRED, starting transcription")
            
            # Read current storage state while locked
            current_text_before = app.storage.general.get(storage_key, "") or ""
            logger.info(f"📖 Voice request #{request_id} - current text length: {len(current_text_before)} chars")
            
            # Process the audio (this is the time-consuming part)
            result = await asyncio.to_thread(lambda: transcribe_func(temp_file_path))
            logger.info(f"🎯 Voice request #{request_id} - transcription completed")

            # Clean up temp file
            try:
                os.unlink(temp_file_path)
                logger.info(f"🗑️ Voice request #{request_id} - temp file cleaned up")
            except OSError:
                logger.warning(f"⚠️ Voice request #{request_id} - failed to clean up temp file")

            if result.get("success"):
                transcribed_text = result["text"]
                if transcribed_text:
                    # Update storage atomically while still locked
                    current_text_after = app.storage.general.get(storage_key, "") or ""
                    
                    # Check if storage was modified during processing (defensive check)
                    if current_text_after != current_text_before:
                        logger.warning(f"⚠️ Voice request #{request_id} - storage changed during processing!")
                        logger.warning(f"   Before: {len(current_text_before)} chars")
                        logger.warning(f"   After: {len(current_text_after)} chars")
                        # Use the current state anyway (most recent)
                        current_text = current_text_after
                    else:
                        current_text = current_text_before
                    
                    new_text = (
                        current_text + "\n" + transcribed_text
                        if current_text
                        else transcribed_text
                    )
                    app.storage.general[storage_key] = new_text
                    
                    logger.info(f"✅ Voice request #{request_id} - storage updated")
                    logger.info(f"   Added: '{transcribed_text[:50]}{'...' if len(transcribed_text) > 50 else ''}'")
                    logger.info(f"   New total length: {len(new_text)} chars")
                    
                    # Auto-save the updated text to backup
                    save_text_backup(new_text, f"voice_transcription_req_{request_id}")
                    
                    logger.info(f"🔓 Voice request #{request_id} - LOCK RELEASED, request completed successfully")
                    
                    return {
                        "success": True,
                        "text": transcribed_text,
                        "processing_time": result.get("processing_time", 0),
                        "language": result.get("language", "unknown"),
                        "request_id": request_id,
                    }
                else:
                    logger.warning(f"⚠️ Voice request #{request_id} - transcription successful but empty text")
            else:
                logger.error(f"❌ Voice request #{request_id} - transcription failed: {result.get('error', 'Unknown error')}")

        logger.error(f"❌ Voice request #{request_id} - failed to process audio")
        return {
            "success": False,
            "error": result.get("error", "Failed to process audio"),
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(f"❌ Voice request #{request_id} - API error: {e}")
        return {"success": False, "error": str(e), "request_id": request_id}


def main():
    """Main function to run the application"""
    ui.run(
        host="0.0.0.0",
        port=8080,
        title="Mobile Text Input",
        reload=False,
        dark=True,
        show=False,
        storage_secret="mobile-text-input-secret-key-2024",
    )


if __name__ == "__main__" or __name__ == "__mp_main__":
    main()
