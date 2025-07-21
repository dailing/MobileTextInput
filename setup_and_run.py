#!/usr/bin/env python3
"""
Setup and run script for Mobile Text Input Web Application
Uses only standard Python library for maximum compatibility
"""

import sys
import subprocess
from pathlib import Path
from os_detector import os_detector


def get_venv_path():
    """Get the path to the virtual environment in user's home directory"""
    home = Path.home()
    return home / ".webinput_env"


def run_command(command, cwd=None, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command, shell=True, cwd=cwd, capture_output=True, text=True, check=check
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"Error: Python 3.8+ required, " f"found {version.major}.{version.minor}")
        return False
    print(f"Python {version.major}.{version.minor}.{version.micro} - OK")
    return True


def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    venv_path = get_venv_path()

    if venv_path.exists():
        print(f"Virtual environment already exists at {venv_path}")
        return True

    print(f"Creating virtual environment at {venv_path}...")
    success, stdout, stderr = run_command(f"{sys.executable} -m venv {venv_path}")

    if success:
        print("Virtual environment created successfully")
        return True
    else:
        print(f"Failed to create virtual environment: {stderr}")
        return False


def get_venv_python():
    """Get the path to Python executable in virtual environment"""
    venv_path = get_venv_path()

    if os_detector.is_windows:
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def get_venv_pip():
    """Get the path to pip executable in virtual environment"""
    venv_path = get_venv_path()

    if os_detector.is_windows:
        return venv_path / "Scripts" / "pip.exe"
    else:
        return venv_path / "bin" / "pip"


def install_requirements():
    """Install requirements in virtual environment"""
    pip_path = get_venv_pip()

    if not pip_path.exists():
        print(f"Error: pip not found at {pip_path}")
        return False

    # First try to upgrade pip using the USTC mirror
    print("Upgrading pip...")
    run_command(
        f'"{pip_path}" install --upgrade pip '
        f"-i https://mirrors.ustc.edu.cn/pypi/simple",
        check=False,
    )

    print("Installing requirements...")
    success, stdout, stderr = run_command(
        f'"{pip_path}" install -r requirements.txt '
        f"-i https://mirrors.ustc.edu.cn/pypi/simple"
    )

    if success:
        print("Requirements installed successfully")
        return True
    else:
        print(f"Failed to install requirements with USTC mirror: {stderr}")
        print("Trying with default PyPI...")
        # Fallback to default PyPI if USTC mirror fails
        success, stdout, stderr = run_command(
            f'"{pip_path}" install -r requirements.txt'
        )

        if success:
            print("Requirements installed successfully using default PyPI")
            return True
        else:
            print(f"Failed to install requirements: {stderr}")
            return False


def check_requirements_installed():
    """Check if requirements are already installed"""
    pip_path = get_venv_pip()

    if not pip_path.exists():
        return False

    success, stdout, stderr = run_command(f'"{pip_path}" list', check=False)

    if not success:
        return False

    # Check for core required packages
    core_packages = ["nicegui", "pyperclip", "pynput"]
    installed_packages = stdout.lower()

    for package in core_packages:
        if package not in installed_packages:
            return False

    return True


def check_voice_requirements():
    """Check if voice-to-text requirements are installed"""
    pip_path = get_venv_pip()

    if not pip_path.exists():
        return False, []

    success, stdout, stderr = run_command(f'"{pip_path}" list', check=False)

    if not success:
        return False, []

    # Check for voice packages
    voice_packages = ["openai-whisper", "librosa", "soundfile", "pydub"]
    installed_packages = stdout.lower()

    missing_packages = []
    for package in voice_packages:
        # Handle package name variations
        # openai-whisper -> openai_whisper
        package_check = package.replace("-", "_")
        if (
            package not in installed_packages
            and package_check not in installed_packages
        ):
            missing_packages.append(package)

    return len(missing_packages) == 0, missing_packages


def check_gpu_support():
    """Check if GPU support is available"""
    pip_path = get_venv_pip()

    if not pip_path.exists():
        return False, "pip not found"

    success, stdout, stderr = run_command(f'"{pip_path}" list', check=False)

    if not success:
        return False, "Failed to list packages"

    # Check if torch is installed
    if "torch" not in stdout.lower():
        return False, "PyTorch not installed"

    # Test GPU availability
    python_path = get_venv_python()
    gpu_test_script = """
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA device count: {torch.cuda.device_count()}")
    print(f"CUDA device name: {torch.cuda.get_device_name(0)}")
"""

    try:
        success, stdout, stderr = run_command(
            f'"{python_path}" -c "{gpu_test_script}"', check=False
        )

        if success and "CUDA available: True" in stdout:
            return True, stdout.strip()
        else:
            return False, f"CUDA not available: {stderr}"
    except Exception as e:
        return False, f"Error checking GPU: {e}"


def install_torch_with_cuda():
    """Install PyTorch with CUDA support on Windows"""
    if not os_detector.is_windows:
        print("CUDA installation is only supported on Windows")
        return False

    pip_path = get_venv_pip()

    if not pip_path.exists():
        print(f"Error: pip not found at {pip_path}")
        return False

    print("Installing PyTorch with CUDA support...")

    # Install torch with CUDA support
    cuda_command = (
        f'"{pip_path}" install torch torchvision torchaudio '
        f"--index-url https://download.pytorch.org/whl/cu126"
    )

    success, stdout, stderr = run_command(cuda_command, check=False)

    if success:
        print("✅ PyTorch with CUDA installed successfully")
        return True
    else:
        print(f"❌ Failed to install PyTorch with CUDA: {stderr}")
        return False


def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        success, stdout, stderr = run_command("ffmpeg -version", check=False)
        return success
    except Exception:
        return False


