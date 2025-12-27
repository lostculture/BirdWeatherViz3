#!/usr/bin/env python3
"""
BirdWeatherViz3 Test Script
Automated testing script for local development.

Version: 1.0.0
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

class Colors:
    """Terminal colors for output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

def print_success(msg):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def check_command(command, name):
    """Check if a command is available."""
    try:
        subprocess.run(
            [command, '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print_success(f"{name} is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error(f"{name} is NOT installed")
        return False

def check_dependencies():
    """Check if all required dependencies are installed."""
    print_header("Checking Dependencies")

    all_ok = True

    # Check Python
    if sys.version_info < (3, 11):
        print_error(f"Python 3.11+ required (found {sys.version_info.major}.{sys.version_info.minor})")
        all_ok = False
    else:
        print_success(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    # Check Node.js
    all_ok &= check_command('node', 'Node.js')

    # Check npm
    all_ok &= check_command('npm', 'npm')

    return all_ok

def setup_backend():
    """Set up backend environment."""
    print_header("Setting Up Backend")

    backend_dir = Path(__file__).parent / 'backend'
    env_file = backend_dir / '.env'
    env_example = backend_dir / '.env.example'

    # Create .env if it doesn't exist
    if not env_file.exists() and env_example.exists():
        print_info("Creating .env from .env.example...")
        import shutil
        shutil.copy(env_example, env_file)
        print_success(".env file created")
    elif env_file.exists():
        print_success(".env file already exists")

    # Check if requirements are installed
    print_info("Checking Python dependencies...")
    try:
        import fastapi
        import sqlalchemy
        import plotly
        print_success("Backend dependencies are installed")
    except ImportError as e:
        print_warning("Some backend dependencies missing")
        print_info("Run: pip install -r backend/requirements.txt")
        return False

    return True

def setup_frontend():
    """Set up frontend environment."""
    print_header("Setting Up Frontend")

    frontend_dir = Path(__file__).parent / 'frontend'
    env_file = frontend_dir / '.env'
    env_example = frontend_dir / '.env.example'
    node_modules = frontend_dir / 'node_modules'

    # Create .env if it doesn't exist
    if not env_file.exists() and env_example.exists():
        print_info("Creating .env from .env.example...")
        import shutil
        shutil.copy(env_example, env_file)
        print_success(".env file created")
    elif env_file.exists():
        print_success(".env file already exists")

    # Check if node_modules exists
    if not node_modules.exists():
        print_warning("node_modules not found")
        print_info("Installing frontend dependencies...")
        try:
            subprocess.run(
                ['npm', 'install'],
                cwd=frontend_dir,
                check=True
            )
            print_success("Frontend dependencies installed")
        except subprocess.CalledProcessError:
            print_error("Failed to install frontend dependencies")
            return False
    else:
        print_success("node_modules already exists")

    return True

def start_backend():
    """Start the backend server."""
    print_header("Starting Backend Server")

    backend_dir = Path(__file__).parent / 'backend'

    print_info("Starting uvicorn on http://localhost:8000...")

    # Start backend in background
    process = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000'],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for backend to start
    print_info("Waiting for backend to start...")
    time.sleep(3)

    # Check if backend is running
    try:
        import urllib.request
        response = urllib.request.urlopen('http://localhost:8000/api/v1/health')
        if response.status == 200:
            print_success("Backend is running at http://localhost:8000")
            print_info("API docs available at http://localhost:8000/api/v1/docs")
            return process
    except Exception as e:
        print_error(f"Backend failed to start: {e}")
        process.kill()
        return None

    return process

def start_frontend():
    """Start the frontend dev server."""
    print_header("Starting Frontend Dev Server")

    frontend_dir = Path(__file__).parent / 'frontend'

    print_info("Starting Vite dev server on http://localhost:3000...")

    # Start frontend in background
    process = subprocess.Popen(
        ['npm', 'run', 'dev'],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for frontend to start
    print_info("Waiting for frontend to start...")
    time.sleep(5)

    # Check if frontend is running
    try:
        import urllib.request
        response = urllib.request.urlopen('http://localhost:3000')
        if response.status == 200:
            print_success("Frontend is running at http://localhost:3000")
            return process
    except Exception as e:
        print_warning(f"Frontend might not be ready yet: {e}")
        print_info("It may take a few more seconds to compile...")
        return process

    return process

def main():
    """Main test script."""
    print_header("BirdWeatherViz3 Test Script")

    # Check dependencies
    if not check_dependencies():
        print_error("Please install missing dependencies before continuing")
        sys.exit(1)

    # Setup backend
    if not setup_backend():
        print_error("Backend setup failed")
        sys.exit(1)

    # Setup frontend
    if not setup_frontend():
        print_error("Frontend setup failed")
        sys.exit(1)

    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print_error("Failed to start backend")
        sys.exit(1)

    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print_error("Failed to start frontend")
        backend_process.kill()
        sys.exit(1)

    # Open browser
    print_header("Opening Browser")
    print_info("Opening http://localhost:3000 in your browser...")
    time.sleep(2)
    webbrowser.open('http://localhost:3000')

    # Keep running
    print_header("Servers Running")
    print_success("Backend: http://localhost:8000")
    print_success("Frontend: http://localhost:3000")
    print_success("API Docs: http://localhost:8000/api/v1/docs")
    print()
    print_warning("Press Ctrl+C to stop all servers")

    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        print_header("Shutting Down")
        print_info("Stopping servers...")
        backend_process.kill()
        frontend_process.kill()
        print_success("All servers stopped")

if __name__ == '__main__':
    main()
