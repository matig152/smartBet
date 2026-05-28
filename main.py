import subprocess
import sys
import os
import time

def install_dependencies():
    """
    Install all dependencies from requirements.txt and npm packages in ui directory
    """
    requirements_file = "requirements.txt"
    ui_dir = "ui"
    
    if not os.path.exists(requirements_file):
        print(f"Error: {requirements_file} not found in the current directory.")
        return False
    
    # Install Python dependencies
    print(f"Installing Python dependencies from {requirements_file}...")
    print("-" * 50)
    
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        print("-" * 50)
        print("✓ Python dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print("-" * 50)
        print(f"✗ Error installing Python dependencies: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False
    
    # Install npm dependencies in ui subdirectory
    if os.path.isdir(ui_dir):
        node_modules = os.path.join(ui_dir, "node_modules")
        
        # Check if node_modules already exists
        if os.path.exists(node_modules) and os.path.isdir(node_modules):
            print(f"\n✓ npm dependencies already installed in {ui_dir}")
            print("Skipping npm install...")
            return True
        
        print(f"\nInstalling npm dependencies in {ui_dir}...")
        print("-" * 50)
        
        try:
            # Fresh install
            print("Installing npm dependencies...")
            subprocess.check_call(
                "npm install",
                cwd=ui_dir,
                stdout=sys.stdout,
                stderr=sys.stderr,
                shell=True
            )
            print("-" * 50)
            print(f"✓ npm dependencies installed successfully in {ui_dir}!")
            return True
        except subprocess.CalledProcessError as e:
            print("-" * 50)
            print(f"✗ Error installing npm dependencies in {ui_dir}: {e}")
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    else:
        print(f"Warning: {ui_dir} directory not found. Skipping npm install.")
        return True

def start_application():
    """
    Start the main application after installing dependencies
    """
    print("Starting the application...")
    
    processes = []

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Start backend server
    print("\n[1/2] Starting backend server (backend/server.py)...")
    try:
        backend_process = subprocess.Popen(
            [sys.executable, "backend/server.py"],
            stderr=subprocess.STDOUT,
            start_new_session=True  # keeps process alive after terminal closes
        )
        processes.append(("Backend Server", backend_process))
        print(f"✓ Backend server started with PID {backend_process.pid}")
    except Exception as e:
        print(f"✗ Error starting backend server: {e}")
        return
    
    # Wait a moment for server to start
    time.sleep(2)
    
    # Start npm app in ui directory
    print("\n[2/2] Starting React app (npm start in ui/)...")
    if os.path.isdir("ui"):
        try:
            npm_process = subprocess.Popen(
                "npm start",
                cwd="ui",
                stderr=subprocess.STDOUT,
                shell=True,
                start_new_session=True  # keeps process alive after terminal closes
            )
            processes.append(("React App", npm_process))
            print(f"✓ React app started with PID {npm_process.pid}")
            
            # Wait for React app to start, then open browser
            print("\nWaiting for React app to initialize...")
            time.sleep(5)
            
        except Exception as e:
            print(f"✗ Error starting React app: {e}")
            return
    else:
        print("✗ Error: ui directory not found")
        return
    
    print("\n" + "="*50)
    print("All services started successfully!")
    print("="*50)

    try:
        # Keep the manager script alive
        while True:
            time.sleep(5)

            # Optional: monitor processes
            for name, process in processes:
                if process.poll() is not None:
                    print(f"\n⚠ {name} exited with code {process.returncode}")

    except KeyboardInterrupt:
        print("\n\nStopping all processes...")

        for name, process in processes:
            try:
                process.terminate()
                print(f"Stopped {name} (PID {process.pid})")
            except:
                pass

    print("Creating database...")
    subprocess.check_call(
            [sys.executable, "init_db.py"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )

if __name__ == "__main__":
    success = install_dependencies()
    if success:
        start_application()
    sys.exit(0 if success else 1)
