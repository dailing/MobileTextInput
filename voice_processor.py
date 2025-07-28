"""
Voice Processing Module
Handles voice-to-text processing using OpenAI Whisper with GPU support
"""

import logging
import time
import torch
import whisper
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# Check for CUDA availability
CUDA_AVAILABLE = torch.cuda.is_available()
if CUDA_AVAILABLE:
    logger.info("✅ CUDA available - GPU acceleration enabled")
    logger.info(f"🚀 CUDA device count: {torch.cuda.device_count()}")
    logger.info(f"🎯 CUDA device name: {torch.cuda.get_device_name(0)}")
else:
    logger.info("💻 CUDA not available - using CPU for voice processing")


class VoiceProcessor:
    """Handle voice-to-text processing using OpenAI Whisper with GPU support"""

    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.model_loading = False
        self.device = "cuda" if CUDA_AVAILABLE else "cpu"
        self.supported_formats = {
            ".mp3",
            ".wav",
            ".m4a",
            ".mp4",
            ".mpeg",
            ".mpga",
            ".webm",
            ".ogg",
        }

        logger.info("✅ Whisper available - starting background model load")
        # Start loading the model in a background thread
        import threading

        threading.Thread(target=self.load_model, daemon=True).start()

    def load_model(self):
        """Load the Whisper model with GPU support if available"""
        if self.model_loading or self.model_loaded:
            return

        self.model_loading = True
        try:
            model_size = "medium"  # Balance between accuracy and speed
            logger.info(f"🔄 Loading Whisper {model_size} model on {self.device}...")

            # Load model with device specification
            self.model = whisper.load_model(model_size, device=self.device)
            
            # Ensure model is on correct device (one-time setup)
            if CUDA_AVAILABLE and hasattr(self.model, "to"):
                self.model.to(self.device)
                logger.info(f"🎯 Model moved to device: {self.device}")
            
            self.model_loaded = True

            logger.info(f"✅ Whisper {model_size} model loaded successfully")
            logger.info(f"🎯 Using device: {self.device}")
            logger.info("📝 Model supports: transcription and translation")
            logger.info("🌍 Languages: Supports 99 languages")

            if CUDA_AVAILABLE:
                logger.info("🚀 GPU acceleration enabled for voice processing")
            else:
                logger.info("💻 Using CPU for voice processing")

        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            self.model_loaded = False
        finally:
            self.model_loading = False

    def is_supported_format(self, filename):
        """Check if the audio file format is supported"""
        return Path(filename).suffix.lower() in self.supported_formats

    def transcribe_audio(self, audio_file_path, language=None):
        """
        Transcribe audio file to text with GPU acceleration if available

        Args:
            audio_file_path (str): Path to the audio file
            language (str, optional): Language code (e.g., 'en', 'es', 'fr')

        Returns:
            dict: Transcription result with text and metadata
        """
        # Wait for model to load (with timeout)
        wait_start = time.time()
        while self.model_loading and time.time() - wait_start < 30:  # 30 sec timeout
            time.sleep(0.5)  # Wait in 0.5s intervals

        if self.model_loading:
            return {"success": False, "error": "Model still loading, please try again"}

        if not self.model_loaded:
            return {"success": False, "error": "Whisper model failed to load"}

        if not os.path.exists(audio_file_path):
            return {"success": False, "error": "Audio file not found"}

        if not self.is_supported_format(audio_file_path):
            return {"success": False, "error": "Unsupported audio format"}

        try:
            logger.info(f"🎤 Starting transcription: {Path(audio_file_path).name}")
            logger.info(f"🎯 Using device: {self.device}")
            start_time = time.time()

            # Transcribe the audio with device specification
            options = {}
            if language:
                options["language"] = language

            # Model is already on correct device from initial loading
            result = self.model.transcribe(audio_file_path, **options)

            processing_time = time.time() - start_time
            text = result["text"].strip()

            logger.info(f"✅ Transcription completed in {processing_time:.2f} seconds")
            logger.info(f"🎯 Processed on: {self.device}")
            logger.info(
                f"📝 Transcribed text: '{text[:100]}{'...' if len(text) > 100 else ''}'"
            )
            logger.info(f"🌍 Detected language: {result.get('language', 'unknown')}")

            return {
                "success": True,
                "text": text,
                "language": result.get("language"),
                "processing_time": processing_time,
                "duration": result.get("duration", 0),
                "device": self.device,
            }

        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            return {"success": False, "error": str(e)}