def run_application():
    """Run the main application"""
    python_path = get_venv_python()

    if not python_path.exists():
        print(f"Error: Python not found at {python_path}")
        return False

    if not Path("main.py").exists():
        print("Error: main.py not found")
        return False

    # Check voice functionality status
    print("Starting application...")
    print("=" * 60)
    print("Mobile Text Input Web Application")
    print("Access from your mobile device using your computer's IP address")
    print("")

    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    # Run the application (this will block until stopped)
    try:
        subprocess.run([str(python_path), "main.py"], check=True)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Application failed to start: {e}")
        return False


def test_voice_functionality():
    """Test if voice functionality is working"""
    python_path = get_venv_python()

    if not python_path.exists():
        return False

    if not Path("test_voice.py").exists():
        print("⚠️ test_voice.py not found, skipping voice test")
        return True  # Don't fail if test file is missing

    print("🧪 Testing voice functionality...")
    try:
        success, stdout, stderr = run_command(
            f'"{python_path}" test_voice.py', check=False
        )

        if success:
            print("✅ Voice functionality test passed")
            return True
        else:
            print(f"❌ Voice functionality test failed: {stderr}")
            return False
    except Exception as e:
        print(f"❌ Voice test error: {e}")
        return False


def main():
    """Main setup and run function"""
    print("Mobile Text Input Web Application - Setup and Run")
    print("=" * 50)
    # Check Python version
    if not check_python_version():
        return 1

    # Create virtual environment
    if not create_virtual_environment():
        return 1

    # Install core requirements if needed
    if not check_requirements_installed():
        print("Installing core requirements...")
        if not install_requirements():
            return 1
    else:
        print("Core requirements already installed")

    # Check voice requirements
    voice_available, missing_voice = check_voice_requirements()
    ffmpeg_available = check_ffmpeg()

    if not voice_available:
        print("\n" + "=" * 50)
        print("Voice-to-Text Setup (Optional)")
        print("=" * 50)
        print("⚠️ Voice-to-text packages not found")
        print(f"Missing packages: {', '.join(missing_voice)}")
        print("")
        print("To enable voice functionality, run:")
        print(f"  {get_venv_pip()} install {' '.join(missing_voice)}")
        print("")

        # Ask user if they want to install voice packages
        try:
            response = input("Install voice packages now? (y/N): ").strip().lower()
            if response in ["y", "yes"]:
                print("Installing voice packages...")
                pip_path = get_venv_pip()
                voice_packages_str = " ".join(missing_voice)

                # Try with mirror first
                success, stdout, stderr = run_command(
                    f'"{pip_path}" install {voice_packages_str} '
                    f"-i https://mirrors.ustc.edu.cn/pypi/simple",
                    check=False,
                )

                if not success:
                    print("Mirror failed, trying default PyPI...")
                    success, stdout, stderr = run_command(
                        f'"{pip_path}" install {voice_packages_str}', check=False
                    )

                if success:
                    print("✅ Voice packages installed successfully")
                    voice_available = True

                    # Check for GPU support and offer CUDA installation
                    if os_detector.is_windows:
                        print("\n" + "=" * 50)
                        print("GPU Acceleration Setup (Optional)")
                        print("=" * 50)
                        try:
                            gpu_response = (
                                input(
                                    "Install PyTorch with CUDA for GPU acceleration? (y/N): "
                                )
                                .strip()
                                .lower()
                            )
                            if gpu_response in ["y", "yes"]:
                                if install_torch_with_cuda():
                                    print("✅ GPU acceleration enabled")
                                else:
                                    print("⚠️ GPU acceleration installation failed")
                        except (KeyboardInterrupt, EOFError):
                            print("\nSkipping GPU acceleration setup")

                    # Test voice functionality after installation
                    if ffmpeg_available:
                        test_voice_functionality()
                    else:
                        print("⚠️ Install FFmpeg to complete voice setup")
                else:
                    print(f"❌ Failed to install voice packages: {stderr}")
                    print("You can install them manually later")
            else:
                print("Skipping voice package installation")
        except (KeyboardInterrupt, EOFError):
            print("\nSkipping voice package installation")
    else:
        # Voice packages are available, test if requested
        if ffmpeg_available:
            try:
                response = input("Test voice functionality? (Y/n): ").strip().lower()
                if response not in ["n", "no"]:
                    test_voice_functionality()
            except (KeyboardInterrupt, EOFError):
                print("\nSkipping voice test")

        # Check GPU support for existing installations
        gpu_available, gpu_info = check_gpu_support()
        if not gpu_available and os_detector.is_windows:
            print("\n" + "=" * 50)
            print("GPU Acceleration Setup (Optional)")
            print("=" * 50)
            print("⚠️ GPU acceleration not available")
            print("Install PyTorch with CUDA for better performance")
            try:
                gpu_response = (
                    input("Install PyTorch with CUDA for GPU acceleration? (y/N): ")
                    .strip()
                    .lower()
                )
                if gpu_response in ["y", "yes"]:
                    if install_torch_with_cuda():
                        print("✅ GPU acceleration enabled")
                    else:
                        print("⚠️ GPU acceleration installation failed")
            except (KeyboardInterrupt, EOFError):
                print("\nSkipping GPU acceleration setup")

    if not ffmpeg_available:
        print("\n" + "=" * 50)
        print("FFmpeg Setup (Required for Voice)")
        print("=" * 50)
        print("⚠️ FFmpeg not found")
        print("FFmpeg is required for voice-to-text functionality")
        print("")
        print("Install FFmpeg:")
        print("  Windows: choco install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg")
        print("")

    # Final status
    print("\n" + "=" * 50)
    print("Setup Complete")
    print("=" * 50)

    # Run the application
    if not run_application():
        return 1

    return 0


if __name__ == "__main__":
    status = main()
    sys.exit(status)
