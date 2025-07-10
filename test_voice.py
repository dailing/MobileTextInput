#!/usr/bin/env python3
"""
Test script for voice-to-text functionality
"""

import sys
import tempfile
import os

def test_whisper_installation():
    """Test if Whisper is properly installed"""
    try:
        import whisper
        print("✅ OpenAI Whisper imported successfully")
        
        # Test model loading
        print("🔄 Loading Whisper base model...")
        model = whisper.load_model("base")
        print("✅ Whisper base model loaded successfully")
        
        # Get model info
        print(f"📝 Model device: {model.device}")
        print(f"📝 Model dimensions: {model.dims}")
        
        return True
    except ImportError:
        print("❌ OpenAI Whisper not found")
        print("📦 Install with: pip install openai-whisper")
        return False
    except Exception as e:
        print(f"❌ Error loading Whisper: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Voice-to-Text Setup")
    print("=" * 40)
    
    result = test_whisper_installation()
    
    if result:
        print("\n🎉 Voice-to-text should work properly!")
    else:
        print("\n⚠️ Please install missing dependencies.")
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main()) 