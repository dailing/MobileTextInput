#!/usr/bin/env python3
"""
Setup and run script for Mobile Text Input Web Application
Uses only standard Python library for maximum compatibility
"""

import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, cwd=None, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            check=check
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"Error: Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print(f"Python {version.major}.{version.minor}.{version.micro} - OK")
    return True


def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("Virtual environment already exists")
        return True
    
    print("Creating virtual environment...")
    success, stdout, stderr = run_command(f"{sys.executable} -m venv venv")
    
    if success:
        print("Virtual environment created successfully")
        return True
    else:
        print(f"Failed to create virtual environment: {stderr}")
        return False


def get_venv_python():
    """Get the path to Python executable in virtual environment"""
    system = platform.system().lower()
    
    if system == "windows":
        return Path("venv") / "Scripts" / "python.exe"
    else:
        return Path("venv") / "bin" / "python"


def get_venv_pip():
    """Get the path to pip executable in virtual environment"""
    system = platform.system().lower()
    
    if system == "windows":
        return Path("venv") / "Scripts" / "pip.exe"
    else:
        return Path("venv") / "bin" / "pip"


def install_requirements():
    """Install requirements in virtual environment"""
    pip_path = get_venv_pip()
    
    if not pip_path.exists():
        print(f"Error: pip not found at {pip_path}")
        return False
    
    # First try to upgrade pip using the USTC mirror
    print("Upgrading pip...")
    run_command(f'"{pip_path}" install --upgrade pip -i https://mirrors.ustc.edu.cn/pypi/simple', check=False)
    
    print("Installing requirements...")
    success, stdout, stderr = run_command(f'"{pip_path}" install -r requirements.txt -i https://mirrors.ustc.edu.cn/pypi/simple')
    
    if success:
        print("Requirements installed successfully")
        return True
    else:
        print(f"Failed to install requirements with USTC mirror: {stderr}")
        print("Trying with default PyPI...")
        # Fallback to default PyPI if USTC mirror fails
        success, stdout, stderr = run_command(f'"{pip_path}" install -r requirements.txt')
        
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
    
    # Check for required packages
    required_packages = ['nicegui', 'pyperclip', 'pynput']
    installed_packages = stdout.lower()
    
    for package in required_packages:
        if package not in installed_packages:
            return False
    
    return True


def run_application():
    """Run the main application"""
    python_path = get_venv_python()
    
    if not python_path.exists():
        print(f"Error: Python not found at {python_path}")
        return False
    
    if not Path("main.py").exists():
        print("Error: main.py not found")
        return False
    
    print("Starting application...")
    print("=" * 50)
    print("Mobile Text Input Web Application")
    print("Access from your mobile device using your computer's IP address")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Run the application (this will block until stopped)
    try:
        subprocess.run([str(python_path), "main.py"], check=True)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Application failed to start: {e}")
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
    
    # Install requirements if needed
    if not check_requirements_installed():
        print("Installing requirements...")
        if not install_requirements():
            return 1
    else:
        print("Requirements already installed")
    
    # Run the application
    if not run_application():
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 